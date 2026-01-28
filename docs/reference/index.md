# API Reference

Complete reference documentation for TinyBase APIs and interfaces.

## Reference Sections

<div class="grid cards" markdown>

- :material-api: [**REST API**](rest-api.md)

  Complete HTTP endpoint documentation with request/response examples.

- :material-console: [**CLI Reference**](cli.md)

  Command-line interface documentation for all TinyBase commands.

- :material-language-python: [**Python API**](python-api.md)

  Python module reference for extending TinyBase.

</div>

## Quick Reference

### Base URLs

| Environment | URL                       |
| ----------- | ------------------------- |
| Development | `http://localhost:8000`   |
| Production  | `https://api.yourapp.com` |

### Authentication

```bash
# Include token in Authorization header
curl -H "Authorization: Bearer tb_your_token_here" \
  http://localhost:8000/api/...
```

### Common HTTP Status Codes

| Code  | Meaning                              |
| ----- | ------------------------------------ |
| `200` | Success                              |
| `201` | Created                              |
| `400` | Bad Request (validation error)       |
| `401` | Unauthorized (invalid/missing token) |
| `403` | Forbidden (insufficient permissions) |
| `404` | Not Found                            |
| `422` | Validation Error                     |
| `500` | Internal Server Error                |

### Response Format

Success response:

```json
{
  "data": { ... },
  "meta": {
    "total": 100,
    "page": 1
  }
}
```

Error response:

```json
{
  "detail": "Error message here"
}
```

## OpenAPI Documentation

TinyBase provides interactive API documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## Versioning

The current API version is **v1** (implicit in all routes).

Future versions will be introduced as `/api/v2/...` when needed.
