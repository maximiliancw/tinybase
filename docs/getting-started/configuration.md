# Configuration

TinyBase uses a **two-layer configuration system**:

1. **Static Config** (`config`) – File-based settings loaded at startup. Changes require a server restart.
2. **Runtime Settings** (`settings`) – Database-backed settings that can be changed at runtime via Admin UI or API.

## Static Configuration

### Precedence

Settings are loaded in this order (later sources override earlier ones):

1. **Built-in defaults**
2. **`tinybase.toml`** in the current directory
3. **Environment variables** (prefixed with `TINYBASE_`)

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

[auth]
token_ttl_hours = 24

[jwt]
algorithm = "HS256"
access_token_expire_minutes = 1440  # 24 hours
refresh_token_expire_days = 30
# secret_key = "your-secret-key"  # Auto-generated if not set

[functions]
path = "./functions"
logging_enabled = true
logging_level = "INFO"
logging_format = "json"  # or "text"
cold_start_pool_size = 3
cold_start_ttl_seconds = 300

[scheduler]
enabled = true
interval_seconds = 5

[rate_limit]
backend = "diskcache"  # or "redis"
cache_dir = "./.tinybase/rate_limit_cache"
# redis_url = "redis://localhost:6379/0"  # Required when backend=redis

[cors]
allow_origins = ["*"]

[admin]
static_dir = "builtin"

[extensions]
enabled = true
path = "~/.tinybase/extensions"

[email]
enabled = false
# smtp_host = "smtp.example.com"
# smtp_port = 587
# smtp_user = "username"
# smtp_password = "password"
# from_address = "noreply@example.com"
# from_name = "TinyBase"
```

### Environment Variables

All settings can be overridden with environment variables using the `TINYBASE_` prefix:

| Environment Variable | Configuration Key | Default |
|---------------------|-------------------|---------|
| `TINYBASE_SERVER_HOST` | `server.host` | `0.0.0.0` |
| `TINYBASE_SERVER_PORT` | `server.port` | `8000` |
| `TINYBASE_DEBUG` | `server.debug` | `false` |
| `TINYBASE_LOG_LEVEL` | `server.log_level` | `info` |
| `TINYBASE_DB_URL` | `database.url` | `sqlite:///./tinybase.db` |
| `TINYBASE_AUTH_TOKEN_TTL_HOURS` | `auth.token_ttl_hours` | `24` |
| `TINYBASE_JWT_SECRET_KEY` | `jwt.secret_key` | Auto-generated |
| `TINYBASE_JWT_ALGORITHM` | `jwt.algorithm` | `HS256` |
| `TINYBASE_JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `jwt.access_token_expire_minutes` | `1440` |
| `TINYBASE_JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `jwt.refresh_token_expire_days` | `30` |
| `TINYBASE_FUNCTIONS_PATH` | `functions.path` | `./functions` |
| `TINYBASE_FUNCTION_LOGGING_ENABLED` | `functions.logging_enabled` | `true` |
| `TINYBASE_FUNCTION_LOGGING_LEVEL` | `functions.logging_level` | `INFO` |
| `TINYBASE_FUNCTION_COLD_START_POOL_SIZE` | `functions.cold_start_pool_size` | `3` |
| `TINYBASE_SCHEDULER_ENABLED` | `scheduler.enabled` | `true` |
| `TINYBASE_SCHEDULER_INTERVAL_SECONDS` | `scheduler.interval_seconds` | `5` |
| `TINYBASE_RATE_LIMIT_BACKEND` | `rate_limit.backend` | `diskcache` |
| `TINYBASE_RATE_LIMIT_CACHE_DIR` | `rate_limit.cache_dir` | `./.tinybase/rate_limit_cache` |
| `TINYBASE_RATE_LIMIT_REDIS_URL` | `rate_limit.redis_url` | — |
| `TINYBASE_CORS_ALLOW_ORIGINS` | `cors.allow_origins` | `["*"]` |
| `TINYBASE_ADMIN_STATIC_DIR` | `admin.static_dir` | `builtin` |
| `TINYBASE_EXTENSIONS_ENABLED` | `extensions.enabled` | `true` |
| `TINYBASE_EXTENSIONS_PATH` | `extensions.path` | `~/.tinybase/extensions` |
| `TINYBASE_EMAIL_ENABLED` | `email.enabled` | `false` |
| `TINYBASE_MAX_FUNCTION_PAYLOAD_BYTES` | — | `10485760` (10MB) |
| `TINYBASE_MAX_FUNCTION_RESULT_BYTES` | — | `10485760` (10MB) |

