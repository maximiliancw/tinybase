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
- **Unique Constraints** – Enforce unique values with automatic index management
- **Collection References** – Foreign key-like relationships between collections
- **Collection Health Monitoring** – Built-in status endpoints for constraint and index health
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
- **Cold Start Pool** – Pre-warmed function processes for faster execution

### 📅 Task Scheduling

- **Cron Expressions** – Standard cron syntax for complex scheduling patterns
- **Interval Scheduling** – Run functions every N seconds, minutes, hours, or days
- **One-Time Tasks** – Schedule functions to run once at a specific date and time
- **Timezone Support** – Full timezone awareness for all scheduled tasks
- **No External Dependencies** – Built-in scheduler, no Redis or Celery required

### 🎨 Admin UI

- **Modern Interface** – Beautiful SPA built with Vue 3, Pinia, Tailwind CSS, and shadcn/vue
- **Complete Management** – Manage collections, records, users, functions, and schedules
- **Activity Feed** – Real-time dashboard with recent activity across your instance
- **Function Monitoring** – View execution history, errors, and performance metrics
- **Visual Schema Editor** – Create and edit collection schemas with a visual interface
- **Extension Settings** – Configure extension settings through the UI
- **Settings Management** – Configure all instance settings through the UI
- **Responsive Design** – Works perfectly on desktop and mobile

### 🔧 Developer Experience

- **One Command Setup** – `tinybase init && tinybase serve` and you're running
- **Hot Reload** – Automatic server restart on code changes with `--reload` flag
- **Full OpenAPI Docs** – Interactive API documentation at `/docs`
- **OpenAPI Export** – Export your API spec for client generation
- **CLI Tools** – Generate function boilerplate, manage users, run migrations
- **Docker Ready** – Multi-stage Dockerfile included for production deployments
- **Environment-Based Config** – Configure via `tinybase.toml` or environment variables
- **Static File Serving** – Optionally serve static files at the root path
- **Email Templates** – Jinja2-based customizable email templates

### 📊 Activity Logging

- **Automatic Tracking** – User actions and system events are logged automatically
- **Extension Integration** – Extensions can log custom activities
- **Dashboard Feed** – View recent activity directly in the Admin UI
- **Audit Trail** – Track who did what and when

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
| --------------- | ----------------------------- |
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

TinyBase uses a **two-layer configuration system**:

### Static Config (`config`)

File-based configuration loaded once at startup. Changes require a server restart.

**Sources** (in order of precedence):

1. Environment variables (`TINYBASE_*`)
1. `tinybase.toml` in the current directory
1. Internal defaults

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

[jwt]
algorithm = "HS256"
access_token_expire_minutes = 1440  # 24 hours
refresh_token_expire_days = 30

[functions]
dir = "./functions"
logging_enabled = true
logging_level = "INFO"
logging_format = "json"
cold_start_pool_size = 3
cold_start_ttl_seconds = 300

[scheduler]
enabled = true
interval_seconds = 5

[rate_limit]
backend = "diskcache"  # or "redis"
cache_dir = "./.tinybase/rate_limit_cache"
# redis_url = "redis://localhost:6379/0"  # required when backend=redis

[cors]
allow_origins = ["*"]

[admin]
static_dir = "builtin"

[extensions]
enabled = true
dir = "./.tinybase/extensions"

[public]
static_dir = ""  # Set to serve static files at root path (e.g., "./public")

[email]
enabled = false
# smtp_host = "smtp.example.com"
# smtp_port = 587
# smtp_user = "user"
# smtp_password = "password"
# from_address = "noreply@example.com"
# from_name = "TinyBase"
```

**Environment variables** (override TOML values):

| Variable                      | Description                                    |
| ----------------------------- | ---------------------------------------------- |
| `TINYBASE_SERVER_HOST`        | Server bind host                               |
| `TINYBASE_SERVER_PORT`        | Server bind port                               |
| `TINYBASE_DEBUG`              | Enable debug mode                              |
| `TINYBASE_LOG_LEVEL`          | Logging level                                  |
| `TINYBASE_DB_URL`             | Database connection URL                        |
| `TINYBASE_JWT_SECRET_KEY`     | JWT signing secret (auto-generated if not set) |
| `TINYBASE_FUNCTIONS_DIR`      | Path to functions directory                    |
| `TINYBASE_SCHEDULER_ENABLED`  | Enable/disable scheduler                       |
| `TINYBASE_RATE_LIMIT_BACKEND` | Rate limit backend (`diskcache` or `redis`)    |
| `TINYBASE_CORS_ALLOW_ORIGINS` | Comma-separated list of allowed origins        |
| `TINYBASE_EXTENSIONS_DIR`     | Path to extensions directory                   |
| `TINYBASE_PUBLIC_STATIC_DIR`  | Path to public static files directory          |
| `TINYBASE_ADMIN_EMAIL`        | Admin email for bootstrap                      |
| `TINYBASE_ADMIN_PASSWORD`     | Admin password for bootstrap                   |

### Runtime Settings (`settings`)

Database-backed settings that can be changed at runtime via the Admin UI or API. No restart required.

**Access in code:**

```python
from tinybase.settings import settings

# Core settings (typed properties)
settings.instance_name              # "TinyBase"
settings.auth.allow_public_registration  # True
settings.auth.portal.enabled        # False
settings.storage.enabled            # False
settings.scheduler.function_timeout_seconds  # 1800
settings.limits.max_concurrent_functions_per_user  # 10

