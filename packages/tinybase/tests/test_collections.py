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
    token = login_response.json()["access_token"]

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


# =============================================================================
# Unique Constraint Tests
# =============================================================================


def test_unique_constraint_on_create(client, admin_token):
    """Test that unique constraint is enforced on record creation."""
    # Create collection with unique field
    create_collection(
        client,
        admin_token,
        name="users_unique",
        schema={
            "fields": [
                {"name": "email", "type": "string", "required": True, "unique": True},
                {"name": "name", "type": "string"},
            ]
        },
    )

    # Create first record
    response = client.post(
        "/api/collections/users_unique/records",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"email": "test@example.com", "name": "Test User"}},
    )
    assert response.status_code == 201

    # Try to create second record with same email - should fail
    response = client.post(
        "/api/collections/users_unique/records",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"email": "test@example.com", "name": "Another User"}},
    )
    assert response.status_code == 400
    assert "unique" in response.json()["detail"].lower()


def test_unique_constraint_on_update(client, admin_token):
    """Test that unique constraint is enforced on record update."""
    # Create collection with unique field
    create_collection(
        client,
        admin_token,
        name="products_unique",
        schema={
            "fields": [
                {"name": "sku", "type": "string", "required": True, "unique": True},
                {"name": "name", "type": "string"},
            ]
        },
    )

    # Create two records with different SKUs
    response1 = client.post(
        "/api/collections/products_unique/records",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"sku": "SKU001", "name": "Product 1"}},
    )
    assert response1.status_code == 201

    response2 = client.post(
        "/api/collections/products_unique/records",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"sku": "SKU002", "name": "Product 2"}},
    )
    assert response2.status_code == 201
    record2_id = response2.json()["id"]

    # Try to update second record to use first record's SKU - should fail
    response = client.patch(
        f"/api/collections/products_unique/records/{record2_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"sku": "SKU001"}},
    )
    assert response.status_code == 400
    assert "unique" in response.json()["detail"].lower()


def test_unique_constraint_allows_same_value_on_self_update(client, admin_token):
    """Test that updating a record with same unique value works."""
    # Create collection with unique field
    create_collection(
        client,
        admin_token,
        name="items_unique",
        schema={
            "fields": [
                {"name": "code", "type": "string", "required": True, "unique": True},
                {"name": "quantity", "type": "number"},
            ]
        },
    )

    # Create record
    response = client.post(
        "/api/collections/items_unique/records",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"code": "ITEM001", "quantity": 10}},
    )
    assert response.status_code == 201
    record_id = response.json()["id"]

    # Update quantity without changing code - should work
    response = client.patch(
        f"/api/collections/items_unique/records/{record_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"code": "ITEM001", "quantity": 20}},
    )
    assert response.status_code == 200
    assert response.json()["data"]["quantity"] == 20


# =============================================================================
# Array and Date Type Tests
# =============================================================================


def test_array_type_field(client, admin_token):
    """Test creating collection with array type field."""
    # Create collection with array field
    create_collection(
        client,
        admin_token,
        name="posts_tags",
        schema={
            "fields": [
                {"name": "title", "type": "string", "required": True},
                {"name": "tags", "type": "array"},
            ]
        },
    )

    # Create record with array data
    response = client.post(
        "/api/collections/posts_tags/records",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"title": "Test Post", "tags": ["python", "fastapi", "tinybase"]}},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["data"]["tags"] == ["python", "fastapi", "tinybase"]


def test_date_type_field(client, admin_token):
    """Test creating collection with date type field."""
    # Create collection with date field
    create_collection(
        client,
        admin_token,
        name="events",
        schema={
            "fields": [
                {"name": "name", "type": "string", "required": True},
                {"name": "event_date", "type": "date"},
            ]
        },
    )

    # Create record with date data
    response = client.post(
        "/api/collections/events/records",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"name": "Conference", "event_date": "2026-06-15T10:00:00"}},
    )
    assert response.status_code == 201


# =============================================================================
# Type-Specific Validation Tests
# =============================================================================


def test_min_max_only_for_numeric_types(client, admin_token):
    """Test that min/max properties only work for numeric types."""
    # Should fail - min/max on string type
    response = client.post(
        "/api/collections",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "invalid_schema",
            "label": "Invalid",
            "schema": {
                "fields": [
                    {"name": "title", "type": "string", "min": 0, "max": 100},
                ]
            },
        },
    )
    assert response.status_code == 400
    assert "min/max" in response.json()["detail"].lower()


def test_min_max_length_only_for_string_type(client, admin_token):
    """Test that min_length/max_length properties only work for string types."""
    # Should fail - min_length on number type
    response = client.post(
        "/api/collections",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "invalid_schema2",
            "label": "Invalid",
            "schema": {
                "fields": [
                    {"name": "count", "type": "number", "min_length": 1},
                ]
            },
        },
    )
    assert response.status_code == 400
    assert "min_length" in response.json()["detail"].lower()


def test_unique_not_allowed_on_complex_types(client, admin_token):
    """Test that unique property cannot be used with object/array types."""
    # Should fail - unique on array type
    response = client.post(
        "/api/collections",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "invalid_schema3",
            "label": "Invalid",
            "schema": {
                "fields": [
                    {"name": "tags", "type": "array", "unique": True},
                ]
            },
        },
    )
    assert response.status_code == 400
    assert "unique" in response.json()["detail"].lower()


