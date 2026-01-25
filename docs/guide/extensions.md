# Extensions

Extensions allow you to extend TinyBase with custom functionality, hooks, and third-party integrations.

## Overview

The TinyBase extension system provides:

- **Lifecycle hooks** - React to startup/shutdown
- **Authentication hooks** - Handle login/registration events
- **Data hooks** - Respond to record changes
- **Function hooks** - Intercept function calls
- **Custom functions** - Register new API endpoints

## Installing Extensions

### From GitHub

```bash
tinybase extensions install https://github.com/user/tinybase-extension
```

!!! warning "Security Notice"
    Extensions execute arbitrary Python code. Only install extensions from trusted sources.

### Managing Extensions

```bash
# List installed extensions
tinybase extensions list

# Disable an extension
tinybase extensions disable my-extension

# Enable an extension
tinybase extensions enable my-extension

# Uninstall an extension
tinybase extensions uninstall my-extension
```

---

## Hook Decorators

### Lifecycle Hooks

::: tinybase.extensions.hooks.on_startup
    options:
      show_source: false
      heading_level: 4

::: tinybase.extensions.hooks.on_shutdown
    options:
      show_source: false
      heading_level: 4

### Authentication Hooks

::: tinybase.extensions.hooks.on_user_login
    options:
      show_source: false
      heading_level: 4

::: tinybase.extensions.hooks.on_user_register
    options:
      show_source: false
      heading_level: 4

### Data Hooks

::: tinybase.extensions.hooks.on_record_create
    options:
      show_source: false
      heading_level: 4

::: tinybase.extensions.hooks.on_record_update
    options:
      show_source: false
      heading_level: 4

::: tinybase.extensions.hooks.on_record_delete
    options:
      show_source: false
      heading_level: 4

### Function Hooks

::: tinybase.extensions.hooks.on_function_call
    options:
      show_source: false
      heading_level: 4

::: tinybase.extensions.hooks.on_function_complete
    options:
      show_source: false
      heading_level: 4

---

## Event Data Classes

These dataclasses are passed to hook functions:

::: tinybase.extensions.hooks.UserLoginEvent
    options:
      show_source: false
      heading_level: 4

::: tinybase.extensions.hooks.UserRegisterEvent
    options:
      show_source: false
      heading_level: 4

::: tinybase.extensions.hooks.RecordCreateEvent
    options:
      show_source: false
      heading_level: 4

::: tinybase.extensions.hooks.RecordUpdateEvent
    options:
      show_source: false
      heading_level: 4

::: tinybase.extensions.hooks.RecordDeleteEvent
    options:
      show_source: false
      heading_level: 4

::: tinybase.extensions.hooks.FunctionCallEvent
    options:
      show_source: false
      heading_level: 4

::: tinybase.extensions.hooks.FunctionCompleteEvent
    options:
      show_source: false
      heading_level: 4

---

## Creating Extensions

### Extension Structure

```
my-extension/
├── extension.toml      # Manifest file
├── __init__.py         # Main entry point
├── hooks.py            # Hook definitions
├── functions.py        # Custom functions
└── README.md           # Documentation
```

### Manifest File

```toml title="extension.toml"
[extension]
name = "my-extension"
version = "1.0.0"
description = "My awesome TinyBase extension"
author = "Your Name"
license = "MIT"

[extension.tinybase]
min_version = "0.3.0"

[extension.dependencies]
requests = ">=2.28.0"
```

### Entry Point

```python title="__init__.py"
"""My TinyBase Extension."""

from .hooks import *
from .functions import *

__version__ = "1.0.0"
```

### Example Extension

```python title="hooks.py"
from tinybase.extensions.hooks import (
    on_startup,
    on_shutdown,
    on_record_create,
    RecordCreateEvent,
)

# State
_connected = False


@on_startup
def connect_to_service():
    """Initialize external service connection."""
    global _connected
    _connected = True
    print("Connected to external service")


@on_shutdown
def disconnect_from_service():
    """Clean up connections."""
    global _connected
    _connected = False
    print("Disconnected from external service")


@on_record_create(collection="events")
def sync_to_external(event: RecordCreateEvent):
    """Sync new events to external service."""
    if _connected:
        send_to_external(event.data)
```

```python title="functions.py"
from pydantic import BaseModel
from tinybase_sdk import register
from tinybase_sdk.cli import run


class SyncInput(BaseModel):
    force: bool = False


class SyncOutput(BaseModel):
    synced_count: int
    errors: list[str]


@register(
    name="ext_sync_all",
    description="Sync all records to external service",
    auth="admin",
)
def sync_all_records(client, payload: SyncInput) -> SyncOutput:
    """Sync all records to external service."""
    # Use client.collections to access data
    records = client.collections.list_records("my_collection")
    synced = 0
    errors = []
    
    for record in records:
        try:
            send_to_external(record["data"])
            synced += 1
        except Exception as e:
            errors.append(f"{record['id']}: {e}")
    
    return SyncOutput(synced_count=synced, errors=errors)


if __name__ == "__main__":
    run()
```

---

## Extension Configuration

Extensions can use runtime settings for configuration:

```python
from tinybase.settings import settings

# In your extension - read settings
api_key = settings.get("ext.my_extension.api_key")
if api_key:
    configure_client(api_key.value)

# Set default values on startup
@on_startup
def setup_defaults():
    if not settings.get("ext.my_extension.enabled"):
        settings.set("ext.my_extension.enabled", True)
        settings.set("ext.my_extension.timeout", 30)
```

Users configure via Admin UI or API, or environment variables:

```bash
export MY_EXT_API_KEY=secret123
tinybase serve
```

---

## Publishing Extensions

### GitHub Repository

1. Create a public GitHub repository
2. Include `extension.toml` manifest
3. Include installation instructions in README
4. Tag releases with semantic versions

### Best Practices

1. **Document thoroughly** - README with examples
2. **Version correctly** - Follow semver
3. **Handle errors** - Don't crash TinyBase
4. **Test thoroughly** - Include tests
5. **Minimize dependencies** - Keep it lightweight

---

## Extension Security

### For Users

- **Review code** before installing
- **Check author reputation**
- **Use specific versions** when possible
- **Monitor extension behavior**

### For Developers

- **Never store secrets in code**
- **Use settings** for configuration
- **Handle errors gracefully**
- **Document permissions needed**

---

## Debugging Extensions

### Enable Debug Logging

```toml
[server]
log_level = "debug"
```

### Check Extension Status

```bash
tinybase extensions list
```

### View Extension Logs

Extensions should use Python's logging:

```python
import logging

logger = logging.getLogger(__name__)

@on_startup
def initialize():
    logger.debug("Extension starting...")
    logger.info("Extension ready")
```

---

## Hook Summary

| Hook | Event Type | When |
|------|------------|------|
| `@on_startup` | None | Server starts |
| `@on_shutdown` | None | Server stops |
| `@on_user_login` | `UserLoginEvent` | User logs in |
| `@on_user_register` | `UserRegisterEvent` | User registers |
| `@on_record_create` | `RecordCreateEvent` | Record created |
| `@on_record_update` | `RecordUpdateEvent` | Record updated |
| `@on_record_delete` | `RecordDeleteEvent` | Record deleted |
| `@on_function_call` | `FunctionCallEvent` | Before function |
| `@on_function_complete` | `FunctionCompleteEvent` | After function |

---

## See Also

- [Functions Guide](functions.md) - Creating functions
- [Python API Reference](../reference/python-api.md) - Full API documentation
- [Configuration](../getting-started/configuration.md) - Settings and config
