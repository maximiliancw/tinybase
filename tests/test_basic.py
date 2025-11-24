"""
Basic tests for TinyBase.

These tests verify the core functionality works correctly.
"""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session


@pytest.fixture(scope="function")
def client():
    """Create a test client with a fresh database."""
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    
    # Set environment variables before importing tinybase modules
    os.environ["TINYBASE_DB_URL"] = f"sqlite:///{db_path}"
    os.environ["TINYBASE_SCHEDULER_ENABLED"] = "false"
    
    # Import after setting env vars
    from tinybase.config import reload_settings
    from tinybase.db.core import reset_engine, create_db_and_tables, get_engine
    from tinybase.db.models import User
    from tinybase.auth import hash_password
    from tinybase.api.app import create_app
    from tinybase.functions.core import reset_global_registry
    from tinybase.collections.schemas import reset_registry
    
    # Reset everything
    reset_engine()
    reset_global_registry()
    reset_registry()
    reload_settings()
    
    # Create tables
    create_db_and_tables()
    
    # Create test admin user
    engine = get_engine()
    with Session(engine) as session:
        admin = User(
            email="admin@test.com",
            password_hash=hash_password("testpassword"),
            is_admin=True,
        )
        session.add(admin)
        session.commit()
    
    # Create app
    app = create_app()
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Cleanup
    reset_engine()
    reset_global_registry()
    reset_registry()
    
    # Remove temp database
    try:
        os.unlink(db_path)
    except Exception:
        pass
    
    # Reset env vars
    os.environ.pop("TINYBASE_DB_URL", None)
    os.environ.pop("TINYBASE_SCHEDULER_ENABLED", None)


def test_root_endpoint(client):
    """Test the root endpoint returns API info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "TinyBase"
    assert "version" in data


def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_auth_register(client):
    """Test user registration."""
    response = client.post("/api/auth/register", json={
        "email": "newuser@test.com",
        "password": "testpassword123",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@test.com"
    assert "id" in data


def test_auth_login(client):
    """Test user login."""
    # Register a user first
    client.post("/api/auth/register", json={
        "email": "logintest@test.com",
        "password": "testpassword123",
    })
    
    # Login
    response = client.post("/api/auth/login", json={
        "email": "logintest@test.com",
        "password": "testpassword123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["email"] == "logintest@test.com"


def test_auth_me(client):
    """Test getting current user info."""
    # Login as admin
    login_response = client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "password": "testpassword",
    })
    token = login_response.json()["token"]
    
    # Get user info
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@test.com"
    assert data["is_admin"] is True


def test_collections_list_empty(client):
    """Test listing collections when empty."""
    response = client.get("/api/collections")
    assert response.status_code == 200
    assert response.json() == []


def test_collections_create_requires_admin(client):
    """Test that creating collections requires admin."""
    # Try without auth
    response = client.post("/api/collections", json={
        "name": "test_collection",
        "label": "Test Collection",
        "schema": {"fields": []},
    })
    assert response.status_code == 401


def test_functions_list(client):
    """Test listing functions."""
    response = client.get("/api/functions")
    assert response.status_code == 200
    # Functions might be empty or contain example functions
    assert isinstance(response.json(), list)
