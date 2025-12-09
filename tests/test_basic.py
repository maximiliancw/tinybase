"""
Basic tests for TinyBase.

These tests verify the core functionality works correctly.
"""

from tests.utils import get_admin_token, get_user_token


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


def test_auth_register_duplicate_email(client):
    """Test that registering with duplicate email fails."""
    # Register first time
    response = client.post(
        "/api/auth/register",
        json={
            "email": "duplicate@test.com",
            "password": "testpassword123",
        },
    )
    assert response.status_code == 201

    # Try to register again with same email
    response = client.post(
        "/api/auth/register",
        json={
            "email": "duplicate@test.com",
            "password": "testpassword123",
        },
    )
    assert response.status_code == 400


def test_auth_register_invalid_email(client):
    """Test that registering with invalid email fails."""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "not-an-email",
            "password": "testpassword123",
        },
    )
    assert response.status_code == 422


def test_auth_register_short_password(client):
    """Test that registering with short password fails."""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "user@test.com",
            "password": "short",  # Less than 8 characters
        },
    )
    assert response.status_code == 422


def test_auth_login_invalid_credentials(client):
    """Test that login with invalid credentials fails."""
    response = client.post(
        "/api/auth/login",
        json={
            "email": "nonexistent@test.com",
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401


def test_auth_me_invalid_token(client):
    """Test that /me endpoint with invalid token fails."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert response.status_code == 401


def test_auth_me_no_token(client):
    """Test that /me endpoint without token fails."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401


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
    token = get_admin_token(client)

    response = client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert data["total"] >= 1  # At least the admin user


def test_admin_list_users_pagination(client):
    """Test pagination for user list."""
    token = get_admin_token(client)

    # Create multiple users
    for i in range(5):
        get_user_token(client, f"user{i}@test.com")

    # Test pagination
    response = client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 2, "offset": 0},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 2
    assert data["offset"] == 0
    assert len(data["users"]) <= 2
    assert data["total"] >= 5


def test_admin_create_user(client, admin_token):
    """Test admin creating a user."""
    response = client.post(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": "admin_created@test.com",
            "password": "testpassword123",
            "is_admin": False,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "admin_created@test.com"
    assert data["is_admin"] is False


def test_admin_create_user_duplicate_email(client, admin_token):
    """Test that creating user with duplicate email fails."""
    # Create user
    client.post(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": "duplicate_admin@test.com",
            "password": "testpassword123",
        },
    )

    # Try to create again
    response = client.post(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": "duplicate_admin@test.com",
            "password": "testpassword123",
        },
    )
    assert response.status_code == 400


def test_admin_get_user(client, admin_token):
    """Test getting a specific user."""
    # Create user
    create_response = client.post(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": "get_user@test.com",
            "password": "testpassword123",
        },
    )
    user_id = create_response.json()["id"]

    # Get user
    response = client.get(
        f"/api/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "get_user@test.com"


def test_admin_get_user_not_found(client, admin_token):
    """Test getting a non-existent user."""
    response = client.get(
        "/api/admin/users/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


def test_admin_update_user(client, admin_token):
    """Test updating a user."""
    # Create user
    create_response = client.post(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": "update_user@test.com",
            "password": "testpassword123",
            "is_admin": False,
        },
    )
    user_id = create_response.json()["id"]

    # Update user
    response = client.patch(
        f"/api/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_admin": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_admin"] is True


def test_admin_delete_user(client, admin_token):
    """Test deleting a user."""
    # Create user
    create_response = client.post(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": "delete_user@test.com",
            "password": "testpassword123",
        },
    )
    user_id = create_response.json()["id"]

    # Delete user
    response = client.delete(
        f"/api/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204

    # Verify deletion
    get_response = client.get(
        f"/api/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_response.status_code == 404


def test_admin_get_function_call_not_found(client, admin_token):
    """Test getting a non-existent function call."""
    response = client.get(
        "/api/admin/functions/calls/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
