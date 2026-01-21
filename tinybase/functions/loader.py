"""
Function module loader.

Handles loading user-defined functions from the functions package directory.
Uses uv run --script to extract metadata from functions running in isolated environments.
"""

import json
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tinybase.functions.core import FunctionMeta, get_global_registry
from tinybase.utils import AuthLevel

logger = logging.getLogger(__name__)


def extract_function_metadata(file_path: Path) -> dict | None:
    """Run script with --metadata to extract function info."""
    try:
        result = subprocess.run(
            ["uv", "run", "--script", str(file_path), "--metadata"],
            capture_output=True,
            text=True,
            timeout=60,  # Allow time for dependency installation
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            logger.error(f"Metadata extraction failed for {file_path}: {result.stderr}")
    except Exception as e:
        logger.error(f"Failed to extract metadata from {file_path}: {e}")
    return None


def prewarm_function_dependencies(file_path: Path) -> bool:
    """
    Pre-install dependencies for a function to reduce first-call latency.

    Uses `uv sync --script` to install dependencies in the function's isolated environment.
    This is called at startup for all functions to ensure dependencies are ready.
    """
    try:
        result = subprocess.run(
            ["uv", "sync", "--script", str(file_path)],
            capture_output=True,
            text=True,
            timeout=120,  # Allow time for dependency installation
        )
        if result.returncode == 0:
            logger.debug(f"Pre-warmed dependencies for {file_path.name}")
            return True
        else:
            logger.warning(f"Failed to pre-warm {file_path.name}: {result.stderr}")
            return False
    except Exception as e:
        logger.warning(f"Error pre-warming {file_path}: {e}")
        return False


def load_functions_from_directory(dir_path: Path) -> int:
    """
    Load all functions from directory via subprocess metadata extraction.

    Process:
    1. Extract metadata from each function file (parallel)
    2. Register functions in the global registry
    3. Pre-warm dependencies for all functions (parallel) to reduce latency
    """
    registry = get_global_registry()
    loaded = 0
    function_files = [f for f in dir_path.glob("*.py") if not f.name.startswith("_")]

    # Step 1: Extract metadata (parallel for faster startup)
    metadata_map = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_file = {
            executor.submit(extract_function_metadata, py_file): py_file
            for py_file in function_files
        }

        for future in as_completed(future_to_file):
            py_file = future_to_file[future]
            try:
                metadata = future.result()
                if metadata:
                    metadata_map[py_file] = metadata
            except Exception as e:
                logger.error(f"Error extracting metadata from {py_file}: {e}")

    # Step 2: Register functions
    for py_file, metadata in metadata_map.items():
        meta = FunctionMeta(
            name=metadata["name"],
            description=metadata.get("description"),
            auth=AuthLevel(metadata.get("auth", "auth")),
            tags=metadata.get("tags", []),
            input_schema=metadata.get("input_schema"),
            output_schema=metadata.get("output_schema"),
            file_path=str(py_file),
        )
        registry.register(meta)
        loaded += 1

    # Step 3: Pre-warm dependencies and add to cold start pool (only if functions are loaded)
    if metadata_map:
        logger.info(f"Pre-warming dependencies for {len(metadata_map)} function(s)...")
        from tinybase.functions.pool import get_pool

        pool = get_pool()
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for py_file in metadata_map.keys():
                # Pre-warm dependencies
                futures.append(executor.submit(prewarm_function_dependencies, py_file))
                # Add to cold start pool
                pool.prewarm_function(py_file)
            # Don't wait - let it run in background
            # Functions will still work if pre-warming isn't complete

    return loaded


def reload_single_function(file_path: Path) -> bool:
    """
    Hot-reload a single function file.

    Process:
    1. Extract metadata from file
    2. Unregister existing function (if any)
    3. Re-register in global registry with new metadata
    4. Pre-warm dependencies in background

    Args:
        file_path: Path to function file

    Returns:
        True if successful, False otherwise
    """
    registry = get_global_registry()

    # Step 1: Extract metadata
    metadata = extract_function_metadata(file_path)
    if not metadata:
        logger.error(f"Failed to extract metadata for hot-reload: {file_path}")
        return False

    function_name = metadata["name"]

    # Step 2: Unregister old version (if exists)
    registry.unregister(function_name)
    logger.info(f"Unregistered old version of function: {function_name}")

    # Step 3: Register new version
    meta = FunctionMeta(
        name=function_name,
        description=metadata.get("description"),
        auth=AuthLevel(metadata.get("auth", "auth")),
        tags=metadata.get("tags", []),
        input_schema=metadata.get("input_schema"),
        output_schema=metadata.get("output_schema"),
        file_path=str(file_path),
    )
    registry.register(meta)
    logger.info(f"Registered new version of function: {function_name}")

    # Step 4: Pre-warm dependencies in background
    from tinybase.functions.pool import get_pool

    pool = get_pool()
    pool.prewarm_function(file_path)
    logger.debug(f"Triggered dependency pre-warming for: {function_name}")

    return True


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
            '    #   "tinybase-sdk",\n'
            '    #   "requests>=2.31.0",\n'
            "    # ]\n"
            "    # ///\n"
            '"""\n'
        )

    return True


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
