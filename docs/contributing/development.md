# Development Setup

This guide covers setting up a development environment for contributing to TinyBase.

## Prerequisites

- **Python 3.11+** - Required for development
- **Node.js 18+** - For the Admin UI
- **uv** - Package manager (recommended)
- **Git** - Version control

## Clone the Repository

```bash
# Clone from GitHub
git clone https://github.com/maximiliancw/tinybase.git
cd tinybase

# Or clone your fork
git clone https://github.com/YOUR_USERNAME/tinybase.git
cd tinybase
```

## Backend Setup

### Using uv (Recommended)

```bash
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv

# Activate
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install with dev dependencies
uv pip install -e ".[dev]"
```

### Using pip

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"
```

## Admin UI Setup

The Admin UI is in the `/apps/admin` directory:

```bash
cd apps/admin

# Install dependencies
yarn install

# Start development server (with hot reload)
yarn dev
```

The dev server runs at `http://localhost:5173` and proxies API requests to `http://localhost:8000`.

## Running TinyBase

### Initialize and Start

```bash
# Initialize (from project root)
tinybase init --admin-email dev@example.com --admin-password devpassword

# Start with auto-reload
tinybase serve --reload
```

### Development URLs

| Service | URL |
|---------|-----|
| API | `http://localhost:8000` |
| API Docs | `http://localhost:8000/docs` |
| Admin UI (dev) | `http://localhost:5173` |
| Admin UI (prod) | `http://localhost:8000/admin` |

## Project Structure

```
tinybase/
├── packages/
│   ├── tinybase/              # Main Python package
│   │   ├── pyproject.toml     # Package config
│   │   ├── tests/             # Test suite
│   │   └── tinybase/          # Package source
│   │       ├── __init__.py
│   │       ├── api/           # FastAPI routes
│   │       ├── cli/           # CLI commands
│   │       ├── collections/   # Collections service
│   │       ├── db/            # Database models
│   │       ├── extensions/    # Extension system
│   │       ├── functions/     # Function registration
│   │       ├── migrations/    # Alembic migrations
│   │       └── schedule/      # Schedule management
│   └── tinybase-sdk/          # Python SDK package
│       ├── pyproject.toml
│       ├── tests/
│       └── tinybase_sdk/
├── apps/
│   └── admin/                 # Admin UI (Vue)
│       ├── src/
│       │   ├── views/         # Page components
│       │   ├── stores/        # Pinia stores
│       │   └── router/        # Vue Router
│       └── package.json
├── clients/
│   └── typescript/            # Auto-generated TS client
├── openapi/                   # OpenAPI contract
├── scripts/                   # Repo management scripts
├── docs/                      # Documentation
├── Makefile                   # Common commands
├── pyproject.toml             # Workspace config
└── mkdocs.yml                 # Docs config
```

## Development Workflow

### 1. Create a Branch

```bash
# Update main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/my-feature

# Or bugfix branch
git checkout -b fix/issue-123
```

### 2. Make Changes

- Write code
- Add tests
- Update documentation

### 3. Run Tests

```bash
# Run all tests (parallel execution recommended)
uv run pytest -n auto

# Run with coverage
uv run pytest --cov=packages/tinybase/tinybase

# Run specific test file
uv run pytest packages/tinybase/tests/test_functions.py

# Run specific test
uv run pytest packages/tinybase/tests/test_functions.py::test_register_function
```

### 4. Check Code Quality

```bash
# Format and lint
ruff check --fix .
ruff format .

# Type checking (if using)
mypy tinybase/
```

### 5. Commit Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: add support for custom validators"

# Push to your fork
git push origin feature/my-feature
```

### 6. Open Pull Request

1. Go to GitHub
2. Click "Compare & pull request"
3. Fill out the template
4. Submit for review

## Common Tasks

### Adding a New API Endpoint

1. Create/edit route handler in `packages/tinybase/tinybase/api/routes/`
2. Register route in `packages/tinybase/tinybase/api/app.py`
3. Add tests in `packages/tinybase/tests/`
4. Update API documentation

### Adding a New CLI Command

1. Add command to the appropriate module in `packages/tinybase/tinybase/cli/`:
   - Core commands → `main.py`
   - Functions commands → `functions.py`
   - Database commands → `db.py`
   - Admin commands → `admin.py`
   - Extensions commands → `extensions.py`
2. Follow existing patterns for Typer commands
3. Add tests in `packages/tinybase/tests/`
4. Update CLI documentation

### Adding a Database Migration

```bash
# Make model changes in packages/tinybase/tinybase/db/models.py

# Generate migration
uv run tinybase db migrate -m "description of change"

# Apply migration
uv run tinybase db upgrade
```

### Building the Admin UI

```bash
# Using Make (recommended)
make build-admin

# Or manually
cd apps/admin
yarn build
```

Built files go to `apps/admin/dist/`. The `make build-admin` command also copies them to `packages/tinybase/tinybase/static/app/`. If using Docker, this is done automatically.

## Debugging

### Server Logs

```bash
# Enable debug logging
TINYBASE_DEBUG=true TINYBASE_LOG_LEVEL=debug tinybase serve
```

### Database Inspection

```bash
# Open SQLite shell
sqlite3 tinybase.db

# View tables
.tables

# Query data
SELECT * FROM user LIMIT 5;
```

### VS Code Launch Config

```json title=".vscode/launch.json"
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "TinyBase Server",
      "type": "python",
      "request": "launch",
      "module": "tinybase.cli",
      # Note: tinybase.cli is now a subpackage, but the entry point remains the same
      "args": ["serve", "--reload"],
      "console": "integratedTerminal"
    },
    {
      "name": "pytest",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["-v"],
      "console": "integratedTerminal"
    }
  ]
}
```

## Documentation

### Running Docs Locally

```bash
# Install docs dependencies
uv pip install -e ".[docs]"

# Or with the docs group
uv add --group docs mkdocs mkdocs-material

# Serve documentation
mkdocs serve
```

Access at `http://localhost:8000`.

### Building Docs

```bash
mkdocs build
```

Built docs are in `site/`.

## Troubleshooting

### Virtual Environment Issues

```bash
# Remove and recreate
rm -rf .venv
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Database Issues

```bash
# Reset database
rm tinybase.db
tinybase init
```

### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 PID
```

### Node Module Issues

```bash
# Clear and reinstall
cd apps/admin
rm -rf node_modules
yarn install
```

## See Also

- [Architecture](architecture.md) - Understanding the codebase
- [Testing](testing.md) - Writing tests
- [Code Style](code-style.md) - Coding conventions

