# Configuration

TinyBase uses a **two-layer configuration system**:

1. **Static Config** (`config`) – File-based settings loaded at startup. Changes require a server restart.
1. **Runtime Settings** (`settings`) – Database-backed settings that can be changed at runtime via Admin UI or API.

## Static Configuration

### Precedence

Settings are loaded in this order (later sources override earlier ones):

1. **Built-in defaults**
1. **`tinybase.toml`** in the current directory
1. **Environment variables** (prefixed with `TINYBASE_`)

### Configuration File

The `tinybase.toml` file is the primary way to configure TinyBase:

```toml title="tinybase.toml"
[server]
host = "0.0.0.0"
port = 8000
debug = false
log_level = "info"

[database]
url = "sqlite:///./tinybase.db"

[jwt]
algorithm = "HS256"
access_token_expire_minutes = 1440
refresh_token_expire_days = 30
# secret_key = "your-secret-key"  # Auto-generated if not set

[functions]
dir = "./functions"
logging_enabled = true
logging_level = "INFO"
cold_start_pool_size = 3

[scheduler]
enabled = true
interval_seconds = 5

[rate_limit]
backend = "diskcache"
cache_dir = "./.tinybase/rate_limit_cache"
# redis_url = "redis://localhost:6379/0"  # Required for redis backend

[cors]
allow_origins = ["*"]

[admin]
static_dir = "builtin"

[extensions]
enabled = true
dir = "./.tinybase/extensions"

[email]
enabled = false
# smtp_host = "smtp.example.com"
# smtp_port = 587
```

### All Configuration Options

All static configuration options with their types, defaults, and descriptions:

::: tinybase.settings.static.Config
options:
show_root_heading: false
show_source: false
show_bases: false
members_order: source
show_docstring_description: false
show_docstring_attributes: true
heading_level: 4

### Bootstrap Variables

These environment variables are used during `tinybase init`:

| Environment Variable      | Purpose                           |
| ------------------------- | --------------------------------- |
| `TINYBASE_ADMIN_EMAIL`    | Admin user email for bootstrap    |
| `TINYBASE_ADMIN_PASSWORD` | Admin user password for bootstrap |

______________________________________________________________________

## Runtime Settings

Runtime settings are stored in the database and can be changed without restarting the server. Manage them via the Admin UI Settings page or programmatically.

### Accessing Settings

```python
from tinybase.settings import settings

# Core settings via typed properties (IDE autocompletion)
settings.instance_name                        # "TinyBase"
settings.auth.allow_public_registration       # True
settings.auth.portal.enabled                  # False
settings.storage.enabled                      # False
settings.scheduler.function_timeout_seconds   # 1800
settings.limits.max_concurrent_functions_per_user  # 10

# Any setting via get() (returns AppSetting object or None)
setting = settings.get("core.instance_name")
if setting:
    print(setting.value)

# Set a setting value
settings.set("core.instance_name", "My App")

# Extension settings
settings.set("ext.my_extension.api_key", "xxx")
api_key = settings.get("ext.my_extension.api_key")
```

### Core Runtime Settings

| Setting Key                                     | Default      | Description                           |
| ----------------------------------------------- | ------------ | ------------------------------------- |
| `core.instance_name`                            | `"TinyBase"` | Display name for the instance         |
| `core.server_timezone`                          | `"UTC"`      | Server timezone                       |
| `core.auth.allow_public_registration`           | `true`       | Allow public user registration        |
| `core.auth.portal.enabled`                      | `false`      | Enable auth portal UI                 |
| `core.auth.portal.logo_url`                     | —            | Custom logo URL                       |
| `core.auth.portal.primary_color`                | —            | Primary brand color                   |
| `core.auth.portal.background_image_url`         | —            | Background image URL                  |
| `core.auth.portal.login_redirect_url`           | —            | Post-login redirect URL               |
| `core.auth.portal.register_redirect_url`        | —            | Post-registration redirect URL        |
| `core.storage.enabled`                          | `false`      | Enable S3-compatible file storage     |
| `core.storage.url`                              | —            | S3 endpoint URL                       |
| `core.storage.bucket`                           | —            | S3 bucket name                        |
| `core.storage.access_key`                       | —            | S3 access key                         |
| `core.storage.secret_key`                       | —            | S3 secret key                         |
| `core.storage.region`                           | —            | S3 region                             |
| `core.scheduler.function_timeout_seconds`       | `1800`       | Max function execution time           |
| `core.scheduler.max_schedules_per_tick`         | `100`        | Max schedules processed per interval  |
| `core.scheduler.max_concurrent_executions`      | `10`         | Max concurrent scheduled executions   |
| `core.limits.max_concurrent_functions_per_user` | `10`         | Concurrent function limit per user    |
| `core.jobs.token_cleanup.interval`              | `60`         | Token cleanup job interval (seconds)  |
| `core.jobs.metrics.interval`                    | `360`        | Metrics collection interval (seconds) |
| `core.jobs.admin_report.enabled`                | `true`       | Enable periodic admin reports         |
| `core.jobs.admin_report.interval_days`          | `7`          | Admin report frequency (days)         |

### Extension Settings

Extensions can register their own settings under the `ext.*` namespace:

```python
# In your extension
settings.set("ext.my_extension.api_key", "xxx")
settings.set("ext.my_extension.enabled", True)
settings.set("ext.my_extension.config", {"timeout": 30})
```

______________________________________________________________________

## Deployment Environments

Use the `[environments]` section to define deployment targets for the CLI:

```toml
[environments.staging]
url = "https://staging.myapp.com"
api_token = "staging-admin-token"

[environments.production]
url = "https://api.myapp.com"
api_token = "production-admin-token"
```

These are used by the `tinybase functions deploy` command:

```bash
tinybase functions deploy my_function --env production
```

______________________________________________________________________

## Example Configurations

### Development

```toml title="tinybase.toml"
[server]
host = "127.0.0.1"
port = 8000
debug = true
log_level = "debug"

[database]
url = "sqlite:///./dev.db"

[scheduler]
interval_seconds = 1  # Faster checks for testing

[cors]
allow_origins = ["*"]
```

### Production

```toml title="tinybase.toml"
[server]
host = "127.0.0.1"  # Behind nginx/caddy
debug = false
log_level = "warning"

[database]
url = "sqlite:////var/lib/tinybase/production.db"

[jwt]
secret_key = "${JWT_SECRET}"

[scheduler]
interval_seconds = 10

[rate_limit]
backend = "redis"
redis_url = "redis://localhost:6379/0"

[cors]
allow_origins = ["https://myapp.com"]

[email]
enabled = true
smtp_host = "smtp.example.com"
smtp_port = 587
```

### Docker

When using Docker, prefer environment variables:

```dockerfile
ENV TINYBASE_SERVER_HOST=0.0.0.0
ENV TINYBASE_DB_URL=sqlite:////data/tinybase.db
ENV TINYBASE_JWT_SECRET_KEY=your-secret-key
ENV TINYBASE_RATE_LIMIT_BACKEND=redis
ENV TINYBASE_RATE_LIMIT_REDIS_URL=redis://redis:6379/0
```

______________________________________________________________________

## See Also

- [Python API Reference](../reference/python-api.md) - Full API documentation
- [Deployment Guide](../deployment/index.md) - Production configuration
- [Docker Guide](../deployment/docker.md) - Container configuration
