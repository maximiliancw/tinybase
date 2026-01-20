"""
Function deployment and validation module.

Handles uploading, validating, and versioning of function files with
comprehensive security and consistency checks.
"""

import ast
import hashlib
import keyword
import re
from pathlib import Path
from uuid import UUID

from sqlmodel import Session, select

from tinybase.db.models import FunctionVersion


class FunctionValidationError(Exception):
    """Raised when function validation fails."""

    pass


def calculate_content_hash(content: str) -> str:
    """
    Calculate SHA256 hash of file content.

    Args:
        content: File content string

    Returns:
        SHA256 hash as hexadecimal string
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def validate_filename(filename: str) -> str:
    """
    Validate function filename.

    Args:
        filename: Function filename (e.g., "my_func.py")

    Returns:
        Base name without .py extension

    Raises:
        FunctionValidationError: If filename is invalid
    """
    # Must end with .py
    if not filename.endswith(".py"):
        raise FunctionValidationError("Filename must end with .py")

    # Remove .py extension
    base_name = filename[:-3]

    # Check for path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise FunctionValidationError("Filename cannot contain path traversal characters")

    # Must be a valid Python identifier
    if not base_name.isidentifier():
        raise FunctionValidationError(
            f"Filename '{base_name}' must be a valid Python identifier (alphanumeric + underscores, no leading numbers)"
        )

    # Cannot be a Python keyword
    if keyword.iskeyword(base_name):
        raise FunctionValidationError(f"Filename '{base_name}' cannot be a Python keyword")

    # Reserved names
    reserved = ["__init__", "test", "__pycache__"]
    if base_name in reserved:
        raise FunctionValidationError(f"Filename '{base_name}' is reserved")

    return base_name


def validate_encoding(content: str) -> None:
    """
    Validate content encoding.

    Args:
        content: File content

    Raises:
        FunctionValidationError: If encoding is invalid
    """
    try:
        content.encode("utf-8")
    except UnicodeEncodeError as e:
        raise FunctionValidationError(f"Content must be valid UTF-8: {e}")


def validate_syntax(content: str) -> ast.Module:
    """
    Validate Python syntax and return AST.

    Args:
        content: Python source code

    Returns:
        Parsed AST module

    Raises:
        FunctionValidationError: If syntax is invalid
    """
    try:
        tree = ast.parse(content)
        return tree
    except SyntaxError as e:
        raise FunctionValidationError(f"Invalid Python syntax at line {e.lineno}: {e.msg}")


def check_sdk_import(tree: ast.Module) -> bool:
    """
    Check if file imports tinybase_sdk.

    Args:
        tree: Parsed AST module

    Returns:
        True if SDK is imported

    Raises:
        FunctionValidationError: If SDK is not imported
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "tinybase_sdk" or alias.name.startswith("tinybase_sdk."):
                    return True
        elif isinstance(node, ast.ImportFrom):
            if node.module and (node.module == "tinybase_sdk" or node.module.startswith("tinybase_sdk.")):
                return True

    raise FunctionValidationError("File must import tinybase_sdk")