#### Bootstrap Variables

These variables are used during initialization (`tinybase init`):

| Environment Variable | Purpose |
|---------------------|---------|
| `TINYBASE_ADMIN_EMAIL` | Admin user email for bootstrap |
| `TINYBASE_ADMIN_PASSWORD` | Admin user password for bootstrap |

### Configuration Sections

#### Server Settings

```toml
[server]
host = "0.0.0.0"      # Bind address
port = 8000           # Port number
debug = false         # Enable debug mode
log_level = "info"    # Logging level: debug, info, warning, error, critical
```

!!! warning "Production Settings"
    In production, set `debug = false` and consider binding to `127.0.0.1` if behind a reverse proxy.

#### Database Settings

```toml
[database]
url = "sqlite:///./tinybase.db"
```

TinyBase uses SQLite by default. The URL format is:

- **Relative path**: `sqlite:///./tinybase.db`
- **Absolute path**: `sqlite:////var/data/tinybase.db`
- **In-memory**: `sqlite:///:memory:` (for testing)

#### JWT Settings

```toml
[jwt]
algorithm = "HS256"                    # Signing algorithm
access_token_expire_minutes = 1440     # Access token TTL (24 hours)
refresh_token_expire_days = 30         # Refresh token TTL
# secret_key = "your-secret-key"       # Auto-generated if not provided
```

!!! tip "JWT Secret Key"
    If not provided, TinyBase auto-generates a secure secret key. For multi-instance deployments, set this explicitly to ensure tokens work across all instances.

#### Functions Settings

```toml
[functions]
path = "./functions"              # Directory containing function files
logging_enabled = true            # Enable structured logging in functions
logging_level = "INFO"            # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
logging_format = "json"           # Format: "json" or "text"
cold_start_pool_size = 3          # Warm processes to keep ready
cold_start_ttl_seconds = 300      # Time to keep warm processes alive
```

#### Rate Limiting Settings

```toml
[rate_limit]
backend = "diskcache"                         # Backend: "diskcache" or "redis"
cache_dir = "./.tinybase/rate_limit_cache"    # DiskCache directory
# redis_url = "redis://localhost:6379/0"      # Required when backend=redis
```

Use Redis for multi-instance deployments to share rate limit state.

#### Scheduler Settings

```toml
[scheduler]
enabled = true          # Enable/disable the scheduler
interval_seconds = 5    # How often to check for scheduled tasks
```

#### CORS Settings

```toml
[cors]
allow_origins = ["*"]   # Allowed origins for CORS
```

For production, specify exact origins:

```toml
[cors]
allow_origins = ["https://myapp.com", "https://admin.myapp.com"]
```

#### Admin UI Settings

```toml
[admin]
static_dir = "builtin"  # Use built-in admin UI
```

Options:

- `"builtin"` - Use the packaged admin UI
- `"/path/to/custom"` - Use custom static files

#### Extensions Settings

```toml
[extensions]
enabled = true
path = "~/.tinybase/extensions"
```

#### Email Settings

```toml
[email]
enabled = false
smtp_host = "smtp.example.com"
smtp_port = 587
smtp_user = "username"
smtp_password = "password"
from_address = "noreply@example.com"
from_name = "TinyBase"
```

Email is used for password reset flows and admin report notifications.

---

## Runtime Settings