def test_numeric_constraints_validation(client, admin_token):
    """Test that numeric constraints are enforced."""
    # Create collection with numeric constraints
    create_collection(
        client,
        admin_token,
        name="ratings",
        schema={
            "fields": [
                {"name": "score", "type": "number", "required": True, "min": 1, "max": 5},
            ]
        },
    )

    # Valid score
    response = client.post(
        "/api/collections/ratings/records",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"score": 3}},
    )
    assert response.status_code == 201

    # Score too low - should fail
    response = client.post(
        "/api/collections/ratings/records",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"score": 0}},
    )
    assert response.status_code == 400

    # Score too high - should fail
    response = client.post(
        "/api/collections/ratings/records",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"score": 10}},
    )
    assert response.status_code == 400


def test_string_length_constraints_validation(client, admin_token):
    """Test that string length constraints are enforced."""
    # Create collection with string constraints
    create_collection(
        client,
        admin_token,
        name="usernames",
        schema={
            "fields": [
                {
                    "name": "username",
                    "type": "string",
                    "required": True,
                    "min_length": 3,
                    "max_length": 20,
                },
            ]
        },
    )

    # Valid username
    response = client.post(
        "/api/collections/usernames/records",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"username": "john_doe"}},
    )
    assert response.status_code == 201

    # Username too short - should fail
    response = client.post(
        "/api/collections/usernames/records",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"username": "ab"}},
    )
    assert response.status_code == 400


# =============================================================================
# Foreign Key / Reference Tests
# =============================================================================


def test_reference_type_requires_collection_property(client, admin_token):
    """Test that reference type requires collection property."""
    response = client.post(
        "/api/collections",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "invalid_ref",
            "label": "Invalid Reference",
            "schema": {
                "fields": [
                    {"name": "author_id", "type": "reference"},  # Missing collection
                ]
            },
        },
    )
    assert response.status_code == 400
    assert "collection" in response.json()["detail"].lower()


def test_reference_field_validates_existing_record(client, admin_token):
    """Test that reference field validates the referenced record exists."""
    # Create target collection
    create_collection(
        client,
        admin_token,
        name="authors",
        schema={
            "fields": [
                {"name": "name", "type": "string", "required": True},
            ]
        },
    )

    # Create an author
    author_response = client.post(
        "/api/collections/authors/records",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"name": "John Doe"}},
    )
    assert author_response.status_code == 201
    author_id = author_response.json()["id"]

    # Create posts collection with reference to authors
    create_collection(
        client,
        admin_token,
        name="posts_with_author",
        schema={
            "fields": [
                {"name": "title", "type": "string", "required": True},
                {
                    "name": "author_id",
                    "type": "reference",
                    "collection": "authors",
                    "required": True,
                },
            ]
        },
    )

    # Create post with valid author reference
    response = client.post(
        "/api/collections/posts_with_author/records",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"title": "My Post", "author_id": author_id}},
    )
    assert response.status_code == 201

    # Try to create post with invalid author reference - should fail
    response = client.post(
        "/api/collections/posts_with_author/records",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "data": {"title": "Another Post", "author_id": "00000000-0000-0000-0000-000000000000"}
        },
    )
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"].lower()


def test_reference_field_validates_invalid_uuid(client, admin_token):
    """Test that reference field validates UUID format."""
    # Create target collection
    create_collection(
        client,
        admin_token,
        name="categories",
        schema={
            "fields": [
                {"name": "name", "type": "string", "required": True},
            ]
        },
    )

    # Create items collection with reference to categories
    create_collection(
        client,
        admin_token,
        name="items_with_category",
        schema={
            "fields": [
                {"name": "name", "type": "string", "required": True},
                {"name": "category_id", "type": "reference", "collection": "categories"},
            ]
        },
    )

    # Try to create item with invalid UUID - should fail
    response = client.post(
        "/api/collections/items_with_category/records",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"name": "Test Item", "category_id": "not-a-uuid"}},
    )
    assert response.status_code == 400
    assert "uuid" in response.json()["detail"].lower()


# =============================================================================
# Filter Tests with SQLite JSON
# =============================================================================


def test_filter_records_by_json_field(client, admin_token):
    """Test filtering records by JSON field using SQLite JSON functions."""
    # Create collection
    create_collection(
        client,
        admin_token,
        name="filtered_items",
        schema={
            "fields": [
                {"name": "name", "type": "string", "required": True},
                {"name": "status", "type": "string"},
                {"name": "priority", "type": "number"},
            ]
        },
    )

    # Create multiple records
    client.post(
        "/api/collections/filtered_items/records",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"name": "Item 1", "status": "active", "priority": 1}},
    )
    client.post(
        "/api/collections/filtered_items/records",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"name": "Item 2", "status": "active", "priority": 2}},
    )
    client.post(
        "/api/collections/filtered_items/records",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"name": "Item 3", "status": "inactive", "priority": 1}},
    )

    # All records
    response = client.get(
        "/api/collections/filtered_items/records",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 3
