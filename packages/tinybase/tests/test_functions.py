"""
Tests for functions functionality.
"""

from tests.utils import get_admin_token


def test_list_functions(client):
    """Test listing functions."""
    response = client.get("/api/functions")
    assert response.status_code == 200
    # Functions list might be empty
    assert isinstance(response.json(), list)


def test_admin_function_list(client, mock_functions):
    """Test admin function list with extended info."""
    token = get_admin_token(client)

    response = client.get(
        "/api/functions/admin/list",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 4  # Should have at least our 4 mock functions

    # Verify extended info fields
    func = data[0]
    assert "module" in func
    assert "file_path" in func
    assert "is_async" in func


def test_function_call_requires_auth_for_auth_functions(client, mock_functions):
    """Test that auth-level functions require authentication."""
    # Try to call auth function without authentication
    response = client.post("/api/functions/auth_test", json={})
    assert response.status_code == 401


def test_function_calls_history(client):
    """Test listing function call history."""
    token = get_admin_token(client)

    response = client.get(
        "/api/admin/functions/calls",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "calls" in data
    assert "total" in data
    assert isinstance(data["calls"], list)
