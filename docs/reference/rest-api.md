# REST API Reference

Complete HTTP API documentation for TinyBase.

## Base URL

```
http://localhost:8000/api
```

## Authentication

Most endpoints require authentication via Bearer token:

```bash
curl -H "Authorization: Bearer tb_your_token" http://localhost:8000/api/...
```

______________________________________________________________________

## Auth Endpoints

### Register User

Create a new user account.

```http
POST /api/auth/register
```

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response:** `201 Created`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "is_admin": false,
  "created_at": "2024-01-01T12:00:00Z"
}
```

______________________________________________________________________

### Login

Authenticate and receive a token.

```http
POST /api/auth/login
```

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response:** `200 OK`

```json
{
  "token": "tb_a1b2c3d4e5f6...",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "is_admin": false
  },
  "expires_at": "2024-01-02T12:00:00Z"
}
```

______________________________________________________________________

### Get Current User

Get the authenticated user's information.

```http
GET /api/auth/me
```

**Headers:** `Authorization: Bearer <token>`

**Response:** `200 OK`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "is_admin": false,
  "created_at": "2024-01-01T12:00:00Z"
}
```

______________________________________________________________________

## Collections Endpoints

### List Collections

Get all collections.

```http
GET /api/collections
```

**Response:** `200 OK`

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "posts",
      "label": "Blog Posts",
      "schema": { ... },
      "options": { ... },
      "created_at": "2024-01-01T12:00:00Z"
    }
  ]
}
```

______________________________________________________________________

### Get Collection

Get a single collection by name.

```http
GET /api/collections/{name}
```

**Response:** `200 OK`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "posts",
  "label": "Blog Posts",
  "schema": {
    "fields": [
      {"name": "title", "type": "string", "required": true}
    ]
  },
  "options": {
    "access": {
      "list": "public",
      "create": "auth"
    }
  }
}
```

______________________________________________________________________

### Create Collection

Create a new collection (admin only).

```http
POST /api/collections
```

**Headers:** `Authorization: Bearer <admin_token>`

**Request Body:**

```json
{
  "name": "products",
  "label": "Products",
  "schema": {
    "fields": [
      {"name": "title", "type": "string", "required": true},
      {"name": "price", "type": "float", "required": true}
    ]
  },
  "options": {
    "access": {
      "list": "public",
      "create": "admin"
    }
  }
}
```

**Response:** `201 Created`

______________________________________________________________________

## Records Endpoints

### List Records

Get records from a collection.

```http
GET /api/collections/{name}/records
```

**Query Parameters:**

| Parameter    | Type   | Default      | Description           |
| ------------ | ------ | ------------ | --------------------- |
| `limit`      | int    | 100          | Max records to return |
| `offset`     | int    | 0            | Records to skip       |
| `sort_by`    | string | `created_at` | Sort field            |
| `sort_order` | string | `desc`       | `asc` or `desc`       |

**Response:** `200 OK`

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "collection_id": "...",
      "owner_id": "...",
      "data": {
        "title": "My Post",
        "content": "..."
      },
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 100
}
```

______________________________________________________________________

### Get Record

Get a single record.

```http
GET /api/collections/{name}/records/{id}
```

**Response:** `200 OK`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "collection_id": "...",
  "owner_id": "...",
  "data": {
    "title": "My Post"
  },
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

______________________________________________________________________

### Create Record

Create a new record in a collection.

```http
POST /api/collections/{name}/records
```

**Request Body:**

```json
{
  "title": "New Post",
  "content": "Post content here"
}
```

**Response:** `201 Created`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "collection_id": "...",
  "owner_id": "...",
  "data": {
    "title": "New Post",
    "content": "Post content here"
  },
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

______________________________________________________________________

### Update Record

Update an existing record (partial update).

```http
PATCH /api/collections/{name}/records/{id}
```

**Request Body:**

```json
{
  "title": "Updated Title"
}
```

**Response:** `200 OK`

______________________________________________________________________

### Delete Record

Delete a record.

```http
DELETE /api/collections/{name}/records/{id}
```

**Response:** `204 No Content`

______________________________________________________________________

## Functions Endpoints

### List Functions

Get all registered functions.

```http
GET /api/functions
```

**Response:** `200 OK`

```json
{
  "items": [
    {
      "name": "add_numbers",
      "description": "Add two numbers",
      "auth": "public",
      "tags": ["math"],
      "input_schema": { ... },
      "output_schema": { ... }
    }
  ]
}
```

______________________________________________________________________

### Call Function

Execute a function.

```http
POST /api/functions/{name}
```

**Request Body:** (depends on function input model)

```json
{
  "x": 1,
  "y": 2
}
```

**Response:** `200 OK`

```json
{
  "call_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "succeeded",
  "result": {
    "sum": 3
  }
}
```

**Error Response:** `200 OK`

```json
{
  "call_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "error": "Division by zero",
  "error_type": "ValueError"
}
```

______________________________________________________________________

## Admin Endpoints

All admin endpoints require admin authentication.

### Users

#### List Users

```http
GET /api/admin/users
```

#### Get User

```http
GET /api/admin/users/{id}
```

#### Update User

```http
PATCH /api/admin/users/{id}
```

```json
{
  "is_admin": true
}
```

#### Delete User

```http
DELETE /api/admin/users/{id}
```

______________________________________________________________________

### Schedules

#### List Schedules

```http
GET /api/admin/schedules
```

**Response:**

```json
{
  "items": [
    {
      "id": "...",
      "function_name": "cleanup",
      "payload": {},
      "schedule": {
        "method": "cron",
        "cron": "0 0 * * *"
      },
      "enabled": true,
      "last_run_at": "2024-01-01T00:00:00Z",
      "next_run_at": "2024-01-02T00:00:00Z"
    }
  ]
}
```

#### Create Schedule

```http
POST /api/admin/schedules
```

```json
{
  "function_name": "send_reports",
  "payload": {},
  "schedule": {
    "method": "cron",
    "timezone": "UTC",
    "cron": "0 9 * * 1-5"
  },
  "enabled": true
}
```

#### Update Schedule

```http
PATCH /api/admin/schedules/{id}
```

```json
{
  "enabled": false
}
```

#### Delete Schedule

```http
DELETE /api/admin/schedules/{id}
```

______________________________________________________________________

### Function Calls

#### List Function Calls

```http
GET /api/admin/function-calls
```

**Query Parameters:**

| Parameter       | Type   | Description             |
| --------------- | ------ | ----------------------- |
| `function_name` | string | Filter by function      |
| `status`        | string | `succeeded` or `failed` |
| `trigger_type`  | string | `manual` or `schedule`  |
| `limit`         | int    | Max results             |
| `offset`        | int    | Skip results            |

#### Get Function Call

```http
GET /api/admin/function-calls/{id}
```

______________________________________________________________________

## Error Responses

### Validation Error (422)

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Unauthorized (401)

```json
{
  "detail": "Invalid token"
}
```

### Forbidden (403)

```json
{
  "detail": "Admin access required"
}
```

### Not Found (404)

```json
{
  "detail": "Record not found"
}
```

## Rate Limiting

TinyBase implements rate limiting:

- **Authenticated**: 100 requests/minute
- **Public**: 20 requests/minute

Rate limit headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704067200
```

When exceeded:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
```

```json
{
  "detail": "Rate limit exceeded"
}
```
