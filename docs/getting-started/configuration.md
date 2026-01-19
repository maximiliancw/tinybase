# Configuration

TinyBase can be configured through environment variables, a TOML configuration file, or a combination of both.

## Configuration Precedence

Settings are loaded in this order (later sources override earlier ones):

1. **Built-in defaults**
2. **`tinybase.toml`** in the current directory
3. **Environment variables** (prefixed with `TINYBASE_`)

## Configuration File

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

[functions]
path = "./functions"
file = "./functions.py"

[scheduler]
enabled = true
interval_seconds = 5
token_cleanup_interval = 60

[cors]
allow_origins = ["*"]

[admin]
static_dir = "builtin"

[extensions]
enabled = true
path = "~/.tinybase/extensions"
```

## Environment Variables

All settings can be overridden with environment variables using the `TINYBASE_` prefix:

| Environment Variable | Configuration Key | Default |
|---------------------|-------------------|---------|
| `TINYBASE_SERVER_HOST` | `server.host` | `0.0.0.0` |
| `TINYBASE_SERVER_PORT` | `server.port` | `8000` |
| `TINYBASE_DEBUG` | `server.debug` | `false` |
| `TINYBASE_LOG_LEVEL` | `server.log_level` | `info` |
| `TINYBASE_DB_URL` | `database.url` | `sqlite:///./tinybase.db` |
| `TINYBASE_AUTH_TOKEN_TTL_HOURS` | `auth.token_ttl_hours` | `24` |
| `TINYBASE_FUNCTIONS_PATH` | `functions.path` | `./functions` |
| `TINYBASE_FUNCTIONS_PATH` | `functions.path` | `./functions` |
| `TINYBASE_SCHEDULER_ENABLED` | `scheduler.enabled` | `true` |
| `TINYBASE_SCHEDULER_INTERVAL_SECONDS` | `scheduler.interval_seconds` | `5` |
| `TINYBASE_SCHEDULER_TOKEN_CLEANUP_INTERVAL` | `scheduler.token_cleanup_interval` | `60` |
| `TINYBASE_CORS_ALLOW_ORIGINS` | `cors.allow_origins` | `["*"]` |
| `TINYBASE_ADMIN_STATIC_DIR` | `admin.static_dir` | `builtin` |
| `TINYBASE_EXTENSIONS_ENABLED` | `extensions.enabled` | `true` |
| `TINYBASE_EXTENSIONS_PATH` | `extensions.path` | `~/.tinybase/extensions` |

### Bootstrap Variables

These variables are used during initialization:

| Environment Variable | Purpose |
|---------------------|---------|
| `TINYBASE_ADMIN_EMAIL` | Admin user email for bootstrap |
| `TINYBASE_ADMIN_PASSWORD` | Admin user password for bootstrap |

## Configuration Sections

### Server Settings

```toml
[server]
host = "0.0.0.0"      # Bind address
port = 8000           # Port number
debug = false         # Enable debug mode
log_level = "info"    # Logging level: debug, info, warning, error, critical
```

!!! warning "Production Settings"
    In production, set `debug = false` and consider binding to `127.0.0.1` if behind a reverse proxy.

### Database Settings

```toml
[database]
url = "sqlite:///./tinybase.db"
```

TinyBase uses SQLite by default. The URL format is:

- **Relative path**: `sqlite:///./tinybase.db`
- **Absolute path**: `sqlite:////var/data/tinybase.db`
- **In-memory**: `sqlite:///:memory:` (for testing)

### Authentication Settings

```toml
[auth]
token_ttl_hours = 24    # Token expiration time in hours
```

Tokens are opaque bearer tokens stored in the database. After the TTL expires, users must re-authenticate.

### Functions Settings

```toml
[functions]
path = "./functions"    # Directory for function modules
path = "./functions" # Directory containing function files
```

TinyBase loads functions from both:

1. The single file specified by `file`
2. All Python files in the `path` directory

### Scheduler Settings

```toml
[scheduler]
enabled = true          # Enable/disable the scheduler
interval_seconds = 5    # How often to check for scheduled tasks
token_cleanup_interval = 60  # Token cleanup interval in scheduler ticks
```

The scheduler runs as a background task and checks for due schedules at the specified interval.

**Token Cleanup Interval**: How often to run token cleanup (in scheduler ticks). For example, if `interval_seconds = 5` and `token_cleanup_interval = 60`, cleanup runs every 5 minutes (60 × 5s). This setting can also be configured via the Admin UI in the Settings page.

### CORS Settings

```toml
[cors]
allow_origins = ["*"]   # Allowed origins for CORS
```

For production, specify exact origins:

```toml
[cors]
allow_origins = ["https://myapp.com", "https://admin.myapp.com"]
```

### Admin UI Settings

```toml
[admin]
static_dir = "builtin"  # Use built-in admin UI
```

Options:

- `"builtin"` - Use the packaged admin UI
- `"/path/to/custom"` - Use custom static files

### Extensions Settings

```toml
[extensions]
enabled = true
path = "~/.tinybase/extensions"
```

## Environment-Specific Configuration

Use the `[environments]` section to define deployment environments:

```toml
[environments.staging]
url = "https://staging.myapp.com"
api_token = "staging-admin-token"

[environments.production]
url = "https://api.myapp.com"
api_token = "production-admin-token"
```

These are used by the `tinybase functions deploy` command.

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

[auth]
token_ttl_hours = 8    # Shorter tokens

[scheduler]
enabled = true
interval_seconds = 10

[cors]
allow_origins = ["https://myapp.com"]

[admin]
static_dir = "builtin"
```

### Docker

When using Docker, prefer environment variables:

```dockerfile
ENV TINYBASE_SERVER_HOST=0.0.0.0
ENV TINYBASE_SERVER_PORT=8000
ENV TINYBASE_DB_URL=sqlite:////data/tinybase.db
ENV TINYBASE_ADMIN_STATIC_DIR=builtin
```

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

