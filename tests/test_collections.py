"""
Tests for collections and records functionality.
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


def test_create_collection(client):
    """Test creating a collection."""
    token = get_admin_token(client)

    response = client.post(
        "/api/collections",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "posts",
            "label": "Blog Posts",
            "schema": {
                "fields": [
                    {"name": "title", "type": "string", "required": True, "max_length": 200},
                    {"name": "content", "type": "string", "required": False},
                    {"name": "published", "type": "boolean", "default": False},
                ]
            },
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "posts"
    assert data["label"] == "Blog Posts"
    assert len(data["schema"]["fields"]) == 3


def test_create_collection_requires_admin(client):
    """Test that creating collections requires admin."""
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
    token = login_response.json()["token"]

    response = client.post(
        "/api/collections",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "posts",
            "label": "Blog Posts",
            "schema": {"fields": []},
        },
    )

    assert response.status_code == 403


def test_list_collections(client):
    """Test listing collections."""
    token = get_admin_token(client)

    # Create a collection first
    client.post(
        "/api/collections",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "items",
            "label": "Items",
            "schema": {"fields": []},
        },
    )

    response = client.get("/api/collections")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "items"


def test_create_record(client):
    """Test creating a record in a collection."""
    token = get_admin_token(client)

    # Create collection
    client.post(
        "/api/collections",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "tasks",
            "label": "Tasks",
            "schema": {
                "fields": [
                    {"name": "title", "type": "string", "required": True},
                    {"name": "done", "type": "boolean", "default": False},
                ]
            },
        },
    )

    # Create record
    response = client.post(
        "/api/collections/tasks/records",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "data": {"title": "Test task", "done": False},
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["data"]["title"] == "Test task"
    assert data["data"]["done"] is False


def test_record_validation(client):
    """Test that record data is validated against schema."""
    token = get_admin_token(client)

    # Create collection with required field
    client.post(
        "/api/collections",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "products",
            "label": "Products",
            "schema": {
                "fields": [
                    {"name": "name", "type": "string", "required": True},
                    {"name": "price", "type": "float", "required": True},
                ]
            },
        },
    )

    # Try to create record without required field
    response = client.post(
        "/api/collections/products/records",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "data": {"name": "Test"},  # Missing price
        },
    )

    assert response.status_code == 400


def test_list_records_with_sorting(client):
    """Test listing records with sorting."""
    token = get_admin_token(client)

    # Create collection
    client.post(
        "/api/collections",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "notes",
            "label": "Notes",
            "schema": {
                "fields": [
                    {"name": "content", "type": "string"},
                ]
            },
        },
    )

    # Create multiple records
    for i in range(3):
        client.post(
            "/api/collections/notes/records",
            headers={"Authorization": f"Bearer {token}"},
            json={"data": {"content": f"Note {i}"}},
        )

    # List with default sort (created_at desc)
    response = client.get(
        "/api/collections/notes/records",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3

    # Verify default sort order (newest first)
    assert data["records"][0]["data"]["content"] == "Note 2"
    assert data["records"][2]["data"]["content"] == "Note 0"


def test_update_record(client):
    """Test updating a record."""
    token = get_admin_token(client)

    # Create collection and record
    client.post(
        "/api/collections",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "entries",
            "label": "Entries",
            "schema": {
                "fields": [
                    {"name": "title", "type": "string"},
                ]
            },
        },
    )

    create_response = client.post(
        "/api/collections/entries/records",
        headers={"Authorization": f"Bearer {token}"},
        json={"data": {"title": "Original"}},
    )
    record_id = create_response.json()["id"]

    # Update record
    response = client.patch(
        f"/api/collections/entries/records/{record_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"data": {"title": "Updated"}},
    )

    assert response.status_code == 200
    assert response.json()["data"]["title"] == "Updated"


def test_delete_record(client):
    """Test deleting a record."""
    token = get_admin_token(client)

    # Create collection and record
    client.post(
        "/api/collections",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "temp",
            "label": "Temp",
            "schema": {"fields": []},
        },
    )

    create_response = client.post(
        "/api/collections/temp/records",
        headers={"Authorization": f"Bearer {token}"},
        json={"data": {}},
    )
    record_id = create_response.json()["id"]

    # Delete record
    response = client.delete(
        f"/api/collections/temp/records/{record_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204

    # Verify deletion
    get_response = client.get(
        f"/api/collections/temp/records/{record_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_response.status_code == 404
