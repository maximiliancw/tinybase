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


# =============================================================================
# Extension Settings Tests
# =============================================================================


def _create_test_extension(client, admin_token, name="test_ext"):
    """Helper to create a test extension directly in the database."""
    from sqlmodel import Session

    from tinybase.db.core import get_db_engine
    from tinybase.db.models import Extension

    engine = get_db_engine()
    with Session(engine) as session:
        ext = Extension(
            name=name,
            description="A test extension",
            version="1.0.0",
            repo_url="https://github.com/test/test-ext",
            install_path=f"extensions/{name}",
            entry_point="main.py",
            is_enabled=True,
        )
        session.add(ext)
        session.commit()
        return ext.name


def test_get_extension_settings_requires_admin(client):
    """Test that getting extension settings requires admin authentication."""
    user_token = get_user_token(client)

    response = client.get(
        "/api/admin/extensions/test_ext/settings",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403


def test_get_extension_settings_not_found(client, admin_token):
    """Test getting settings for a non-existent extension."""
    response = client.get(
        "/api/admin/extensions/nonexistent/settings",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_extension_settings_empty(client, admin_token):
    """Test getting settings for an extension with no settings."""
    # Create a test extension
    ext_name = _create_test_extension(client, admin_token, "ext_no_settings")

    response = client.get(
        f"/api/admin/extensions/{ext_name}/settings",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["extension_name"] == ext_name
    assert data["settings"] == []


def test_get_extension_settings_returns_settings(client, admin_token):
    """Test that extension settings are returned with prefix stripped."""
    from sqlmodel import Session

    from tinybase.db.core import get_db_engine
    from tinybase.db.models import AppSetting

    # Create a test extension
    ext_name = _create_test_extension(client, admin_token, "ext_with_settings")

    # Create some settings for the extension
    engine = get_db_engine()
    with Session(engine) as session:
        setting1 = AppSetting(
            key=f"ext.{ext_name}.api_key",
            value="secret123",
            value_type="str",
            description="API Key for the extension",
        )
        setting2 = AppSetting(
            key=f"ext.{ext_name}.max_retries",
            value="5",
            value_type="int",
        )
        session.add(setting1)
        session.add(setting2)
        session.commit()

    response = client.get(
        f"/api/admin/extensions/{ext_name}/settings",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["extension_name"] == ext_name
    assert len(data["settings"]) == 2

    # Check that keys have prefix stripped
    keys = [s["key"] for s in data["settings"]]
    assert "api_key" in keys
    assert "max_retries" in keys

    # Check all fields are present
    for setting in data["settings"]:
        assert "key" in setting
        assert "value" in setting
        assert "value_type" in setting
        assert "description" in setting


def test_update_extension_settings_requires_admin(client):
    """Test that updating extension settings requires admin authentication."""
    user_token = get_user_token(client)

    response = client.patch(
        "/api/admin/extensions/test_ext/settings",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"settings": {"key": "value"}},
    )
    assert response.status_code == 403


def test_update_extension_settings_not_found(client, admin_token):
    """Test updating settings for a non-existent extension."""
    response = client.patch(
        "/api/admin/extensions/nonexistent/settings",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"settings": {"key": "value"}},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_extension_settings_creates_new(client, admin_token):
    """Test that updating settings creates new settings if they don't exist."""
    # Create a test extension
    ext_name = _create_test_extension(client, admin_token, "ext_create_settings")

    response = client.patch(
        f"/api/admin/extensions/{ext_name}/settings",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"settings": {"new_setting": "new_value"}},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["extension_name"] == ext_name
    assert len(data["settings"]) == 1
    assert data["settings"][0]["key"] == "new_setting"
    assert data["settings"][0]["value"] == "new_value"
    assert data["settings"][0]["value_type"] == "str"  # Default type


def test_update_extension_settings_updates_existing(client, admin_token):
    """Test that updating settings updates existing settings."""
    from sqlmodel import Session

    from tinybase.db.core import get_db_engine
    from tinybase.db.models import AppSetting

    # Create a test extension
    ext_name = _create_test_extension(client, admin_token, "ext_update_settings")

    # Create an existing setting
    engine = get_db_engine()
    with Session(engine) as session:
        setting = AppSetting(
            key=f"ext.{ext_name}.existing",
            value="old_value",
            value_type="str",
        )
        session.add(setting)
        session.commit()

    # Update the setting
    response = client.patch(
        f"/api/admin/extensions/{ext_name}/settings",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"settings": {"existing": "new_value"}},
    )
    assert response.status_code == 200

    data = response.json()
    setting_data = next(s for s in data["settings"] if s["key"] == "existing")
    assert setting_data["value"] == "new_value"


def test_update_extension_settings_multiple(client, admin_token):
    """Test updating multiple settings in one request."""
    # Create a test extension
    ext_name = _create_test_extension(client, admin_token, "ext_multi_settings")

    response = client.patch(
        f"/api/admin/extensions/{ext_name}/settings",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "settings": {
                "setting1": "value1",
                "setting2": "value2",
                "setting3": "value3",
            }
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data["settings"]) == 3

    keys = {s["key"] for s in data["settings"]}
    assert keys == {"setting1", "setting2", "setting3"}


def test_update_extension_settings_persists(client, admin_token):
    """Test that settings persist across requests."""
    # Create a test extension
    ext_name = _create_test_extension(client, admin_token, "ext_persist_settings")

    # Create a setting
    response = client.patch(
        f"/api/admin/extensions/{ext_name}/settings",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"settings": {"persistent": "stored_value"}},
    )
    assert response.status_code == 200

    # Fetch settings again
    response = client.get(
        f"/api/admin/extensions/{ext_name}/settings",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data["settings"]) == 1
    assert data["settings"][0]["key"] == "persistent"
    assert data["settings"][0]["value"] == "stored_value"
