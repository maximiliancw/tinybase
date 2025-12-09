"""
Tests for functions functionality.
"""

import pytest

from tests.utils import get_admin_token


def test_list_functions(client):
    """Test listing functions."""
    response = client.get("/api/functions")
    assert response.status_code == 200
    # Functions list might be empty
    assert isinstance(response.json(), list)


def test_admin_function_list(client):
    """Test admin function list with extended info."""
    token = get_admin_token(client)

    response = client.get(
        "/api/functions/admin/list",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # If there are functions, verify extended info fields
    if data:
        func = data[0]
        assert "module" in func
        assert "file_path" in func
        assert "is_async" in func


def test_function_call_requires_auth_for_auth_functions(client):
    """Test that auth-level functions require authentication."""
    # This test depends on having an auth-level function registered
    # Skip if no functions are available
    response = client.get("/api/functions")
    functions = response.json()

    auth_function = next((f for f in functions if f["auth"] == "auth"), None)
    if auth_function is None:
        pytest.skip("No auth-level function available for testing")

    # Try to call without auth
    response = client.post(f"/api/functions/{auth_function['name']}", json={})
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
