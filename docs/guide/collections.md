# Collections

Collections are the primary way to store and manage data in TinyBase. They provide schema-driven data tables with automatic validation, CRUD endpoints, and access control.

## Overview

A collection in TinyBase is:

- A **table** in the SQLite database
- Defined by a **JSON schema** specifying fields and constraints
- Automatically generates **Pydantic models** for validation
- Exposes **REST endpoints** for CRUD operations

## Creating Collections

### Via Admin UI

1. Navigate to **Collections** in the sidebar
1. Click **New Collection**
1. Enter a name and label
1. Define the schema

### Via API

```bash
curl -X POST http://localhost:8000/api/collections \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "products",
    "label": "Products",
    "schema": {
      "fields": [
        {"name": "title", "type": "string", "required": true, "max_length": 200},
        {"name": "price", "type": "float", "required": true, "min": 0},
        {"name": "in_stock", "type": "boolean", "default": true},
        {"name": "tags", "type": "list"}
      ]
    }
  }'
```

## Schema Definition

The schema defines the structure and validation rules for records.

### Field Types

| Type        | Description                       | Additional Options                    |
| ----------- | --------------------------------- | ------------------------------------- |
| `string`    | Text data                         | `max_length`, `min_length`, `pattern` |
| `number`    | Decimal numbers                   | `min`, `max`                          |
| `boolean`   | True/false                        | -                                     |
| `array`     | Array of values                   | -                                     |
| `object`    | Nested object                     | -                                     |
| `date`      | Date/time values                  | Stored as ISO 8601 strings            |
| `reference` | Foreign key to another collection | `collection` (required)               |

### Field Options

| Option        | Type    | Description                                                    |
| ------------- | ------- | -------------------------------------------------------------- |
| `required`    | boolean | Field must be provided (default: `false`)                      |
| `unique`      | boolean | Values must be unique within the collection (default: `false`) |
| `default`     | any     | Default value if not provided                                  |
| `description` | string  | Human-readable field description                               |
| `max_length`  | integer | Maximum string length (string only)                            |
| `min_length`  | integer | Minimum string length (string only)                            |
| `pattern`     | string  | Regex pattern for validation (string only)                     |
| `min`         | number  | Minimum numeric value (number only)                            |
| `max`         | number  | Maximum numeric value (number only)                            |
| `collection`  | string  | Target collection name (reference only)                        |

!!! note "Type-Specific Options"
Field options are validated based on the field type:

```
- `min`/`max` can only be used with `number` type
- `min_length`/`max_length`/`pattern` can only be used with `string` type
- `unique` cannot be used with `array` or `object` types
- `collection` is required when type is `reference`
```

### Example Schema

```json
{
  "fields": [
    {
      "name": "email",
      "type": "string",
      "required": true,
      "unique": true,
      "pattern": "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$"
    },
    {
      "name": "age",
      "type": "number",
      "min": 0,
      "max": 150
    },
    {
      "name": "preferences",
      "type": "object",
      "default": {}
    },
    {
      "name": "tags",
      "type": "array",
      "default": []
    },
    {
      "name": "created_date",
      "type": "date",
      "description": "When this record was created"
    }
  ]
}
```

### Unique Constraints

Fields marked as `unique: true` enforce that no two records in the collection can have the same value for that field.

```json
{
  "fields": [
    {
      "name": "sku",
      "type": "string",
      "required": true,
      "unique": true
    }
  ]
}
```

- Unique constraints are checked on both create and update operations
- Database indexes are automatically created for unique fields to ensure fast lookups
- Attempting to create a duplicate value returns a `400 Bad Request` error

### Collection References (Foreign Keys)

The `reference` type allows you to create relationships between collections:

```json
{
  "fields": [
    {
      "name": "author_id",
      "type": "reference",
      "collection": "users",
      "required": true
    }
  ]
}
```

- Reference fields store a UUID pointing to a record in the target collection
- TinyBase validates that the referenced record exists on create/update
- Invalid references (non-existent records) return a `400 Bad Request` error

**Example: Blog with Posts and Authors**

```json
// users collection schema
{
  "fields": [
    {"name": "name", "type": "string", "required": true},
    {"name": "email", "type": "string", "required": true, "unique": true}
  ]
}

// posts collection schema
{
  "fields": [
    {"name": "title", "type": "string", "required": true},
    {"name": "content", "type": "string"},
    {"name": "author_id", "type": "reference", "collection": "users", "required": true},
    {"name": "published_at", "type": "date"}
  ]
}
```

## REST API Endpoints

Each collection automatically provides these endpoints:

### List Records

```http
GET /api/collections/{name}/records
```

Query parameters:

| Parameter    | Description                             | Default      |
| ------------ | --------------------------------------- | ------------ |
| `limit`      | Max records to return                   | 100          |
| `offset`     | Records to skip                         | 0            |
| `sort_by`    | Sort field (`created_at`, `updated_at`) | `created_at` |
| `sort_order` | Sort direction (`asc`, `desc`)          | `desc`       |

Example:

```bash
curl "http://localhost:8000/api/collections/products/records?limit=10&sort_by=created_at"
```

Response:

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "collection_id": "...",
      "owner_id": null,
      "data": {
        "title": "Widget",
        "price": 19.99,
        "in_stock": true
      },
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10
}
```

### Get Single Record

```http
GET /api/collections/{name}/records/{id}
```

### Create Record

```http
POST /api/collections/{name}/records
```

```bash
curl -X POST http://localhost:8000/api/collections/products/records \
  -H "Content-Type: application/json" \
  -d '{"title": "New Widget", "price": 29.99}'
