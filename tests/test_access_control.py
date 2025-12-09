"""
Tests for access control functionality.
"""

from fastapi.testclient import TestClient


def get_admin_token(client: TestClient) -> str:
    """Helper to login as admin and get token."""
    response = client.post(
        "/api/auth/login",
        json={
            "email": "admin@test.com",
            "password": "testpassword",
        },
    )
    return response.json()["token"]


def get_user_token(client: TestClient, email: str = "testuser@test.com") -> str:
    """Helper to create and login as a regular user."""
    # Register user
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "testpassword123",
        },
    )

    # Login
    response = client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": "testpassword123",
        },
    )
    return response.json()["token"]


def test_public_access_collection(client):
    """Test collection with public list access."""
    admin_token = get_admin_token(client)

    # Create collection with public list access
    client.post(
        "/api/collections",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "public_items",
            "label": "Public Items",
            "schema": {"fields": [{"name": "title", "type": "string"}]},
            "options": {
                "access": {
                    "list": "public",
                    "read": "public",
                    "create": "auth",
                }
            },
        },
    )

    # List should work without auth
    response = client.get("/api/collections/public_items/records")
    assert response.status_code == 200


def test_auth_required_collection(client):
    """Test collection requiring authentication for listing."""
    admin_token = get_admin_token(client)

    # Create collection with auth required for list
    client.post(
        "/api/collections",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "private_items",
            "label": "Private Items",
            "schema": {"fields": [{"name": "title", "type": "string"}]},
            "options": {
                "access": {
                    "list": "auth",
                    "read": "auth",
                    "create": "auth",
                }
            },
        },
    )

    # List without auth should fail
    response = client.get("/api/collections/private_items/records")
    assert response.status_code == 403

    # List with auth should work
    user_token = get_user_token(client)
    response = client.get(
        "/api/collections/private_items/records",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200


def test_owner_only_update(client):
    """Test that only record owner can update by default."""
    admin_token = get_admin_token(client)
    user1_token = get_user_token(client, "user1@test.com")
    user2_token = get_user_token(client, "user2@test.com")

    # Create collection
    client.post(
        "/api/collections",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "owned_items",
            "label": "Owned Items",
            "schema": {"fields": [{"name": "title", "type": "string"}]},
        },
    )

    # User1 creates a record
    create_response = client.post(
        "/api/collections/owned_items/records",
        headers={"Authorization": f"Bearer {user1_token}"},
        json={"data": {"title": "User1's item"}},
    )
    record_id = create_response.json()["id"]

    # User2 tries to update - should fail
    response = client.patch(
        f"/api/collections/owned_items/records/{record_id}",
        headers={"Authorization": f"Bearer {user2_token}"},
        json={"data": {"title": "Updated by user2"}},
    )
    assert response.status_code == 403

    # User1 can update their own record
    response = client.patch(
        f"/api/collections/owned_items/records/{record_id}",
        headers={"Authorization": f"Bearer {user1_token}"},
        json={"data": {"title": "Updated by owner"}},
    )
    assert response.status_code == 200


def test_admin_bypasses_owner_check(client):
    """Test that admin can update any record."""
    admin_token = get_admin_token(client)
    user_token = get_user_token(client, "regular@test.com")

    # Create collection
    client.post(
        "/api/collections",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "user_items",
            "label": "User Items",
            "schema": {"fields": [{"name": "title", "type": "string"}]},
        },
    )

    # User creates a record
    create_response = client.post(
        "/api/collections/user_items/records",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"data": {"title": "User's item"}},
    )
    record_id = create_response.json()["id"]

    # Admin can update any record
    response = client.patch(
        f"/api/collections/user_items/records/{record_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"title": "Updated by admin"}},
    )
    assert response.status_code == 200
