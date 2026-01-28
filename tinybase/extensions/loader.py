"""
Extension loader.

Handles loading installed extensions from the database and importing their Python modules.
"""

import importlib.util
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlmodel import Session

logger = logging.getLogger(__name__)


def get_extensions_directory() -> Path:
    """
    Get the extensions directory path, creating it if needed.

    Returns:
        Path to the extensions directory.
    """
    from tinybase.settings import config

    extensions_dir = Path(config.extensions_dir).expanduser()
    extensions_dir.mkdir(parents=True, exist_ok=True)
    return extensions_dir


def load_extension_module(extension_path: Path, entry_point: str) -> bool:
    """
    Load an extension's Python module.

    Args:
        extension_path: Path to the extension directory.
        entry_point: Entry point file name (e.g., "main.py").

    Returns:
        True if loaded successfully, False otherwise.
    """
    module_file = extension_path / entry_point

    if not module_file.exists():
        logger.error(f"Extension entry point not found: {module_file}")
        return False

    # Create a unique module name
    module_name = f"tinybase_extension_{extension_path.name}"

    # Remove existing module if it was previously loaded
    if module_name in sys.modules:
        del sys.modules[module_name]

    try:
        # Add extension path to sys.path temporarily for imports
        ext_path_str = str(extension_path)
        if ext_path_str not in sys.path:
            sys.path.insert(0, ext_path_str)

        try:
            spec = importlib.util.spec_from_file_location(module_name, module_file)
            if spec is None or spec.loader is None:
                logger.error(f"Failed to create module spec for {module_file}")
                return False

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            logger.info(f"Loaded extension module: {module_name}")
            return True
        finally:
            # Remove from sys.path
            if ext_path_str in sys.path:
                sys.path.remove(ext_path_str)

    except Exception as e:
        logger.error(f"Error loading extension from {extension_path}: {e}")
        return False


def load_enabled_extensions(session: "Session") -> int:
    """
    Load all enabled extensions from the database.

    Args:
        session: Database session.

    Returns:
        Number of extensions successfully loaded.
    """
    from sqlmodel import select

    from tinybase.db.models import Extension
    from tinybase.settings import config

    if not config.extensions_enabled:
        logger.info("Extensions are disabled in configuration")
        return 0

    extensions_dir = get_extensions_directory()
    loaded_count = 0

    # Get all enabled extensions
    stmt = select(Extension).where(Extension.is_enabled)
    extensions = session.exec(stmt).all()

    for ext in extensions:
        ext_path = extensions_dir / ext.install_path

        if not ext_path.exists():
            logger.warning(f"Extension directory not found: {ext_path}")
            continue

        if load_extension_module(ext_path, ext.entry_point):
            loaded_count += 1
            logger.info(f"Loaded extension: {ext.name} v{ext.version}")
        else:
            logger.error(f"Failed to load extension: {ext.name}")

    return loaded_count


def unload_extension(name: str) -> bool:
    """
    Unload an extension module from memory.

    Note: This doesn't unregister functions that were already registered.
    A server restart is recommended after uninstalling extensions.

    Args:
        name: Extension name.

    Returns:
        True if unloaded, False if not found.
    """
    module_name = f"tinybase_extension_{name}"

    if module_name in sys.modules:
        del sys.modules[module_name]
        logger.info(f"Unloaded extension module: {module_name}")
        return True

    return False