```

### Update Record

```http
PATCH /api/collections/{name}/records/{id}
```

Partial updates only send changed fields:

```bash
curl -X PATCH http://localhost:8000/api/collections/products/records/$ID \
  -H "Content-Type: application/json" \
  -d '{"price": 24.99}'
```

### Delete Record

```http
DELETE /api/collections/{name}/records/{id}
```

## Access Control

Collections support fine-grained access control for each operation.

### Access Rules

| Rule     | Description              |
| -------- | ------------------------ |
| `public` | Anyone can access        |
| `auth`   | Authenticated users only |
| `owner`  | Only the record owner    |
| `admin`  | Admin users only         |

### Configuring Access

Set access rules in the collection options:

```json
{
  "name": "posts",
  "label": "Blog Posts",
  "schema": { ... },
  "options": {
    "access": {
      "list": "public",
      "read": "public",
      "create": "auth",
      "update": "owner",
      "delete": "admin"
    }
  }
}
```

### Default Access Rules

If not specified, collections use these defaults:

| Operation | Default  |
| --------- | -------- |
| `list`    | `public` |
| `read`    | `public` |
| `create`  | `auth`   |
| `update`  | `owner`  |
| `delete`  | `owner`  |

## Record Ownership

When an authenticated user creates a record, their user ID is stored as `owner_id`. This enables:

- **Owner-based access**: Only the creator can update/delete
- **Filtering**: Query records by owner
- **Audit trail**: Track who created what

```bash
# List only your records (when authenticated)
curl http://localhost:8000/api/collections/posts/records \
  -H "Authorization: Bearer $USER_TOKEN"
```

## Working with Records in Functions

!!! note "Function Format"
The examples below show internal API usage for extensions. User functions should use the [TinyBase SDK format](functions.md#defining-functions) and access collections via the `client` API object instead of direct database access.

Access collections from within functions using the context:

```python
from sqlmodel import select
from tinybase.db.models import Collection, Record
from tinybase.functions import Context, register
from tinybase.collections.service import CollectionService


@register(name="get_featured_products", auth="public", ...)
def get_featured_products(ctx: Context, payload: Input) -> Output:
    # Use the CollectionService
    service = CollectionService(ctx.db)

    # Get the collection
    collection = service.get_collection_by_name("products")

    # List records
    records, total = service.list_records(
        collection,
        limit=10,
        filters={"featured": True}
    )

    return Output(products=[r.data for r in records])
```

Or use raw SQLModel queries:

```python
@register(name="search_products", auth="public", ...)
def search_products(ctx: Context, payload: SearchInput) -> SearchOutput:
    # Direct database query
    stmt = select(Record).where(
        Record.collection_id == collection.id
    )
    records = ctx.db.exec(stmt).all()

    # Filter in Python for complex queries
    results = [
        r for r in records
        if payload.query.lower() in r.data.get("title", "").lower()
    ]

    return SearchOutput(items=results)
```

## Schema Migrations

When you update a collection's schema:

1. **Adding fields**: New fields get default values for existing records
1. **Removing fields**: Old data is preserved but ignored
1. **Changing types**: May cause validation errors for existing records
1. **Adding unique constraints**: Indexes are automatically created
1. **Removing unique constraints**: Indexes are automatically dropped

!!! info "Automatic Index Management"
TinyBase automatically manages database indexes for unique fields. When you add or remove the `unique` property from a field, the corresponding index is created or dropped without any manual intervention.

```
- Adding `unique: true` to a field with duplicate values will fail with an error
- All index operations are logged for debugging purposes
```

!!! warning "Schema Changes"
Changing field types or adding required fields without defaults may break existing records. Always backup your database before schema changes.

### Safe Schema Updates

```json
// Add optional field with default
{
  "name": "discount",
  "type": "number",
  "required": false,
  "default": 0
}

// Add required field with default
{
  "name": "status",
  "type": "string",
  "required": true,
  "default": "active"
}

// Add unique constraint (ensure no duplicates exist first)
{
  "name": "slug",
  "type": "string",
  "unique": true
}
```

## Collection Health Monitoring

Administrators can monitor collection health and index status via the Admin API:

### Get All Collections Status

```http
GET /api/admin/collections/status
```

Returns a summary of all collections including record counts and health status.

### Get Single Collection Status

```http
GET /api/admin/collections/{name}/status
```

Returns detailed status including:

- Record count and schema field count
- Unique field index status (active/missing)
- Reference field validation status
- Overall health status (healthy/warning/error)

```json
{
  "collection": "posts",
  "record_count": 1542,
  "schema_fields": 5,
  "unique_fields": ["slug"],
  "indexes": [
    {
      "field": "slug",
      "index_name": "idx_posts_slug_unique",
      "has_index": true,
      "status": "active"
    }
  ],
  "references": [
    {
      "field": "author_id",
      "target_collection": "users",
      "target_exists": true
    }
  ],
  "health_status": "healthy"
}
```

## Best Practices

### Naming Conventions

- Use **lowercase** with **underscores** for collection names: `blog_posts`, not `BlogPosts`
- Use **singular** or **plural** consistently
- Keep names short but descriptive

### Schema Design

- Start with required fields only
- Add optional fields with sensible defaults
- Use appropriate types (don't store numbers as strings)
- Consider access patterns when designing schemas

### Performance

- Add indexes for frequently queried fields (future feature)
- Use pagination for large collections
- Avoid storing large blobs in records

## See Also

- [Functions Guide](functions.md) - Access collections from functions
- [Authentication Guide](authentication.md) - User and access control
- [REST API Reference](../reference/rest-api.md) - Complete endpoint documentation
