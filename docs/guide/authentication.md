# Authentication

TinyBase includes a complete authentication system with user management, token-based auth, and role-based access control.

## Overview

TinyBase authentication features:

- **User registration and login**
- **JWT tokens** with access and refresh tokens
- **Token expiration** with configurable TTL
- **Role-based access** (admin vs. regular users)
- **Password hashing** with bcrypt
- **Token revocation** via database tracking

## Authentication Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant A as Auth API
    participant D as Database
    
    C->>A: POST /api/auth/register
    A->>D: Create user
    D-->>A: User created
    A-->>C: 201 Created
    
    C->>A: POST /api/auth/login
    A->>D: Verify credentials
    D-->>A: User found
    A->>D: Create token
    A-->>C: 200 OK + token
    
    C->>A: GET /api/... (with token)
    A->>D: Validate token
    D-->>A: Token valid
    A-->>C: Protected resource
```

## User Registration

### Register a New User

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

Response (201 Created):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "is_admin": false,
  "created_at": "2024-01-01T12:00:00Z"
}
```

### Password Requirements

- Minimum 8 characters (recommended)
- Stored as bcrypt hash
- Never returned in API responses

## User Login

### Authenticate and Get Token

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

Response (200 OK):

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "is_admin": false
}
```

### Token Format

TinyBase uses JWT (JSON Web Tokens) for authentication:

- **Access tokens**: Short-lived tokens for API requests (default: 24 hours)
- **Refresh tokens**: Long-lived tokens for obtaining new access tokens (default: 30 days)
- **Signed with HS256**: Cryptographically signed with your secret key
- **Stored in database**: For revocation tracking

JWT claims include:
- `sub`: User ID
- `exp`: Expiration timestamp
- `iat`: Issued at timestamp
- `jti`: Unique token ID (for revocation)
- `is_admin`: Admin flag
- `type`: "access" or "refresh"
- `scope`: "user", "application", or "internal"

## Using Tokens

### Authorization Header

Include the access token in all authenticated requests:

```bash
curl http://localhost:8000/api/protected-endpoint \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Token Expiration and Refresh

Access tokens expire after 24 hours (default). Use refresh tokens to obtain new access tokens:

```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Authorization: Bearer $REFRESH_TOKEN"
```

Response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "is_admin": false
}
```

Configure token expiration in `tinybase.toml`:

```toml
[auth]
jwt_access_token_expire_minutes = 1440  # 24 hours
jwt_refresh_token_expire_days = 30      # 30 days
jwt_secret_key = "your-secret-key-here" # Auto-generated if not provided
jwt_algorithm = "HS256"
```

### Logout and Token Revocation

Revoke all tokens for the current user:

```bash
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

This deletes all access and refresh tokens from the database, forcing the user to log in again.

## Current User

### Get Current User Info

```bash
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

Response:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "is_admin": false,
  "created_at": "2024-01-01T12:00:00Z"
}
```

## Admin Users

### Creating Admin Users

#### Via CLI (Recommended)

```bash
tinybase admin add admin@example.com secretpassword
```

#### Via Init Command

```bash
tinybase init --admin-email admin@example.com --admin-password secretpassword
```

#### Via Environment Variables

```bash
export TINYBASE_ADMIN_EMAIL=admin@example.com
export TINYBASE_ADMIN_PASSWORD=secretpassword
tinybase init
```

### Admin Privileges

Admin users can:

- Access all admin endpoints (`/api/admin/*`)
- Create, update, delete collections
- Manage all users
- Create and manage schedules
- View all function calls
- Access any record regardless of ownership

## Access Control

### Function Auth Levels

```python
# No authentication required
@register(name="public_func", auth="public", ...)

# Any authenticated user
@register(name="user_func", auth="auth", ...)

# Admin users only
@register(name="admin_func", auth="admin", ...)
```

### Collection Access Rules

```json
{
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

### Access Levels

| Level | Description |
|-------|-------------|
| `public` | No authentication required |
| `auth` | Any authenticated user |
| `owner` | Record owner only |
| `admin` | Admin users only |

## User Management (Admin)

### List All Users

```bash
curl http://localhost:8000/api/admin/users \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Get User Details

```bash
curl http://localhost:8000/api/admin/users/$USER_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Update User

```bash
curl -X PATCH http://localhost:8000/api/admin/users/$USER_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_admin": true}'
```

### Delete User

```bash
curl -X DELETE http://localhost:8000/api/admin/users/$USER_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## Authentication in Functions

Access user information via the Context:

```python
@register(name="user_action", auth="auth", ...)
def user_action(ctx: Context, payload: Input) -> Output:
    # Get current user ID
    user_id = ctx.user_id
    
    # Check admin status
    if ctx.is_admin:
        # Admin-specific logic
        pass
    
    # Query user from database
    from tinybase.db.models import User
    user = ctx.db.get(User, user_id)
    
    return Output(user_email=user.email)
```

### Conditional Admin Logic

```python
@register(name="get_data", auth="auth", ...)
def get_data(ctx: Context, payload: Input) -> Output:
    if ctx.is_admin:
        # Return all data for admins
        data = get_all_data()
    else:
        # Return only user's data
        data = get_user_data(ctx.user_id)
    
    return Output(data=data)
```

## Security Best Practices

### 1. Use Strong Passwords

Enforce minimum password requirements:

```python
from pydantic import BaseModel, field_validator


class RegisterInput(BaseModel):
    email: str
    password: str
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain a number")
        return v
```

### 2. Use HTTPS in Production

Always use HTTPS to protect tokens in transit:

```bash
# Behind nginx/caddy with TLS termination
[server]
host = "127.0.0.1"
port = 8000
```

### 3. Set Appropriate Token TTL

```toml
[auth]
# Shorter for sensitive applications
token_ttl_hours = 1

# Longer for convenience
token_ttl_hours = 168  # 1 week
```

### 4. Protect Admin Credentials

- Use environment variables for initial admin setup
- Change default passwords immediately
- Use unique passwords for each environment

### 5. Audit Access

Monitor function calls and user activity:

```python
@register(name="sensitive_action", auth="admin", ...)
def sensitive_action(ctx: Context, payload: Input) -> Output:
    # Log the action
    logger.info(f"Sensitive action by {ctx.user_id}: {payload}")
    
    # Perform action
    result = do_sensitive_thing()
    
    return Output(result=result)
```

## Logout

TinyBase provides a logout endpoint that revokes all tokens for the current user.

To logout:

```bash
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

This deletes all access and refresh tokens from the database, forcing the user to log in again to obtain new tokens.

## Error Responses

### Invalid Credentials (401)

```json
{
  "detail": "Invalid email or password"
}
```

### Token Expired (401)

```json
{
  "detail": "Token expired"
}
```

### Invalid Token (401)

```json
{
  "detail": "Invalid token"
}
```

### Insufficient Permissions (403)

```json
{
  "detail": "Admin access required"
}
```

## See Also

- [Collections Guide](collections.md) - Access control for data
- [Functions Guide](functions.md) - Auth levels for functions
- [REST API Reference](../reference/rest-api.md) - Complete auth endpoints

