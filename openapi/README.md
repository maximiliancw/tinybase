# OpenAPI Contract

This directory contains the canonical OpenAPI specification for the TinyBase API.

## Files

- `openapi.json` - The OpenAPI 3.x specification (auto-generated)

## Regenerating the Spec

To regenerate the OpenAPI specification from the FastAPI application:

```bash
# Using Make
make export-openapi

# Using the script directly
uv run python scripts/export_openapi.py
```

## Verification

CI verifies that the committed `openapi.json` matches the generated output:

```bash
uv run python scripts/export_openapi.py --check
```

If the spec is out of date, regenerate it and commit the changes.

## Usage

The OpenAPI spec is used to generate typed API clients:

- **TypeScript client**: `clients/typescript/` - Auto-generated for frontend applications
- **Python SDK**: `packages/tinybase-sdk/` - Hand-crafted SDK that wraps an auto-generated client

## Versioning

The OpenAPI spec follows the same versioning as the TinyBase package. When releasing a new version:

1. Ensure the spec is up to date (`make export-openapi`)
1. Commit the updated `openapi.json`
1. Tag the release - the tag points to the exact spec at that time
