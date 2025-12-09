"""
Tests for access control functionality.
"""

from tests.utils import create_collection, get_admin_token, get_user_token


def test_public_access_collection(client):
    """Test collection with public list access."""
    admin_token = get_admin_token(client)

    # Create collection with public list access
    create_collection(
        client,
        admin_token,
        name="public_items",
        label="Public Items",
        schema={"fields": [{"name": "title", "type": "string"}]},
        options={
            "access": {
                "list": "public",
                "read": "public",
                "create": "auth",
            }
        },
    )

    # List should work without auth
    response = client.get("/api/collections/public_items/records")
    assert response.status_code == 200


def test_auth_required_collection(client):
    """Test collection requiring authentication for listing."""
    admin_token = get_admin_token(client)

    # Create collection with auth required for list
    create_collection(
        client,
        admin_token,
        name="private_items",
        label="Private Items",
        schema={"fields": [{"name": "title", "type": "string"}]},
        options={
            "access": {
                "list": "auth",
                "read": "auth",
                "create": "auth",
            }
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
    create_collection(
        client,
        admin_token,
        name="owned_items",
        label="Owned Items",
        schema={"fields": [{"name": "title", "type": "string"}]},
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
    create_collection(
        client,
        admin_token,
        name="user_items",
        label="User Items",
        schema={"fields": [{"name": "title", "type": "string"}]},
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
