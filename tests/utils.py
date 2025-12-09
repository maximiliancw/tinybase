"""
Test utilities and helpers for TinyBase tests.

Provides reusable functions and fixtures to reduce code duplication.
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
    assert response.status_code == 200
    return response.json()["token"]


def get_user_token(
    client: TestClient, email: str = "testuser@test.com", password: str = "testpassword123"
) -> str:
    """Helper to create and login as a regular user."""
    # Register user if not exists (try login first)
    login_response = client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    if login_response.status_code == 200:
        return login_response.json()["token"]

    # User doesn't exist, register them
    register_response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": password,
        },
    )
    assert register_response.status_code == 201

    # Login
    login_response = client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert login_response.status_code == 200
    return login_response.json()["token"]


def create_collection(
    client: TestClient,
    token: str,
    name: str = "test_collection",
    label: str = "Test Collection",
    schema: dict | None = None,
    options: dict | None = None,
) -> dict:
    """Helper to create a collection."""
    if schema is None:
        schema = {"fields": [{"name": "title", "type": "string"}]}

    payload = {
        "name": name,
        "label": label,
        "schema": schema,
    }
    if options:
        payload["options"] = options

    response = client.post(
        "/api/collections",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response.status_code == 201
    return response.json()


def create_record(
    client: TestClient,
    token: str,
    collection_name: str,
    data: dict,
) -> dict:
    """Helper to create a record in a collection."""
    response = client.post(
        f"/api/collections/{collection_name}/records",
        headers={"Authorization": f"Bearer {token}"},
        json={"data": data},
    )
    assert response.status_code == 201
    return response.json()
