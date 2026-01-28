# Packages

This directory contains the Python packages that make up TinyBase.

## Structure

```
packages/
├── tinybase/           # Core TinyBase package (FastAPI server + CLI)
│   ├── pyproject.toml  # Package configuration
│   ├── tests/          # Test suite
│   └── tinybase/       # Package source code
└── tinybase-sdk/       # Python SDK for writing TinyBase functions
    ├── pyproject.toml  # Package configuration
    ├── tests/          # SDK tests
    └── tinybase_sdk/   # SDK source code
```

## Packages

### tinybase

The core TinyBase package containing:

- **FastAPI Server** - REST API for collections, authentication, functions, and scheduling
- **CLI** - Command-line interface (`tinybase init`, `tinybase serve`, etc.)
- **Database** - SQLModel/SQLAlchemy models and migrations
- **Function Execution** - Isolated subprocess execution environment
- **Extension System** - Plugin architecture for extending TinyBase

### tinybase-sdk

The SDK used by TinyBase functions:

- **@register decorator** - Registers functions with metadata
- **Context** - Provides execution context to functions
- **Client** - Authenticated API client for calling back into TinyBase
- **CLI Runner** - Handles function invocation from subprocess

## Development

Both packages are managed as a uv workspace. Install all dependencies from the repository root:

```bash
uv sync --group dev
```

Run tests:

```bash
# All tests
uv run pytest

# Core package tests only
uv run pytest packages/tinybase/tests/

# SDK tests only
uv run pytest packages/tinybase-sdk/tests/
```

## Publishing

Packages are published to PyPI separately:

- `tinybase` - The main package users install
- `tinybase-sdk` - Automatically installed as a dependency of function scripts

See the root `pyproject.toml` for workspace configuration.
