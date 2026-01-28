"""
Extension installer.

Handles installing extensions from GitHub repositories:
- Cloning repositories
- Validating extension manifests
- Installing Python dependencies
- Managing extension metadata
"""

import logging
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from sqlmodel import Session

    from tinybase.db.models import Extension

# Handle tomli import for Python < 3.11
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

logger = logging.getLogger(__name__)


@dataclass
class ExtensionManifest:
    """Parsed extension.toml manifest."""

    name: str
    version: str
    description: str | None = None
    author: str | None = None
    entry_point: str = "main.py"


class InstallError(Exception):
    """Raised when extension installation fails."""

    pass


def parse_github_url(url: str) -> tuple[str, str, str | None]:
    """
    Parse a GitHub URL into owner, repo, and optional branch/tag.

    Supports formats:
    - https://github.com/owner/repo
    - https://github.com/owner/repo.git
    - https://github.com/owner/repo/tree/branch
    - github.com/owner/repo
    - owner/repo (assumes GitHub)

    Args:
        url: GitHub URL or shorthand.

    Returns:
        Tuple of (owner, repo, branch_or_tag).

    Raises:
        InstallError: If URL format is invalid.
    """
    # Normalize URL
    url = url.strip()

    # Handle shorthand format (owner/repo)
    if re.match(r"^[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+$", url):
        parts = url.split("/")
        return parts[0], parts[1], None

    # Remove .git suffix if present
    if url.endswith(".git"):
        url = url[:-4]

    # Parse full GitHub URL
    patterns = [
        # https://github.com/owner/repo/tree/branch
        r"(?:https?://)?github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+)/tree/([a-zA-Z0-9_.-]+)",
        # https://github.com/owner/repo
        r"(?:https?://)?github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+)",
    ]

    for pattern in patterns:
        match = re.match(pattern, url)
        if match:
            groups = match.groups()
            owner = groups[0]
            repo = groups[1]
            branch = groups[2] if len(groups) > 2 else None
            return owner, repo, branch

    raise InstallError(f"Invalid GitHub URL format: {url}")


