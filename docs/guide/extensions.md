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

### Listing Extensions

```bash
tinybase extensions list
```

### Enable/Disable Extensions

```bash
# Disable an extension
tinybase extensions disable my-extension

# Enable an extension
tinybase extensions enable my-extension
```

### Uninstalling Extensions

```bash
tinybase extensions uninstall my-extension
```

## Extension Hooks

### Lifecycle Hooks

React to TinyBase starting and stopping:

```python
from tinybase.extensions import on_startup, on_shutdown


@on_startup
def initialize():
    """Called when TinyBase starts."""
    print("Extension initialized!")
    # Connect to external services
    # Load configuration
    # Initialize caches


@on_shutdown
def cleanup():
    """Called when TinyBase shuts down."""
    print("Extension shutting down!")
    # Close connections
    # Flush buffers
    # Save state
```

### Authentication Hooks

React to user authentication events:

```python
from tinybase.extensions import (
    on_user_login,
    on_user_register,
    UserLoginEvent,
    UserRegisterEvent,
)


@on_user_login
def handle_login(event: UserLoginEvent):
    """Called when a user logs in."""
    print(f"User logged in: {event.email}")
    
    if event.is_admin:
        send_admin_login_alert(event.email)
    
    track_analytics("user_login", {"user_id": str(event.user_id)})


@on_user_register
def handle_registration(event: UserRegisterEvent):
    """Called when a new user registers."""
    print(f"New user: {event.email}")
    
    send_welcome_email(event.email)
    create_default_data(event.user_id)
```

#### Event Data

```python
@dataclass
class UserLoginEvent:
    user_id: UUID
    email: str
    is_admin: bool


@dataclass
class UserRegisterEvent:
    user_id: UUID
    email: str
```

### Data Hooks

React to record CRUD operations:

```python
from tinybase.extensions import (
    on_record_create,
    on_record_update,
    on_record_delete,
    RecordCreateEvent,
    RecordUpdateEvent,
    RecordDeleteEvent,
)


@on_record_create(collection="orders")
def handle_new_order(event: RecordCreateEvent):
    """Called when an order is created."""
    print(f"New order: {event.record_id}")
    
    send_order_confirmation(event.data["email"], event.record_id)
    update_inventory(event.data["items"])


@on_record_update(collection="orders")
def handle_order_update(event: RecordUpdateEvent):
    """Called when an order is updated."""
    old_status = event.old_data.get("status")
    new_status = event.new_data.get("status")
    
    if old_status != new_status:
        notify_status_change(event.record_id, new_status)


@on_record_delete(collection="files")
def handle_file_delete(event: RecordDeleteEvent):
    """Called when a file record is deleted."""
    file_path = event.data.get("path")
    if file_path:
        delete_from_storage(file_path)
```

#### Collection Filtering

```python
# Specific collection
@on_record_create(collection="orders")
def orders_only(event):
    ...

# All collections
@on_record_create()
def all_collections(event):
    print(f"Record created in {event.collection}")
```

#### Event Data

```python
@dataclass
class RecordCreateEvent:
    collection: str
    record_id: UUID
    data: dict
    owner_id: UUID | None


@dataclass
class RecordUpdateEvent:
    collection: str
    record_id: UUID
    old_data: dict
    new_data: dict
    owner_id: UUID | None


@dataclass
class RecordDeleteEvent:
    collection: str
    record_id: UUID
    data: dict
    owner_id: UUID | None
```

### Function Hooks

Intercept function calls:

```python
from tinybase.extensions import (
    on_function_call,
    on_function_complete,
    FunctionCallEvent,
    FunctionCompleteEvent,
)


@on_function_call(name="process_payment")
def before_payment(event: FunctionCallEvent):
    """Called before payment processing."""
    print(f"Payment attempt by {event.user_id}")
    audit_log("payment_attempt", event.payload)


@on_function_complete()
def track_all_functions(event: FunctionCompleteEvent):
    """Called after any function completes."""
    metrics.record(
        function=event.function_name,
        duration_ms=event.duration_ms,
        success=event.status == "succeeded"
    )


@on_function_complete(name="critical_task")
def alert_on_failure(event: FunctionCompleteEvent):
    """Alert when critical task fails."""
    if event.status == "failed":
        send_alert(
            f"Critical task failed: {event.error_message}",
            error_type=event.error_type
        )
```

#### Event Data

```python
@dataclass
class FunctionCallEvent:
    function_name: str
    user_id: UUID | None
    payload: dict


@dataclass
class FunctionCompleteEvent:
    function_name: str
    user_id: UUID | None
    status: str  # "succeeded" or "failed"
    duration_ms: int
    error_message: str | None
    error_type: str | None
```

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
from tinybase.extensions import (
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
from tinybase.functions import Context, register


class SyncInput(BaseModel):
    force: bool = False


class SyncOutput(BaseModel):
    synced_count: int
    errors: list[str]


@register(
    name="ext_sync_all",
    description="Sync all records to external service",
    auth="admin",
    input_model=SyncInput,
    output_model=SyncOutput,
    tags=["my-extension", "sync"],
)
def sync_all_records(ctx: Context, payload: SyncInput) -> SyncOutput:
    """Sync all records to external service."""
    from sqlmodel import select
    from tinybase.db.models import Record
    
    records = ctx.db.exec(select(Record)).all()
    synced = 0
    errors = []
    
    for record in records:
        try:
            send_to_external(record.data)
            synced += 1
        except Exception as e:
            errors.append(f"{record.id}: {e}")
    
    return SyncOutput(synced_count=synced, errors=errors)
```

## Extension Configuration

Extensions can read configuration from environment variables:

```python
import os

# In your extension
EXTERNAL_API_KEY = os.environ.get("MY_EXT_API_KEY")
EXTERNAL_API_URL = os.environ.get("MY_EXT_API_URL", "https://api.example.com")
```

Users configure via environment:

```bash
export MY_EXT_API_KEY=secret123
export MY_EXT_API_URL=https://custom.api.com
tinybase serve
```

## Publishing Extensions

### GitHub Repository

1. Create a public GitHub repository
2. Include `extension.toml` manifest
3. Include installation instructions
4. Tag releases with semantic versions

### Best Practices

1. **Document thoroughly** - README with examples
2. **Version correctly** - Follow semver
3. **Handle errors** - Don't crash TinyBase
4. **Test thoroughly** - Include tests
5. **Minimize dependencies** - Keep it lightweight

## Extension Security

### For Users

- **Review code** before installing
- **Check author reputation**
- **Use specific versions** when possible
- **Monitor extension behavior**

### For Developers

- **Never store secrets in code**
- **Use environment variables** for configuration
- **Handle errors gracefully**
- **Document permissions needed**

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

## Built-in Hooks Summary

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

## See Also

- [Functions Guide](functions.md) - Creating functions
- [Python API Reference](../reference/python-api.md) - API documentation
- [Contributing Guide](../contributing/index.md) - Extension development

