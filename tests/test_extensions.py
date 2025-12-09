"""
Tests for extension management functionality.
"""

from tests.utils import get_user_token


def test_list_extensions_requires_admin(client):
    """Test that listing extensions requires admin."""
    user_token = get_user_token(client)

    response = client.get(
        "/api/admin/extensions",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403


def test_list_extensions_empty(client, admin_token):
    """Test listing extensions when empty."""
    response = client.get(
        "/api/admin/extensions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["extensions"] == []


def test_list_extensions_with_filters(client, admin_token):
    """Test listing extensions with filters."""
    response = client.get(
        "/api/admin/extensions",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"enabled_only": True, "check_updates": False, "limit": 10, "offset": 0},
    )
    assert response.status_code == 200
    data = response.json()
    assert "extensions" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data


def test_get_extension_not_found(client, admin_token):
    """Test getting a non-existent extension."""
    response = client.get(
        "/api/admin/extensions/nonexistent",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


def test_update_extension_not_found(client, admin_token):
    """Test updating a non-existent extension."""
    response = client.patch(
        "/api/admin/extensions/nonexistent",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_enabled": True},
    )
    assert response.status_code == 404


def test_delete_extension_not_found(client, admin_token):
    """Test deleting a non-existent extension."""
    response = client.delete(
        "/api/admin/extensions/nonexistent",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


def test_install_extension_invalid_repo(client, admin_token):
    """Test installing extension with invalid repository URL."""
    response = client.post(
        "/api/admin/extensions",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"repo_url": "not-a-valid-url"},
    )
    # Should return 400 for invalid URL
    assert response.status_code in [400, 422]


def test_list_extensions_pagination(client, admin_token):
    """Test pagination parameters."""
    response = client.get(
        "/api/admin/extensions",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"limit": 5, "offset": 0},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 5
    assert data["offset"] == 0

