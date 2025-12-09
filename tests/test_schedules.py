"""
Tests for schedule management functionality.
"""

from tests.utils import get_admin_token, get_user_token


def test_list_schedules_requires_admin(client):
    """Test that listing schedules requires admin."""
    user_token = get_user_token(client)

    response = client.get(
        "/api/admin/schedules",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403


def test_list_schedules_empty(client, admin_token):
    """Test listing schedules when empty."""
    response = client.get(
        "/api/admin/schedules",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["schedules"] == []


def test_create_schedule_requires_function(client, admin_token):
    """Test that creating a schedule requires an existing function."""
    response = client.post(
        "/api/admin/schedules",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "test_schedule",
            "function_name": "nonexistent_function",
            "schedule": {"type": "cron", "cron": "0 * * * *"},
        },
    )
    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


def test_create_schedule_invalid_config(client, admin_token):
    """Test creating a schedule with invalid configuration."""
    # Check if there are any functions available
    functions_response = client.get("/api/functions")
    functions = functions_response.json()
    
    if not functions:
        # No functions available, so we can only test function not found
        response = client.post(
            "/api/admin/schedules",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "test_schedule",
                "function_name": "nonexistent_function",
                "schedule": {"type": "invalid"},
            },
        )
        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()
    else:
        # Use first available function to test invalid schedule config
        function_name = functions[0]["name"]
        response = client.post(
            "/api/admin/schedules",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "test_schedule",
                "function_name": function_name,
                "schedule": {"type": "invalid"},
            },
        )
        assert response.status_code == 400
        detail = response.json()["detail"].lower()
        assert "invalid" in detail or "schedule" in detail


def test_get_schedule_not_found(client, admin_token):
    """Test getting a non-existent schedule."""
    response = client.get(
        "/api/admin/schedules/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


def test_update_schedule_not_found(client, admin_token):
    """Test updating a non-existent schedule."""
    response = client.patch(
        "/api/admin/schedules/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "updated"},
    )
    assert response.status_code == 404


def test_delete_schedule_not_found(client, admin_token):
    """Test deleting a non-existent schedule."""
    response = client.delete(
        "/api/admin/schedules/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


def test_list_schedules_with_filters(client, admin_token):
    """Test listing schedules with filters."""
    response = client.get(
        "/api/admin/schedules",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"is_active": True, "limit": 10, "offset": 0},
    )
    assert response.status_code == 200
    data = response.json()
    assert "schedules" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data


def test_list_schedules_pagination(client, admin_token):
    """Test pagination parameters."""
    response = client.get(
        "/api/admin/schedules",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"limit": 5, "offset": 0},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 5
    assert data["offset"] == 0

