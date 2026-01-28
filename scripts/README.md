# Scripts

This directory contains repository management scripts for TinyBase development.

## Available Scripts

### `repo.py` - Repository Management CLI

A Typer-based CLI for common repository management tasks.

```bash
# Run via Make
make repo <command>

# Or directly with uv
uv run python scripts/repo.py <command>
```

**Commands:**

- `build-admin` - Build the admin UI and copy to the backend static folder
- `version bump <part>` - Bump version across all packages (major/minor/patch)
- `release` - Run the full release pipeline

### `export_openapi.py` - OpenAPI Spec Export

Exports the OpenAPI specification from the FastAPI application.

```bash
# Generate openapi/openapi.json
uv run python scripts/export_openapi.py

# Verify spec is up-to-date (used in CI)
uv run python scripts/export_openapi.py --check
```

## Using Make

The root `Makefile` provides convenient shortcuts:

```bash
# Build admin UI
make build-admin

# Export OpenAPI spec
make export-openapi

# Run tests
make test

# Start development server
make dev

# Pass through to repo.py
make repo version bump patch
```

## Adding New Scripts

When adding new scripts:

1. Create the script in this directory
1. Add a corresponding Make target if appropriate
1. Document the script in this README
1. If the script has CLI options, use Typer for consistency

Example:

```python
#!/usr/bin/env python3
"""Description of what this script does."""

import typer

app = typer.Typer(help="Script description")

@app.command()
def main(
    option: str = typer.Option(..., help="Option description"),
):
    """Command description."""
    pass

if __name__ == "__main__":
    app()
```
