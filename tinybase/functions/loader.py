"""
Function module loader.

Handles loading user-defined functions from the functions package directory.
Supports uv's single-file script feature with inline dependencies using uv run --script.
"""

import importlib.util
import logging
import re
import subprocess
import sys
from pathlib import Path


def _has_uv_inline_dependencies(file_path: Path) -> bool:
    """
    Check if a file has uv inline script dependencies.
    
    Looks for the dependency block format:
    # /// script
    # dependencies = [...]
    # ///
    
    Args:
        file_path: Path to the Python file
    
    Returns:
        True if inline dependencies are found, False otherwise
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        # Pattern to match uv inline dependency block
        pattern = r'# ///\s*script\s*\n(.*?)# ///'
        match = re.search(pattern, content, re.DOTALL)
        return match is not None
    except Exception:
        return False


def _load_with_uv_dependencies(file_path: Path) -> bool:
    """
    Load a function file that has uv inline script dependencies.
    
    Extracts dependencies from the inline metadata block and installs them
    using uv pip install to the current Python environment, then imports
    the module normally.
    
    This approach ensures dependencies are available in the current process
    when we import the module, which is necessary for the @register decorator
    to work correctly with the global registry.
    
    Args:
        file_path: Path to the Python file to load
    
    Returns:
        True if the file was loaded successfully, False otherwise
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Extract dependencies from the inline metadata block
        # Format: # /// script\n# dependencies = [...]\n# ///
        
        # Extract dependencies from the file
        content = file_path.read_text(encoding="utf-8")
        pattern = r'# ///\s*script\s*\n(.*?)# ///'
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            return False
        
        deps_block = match.group(1)
        deps_pattern = r'dependencies\s*=\s*\[(.*?)\]'
        deps_match = re.search(deps_pattern, deps_block, re.DOTALL)
        
        if not deps_match:
            return False
        
        deps_str = deps_match.group(1)
        # Parse dependencies
        deps = []
        deps_str = re.sub(r'#.*$', '', deps_str, flags=re.MULTILINE)
        
        current_dep = ""
        in_quotes = False
        quote_char = None
        
        for char in deps_str:
            if char in ('"', "'") and not in_quotes:
                in_quotes = True
                quote_char = char
                current_dep += char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
                current_dep += char
            elif char == ',' and not in_quotes:
                dep = current_dep.strip().strip('"\'')
                if dep:
                    deps.append(dep)
                current_dep = ""
            else:
                current_dep += char
        
        if current_dep.strip():
            dep = current_dep.strip().strip('"\'')
            if dep:
                deps.append(dep)
        
        if not deps:
            return False
        
        # Install dependencies using uv pip install to the current environment
        # uv will automatically detect the current Python environment (venv or system)
        # This ensures they're available when we import the module
        cmd = ["uv", "pip", "install"] + deps
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        
        if result.returncode != 0:
            logger.error(
                f"Failed to install dependencies for {file_path.name}: "
                f"{result.stderr}"
            )
            return False
        
        # Now import the module normally (dependencies are installed)
        return _load_module_directly(file_path)
        
    except Exception as e:
        logger.error(f"Error loading {file_path} with uv dependencies: {e}")
        return False


def _load_module_directly(file_path: Path) -> bool:
    """
    Load a Python module directly without special dependency handling.
    
    Args:
        file_path: Path to the Python file to load
    
    Returns:
        True if the file was loaded successfully, False otherwise
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Create a unique module name based on file path
    module_name = f"tinybase_functions_{file_path.stem}"
    
    # Remove existing module if it was previously loaded
    if module_name in sys.modules:
        del sys.modules[module_name]
    
    try:
        # Load the module from file
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return False
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        return True
    except Exception as e:
        logger.error(f"Error loading functions from {file_path}: {e}")
        return False


def load_functions_from_file(file_path: str | Path) -> bool:
    """
    Load functions from a single Python file.
    
    The file is imported as a module, which triggers any @register
    decorators to register their functions with the global registry.
    
    Supports uv's single-file script feature by detecting inline dependencies
    and installing them using uv pip install before loading the module.
    
    Args:
        file_path: Path to the Python file to load
    
    Returns:
        True if the file was loaded successfully, False otherwise
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return False
    
    if not file_path.suffix == ".py":
        return False
    
    # Check for uv inline dependencies
    if _has_uv_inline_dependencies(file_path):
        # Use uv to handle dependencies
        return _load_with_uv_run_script(file_path)
    else:
        # No inline dependencies, load directly
        return _load_module_directly(file_path)


def ensure_functions_package(dir_path: Path) -> bool:
    """
    Ensure the functions directory exists and has an __init__.py file.
    
    Args:
        dir_path: Path to the functions directory
    
    Returns:
        True if the package is ready, False otherwise
    """
    # Create directory if it doesn't exist
    dir_path.mkdir(parents=True, exist_ok=True)
    
    # Create __init__.py if it doesn't exist
    init_file = dir_path / "__init__.py"
    if not init_file.exists():
        init_file.write_text(
            '"""\n'
            "TinyBase Functions Package\n"
            "\n"
            "User-defined functions should be placed in individual files within this package.\n"
            "Each function file can use uv's single-file script feature to define inline dependencies.\n"
            "\n"
            "Example:\n"
            "    # /// script\n"
            "    # dependencies = [\n"
            "    #   \"requests>=2.31.0\",\n"
            "    # ]\n"
            "    # ///\n"
            '"""\n'
        )
    
    return True


def load_functions_from_directory(dir_path: str | Path) -> int:
    """
    Load functions from all Python files in the functions package directory.
    
    Ensures the directory is a proper Python package (has __init__.py).
    Recursively searches for .py files and loads them as modules.
    Files starting with underscore (_) are skipped.
    
    Args:
        dir_path: Path to the functions directory
    
    Returns:
        Number of files successfully loaded
    """
    dir_path = Path(dir_path)
    
    # Ensure the directory exists and is a package
    if not ensure_functions_package(dir_path):
        return 0
    
    loaded_count = 0
    
    # Find all Python files
    for py_file in dir_path.rglob("*.py"):
        # Skip __init__.py and private modules
        if py_file.name.startswith("_"):
            continue
        
        if load_functions_from_file(py_file):
            loaded_count += 1
    
    return loaded_count


def load_functions_from_settings() -> int:
    """
    Load functions from the functions package directory.
    
    The functions_path setting specifies the directory containing function files.
    Each function should be in its own file within this package.
    
    Returns:
        Total number of files loaded
    """
    from tinybase.config import settings
    
    config = settings()
    
    # Load from functions package directory only
    functions_path = Path(config.functions_path)
    return load_functions_from_directory(functions_path)

