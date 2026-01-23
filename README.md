# TinyBase

![GitHub License](https://img.shields.io/github/license/maximiliancw/tinybase)
![Codecov](https://img.shields.io/codecov/c/github/maximiliancw/tinybase)

**TinyBase is a lightweight, self-hosted Backend-as-a-Service (BaaS) framework designed for Python developers who want simplicity and ease-of-use.**

Build and deploy production-ready APIs in minutes with:

- 🚀 **Zero configuration** – Get started with a single command
- 🐍 **Python-first** – Write server-side functions in pure Python with full type safety
- 📦 **Easy deployment** – SQLite database + FastAPI backend in one package
- 🔒 **Built-in authentication** – JWT-based auth with access and refresh tokens
- ⚡ **Auto-scaling functions** – Isolated execution with automatic dependency management
- 🎨 **Modern Admin UI** – Beautiful Vue 3 interface for managing everything
- 📅 **Native scheduling** – Cron and interval-based task automation
- 🔌 **Extensible** – Hook into any part of the system with Python extensions

> 👉 **[Read the full documentation](https://maximiliancw.github.io/TinyBase/)**

## ✨ Features

### 🗄️ Data & Collections

- **Dynamic Collections** – Create schema-driven collections with JSON schemas, no migrations needed
- **Pydantic Validation** – Automatic validation for all records with detailed error messages
- **SQLite Backend** – Simple, reliable, and portable – your entire database in a single file
- **REST API** – Auto-generated CRUD endpoints for all collections

### 🔐 Authentication & Security

- **JWT Authentication** – Secure token-based auth with access and refresh tokens
- **User Management** – Built-in registration, login, and password reset flows
- **Role-Based Access** – Admin and user roles with fine-grained permissions
- **Token Revocation** – Logout endpoint that invalidates all user tokens
- **Rate Limiting** – Configurable concurrent execution limits per user

### ⚡ Serverless Functions

- **Type-Safe Functions** – Define functions with Pydantic models for inputs and outputs
- **Isolated Execution** – Each function runs in its own subprocess with dependency isolation
- **Automatic Dependencies** – Use `uv`'s inline script dependencies for zero-config package management
- **OpenAPI Integration** – All functions automatically documented and exposed as REST endpoints
- **Execution Tracking** – Full metadata for every function call (status, duration, errors)
- **Client API** – Built-in authenticated client for calling back into TinyBase

### 📅 Task Scheduling

- **Cron Expressions** – Standard cron syntax for complex scheduling patterns
- **Interval Scheduling** – Run functions every N seconds, minutes, hours, or days
- **One-Time Tasks** – Schedule functions to run once at a specific date and time
- **Timezone Support** – Full timezone awareness for all scheduled tasks
- **No External Dependencies** – Built-in scheduler, no Redis or Celery required

### 🎨 Admin UI

- **Modern Interface** – Beautiful SPA built with Vue 3, Pinia, and PicoCSS
- **Complete Management** – Manage collections, records, users, functions, and schedules
- **Function Monitoring** – View execution history, errors, and performance metrics
- **Settings Management** – Configure all instance settings through the UI
- **Responsive Design** – Works perfectly on desktop and mobile

### 🔧 Developer Experience

- **One Command Setup** – `tinybase init && tinybase serve` and you're running
- **Hot Reload** – Automatic server restart on code changes with `--reload` flag
- **Full OpenAPI Docs** – Interactive API documentation at `/docs`
- **CLI Tools** – Generate function boilerplate, manage users, run migrations
- **Docker Ready** – Multi-stage Dockerfile included for production deployments
- **Environment-Based Config** – Configure via `tinybase.toml` or environment variables

## 📦 Installation

**Using uv (recommended):**

```bash
uv add tinybase
```

**Using pip:**

```bash
pip install tinybase
```

**Requirements:**

- Python 3.11 or higher
- No additional dependencies required for basic usage

## 🚀 Quickstart

**1. Initialize your project:**

```bash
tinybase init --admin-email admin@example.com --admin-password admin123
```

This creates:

- `tinybase.toml` configuration file
- SQLite database with initial schema
- Admin user account
- `functions/` directory for your server-side functions

**2. Start the development server:**

```bash
tinybase serve --reload
```

**3. Access your instance:**

| Service         | URL                           |
| --------------  | ----------------------------- |
| 🎨 **Admin UI** | <http://localhost:8000/admin> |
| 📚 **API Docs** | <http://localhost:8000/docs>  |
| 🔌 **REST API** | <http://localhost:8000/api>   |

**4. Create your first function:**

```bash
tinybase functions new hello -d "Say hello"
```

That's it! You now have a fully functional backend with authentication, database, API, and admin interface.

> 📖 **[Follow the complete tutorial](https://maximiliancw.github.io/TinyBase/getting-started/quickstart/)**

## Configuration

TinyBase reads configuration from:

1. Environment variables.
2. `tinybase.toml` in the current directory.
3. Internal defaults.

Typical configuration options:

```toml
[server]
host = "0.0.0.0"
port = 8000
debug = false
log_level = "info"

[database]
url = "sqlite:///./tinybase.db"

[auth]
token_ttl_hours = 24

[functions]
path = "./functions"

[scheduler]
enabled = true
interval_seconds = 5
token_cleanup_interval = 60

[cors]
allow_origins = ["*"]

[admin]
static_dir = "builtin"   # or path to custom admin static files

[environments.production]
url = "https://tinybase.example.com"
api_token = "ADMIN_TOKEN"
```

Corresponding environment variables (examples):

- `TINYBASE_SERVER_HOST`
- `TINYBASE_SERVER_PORT`
- `TINYBASE_DB_URL`
- `TINYBASE_AUTH_TOKEN_TTL_HOURS`
- `TINYBASE_FUNCTIONS_PATH`
- `TINYBASE_SCHEDULER_ENABLED`
- `TINYBASE_SCHEDULER_INTERVAL_SECONDS`
- `TINYBASE_SCHEDULER_TOKEN_CLEANUP_INTERVAL`
- `TINYBASE_CORS_ALLOW_ORIGINS`
- `TINYBASE_ADMIN_STATIC_DIR`

Admin bootstrap (used by `tinybase init` if present):

- `TINYBASE_ADMIN_EMAIL`
- `TINYBASE_ADMIN_PASSWORD`

## Defining Functions

Functions are regular Python callables registered with the TinyBase SDK decorator and (automatically) exposed as HTTP endpoints and schedulable tasks. Each function should live in its own file within the `functions/` package directory generated by `tinybase init`.

Functions run in isolated subprocess environments with automatic dependency management using `uv`'s single-file script feature.

Example (`functions/add_numbers.py`):

```python
# /// script
# dependencies = [
#   "tinybase-sdk",
# ]
# ///

from pydantic import BaseModel
from tinybase_sdk import register
from tinybase_sdk.cli import run


class AddInput(BaseModel):
    x: int
    y: int


class AddOutput(BaseModel):
    sum: int


@register(
    name="add_numbers",
    description="Add two numbers",
    auth="auth",  # "public" | "auth" | "admin"
    tags=["math"],
)
def add_numbers(client, payload: AddInput) -> AddOutput:
    # Use client to make API calls back to TinyBase
    return AddOutput(sum=payload.x + payload.y)


if __name__ == "__main__":
    run()
```

This function is automatically exposed at:

- `POST /api/functions/add_numbers`

Request body:

```json
{
  "x": 1,
  "y": 2
}
```

Response:

```json
{
  "call_id": "<uuid>",
  "status": "succeeded",
  "result": {
    "sum": 3
  }
}
```

Function calls are also recorded as `FunctionCall` records for diagnostics (status, duration, errors).

### Generating boilerplate

Use the CLI to generate boilerplate for a new function:

```bash
tinybase functions new my_function -d "My example function"
```

This creates a new file `functions/my_function.py` with a typed function template using the SDK format.

## Scheduling

TinyBase supports scheduling functions using three methods:

- `once` (single run at a particular date/time).
- `interval` (every N seconds/minutes/hours/days).
- `cron` (cron expressions, via `croniter`).

Schedules are defined as JSON objects stored in the `schedule` field of `FunctionSchedule` and validated with Pydantic.

Examples:

Once:

```json
{
  "method": "once",
  "timezone": "Europe/Berlin",
  "date": "2025-11-25",
  "time": "08:00:00"
}
```

Interval:

```json
{
  "method": "interval",
  "timezone": "UTC",
  "unit": "hours",
  "value": 1
}
```

Cron:

```json
{
  "method": "cron",
  "timezone": "Europe/Berlin",
  "cron": "0 8 * * *",
  "description": "every day at 8am"
}
```

Admin endpoints for schedules:

- `GET /api/admin/schedules`
- `POST /api/admin/schedules`
- `GET /api/admin/schedules/{id}`
- `PATCH /api/admin/schedules/{id}`
- `DELETE /api/admin/schedules/{id}`

> **Note:** The scheduler runs as a background loop in TinyBase and triggers functions according to their schedule, creating `FunctionCall` records for each invocation.

## Collections and Records

TinyBase collections are **dynamic, schema-driven tables** stored in SQLite.

- Collections are defined with a JSON schema describing their fields and constraints.
- Pydantic models are generated at startup to validate records.
- CRUD endpoints are provided for each collection.

Example schema (`Collection.schema`):

```json
{
  "fields": [
    {
      "name": "title",
      "type": "string",
      "required": true,
      "max_length": 200
    },
    {
      "name": "published",
      "type": "boolean",
      "required": false,
      "default": false
    }
  ]
}
```

Associated endpoints:

- `GET /api/collections`
- `POST /api/collections` (admin)
- `GET /api/collections/{collection_name}`
- `GET /api/collections/{collection_name}/records`
- `POST /api/collections/{collection_name}/records`
- `GET /api/collections/{collection_name}/records/{id}`
- `PATCH /api/collections/{collection_name}/records/{id}`
- `DELETE /api/collections/{collection_name}/records/{id}`

## Admin UI

The admin UI is a single-page application built with:

- Vue 3
- Pinia
- Vite
- PicoCSS

Source:

- Located in the repository root under `/app`.

Build:

```bash
cd app
yarn install
yarn build
```

This produces a `/app/dist` directory, which should be copied into the Python package (e.g. `tinybase/static/app`) during the build process.

> Note: Per default, this is done automatically during the Docker build process.

At runtime, FastAPI serves the admin UI at:

- `GET /admin`

The admin UI allows administrators to:

- Log in.
- Manage collections and schemas.
- Inspect and edit records.
- View and manage users.
- View and manage functions.
- Configure schedules.
- Inspect function call metadata.

## 🛠️ Development

### Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](docs/contributing/index.md) for details.

### Setup

**Backend development:**

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
uv pip install -e ".[dev]"

# Initialize and run
tinybase init --admin-email admin@example.com --admin-password admin123
tinybase serve --reload
```

**Admin UI development:**

```bash
cd app
yarn install
yarn dev  # Start Vite dev server with hot reload
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=tinybase --cov-report=html

# Run specific test file
pytest tests/test_function_execution.py

# Run linting
ruff check .
```

Test coverage includes:

- ✅ Function execution and isolation
- ✅ Authentication and JWT flows  
- ✅ Collection CRUD operations
- ✅ Scheduling and cron parsing
- ✅ Rate limiting and resource management
- ✅ SDK decorator and CLI

## 🐳 Deployment

### Docker

The included `Dockerfile` provides a production-ready build:

**Build:**

```bash
docker build -t tinybase .
```

**Run:**

```bash
docker run -p 8000:8000 \
  -e TINYBASE_ADMIN_EMAIL=admin@example.com \
  -e TINYBASE_ADMIN_PASSWORD=admin123 \
  -v $(pwd)/data:/app/data \
  tinybase
```

The multi-stage build:

1. Builds the Vue admin UI with yarn
2. Creates a minimal Python runtime using uv
3. Bundles everything into a single optimized image

> 📖 **[View deployment guides](https://maximiliancw.github.io/TinyBase/deployment/)**

### Production Considerations

- Use environment variables for secrets (don't commit `tinybase.toml` with credentials)
- Mount a volume for persistent SQLite database storage
- Use a reverse proxy (nginx/Caddy) with HTTPS in production
- Consider Redis for rate limiting in multi-instance deployments
- Enable CORS only for trusted origins

## 🗺️ Roadmap

Planned improvements **may** include:

- 🔍 **Advanced Querying** – GraphQL support and complex filtering for collections
- 🔌 **WebSocket Support** – Real-time updates and subscriptions
- 📊 **Enhanced Monitoring** – Built-in metrics, logs, and performance dashboards
- 🧩 **Plugin Library** – Discover and install community extensions
- 🌍 **Multi-tenancy** – Built-in support for multi-tenant applications
- 🔄 **Database Replication** – SQLite replication for high availability
- 📱 **Mobile SDKs** – Native SDKs for iOS and Android
- 🤖 **AI Integration** – Built-in support for LLM function calling

Have a feature request? [Open an issue](https://github.com/maximiliancw/TinyBase/issues) or start a [discussion](https://github.com/maximiliancw/TinyBase/discussions)!

## 📄 License

TinyBase is released under the **MIT License**. See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

TinyBase is built on the shoulders of giants:

- [FastAPI](https://fastapi.tiangolo.com/) – Modern Python web framework
- [SQLModel](https://sqlmodel.tiangolo.com/) – SQL databases with Python type hints
- [Pydantic](https://pydantic.dev/) – Data validation and settings management
- [Vue 3](https://vuejs.org/) – Progressive JavaScript framework
- [uv](https://github.com/astral-sh/uv) – Fast Python package installer

## ⭐ Support

If you find TinyBase useful, please consider:

- ⭐ Starring the repository
- 🐛 Reporting bugs and issues
- 💡 Suggesting new features
- 📖 Improving documentation
- 🔀 Contributing code

