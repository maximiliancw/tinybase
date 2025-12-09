"""
Admin UI static file serving.

Mounts the Vue 3 SPA built assets to serve the admin interface.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from tinybase.config import settings


def get_admin_static_dir() -> Path | None:
    """
    Get the path to admin static files.

    Returns the built-in admin_static directory if using "builtin",
    or a custom path if specified in settings.

    Returns:
        Path to static files directory, or None if not available.
    """
    config = settings()

    if config.admin_static_dir == "builtin":
        # Look for bundled admin_static directory
        builtin_path = Path(__file__).parent.parent.parent / "admin_static"
        if builtin_path.exists():
            return builtin_path
        return None
    else:
        # Custom path
        custom_path = Path(config.admin_static_dir)
        if custom_path.exists():
            return custom_path
        return None


def mount_admin_ui(app: FastAPI) -> bool:
    """
    Mount the admin UI static files to /admin.

    The admin UI is a Vue 3 SPA that needs to be served with
    html=True to enable SPA routing (all routes serve index.html).

    Args:
        app: FastAPI application instance

    Returns:
        True if admin UI was mounted, False if static files not found.
    """
    static_dir = get_admin_static_dir()

    if static_dir is None:
        return False

    # Mount with html=True for SPA support
    app.mount("/admin", StaticFiles(directory=str(static_dir), html=True), name="admin")

    return True
