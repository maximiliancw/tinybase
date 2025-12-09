"""
Basic tests for TinyBase.

These tests verify the core functionality works correctly.
"""


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
    response = client.post(
        "/api/auth/register",
        json={
            "email": "newuser@test.com",
            "password": "testpassword123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@test.com"
    assert "id" in data


def test_auth_login(client):
    """Test user login."""
    # Register a user first
    client.post(
        "/api/auth/register",
        json={
            "email": "logintest@test.com",
            "password": "testpassword123",
        },
    )

    # Login
    response = client.post(
        "/api/auth/login",
        json={
            "email": "logintest@test.com",
            "password": "testpassword123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["email"] == "logintest@test.com"


def test_auth_me(client):
    """Test getting current user info."""
    # Login as admin
    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "admin@test.com",
            "password": "testpassword",
        },
    )
    token = login_response.json()["token"]

    # Get user info
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
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
    response = client.post(
        "/api/collections",
        json={
            "name": "test_collection",
            "label": "Test Collection",
            "schema": {"fields": []},
        },
    )
    assert response.status_code == 401


def test_functions_list(client):
    """Test listing functions."""
    response = client.get("/api/functions")
    assert response.status_code == 200
    # Functions might be empty or contain example functions
    assert isinstance(response.json(), list)


def test_users_list_requires_admin(client):
    """Test that listing users requires admin."""
    # Register a regular user
    client.post(
        "/api/auth/register",
        json={
            "email": "regular@test.com",
            "password": "testpassword123",
        },
    )

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "regular@test.com",
            "password": "testpassword123",
        },
    )
    token = login_response.json()["token"]

    # Try to list users
    response = client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_admin_can_list_users(client):
    """Test that admin can list users."""
    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "admin@test.com",
            "password": "testpassword",
        },
    )
    token = login_response.json()["token"]

    response = client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert data["total"] >= 1  # At least the admin user
