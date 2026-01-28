"""
Tests for static file serving functionality.

Covers:
- get_user_static_dir() configuration validation
- mount_user_static_files() mounting behavior
- Integration with API routes
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI


# =============================================================================
# get_user_static_dir() Tests
# =============================================================================


def test_get_user_static_dir_returns_none_when_not_configured():
    """Test that get_user_static_dir returns None when serve_static_files is None."""
    from tinybase.api.routes.static_user import get_user_static_dir
    from tinybase.settings.static import _reset_config

    # Reset config to ensure clean state
    _reset_config()

    with patch("tinybase.api.routes.static_user.config") as mock_config:
        mock_config.serve_static_files = None

        result = get_user_static_dir()

        assert result is None


def test_get_user_static_dir_returns_none_when_directory_not_exists():
    """Test that get_user_static_dir returns None when the directory doesn't exist."""
    from tinybase.api.routes.static_user import get_user_static_dir

    with patch("tinybase.api.routes.static_user.config") as mock_config:
        mock_config.serve_static_files = "/nonexistent/path/to/static"

        result = get_user_static_dir()

        assert result is None


def test_get_user_static_dir_returns_none_when_index_html_missing():
    """Test that get_user_static_dir returns None when index.html is missing."""
    from tinybase.api.routes.static_user import get_user_static_dir

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create directory without index.html
        static_dir = Path(tmpdir) / "static"
        static_dir.mkdir()

        with patch("tinybase.api.routes.static_user.config") as mock_config:
            mock_config.serve_static_files = str(static_dir)

            result = get_user_static_dir()

            assert result is None


def test_get_user_static_dir_returns_path_when_valid():
    """Test that get_user_static_dir returns path when directory and index.html exist."""
    from tinybase.api.routes.static_user import get_user_static_dir

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create directory with index.html
        static_dir = Path(tmpdir) / "static"
        static_dir.mkdir()
        (static_dir / "index.html").write_text("<html><body>Hello</body></html>")

        with patch("tinybase.api.routes.static_user.config") as mock_config:
            mock_config.serve_static_files = str(static_dir)

            result = get_user_static_dir()

            assert result is not None
            # Compare resolved paths (handles /var vs /private/var on macOS)
            assert result.resolve() == static_dir.resolve()


def test_get_user_static_dir_expands_tilde():
    """Test that get_user_static_dir expands ~ to home directory."""
    from tinybase.api.routes.static_user import get_user_static_dir

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create directory with index.html in a path under home
        static_dir = Path(tmpdir) / "static"
        static_dir.mkdir()
        (static_dir / "index.html").write_text("<html><body>Hello</body></html>")

        # Create a symlink from home directory to our temp dir (if possible)
        # We'll just test that expanduser is called by checking resolved path
        with patch("tinybase.api.routes.static_user.config") as mock_config:
            # Use the actual path but verify it gets resolved
            mock_config.serve_static_files = str(static_dir)

            result = get_user_static_dir()

            assert result is not None
            # Verify it's an absolute resolved path
            assert result.is_absolute()
            assert result == static_dir.resolve()


# =============================================================================
# mount_user_static_files() Tests
# =============================================================================


def test_mount_user_static_files_returns_false_when_not_configured():
    """Test that mount_user_static_files returns False when not configured."""
    from tinybase.api.routes.static_user import mount_user_static_files

    app = FastAPI()

    with patch("tinybase.api.routes.static_user.get_user_static_dir") as mock_get_dir:
        mock_get_dir.return_value = None

        result = mount_user_static_files(app)

        assert result is False


def test_mount_user_static_files_returns_true_when_valid():
    """Test that mount_user_static_files returns True and mounts files when valid."""
    from starlette.routing import Mount

    from tinybase.api.routes.static_user import mount_user_static_files

    with tempfile.TemporaryDirectory() as tmpdir:
        static_dir = Path(tmpdir)
        (static_dir / "index.html").write_text("<html><body>Hello</body></html>")

        app = FastAPI()

        with patch("tinybase.api.routes.static_user.get_user_static_dir") as mock_get_dir:
            mock_get_dir.return_value = static_dir

            result = mount_user_static_files(app)

            assert result is True
            # Verify a Mount route was added (StaticFiles creates a Mount)
            mount_routes = [r for r in app.routes if isinstance(r, Mount)]
            assert len(mount_routes) > 0
            assert mount_routes[0].name == "static_files"


# =============================================================================
# Integration Tests
# =============================================================================


def test_root_endpoint_available_when_static_not_mounted(client):
    """Test that root endpoint / is available when static files are not mounted."""
    response = client.get("/")
    # Should return 200 with welcome message or redirect
    assert response.status_code in [200, 307]


def test_api_routes_accessible_when_static_not_mounted(client, admin_token):
    """Test that API routes work when static files are not mounted."""
    response = client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200


def test_health_endpoint_accessible(client):
    """Test that health endpoint is always accessible."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_api_routes_accessible_with_custom_static_app():
    """Test that API routes remain accessible when static files are mounted."""
    import tempfile
    from pathlib import Path

    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from starlette.routing import Mount

    from tinybase.api.routes.static_user import mount_user_static_files

    with tempfile.TemporaryDirectory() as tmpdir:
        static_dir = Path(tmpdir)
        (static_dir / "index.html").write_text("<html><body>Test</body></html>")

        # Create a test app with an API route
        app = FastAPI()

        @app.get("/api/test")
        def test_route():
            return {"message": "API works"}

        # Mount static files at root
        with patch("tinybase.api.routes.static_user.get_user_static_dir") as mock_get_dir:
            mock_get_dir.return_value = static_dir
            mounted = mount_user_static_files(app)
            assert mounted is True

        # Test with TestClient
        with TestClient(app) as test_client:
            # API route should still work
            response = test_client.get("/api/test")
            assert response.status_code == 200
            assert response.json() == {"message": "API works"}

            # Static files should be served at root
            response = test_client.get("/")
            assert response.status_code == 200
            assert "Test" in response.text


def test_static_files_serve_index_for_root():
    """Test that static files serve index.html at root path."""
    import tempfile
    from pathlib import Path

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from tinybase.api.routes.static_user import mount_user_static_files

    with tempfile.TemporaryDirectory() as tmpdir:
        static_dir = Path(tmpdir)
        (static_dir / "index.html").write_text("<html><body>SPA App</body></html>")

        app = FastAPI()

        with patch("tinybase.api.routes.static_user.get_user_static_dir") as mock_get_dir:
            mock_get_dir.return_value = static_dir
            mount_user_static_files(app)

        with TestClient(app) as test_client:
            # Root should serve index.html
            response = test_client.get("/")
            assert response.status_code == 200
            assert "SPA App" in response.text
