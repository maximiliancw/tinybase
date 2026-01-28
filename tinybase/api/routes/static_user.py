"""
User static file serving.

Mounts user-provided static files (e.g., a frontend SPA) at the root path.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from tinybase.settings import config


def get_user_static_dir() -> Path | None:
    """
    Get the path to user static files.

    Returns the configured directory if it exists and contains an index.html file.

    Returns:
        Path to static files directory, or None if not configured or invalid.
    """
    if config.serve_static_files is None:
        return None

    static_path = Path(config.serve_static_files).expanduser().resolve()

    if not static_path.exists():
        return None

    # Validate that index.html exists (required for SPA)
    index_file = static_path / "index.html"
    if not index_file.exists():
        return None

    return static_path


def mount_user_static_files(app: FastAPI) -> bool:
    """
    Mount user static files at the root path.

    The static files are served with html=True to enable SPA routing
    (all routes serve index.html).

    IMPORTANT: This should be mounted LAST, after all API routes,
    to ensure API routes take precedence.

    Args:
        app: FastAPI application instance

    Returns:
        True if static files were mounted, False if not configured or invalid.
    """
    static_dir = get_user_static_dir()

    if static_dir is None:
        return False

    # Mount with html=True for SPA support
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static_files")

    return True