Runtime settings are stored in the database and can be changed without restarting the server. Manage them via the Admin UI Settings page or programmatically.

### Accessing Settings in Code

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

| Setting Key | Default | Description |
|-------------|---------|-------------|
| `core.instance_name` | `"TinyBase"` | Display name for the instance |
| `core.server_timezone` | `"UTC"` | Server timezone |
| `core.auth.allow_public_registration` | `true` | Allow public user registration |
| `core.auth.portal.enabled` | `false` | Enable auth portal UI |
| `core.auth.portal.logo_url` | — | Custom logo URL |
| `core.auth.portal.primary_color` | — | Primary brand color |
| `core.auth.portal.background_image_url` | — | Background image URL |
| `core.auth.portal.login_redirect_url` | — | Post-login redirect URL |
| `core.auth.portal.register_redirect_url` | — | Post-registration redirect URL |
| `core.storage.enabled` | `false` | Enable S3-compatible file storage |
| `core.storage.endpoint` | — | S3 endpoint URL |
| `core.storage.bucket` | — | S3 bucket name |
| `core.storage.access_key` | — | S3 access key |
| `core.storage.secret_key` | — | S3 secret key |
| `core.storage.region` | — | S3 region |
| `core.scheduler.function_timeout_seconds` | `1800` | Max function execution time |
| `core.scheduler.max_schedules_per_tick` | `100` | Max schedules processed per interval |
| `core.scheduler.max_concurrent_executions` | `10` | Max concurrent scheduled executions |
| `core.limits.max_concurrent_functions_per_user` | `10` | Concurrent function limit per user |
| `core.jobs.token_cleanup.interval` | `60` | Token cleanup job interval (seconds) |
| `core.jobs.metrics.interval` | `360` | Metrics collection interval (seconds) |
| `core.jobs.admin_report.enabled` | `true` | Enable periodic admin reports |
| `core.jobs.admin_report.interval_days` | `7` | Admin report frequency (days) |

### Extension Settings

Extensions can register their own settings under the `ext.*` namespace:

```python
# In your extension
settings.set("ext.my_extension.api_key", "xxx")
settings.set("ext.my_extension.enabled", True)
settings.set("ext.my_extension.config", {"timeout": 30})
```

---

## Deployment Environment Configuration

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

---

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
enabled = true
interval_seconds = 1    # Faster checks for testing

[cors]
allow_origins = ["*"]
```

### Production

```toml title="tinybase.toml"
[server]
host = "127.0.0.1"    # Behind nginx/caddy
port = 8000
debug = false
log_level = "warning"

[database]
url = "sqlite:////var/lib/tinybase/production.db"

[jwt]
secret_key = "${JWT_SECRET}"  # Set via environment variable

[auth]
token_ttl_hours = 8    # Shorter tokens

[scheduler]
enabled = true
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
smtp_user = "noreply@myapp.com"
smtp_password = "${SMTP_PASSWORD}"
from_address = "noreply@myapp.com"
from_name = "My App"
```

### Docker

When using Docker, prefer environment variables:

```dockerfile
ENV TINYBASE_SERVER_HOST=0.0.0.0
ENV TINYBASE_SERVER_PORT=8000
ENV TINYBASE_DB_URL=sqlite:////data/tinybase.db
ENV TINYBASE_JWT_SECRET_KEY=your-secret-key
ENV TINYBASE_RATE_LIMIT_BACKEND=redis
ENV TINYBASE_RATE_LIMIT_REDIS_URL=redis://redis:6379/0
```

---

## Validating Configuration

TinyBase validates configuration at startup. If there are errors, you'll see messages like:

```
Error: Invalid configuration
  - log_level: must be one of {'debug', 'info', 'warning', 'error', 'critical'}
  - port: must be between 1 and 65535
```

## See Also

- [CLI Reference](../reference/cli.md) - Command-line options
- [Deployment Guide](../deployment/index.md) - Production configuration
- [Docker Guide](../deployment/docker.md) - Container configuration