def validate_manifest(manifest_path: Path) -> ExtensionManifest:
    """
    Validate and parse an extension.toml manifest.

    Args:
        manifest_path: Path to extension.toml file.

    Returns:
        Parsed ExtensionManifest.

    Raises:
        InstallError: If manifest is invalid.
    """
    if not manifest_path.exists():
        raise InstallError(f"Manifest not found: {manifest_path}")

    try:
        with open(manifest_path, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        raise InstallError(f"Failed to parse manifest: {e}")

    # Get extension section
    ext_data = data.get("extension", {})

    # Validate required fields
    if "name" not in ext_data:
        raise InstallError("Manifest missing required field: name")
    if "version" not in ext_data:
        raise InstallError("Manifest missing required field: version")

    # Validate name format (alphanumeric with hyphens)
    name = ext_data["name"]
    if not re.match(r"^[a-z][a-z0-9-]*$", name):
        raise InstallError(
            f"Invalid extension name '{name}'. "
            "Must be lowercase alphanumeric with hyphens, starting with a letter."
        )

    return ExtensionManifest(
        name=ext_data["name"],
        version=ext_data["version"],
        description=ext_data.get("description"),
        author=ext_data.get("author"),
        entry_point=ext_data.get("entry_point", "main.py"),
    )


def clone_repository(url: str, target_dir: Path, branch: str | None = None) -> None:
    """
    Clone a Git repository.

    Args:
        url: Git repository URL.
        target_dir: Target directory for clone.
        branch: Optional branch or tag to checkout.

    Raises:
        InstallError: If clone fails.
    """
    # Ensure target directory doesn't exist
    if target_dir.exists():
        shutil.rmtree(target_dir)

    # Build git clone command
    cmd = ["git", "clone", "--depth", "1"]
    if branch:
        cmd.extend(["--branch", branch])
    cmd.extend([url, str(target_dir)])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
        )
        if result.returncode != 0:
            raise InstallError(f"Git clone failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        raise InstallError("Git clone timed out")
    except FileNotFoundError:
        raise InstallError("Git is not installed or not in PATH")


def install_dependencies(extension_dir: Path) -> None:
    """
    Install Python dependencies from requirements.txt if present.

    Args:
        extension_dir: Path to extension directory.

    Raises:
        InstallError: If dependency installation fails.
    """
    requirements_file = extension_dir / "requirements.txt"

    if not requirements_file.exists():
        logger.debug(f"No requirements.txt found in {extension_dir}")
        return

    logger.info(f"Installing dependencies from {requirements_file}")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        if result.returncode != 0:
            raise InstallError(f"Dependency installation failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        raise InstallError("Dependency installation timed out")


def install_extension(
    session: "Session",
    repo_url: str,
    user_id: UUID | None = None,
) -> "Extension":
    """
    Install an extension from a GitHub repository.

    Args:
        session: Database session.
        repo_url: GitHub repository URL.
        user_id: ID of user performing the installation.

    Returns:
        Created Extension model instance.

    Raises:
        InstallError: If installation fails.
    """
    from sqlmodel import select

    from tinybase.db.models import Extension
    from tinybase.extensions.loader import get_extensions_directory, load_extension_module

    # Parse GitHub URL
    owner, repo, branch = parse_github_url(repo_url)
    git_url = f"https://github.com/{owner}/{repo}.git"

    # Get extensions directory
    extensions_dir = get_extensions_directory()

    # Clone to temporary location first
    temp_dir = extensions_dir / f".temp_{repo}"
    try:
        logger.info(f"Cloning repository: {git_url}")
        clone_repository(git_url, temp_dir, branch)

        # Validate manifest
        manifest = validate_manifest(temp_dir / "extension.toml")
        logger.info(f"Found extension: {manifest.name} v{manifest.version}")

        # Check if extension already installed
        existing = session.exec(select(Extension).where(Extension.name == manifest.name)).first()

        if existing:
            # Clean up temp dir
            shutil.rmtree(temp_dir)
            raise InstallError(
                f"Extension '{manifest.name}' is already installed. "
                "Uninstall it first to reinstall."
            )

        # Move to final location
        final_dir = extensions_dir / manifest.name
        if final_dir.exists():
            shutil.rmtree(final_dir)
        temp_dir.rename(final_dir)

        # Install dependencies
        install_dependencies(final_dir)

        # Create database record
        extension = Extension(
            name=manifest.name,
            version=manifest.version,
            description=manifest.description,
            author=manifest.author,
            repo_url=repo_url,
            install_path=manifest.name,
            entry_point=manifest.entry_point,
            is_enabled=True,
            installed_by_user_id=user_id,
        )
        session.add(extension)
        session.commit()
        session.refresh(extension)

        # Load the extension
        load_extension_module(final_dir, manifest.entry_point)

        # Log activity
        from tinybase.activity import Actions, log_activity

        log_activity(
            action=Actions.EXTENSION_INSTALL,
            resource_type="extension",
            resource_id=extension.name,
            user_id=user_id,
            meta_data={"version": extension.version, "repo_url": repo_url},
        )

        logger.info(f"Successfully installed extension: {manifest.name}")
        return extension

    except Exception:
        # Clean up on failure
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        raise


def uninstall_extension(session: "Session", name: str) -> bool:
    """
    Uninstall an extension.

    Args:
        session: Database session.
        name: Extension name.

    Returns:
        True if uninstalled, False if not found.
    """
    from sqlmodel import select

    from tinybase.db.models import Extension
    from tinybase.extensions.loader import get_extensions_directory, unload_extension

    # Find extension in database
    extension = session.exec(select(Extension).where(Extension.name == name)).first()

    if not extension:
        return False

    # Log activity before deletion
    from tinybase.activity import Actions, log_activity

    log_activity(
        action=Actions.EXTENSION_UNINSTALL,
        resource_type="extension",
        resource_id=extension.name,
        meta_data={"version": extension.version},
    )

    # Unload from memory
    unload_extension(name)

    # Remove files
    extensions_dir = get_extensions_directory()
    ext_dir = extensions_dir / extension.install_path
    if ext_dir.exists():
        shutil.rmtree(ext_dir)
        logger.info(f"Removed extension files: {ext_dir}")

    # Remove database record
    session.delete(extension)
    session.commit()

    logger.info(f"Uninstalled extension: {name}")
    return True


def check_for_updates(session: "Session", name: str) -> tuple[str, str] | None:
    """
    Check if an extension has updates available.

    Args:
        session: Database session.
        name: Extension name.

    Returns:
        Tuple of (current_version, latest_version) if update available, None otherwise.
    """
    from sqlmodel import select

    from tinybase.db.models import Extension

    extension = session.exec(select(Extension).where(Extension.name == name)).first()

    if not extension:
        return None

    # Parse the repo URL and fetch latest manifest
    try:
        owner, repo, _ = parse_github_url(extension.repo_url)

        # Fetch raw extension.toml from GitHub
        import urllib.request

        manifest_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/extension.toml"

        try:
            with urllib.request.urlopen(manifest_url, timeout=10) as response:
                manifest_content = response.read()
                manifest_data = tomllib.loads(manifest_content.decode("utf-8"))
                latest_version = manifest_data.get("extension", {}).get("version")

                if latest_version and latest_version != extension.version:
                    return (extension.version, latest_version)
        except Exception:
            # Try HEAD branch as fallback
            manifest_url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/extension.toml"
            with urllib.request.urlopen(manifest_url, timeout=10) as response:
                manifest_content = response.read()
                manifest_data = tomllib.loads(manifest_content.decode("utf-8"))
                latest_version = manifest_data.get("extension", {}).get("version")

                if latest_version and latest_version != extension.version:
                    return (extension.version, latest_version)

    except Exception as e:
        logger.debug(f"Failed to check for updates for {name}: {e}")

    return None