# Extension settings (via get/set)
settings.get("ext.my_extension.api_key")  # Returns AppSetting | None
settings.set("ext.my_extension.api_key", "xxx")
```

**Core runtime settings:**

| Setting                                         | Default      | Description                                         |
| ----------------------------------------------- | ------------ | --------------------------------------------------- |
| `core.instance_name`                            | `"TinyBase"` | Instance display name                               |
| `core.auth.allow_public_registration`           | `true`       | Allow public user registration                      |
| `core.auth.portal.*`                            | —            | Auth portal customization (logo, colors, redirects) |
| `core.storage.*`                                | —            | S3-compatible storage configuration                 |
| `core.scheduler.function_timeout_seconds`       | `1800`       | Max function execution time                         |
| `core.limits.max_concurrent_functions_per_user` | `10`         | Concurrent function limit per user                  |
| `core.jobs.admin_report.enabled`                | `true`       | Enable periodic admin report emails                 |

Extensions can register their own settings under the `ext.*` namespace.

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
- Unique constraints are enforced with automatic index management.
- Foreign key-like references between collections are supported.

**Supported field types:** `string`, `number`, `integer`, `boolean`, `array`, `object`, `date`, `reference`

**Field options:** `required`, `unique`, `default`, `min`, `max`, `min_length`, `max_length`, `pattern`, `collection`

Example schema (`Collection.schema`):

```json
{
  "fields": [
    {
      "name": "email",
      "type": "string",
      "required": true,
      "unique": true,
      "pattern": "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$"
    },
    {
      "name": "score",
      "type": "number",
      "min": 0,
      "max": 100
    },
    {
      "name": "tags",
      "type": "array",
      "default": []
    },
    {
      "name": "author_id",
      "type": "reference",
      "collection": "users"
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
- `GET /api/admin/collections/status` (admin - health monitoring)
- `GET /api/admin/collections/{collection_name}/status` (admin - detailed status)

## Admin UI

The admin UI is a single-page application built with:

- Vue 3
- Pinia
- Vite
- Tailwind CSS
- shadcn/vue (via reka-ui)

Source:

- Located in the repository under `/apps/admin`.

Build:

```bash
cd apps/admin
yarn install
yarn build
```

Or using Make:

```bash
make build-admin
```

This produces an `/apps/admin/dist` directory, which is copied into the Python package (`packages/tinybase/tinybase/static/app`) during the build process.

> Note: Per default, this is done automatically during the Docker build process.

At runtime, FastAPI serves the admin UI at:

- `GET /admin`

The admin UI allows administrators to:

- Log in
- View activity feed on the dashboard
- Manage collections and schemas with visual editor
- Inspect and edit records
- View and manage users
- View and manage functions
- Configure schedules
- Inspect function call metadata
- Configure extension settings
- Manage instance settings

## 🛠️ Development

### Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](docs/contributing/index.md) for details.

### Setup

**Backend development:**

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install workspace dependencies
uv sync --group dev

# Initialize TinyBase
uv run tinybase init --admin-email admin@example.com --admin-password admin123

# Start both backend and frontend dev servers
make dev

# Or start backend only
make dev-backend
```

**Admin UI development:**

```bash
cd apps/admin
yarn install
yarn dev  # Start Vite dev server with hot reload
```

### Project Structure

This is a monorepo with the following structure:

```text
tinybase/
├── packages/
│   ├── tinybase/           # Core Python package (API server + CLI)
│   └── tinybase-sdk/       # Python SDK for writing functions
├── apps/
│   └── admin/              # Vue 3 Admin UI
├── clients/
│   └── typescript/         # Auto-generated TypeScript client
├── openapi/                # OpenAPI specification
├── scripts/                # Repo management scripts
├── docs/                   # Documentation (MkDocs)
├── Makefile                # Common commands
└── pyproject.toml          # Workspace configuration
```

### Common Commands

```bash
make dev              # Start backend + frontend dev servers
make dev-backend      # Start backend only
make dev-frontend     # Start frontend only
make test             # Run all tests in parallel
make lint             # Lint Python and Markdown files
make format           # Format all files
make build-admin      # Build admin UI
make export-openapi   # Export OpenAPI spec
make pre-commit       # Run all pre-commit hooks
```

### Testing

```bash
# Run all tests in parallel (recommended, ~1-2 min)
make test
# Or: uv run pytest -n auto

# Run with coverage
uv run pytest -n auto --cov=packages/tinybase/tinybase --cov-report=html

# Fast dev loop - only last failed tests
uv run pytest --lf

# Run specific test file
uv run pytest packages/tinybase/tests/test_function_execution.py

# Skip slow tests during development
uv run pytest -m "not slow"

# Run linting
make lint
```

Test coverage includes:

- ✅ Function execution and isolation
- ✅ Authentication and JWT flows
- ✅ Collection CRUD operations
- ✅ Scheduling and cron parsing
- ✅ Rate limiting and resource management
- ✅ SDK decorator and CLI
- ✅ Activity logging
- ✅ Extension settings

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
  -v $(pwd)/data:/home/tinybase/data \
  tinybase
```

The multi-stage build:

1. Builds the Vue admin UI with yarn
1. Creates a minimal Python runtime using uv
1. Bundles everything into a single optimized image

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
- [Tailwind CSS](https://tailwindcss.com/) – Utility-first CSS framework
- [shadcn/vue](https://www.shadcn-vue.com/) – Re-usable UI components
- [uv](https://github.com/astral-sh/uv) – Fast Python package installer

## ⭐ Support

If you find TinyBase useful, please consider:

- ⭐ Starring the repository
- 🐛 Reporting bugs and issues
- 💡 Suggesting new features
- 📖 Improving documentation
- 🔀 Contributing code
