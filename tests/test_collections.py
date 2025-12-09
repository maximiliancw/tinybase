"""
Tests for collections and records functionality.
"""

from tests.utils import create_collection, create_record, get_admin_token


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


def test_get_collection_not_found(client):
    """Test getting a non-existent collection."""
    response = client.get("/api/collections/nonexistent")
    assert response.status_code == 404


def test_get_record_not_found(client, admin_token):
    """Test getting a non-existent record."""
    # Create collection
    create_collection(client, admin_token, name="test", schema={"fields": []})

    response = client.get(
        "/api/collections/test/records/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


def test_update_record_not_found(client, admin_token):
    """Test updating a non-existent record."""
    # Create collection
    create_collection(client, admin_token, name="test", schema={"fields": []})

    response = client.patch(
        "/api/collections/test/records/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"title": "Updated"}},
    )
    assert response.status_code == 404


def test_delete_record_not_found(client, admin_token):
    """Test deleting a non-existent record."""
    # Create collection
    create_collection(client, admin_token, name="test", schema={"fields": []})

    response = client.delete(
        "/api/collections/test/records/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


def test_list_records_pagination(client, admin_token):
    """Test pagination for records list."""
    # Create collection
    create_collection(
        client,
        admin_token,
        name="pagination_test",
        schema={"fields": [{"name": "value", "type": "integer"}]},
    )

    # Create multiple records
    for i in range(10):
        create_record(client, admin_token, "pagination_test", {"value": i})

    # Test pagination
    response = client.get(
        "/api/collections/pagination_test/records",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"limit": 3, "offset": 0},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 3
    assert data["offset"] == 0
    assert len(data["records"]) == 3
    assert data["total"] == 10

    # Test second page
    response = client.get(
        "/api/collections/pagination_test/records",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"limit": 3, "offset": 3},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["offset"] == 3
    assert len(data["records"]) == 3


def test_create_collection_duplicate_name(client, admin_token):
    """Test that creating collection with duplicate name fails."""
    # Create first collection
    create_collection(client, admin_token, name="duplicate", schema={"fields": []})

    # Try to create again with same name
    response = client.post(
        "/api/collections",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "duplicate",
            "label": "Duplicate",
            "schema": {"fields": []},
        },
    )
    assert response.status_code == 400


def test_create_record_in_nonexistent_collection(client, admin_token):
    """Test creating record in non-existent collection."""
    response = client.post(
        "/api/collections/nonexistent/records",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"title": "Test"}},
    )
    assert response.status_code == 404


def test_update_collection(client, admin_token):
    """Test updating a collection."""
    # Create collection
    create_collection(
        client,
        admin_token,
        name="updatable",
        label="Original Label",
        schema={"fields": [{"name": "title", "type": "string"}]},
    )

    # Update collection
    response = client.patch(
        "/api/collections/updatable",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"label": "Updated Label"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["label"] == "Updated Label"


def test_delete_collection(client, admin_token):
    """Test deleting a collection."""
    # Create collection
    create_collection(client, admin_token, name="deletable", schema={"fields": []})

    # Delete collection
    response = client.delete(
        "/api/collections/deletable",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204

    # Verify deletion
    get_response = client.get("/api/collections/deletable")
    assert get_response.status_code == 404