def extract_register_decorator(tree: ast.Module) -> str:
    """
    Extract function name from @register decorator.

    Args:
        tree: Parsed AST module

    Returns:
        Function name from @register(name="...")

    Raises:
        FunctionValidationError: If @register decorator not found or invalid
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                # Check for @register(name="...")
                if isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Name) and decorator.func.id == "register":
                        # Find the 'name' keyword argument
                        for keyword in decorator.keywords:
                            if keyword.arg == "name":
                                if isinstance(keyword.value, ast.Constant):
                                    return str(keyword.value.value)

    raise FunctionValidationError("File must contain @register decorator with name parameter")


def scan_dangerous_imports(tree: ast.Module) -> list[str]:
    """
    Scan for potentially dangerous imports.

    Args:
        tree: Parsed AST module

    Returns:
        List of warning messages for suspicious imports
    """
    warnings = []
    dangerous_modules = {
        "os.system",
        "subprocess",
        "eval",
        "exec",
        "compile",
        "__import__",
        "importlib.import_module",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if any(dangerous in alias.name for dangerous in dangerous_modules):
                    warnings.append(f"Potentially dangerous import: {alias.name}")

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for dangerous in dangerous_modules:
                    if dangerous in node.module:
                        warnings.append(f"Potentially dangerous import from: {node.module}")

        # Check for direct calls to eval/exec/compile
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ["eval", "exec", "compile"]:
                warnings.append(f"Direct call to {node.func.id}()")

    return warnings


def validate_function_file(filename: str, content: str, max_size_bytes: int = 1048576) -> tuple[str, list[str]]:
    """
    Comprehensive validation of function file.

    Performs all validation checks:
    1. Filename validation
    2. File size check
    3. UTF-8 encoding validation
    4. Python syntax validation
    5. SDK import detection
    6. @register decorator extraction
    7. Function name consistency check
    8. Dangerous import scanning

    Args:
        filename: Function filename (e.g., "my_func.py")
        content: File content
        max_size_bytes: Maximum allowed file size (default 1MB)

    Returns:
        Tuple of (function_name, warnings)
        - function_name: Name extracted from @register decorator
        - warnings: List of security/validation warnings

    Raises:
        FunctionValidationError: If any validation check fails
    """
    # 1. Validate filename
    base_name = validate_filename(filename)

    # 2. Check file size
    content_bytes = content.encode("utf-8")
    if len(content_bytes) > max_size_bytes:
        raise FunctionValidationError(
            f"File size ({len(content_bytes)} bytes) exceeds maximum ({max_size_bytes} bytes)"
        )

    # 3. Validate encoding
    validate_encoding(content)

    # 4. Validate Python syntax
    tree = validate_syntax(content)

    # 5. Check SDK import
    check_sdk_import(tree)

    # 6. Extract function name from @register
    function_name = extract_register_decorator(tree)

    # 7. Verify function name matches filename
    if function_name != base_name:
        raise FunctionValidationError(
            f"Function name '{function_name}' in @register decorator must match filename '{base_name}'"
        )

    # 8. Scan for dangerous imports
    warnings = scan_dangerous_imports(tree)

    return function_name, warnings


def write_function_file(functions_dir: Path, filename: str, content: str) -> Path:
    """
    Write function file to disk, overwriting if exists.

    Args:
        functions_dir: Functions directory path
        filename: Function filename
        content: File content

    Returns:
        Path to written file
    """
    file_path = functions_dir / filename
    file_path.write_text(content, encoding="utf-8")
    return file_path


def get_or_create_version(
    session: Session,
    function_name: str,
    content_hash: str,
    file_size: int,
    deployed_by_user_id: UUID | None,
    notes: str | None = None,
) -> tuple[FunctionVersion, bool]:
    """
    Get existing version or create new one.

    Args:
        session: Database session
        function_name: Function name
        content_hash: SHA256 hash of content
        file_size: File size in bytes
        deployed_by_user_id: ID of user deploying
        notes: Optional deployment notes

    Returns:
        Tuple of (version, is_new)
        - version: FunctionVersion instance
        - is_new: True if newly created, False if existing
    """
    # Check if version already exists
    stmt = select(FunctionVersion).where(
        FunctionVersion.function_name == function_name, FunctionVersion.content_hash == content_hash
    )
    existing = session.exec(stmt).first()

    if existing:
        return existing, False

    # Create new version
    version = FunctionVersion(
        function_name=function_name,
        content_hash=content_hash,
        file_size=file_size,
        deployed_by_user_id=deployed_by_user_id,
        notes=notes,
    )
    session.add(version)
    session.commit()
    session.refresh(version)

    return version, True


def get_current_function_version(
    session: Session, function_name: str, file_path: str
) -> FunctionVersion | None:
    """
    Get the version record for currently deployed function.

    Args:
        session: Database session
        function_name: Function name
        file_path: Path to function file

    Returns:
        FunctionVersion instance or None if not found
    """
    try:
        # Read file and calculate hash
        content = Path(file_path).read_text(encoding="utf-8")
        content_hash = calculate_content_hash(content)

        # Query for matching version
        stmt = select(FunctionVersion).where(
            FunctionVersion.function_name == function_name, FunctionVersion.content_hash == content_hash
        )
        return session.exec(stmt).first()
    except Exception:
        # If file can't be read or version not found, return None
        return None
