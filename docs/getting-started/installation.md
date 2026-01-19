# Installation

This guide covers the different ways to install TinyBase and set up your development environment.

## Requirements

- **Python 3.11 or later** - TinyBase uses modern Python features
- **pip, uv, or pipx** - For package installation

## Installation Methods

### Using pip (Standard)

The simplest way to install TinyBase:

```bash
pip install tinybase
```

### Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package manager from Astral:

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install TinyBase
uv add tinybase
```

!!! tip "Why uv?"
    uv is 10-100x faster than pip and provides better dependency resolution. TinyBase is designed to work seamlessly with uv.

### Using pipx (Isolated Installation)

For CLI-only usage without affecting your project dependencies:

```bash
pipx install tinybase
```

### From Source (Development)

For contributing or development:

```bash
# Clone the repository
git clone https://github.com/maximiliancw/tinybase.git
cd tinybase

# Install with development dependencies
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -e ".[dev]"
```

## Verify Installation

After installation, verify TinyBase is working:

```bash
tinybase version
```

You should see output like:

```
TinyBase v0.3.0
```

## Project Setup

### Initialize a New Project

Create a new TinyBase project:

```bash
mkdir my-project
cd my-project
tinybase init
```

This creates the following structure:

```
my-project/
├── tinybase.toml      # Configuration file
├── tinybase.db        # SQLite database
├── functions.py       # Main functions file
└── functions/         # Additional function modules
```

### Initialize with Admin User

You can create an admin user during initialization:

```bash
tinybase init --admin-email admin@example.com --admin-password secretpassword
```

Or use environment variables:

```bash
export TINYBASE_ADMIN_EMAIL=admin@example.com
export TINYBASE_ADMIN_PASSWORD=secretpassword
tinybase init
```

## Docker Installation

TinyBase includes a Dockerfile for containerized deployments:

```bash
# Build the image
docker build -t tinybase .

# Run the container
docker run -p 8000:8000 -v $(pwd)/data:/app/data tinybase
```

See the [Docker Deployment Guide](../deployment/docker.md) for more details.

## Dependencies

TinyBase automatically installs these core dependencies:

| Package | Purpose |
|---------|---------|
| FastAPI | Web framework |
| Uvicorn | ASGI server |
| SQLModel | Database ORM |
| Pydantic | Data validation |
| Typer | CLI framework |
| bcrypt | Password hashing |
| croniter | Cron expression parsing |

## Optional Dependencies

For development, install additional tools:

```bash
# Using pip
pip install tinybase[dev]

# Using uv
uv add tinybase --group dev
```

This includes:

- `pytest` - Testing framework
- `httpx` - HTTP client for tests
- `ruff` - Linter and formatter

## Troubleshooting

### Python Version Error

If you see an error about Python version:

```
ERROR: Package 'tinybase' requires a different Python: 3.10.0 not in '>=3.11'
```

**Solution**: Install Python 3.11+ and ensure it's active:

```bash
# Using pyenv
pyenv install 3.11
pyenv local 3.11

# Using uv
uv python install 3.11
```

### Permission Errors

If you encounter permission errors during installation:

```bash
# Use --user flag with pip
pip install --user tinybase

# Or use a virtual environment
python -m venv .venv
source .venv/bin/activate
pip install tinybase
```

### Database Errors

If the database fails to initialize:

1. Ensure you have write permissions in the directory
2. Delete any corrupted `tinybase.db` file
3. Run `tinybase init` again

## Next Steps

- [Quickstart Tutorial](quickstart.md) - Build your first app
- [Configuration Guide](configuration.md) - Customize TinyBase
- [Docker Deployment](../deployment/docker.md) - Deploy with containers

