# Python API Reference

This reference documents TinyBase's Python API for building extensions, custom integrations, and advanced use cases.

---

## Settings

The settings module provides both static configuration (environment/TOML) and runtime settings (database).

### Module Overview

::: tinybase.settings
    options:
      show_root_heading: false
      show_source: false
      members: false

### Static Configuration

File-based configuration loaded at startup from environment variables and `tinybase.toml`.

::: tinybase.settings.static.Config
    options:
      show_source: false
      members_order: source
      show_docstring_attributes: true
      show_root_heading: true
      heading_level: 4

### Runtime Settings

Database-backed settings that can be changed at runtime without restarting.

::: tinybase.settings.core.Settings
    options:
      show_source: false
      members:
        - load
        - reload
        - get
        - set
        - delete
        - get_all
        - instance_name
        - server_timezone
        - auth
        - storage
        - scheduler
        - jobs
        - limits

---

## Authentication

The auth module provides password hashing, JWT tokens, and FastAPI dependencies.

### Module Exports

::: tinybase.auth
    options:
      show_root_heading: false
      show_source: false
      members: false

### Password Utilities

::: tinybase.auth.core.hash_password
    options:
      show_source: false

::: tinybase.auth.core.verify_password
    options:
      show_source: false

### Token Creation

::: tinybase.auth.core.create_auth_token
    options:
      show_source: false

::: tinybase.auth.core.create_internal_token
    options:
      show_source: false

::: tinybase.auth.core.create_application_token
    options:
      show_source: false

::: tinybase.auth.jwt.create_refresh_token
    options:
      show_source: false

### Token Verification

::: tinybase.auth.jwt.verify_jwt_token
    options:
      show_source: false

::: tinybase.auth.core.get_token_user
    options:
      show_source: false

### Token Revocation

::: tinybase.auth.jwt.revoke_token
    options:
      show_source: false

::: tinybase.auth.jwt.revoke_all_user_tokens
    options:
      show_source: false

::: tinybase.auth.core.revoke_application_token
    options:
      show_source: false

### FastAPI Dependencies

Use these as FastAPI `Depends()` for authentication:

```python
from fastapi import Depends
from tinybase.auth import CurrentUser, CurrentUserOptional, CurrentAdminUser, DBSession

@app.get("/me")
def get_me(user: CurrentUser):
    return {"email": user.email}

@app.get("/public")
def public_endpoint(user: CurrentUserOptional):
    if user:
        return {"message": f"Hello {user.email}"}
    return {"message": "Hello anonymous"}

@app.get("/admin-only")
def admin_only(user: CurrentAdminUser):
    return {"admin": True}
```

| Type Alias | Description |
|------------|-------------|
| `CurrentUser` | Requires authentication, returns `User` |
| `CurrentUserOptional` | Optional auth, returns `User \| None` |
| `CurrentAdminUser` | Requires admin user |
| `DBSession` | Database session dependency |

---

## Functions

The functions module handles serverless function registration, metadata, and execution.

### FunctionMeta

::: tinybase.functions.core.FunctionMeta
    options:
      show_source: false
      members_order: source

### FunctionRegistry

::: tinybase.functions.core.FunctionRegistry
    options:
      show_source: false
      members:
        - register
        - get
        - all
        - names
        - unregister
        - clear

### Registry Access

::: tinybase.functions.core.get_function_registry
    options:
      show_source: false

::: tinybase.functions.core.reset_function_registry
    options:
      show_source: false

### Function Execution

::: tinybase.functions.core.execute_function
    options:
      show_source: false

::: tinybase.functions.core.FunctionCallResult
    options:
      show_source: false

---

## Database

### Engine & Session Management

::: tinybase.db.core
    options:
      show_source: false
      members:
        - get_db_engine
        - get_db_session
        - init_db
        - reset_db_engine

### Models

All database models are SQLModel classes that can be used directly with SQLAlchemy queries.

#### User

::: tinybase.db.models.User
    options:
      show_source: false
      members: false

#### AuthToken

::: tinybase.db.models.AuthToken
    options:
      show_source: false
      members:
        - is_expired

#### Collection

::: tinybase.db.models.Collection
    options:
      show_source: false
      members: false

#### Record

::: tinybase.db.models.Record
    options:
      show_source: false
      members: false

#### FunctionCall

::: tinybase.db.models.FunctionCall
    options:
      show_source: false
      members: false

#### FunctionSchedule

::: tinybase.db.models.FunctionSchedule
    options:
      show_source: false
      members:
        - is_active
        - should_run
        - calculate_next_run_time

#### AppSetting

::: tinybase.db.models.AppSetting
    options:
      show_source: false
      members: false

#### Extension

::: tinybase.db.models.Extension
    options:
      show_source: false
      members: false

---

## Collections

### Collection Service

::: tinybase.collections.service
    options:
      show_source: false
      members:
        - get_collection_by_name
        - load_collections_into_registry

### Schema Management

::: tinybase.collections.schemas.get_collection_registry
    options:
      show_source: false

::: tinybase.collections.schemas.reset_collection_registry
    options:
      show_source: false

---

## Utilities

### Enums

::: tinybase.utils.AuthLevel
    options:
      show_source: false

::: tinybase.utils.AccessRule
    options:
      show_source: false

::: tinybase.utils.FunctionCallStatus
    options:
      show_source: false

::: tinybase.utils.TriggerType
    options:
      show_source: false

::: tinybase.utils.ScheduleMethod
    options:
      show_source: false

::: tinybase.utils.IntervalUnit
    options:
      show_source: false

### Helper Functions

::: tinybase.utils.utcnow
    options:
      show_source: false

---

## Extensions

### Loading Extensions

::: tinybase.extensions.loader.load_enabled_extensions
    options:
      show_source: false

### Extension Hook Decorators

::: tinybase.extensions.hooks.on_startup
    options:
      show_source: false

::: tinybase.extensions.hooks.on_shutdown
    options:
      show_source: false

### Hook Runners (Internal)

::: tinybase.extensions.hooks.run_startup_hooks
    options:
      show_source: false

::: tinybase.extensions.hooks.run_shutdown_hooks
    options:
      show_source: false

---

## Scheduler

### Starting/Stopping

::: tinybase.schedule.start_scheduler
    options:
      show_source: false

::: tinybase.schedule.stop_scheduler
    options:
      show_source: false

### Schedule Utilities

::: tinybase.schedule.utils.parse_schedule_config
    options:
      show_source: false

::: tinybase.schedule.utils.validate_cron_expression
    options:
      show_source: false

::: tinybase.schedule.utils.validate_timezone
    options:
      show_source: false

---

## Rate Limiting

::: tinybase.rate_limit.get_rate_limit_backend
    options:
      show_source: false

::: tinybase.rate_limit.reset_rate_limit_backend
    options:
      show_source: false

::: tinybase.rate_limit.check_rate_limit
    options:
      show_source: false

---

## Logging

::: tinybase.logs.setup_logging
    options:
      show_source: false

---

## Version

::: tinybase.version
    options:
      show_source: false
      members:
        - __version__
