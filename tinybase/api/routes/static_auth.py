"""
Auth Portal static file serving.

Mounts the same admin SPA at /auth to serve auth portal routes.
The auth portal is integrated into the admin SPA.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from tinybase.config import settings


def get_app_static_dir() -> Path | None:
    """
    Get the path to app static files (same as admin UI).

    Returns the built-in static/app directory if using "builtin",
    or a custom path if specified in settings.

    Returns:
        Path to static files directory, or None if not available.
    """
    config = settings()

    if config.admin_static_dir == "builtin":
        # Look for bundled static/app directory
        builtin_path = Path(__file__).parent.parent.parent / "static" / "app"
        if builtin_path.exists():
            return builtin_path
        return None
    else:
        # Custom path
        custom_path = Path(config.admin_static_dir)
        if custom_path.exists():
            return custom_path
        return None


def mount_auth_portal(app: FastAPI) -> bool:
    """
    Mount the admin SPA static files.

    The auth portal is integrated into the admin SPA, so we serve
    the same static files at /auth. The router will handle routing
    to the appropriate auth portal views.

    Args:
        app: FastAPI application instance

    Returns:
        True if auth portal was mounted, False if static files not found.
    """
    static_dir = get_app_static_dir()

    if static_dir is None:
        return False

    # Mount with html=True for SPA support
    # This serves the same SPA as /admin, but at /auth path
    app.mount("/auth", StaticFiles(directory=str(static_dir), html=True), name="auth")

    return True
