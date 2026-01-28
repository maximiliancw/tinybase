<h1 align="center">TinyBase</h1>

<p align="center">
  <strong><i>Deploy Python-based backends in minutes</i></strong>
</p>

<p align="center">
  <a href="https://github.com/maximiliancw/tinybase/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/maximiliancw/tinybase/ci.yml?branch=staging&label=CI" alt="CI"></a>
  <a href="https://codecov.io/gh/maximiliancw/tinybase"><img src="https://img.shields.io/codecov/c/github/maximiliancw/tinybase" alt="Codecov"></a>
  <a href="https://github.com/maximiliancw/tinybase/blob/main/LICENSE"><img src="https://img.shields.io/github/license/maximiliancw/tinybase" alt="License"></a>
</p>

<p align="center">
  TinyBase is a Python-based Backend-as-a-Service (BaaS) framework with typed functions, built-in scheduling, and a modern admin UI.
</p>

<p align="center">
  <a href="https://maximiliancw.github.io/TinyBase/">Documentation</a> •
  <a href="https://maximiliancw.github.io/TinyBase/getting-started/quickstart/">Quickstart</a> •
  <a href="https://github.com/maximiliancw/TinyBase/issues">Issues</a> •
  <a href="https://github.com/maximiliancw/TinyBase/discussions">Discussions</a>
</p>

______________________________________________________________________

## Installation

```bash
# Using uv (recommended)
uv add tinybase

# Using pip
pip install tinybase
```

**Requirements:** Python 3.11+

## Quickstart

```bash
# Initialize your project
tinybase init --admin-email admin@example.com --admin-password admin123

# Start the server
tinybase serve --reload
```

That's it! Your backend is running:

| Service  | URL                           |
| -------- | ----------------------------- |
| Admin UI | <http://localhost:8000/admin> |
| API Docs | <http://localhost:8000/docs>  |
| REST API | <http://localhost:8000/api>   |

