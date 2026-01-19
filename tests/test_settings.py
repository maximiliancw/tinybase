"""
Tests for instance settings functionality.
"""

from tests.utils import get_admin_token


def test_get_settings_requires_admin(client):
    """Test that getting settings requires admin."""
    # Register a regular user
    client.post(
        "/api/auth/register",
        json={
            "email": "user@test.com",
            "password": "testpassword123",
        },
    )

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "user@test.com",
            "password": "testpassword123",
        },
    )
    token = login_response.json()["access_token"]

    response = client.get(
        "/api/admin/settings",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_get_settings(client):
    """Test getting instance settings."""
    token = get_admin_token(client)

    response = client.get(
        "/api/admin/settings",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Check required fields
    assert "instance_name" in data
    assert "allow_public_registration" in data
    assert "server_timezone" in data
    assert "storage_enabled" in data


def test_update_settings(client):
    """Test updating instance settings."""
    token = get_admin_token(client)

    response = client.patch(
        "/api/admin/settings",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "instance_name": "My TinyBase Instance",
            "allow_public_registration": False,
            "server_timezone": "America/New_York",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["instance_name"] == "My TinyBase Instance"
    assert data["allow_public_registration"] is False
    assert data["server_timezone"] == "America/New_York"


def test_update_settings_invalid_timezone(client):
    """Test updating settings with invalid timezone."""
    token = get_admin_token(client)

    response = client.patch(
        "/api/admin/settings",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "server_timezone": "Invalid/Timezone",
        },
    )

    assert response.status_code == 400
    assert "timezone" in response.json()["detail"].lower()


def test_registration_disabled(client):
    """Test that registration can be disabled via settings."""
    token = get_admin_token(client)

    # Disable public registration
    client.patch(
        "/api/admin/settings",
        headers={"Authorization": f"Bearer {token}"},
        json={"allow_public_registration": False},
    )

    # Try to register
    response = client.post(
        "/api/auth/register",
        json={
            "email": "newuser@test.com",
            "password": "testpassword123",
        },
    )

    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()
