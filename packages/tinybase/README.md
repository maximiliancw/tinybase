# TinyBase Core Package

The core TinyBase Python package containing the FastAPI server, CLI, and all backend functionality.

## Structure

```text
tinybase/
├── pyproject.toml      # Package configuration and dependencies
├── tests/              # Test suite
│   ├── conftest.py     # Shared pytest fixtures
│   └── test_*.py       # Test modules
└── tinybase/           # Package source
    ├── __init__.py
    ├── api/            # FastAPI routes and app configuration
    │   ├── app.py      # Application factory
    │   └── routes/     # Route handlers
    ├── auth/           # Authentication (JWT, password hashing)
    ├── cli/            # Typer CLI commands
    ├── collections/    # Dynamic collection service
    ├── db/             # SQLModel models and database core
    ├── extensions/     # Extension/plugin system
    ├── functions/      # Function registry and execution
    ├── migrations/     # Alembic database migrations
    ├── schedule/       # Task scheduling
    ├── settings/       # Configuration management
    ├── static/         # Static files (admin UI gets copied here)
    └── templates/      # Email templates
```

## Key Components

### API (`api/`)

FastAPI application with routes for:

- `/api/auth/*` - Authentication endpoints
- `/api/collections/*` - Collection CRUD
- `/api/functions/*` - Function execution
- `/api/admin/*` - Admin-only endpoints
- `/admin` - Admin UI (static files)

### CLI (`cli/`)

Typer-based command-line interface:

- `tinybase init` - Initialize a new instance
- `tinybase serve` - Start the server
- `tinybase functions new` - Generate function boilerplate
- `tinybase db migrate/upgrade` - Database migrations
- `tinybase admin add` - Create admin users
- `tinybase extensions install` - Manage extensions

### Database (`db/`)

SQLModel models and SQLite database management:

- `User`, `Collection`, `Record`, `FunctionCall`, `FunctionSchedule`
- Automatic schema migrations with Alembic

### Functions (`functions/`)

Serverless function infrastructure:

- Function discovery and registration
- Isolated subprocess execution
- Cold start pool optimization
- Dependency management via uv

## Development

From the repository root:

```bash
# Install dependencies
uv sync --group dev

# Run the server
uv run tinybase serve --reload

# Run tests
uv run pytest packages/tinybase/tests/
```

## Building

The package uses hatchling for building:

```bash
uv build -p packages/tinybase
```

## Static Files

The `static/app/` directory contains a `.gitkeep` placeholder. During the build process (Docker or `make build-admin`), the compiled Vue admin UI is copied here.