> **[Follow the complete tutorial](https://maximiliancw.github.io/TinyBase/getting-started/quickstart/)**

## Why TinyBase?

| Feature               | TinyBase       | PocketBase | Supabase         | Appwrite       |
| --------------------- | -------------- | ---------- | ---------------- | -------------- |
| Language              | Python         | Go         | PostgreSQL/Deno  | MariaDB/Multi  |
| Self-hosted           | Yes            | Yes        | Yes              | Yes            |
| Single File Deploy    | Yes (SQLite)   | Yes        | No               | No             |
| Typed Functions       | Yes (Pydantic) | No         | Yes (TypeScript) | Yes            |
| Python SDK            | Native         | Community  | Official         | Official       |
| Built-in Scheduling   | Yes            | No         | Limited          | Yes            |
| Zero Config Start     | Yes            | Yes        | No               | No             |
| External Dependencies | None           | None       | PostgreSQL, etc. | Redis, MariaDB |

**TinyBase is ideal for:**

- **Python developers** who want a backend without learning Go or managing PostgreSQL
- **Small to medium projects** that don't need cloud-scale complexity
- **Prototypes and MVPs** where development speed matters
- **Self-hosted apps** where you need full control over your data

## Key Features

### Python-First Development

Write server-side functions with Pydantic models for full type safety and IDE support. No new language to learn.

```python
@register(name="greet", auth="public")
def greet(client, payload: GreetInput) -> GreetOutput:
    return GreetOutput(message=f"Hello, {payload.name}!")
```

### Zero Infrastructure

SQLite database + single Python process. No Redis, PostgreSQL, or Docker required for development. Your entire backend in one command.

### Isolated Function Execution

Each function runs in its own subprocess with automatic dependency management via `uv`. Add any PyPI package with inline script metadata.

### Built-in Task Scheduling

Cron expressions, intervals, and one-time tasks — no external job queue needed. Full timezone support.

### Modern Admin UI

Vue 3 dashboard with visual schema editor, function monitoring, user management, and real-time activity feed.

## Documentation

| Topic                                                                           | Description                    |
| ------------------------------------------------------------------------------- | ------------------------------ |
| [Getting Started](https://maximiliancw.github.io/TinyBase/getting-started/)     | Installation and first steps   |
| [Collections](https://maximiliancw.github.io/TinyBase/guide/collections/)       | Schema-driven data modeling    |
| [Functions](https://maximiliancw.github.io/TinyBase/guide/functions/)           | Type-safe serverless functions |
| [Scheduling](https://maximiliancw.github.io/TinyBase/guide/scheduling/)         | Cron and interval tasks        |
| [Authentication](https://maximiliancw.github.io/TinyBase/guide/authentication/) | JWT auth and user management   |
| [Extensions](https://maximiliancw.github.io/TinyBase/guide/extensions/)         | Extend TinyBase with plugins   |
| [Deployment](https://maximiliancw.github.io/TinyBase/deployment/)               | Docker and production setup    |
| [API Reference](https://maximiliancw.github.io/TinyBase/reference/)             | CLI, REST API, Python API      |

## Example Function

```python
# functions/add_numbers.py
# /// script
# dependencies = ["tinybase-sdk"]
# ///

from pydantic import BaseModel
from tinybase_sdk import register
from tinybase_sdk.cli import run


class AddInput(BaseModel):
    x: int
    y: int


class AddOutput(BaseModel):
    sum: int


@register(name="add_numbers", description="Add two numbers", auth="auth")
def add_numbers(client, payload: AddInput) -> AddOutput:
    return AddOutput(sum=payload.x + payload.y)


if __name__ == "__main__":
    run()
```

Call via REST API:

```bash
curl -X POST http://localhost:8000/api/functions/add_numbers \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"x": 1, "y": 2}'
```

<details>
<summary><strong>All Features</strong></summary>

### Data & Collections

- **Dynamic Collections** – Create schema-driven collections with JSON schemas, no migrations needed
- **Pydantic Validation** – Automatic validation for all records with detailed error messages
- **Unique Constraints** – Enforce unique values with automatic index management
- **Collection References** – Foreign key-like relationships between collections
- **SQLite Backend** – Simple, reliable, and portable – your entire database in a single file
- **REST API** – Auto-generated CRUD endpoints for all collections

### Authentication & Security

- **JWT Authentication** – Secure token-based auth with access and refresh tokens
- **User Management** – Built-in registration, login, and password reset flows
- **Role-Based Access** – Admin and user roles with fine-grained permissions
- **Rate Limiting** – Configurable concurrent execution limits per user

### Serverless Functions

- **Type-Safe Functions** – Define functions with Pydantic models for inputs and outputs
- **Isolated Execution** – Each function runs in its own subprocess with dependency isolation
- **Automatic Dependencies** – Use `uv`'s inline script dependencies for zero-config package management
- **OpenAPI Integration** – All functions automatically documented and exposed as REST endpoints
- **Execution Tracking** – Full metadata for every function call (status, duration, errors)
- **Cold Start Pool** – Pre-warmed function processes for faster execution

### Task Scheduling

- **Cron Expressions** – Standard cron syntax for complex scheduling patterns
- **Interval Scheduling** – Run functions every N seconds, minutes, hours, or days
- **One-Time Tasks** – Schedule functions to run once at a specific date and time
- **Timezone Support** – Full timezone awareness for all scheduled tasks
- **No External Dependencies** – Built-in scheduler, no Redis or Celery required

### Admin UI

- **Modern Interface** – Beautiful SPA built with Vue 3, Pinia, Tailwind CSS, and shadcn/vue
- **Visual Schema Editor** – Create and edit collection schemas with a visual interface
- **Function Monitoring** – View execution history, errors, and performance metrics
- **Activity Feed** – Real-time dashboard with recent activity across your instance
- **Responsive Design** – Works perfectly on desktop and mobile

### Developer Experience

- **Hot Reload** – Automatic server restart on code changes with `--reload` flag
- **Full OpenAPI Docs** – Interactive API documentation at `/docs`
- **CLI Tools** – Generate function boilerplate, manage users, run migrations
- **Docker Ready** – Multi-stage Dockerfile included for production deployments
- **Environment-Based Config** – Configure via `tinybase.toml` or environment variables

</details>

## Configuration

TinyBase uses a two-layer configuration system:

1. **Static Config** – File-based (`tinybase.toml`) or environment variables (`TINYBASE_*`), loaded at startup
1. **Runtime Settings** – Database-backed, changeable via Admin UI without restart

```bash
# Key environment variables
TINYBASE_SERVER_HOST=0.0.0.0
TINYBASE_SERVER_PORT=8000
TINYBASE_DB_URL=sqlite:///./tinybase.db
TINYBASE_JWT_SECRET_KEY=your-secret-key
```

> **[Full configuration reference](https://maximiliancw.github.io/TinyBase/getting-started/configuration/)**

## Development

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/maximiliancw/tinybase.git
cd tinybase
uv sync --group dev

# Initialize and run
uv run tinybase init --admin-email admin@example.com --admin-password admin123
make dev
```

### Project Structure

```text
tinybase/
├── packages/
│   ├── tinybase/           # Core Python package
│   └── tinybase-sdk/       # SDK for writing functions
├── apps/
│   └── admin/              # Vue 3 Admin UI
├── clients/
│   └── typescript/         # Auto-generated TypeScript client
├── docs/                   # Documentation (MkDocs)
└── Makefile                # Common commands
```

### Commands

```bash
make dev              # Start backend + frontend dev servers
make test             # Run all tests in parallel
make lint             # Lint Python and Markdown files
make build-admin      # Build admin UI
```

> **[Contributing guide](https://maximiliancw.github.io/TinyBase/contributing/)**

## Deployment

```bash
# Build Docker image
docker build -t tinybase .

# Run container
docker run -p 8000:8000 \
  -e TINYBASE_ADMIN_EMAIL=admin@example.com \
  -e TINYBASE_ADMIN_PASSWORD=admin123 \
  -v $(pwd)/data:/home/tinybase/data \
  tinybase
```

> **[Deployment guides](https://maximiliancw.github.io/TinyBase/deployment/)**

## Roadmap

- **Advanced Querying** – GraphQL support and complex filtering
- **WebSocket Support** – Real-time updates and subscriptions
- **Enhanced Monitoring** – Built-in metrics and performance dashboards
- **Plugin Library** – Discover and install community extensions
- **Multi-tenancy** – Built-in support for multi-tenant applications
- **Mobile SDKs** – Native SDKs for iOS and Android

[Open an issue](https://github.com/maximiliancw/TinyBase/issues) or start a [discussion](https://github.com/maximiliancw/TinyBase/discussions)!

## License

TinyBase is released under the **MIT License**. See [LICENSE](LICENSE) for details.

## Acknowledgments

Built with [FastAPI](https://fastapi.tiangolo.com/), [SQLModel](https://sqlmodel.tiangolo.com/), [Pydantic](https://pydantic.dev/), [Vue 3](https://vuejs.org/), [Tailwind CSS](https://tailwindcss.com/), [shadcn/vue](https://www.shadcn-vue.com/), and [uv](https://github.com/astral-sh/uv).

______________________________________________________________________

<p align="center">
  <strong>If you find TinyBase useful, please consider <a href="https://github.com/maximiliancw/tinybase">starring the repository</a>!</strong>
</p>
