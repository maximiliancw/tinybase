# Python API Reference

Reference documentation for TinyBase Python modules.

!!! info "Two Function APIs"
    TinyBase provides two ways to define functions:
    
    1. **TinyBase SDK** (`tinybase_sdk`) - For user functions that run in isolated subprocesses
        - Recommended for most use cases
        - Automatic dependency management with inline script dependencies
        - Full isolation and security
        - See [Functions Guide](../guide/functions.md)
    
    2. **Internal API** (`tinybase.functions`) - For extensions and internal code
        - Direct access to TinyBase internals
        - Runs in the main process
        - Used by extensions and system integrations
        - Documented below

## SDK Module (User Functions)

### tinybase_sdk

The SDK for writing user functions with isolated execution.

```python
# /// script
# dependencies = ["tinybase-sdk"]
# ///

from tinybase_sdk import register
from tinybase_sdk.cli import run
from pydantic import BaseModel

class MyInput(BaseModel):
    value: str

class MyOutput(BaseModel):
    result: str

@register(
    name="my_function",
    description="My function",
    auth="auth",  # "public", "auth", "admin"
    tags=["category"]
)
def my_function(client, payload: MyInput) -> MyOutput:
    # client provides authenticated access to TinyBase API
    # payload is automatically validated against MyInput
    return MyOutput(result=f"Processed: {payload.value}")

if __name__ == "__main__":
    run()
```

**The `client` Object:**

The `client` parameter provides authenticated HTTP access to the TinyBase API:

```python
# GET request
response = client.get("/api/collections/tasks/records")
data = response.json()

# POST request
response = client.post(
    "/api/collections/tasks/records",
    json={"data": {"title": "New task"}}
)

# Other HTTP methods
response = client.patch(url, json=data)
response = client.delete(url)
response = client.put(url, json=data)
```

---

## Internal Functions Module (Extensions)

### tinybase.functions

The main module for defining server-side functions.

#### register

Decorator to register a function with TinyBase.

```python
from tinybase.functions import register

@register(
    name: str,
    description: str | None = None,
    auth: str = "auth",  # "public", "auth", "admin"
    input_model: type[BaseModel] | None = None,
    output_model: type[BaseModel] | None = None,
    tags: list[str] | None = None,
)
def my_function(ctx: Context, payload: InputModel) -> OutputModel:
    ...
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Unique function identifier |
| `description` | `str \| None` | Human-readable description |
| `auth` | `str` | Auth level: `"public"`, `"auth"`, `"admin"` |
| `input_model` | `type[BaseModel]` | Pydantic input model |
| `output_model` | `type[BaseModel]` | Pydantic output model |
| `tags` | `list[str]` | Categorization tags |

#### Context

Execution context passed to all functions.

```python
from tinybase.functions import Context

class Context(BaseModel):
    # Execution metadata
    function_name: str
    trigger_type: Literal["manual", "schedule"]
    trigger_id: UUID | None
    request_id: UUID
    
    # User information
    user_id: UUID | None
    is_admin: bool
    
    # Utilities
    now: datetime
    db: Session
    request: Request | None
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `function_name` | `str` | Name of executing function |
| `trigger_type` | `str` | `"manual"` or `"schedule"` |
| `trigger_id` | `UUID \| None` | Schedule ID if scheduled |
| `request_id` | `UUID` | Unique execution ID |
| `user_id` | `UUID \| None` | Calling user's ID |
| `is_admin` | `bool` | User's admin status |
| `now` | `datetime` | Current UTC time |
| `db` | `Session` | Database session |
| `request` | `Request \| None` | FastAPI request object |

---

## Collections Module

### tinybase.collections.service

Service class for collection operations.

#### CollectionService

```python
from tinybase.collections.service import CollectionService

service = CollectionService(session: Session)
```

**Methods:**

##### list_collections

```python
def list_collections(self) -> list[Collection]:
    """List all collections."""
```

##### get_collection_by_name

```python
def get_collection_by_name(self, name: str) -> Collection | None:
    """Get a collection by name."""
```

##### create_collection

```python
def create_collection(
    self,
    name: str,
    label: str,
    schema: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> Collection:
    """Create a new collection."""
```

##### update_collection

```python
def update_collection(
    self,
    collection: Collection,
    label: str | None = None,
    schema: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
) -> Collection:
    """Update an existing collection."""
```

##### delete_collection

```python
def delete_collection(self, collection: Collection) -> None:
    """Delete a collection and all its records."""
```

##### list_records

```python
def list_records(
    self,
    collection: Collection,
    owner_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
    filters: dict[str, Any] | None = None,
    sort_by: str | None = None,
    sort_order: str = "desc",
) -> tuple[list[Record], int]:
    """List records with filtering and pagination."""
```

##### create_record

```python
def create_record(
    self,
    collection: Collection,
    data: dict[str, Any],
    owner_id: UUID | None = None,
) -> Record:
    """Create a new record."""
```

##### update_record

```python
def update_record(
    self,
    collection: Collection,
    record: Record,
    data: dict[str, Any],
    partial: bool = True,
) -> Record:
    """Update an existing record."""
```

##### delete_record

```python
def delete_record(self, record: Record) -> None:
    """Delete a record."""
```

---

## Extensions Module

### tinybase.extensions

Module for extension hooks and events.

#### Lifecycle Hooks

##### on_startup

```python
from tinybase.extensions import on_startup

@on_startup
def my_startup_handler() -> None:
    """Called when TinyBase starts."""
```

##### on_shutdown

```python
from tinybase.extensions import on_shutdown

@on_shutdown
def my_shutdown_handler() -> None:
    """Called when TinyBase shuts down."""
```

#### Authentication Hooks

##### on_user_login

```python
from tinybase.extensions import on_user_login, UserLoginEvent

@on_user_login
def handle_login(event: UserLoginEvent) -> None:
    """Called when a user logs in."""
```

##### on_user_register

```python
from tinybase.extensions import on_user_register, UserRegisterEvent

@on_user_register
def handle_register(event: UserRegisterEvent) -> None:
    """Called when a user registers."""
```

#### Data Hooks

##### on_record_create

```python
from tinybase.extensions import on_record_create, RecordCreateEvent

@on_record_create(collection="orders")  # or collection=None for all
def handle_create(event: RecordCreateEvent) -> None:
    """Called when a record is created."""
```

##### on_record_update

```python
from tinybase.extensions import on_record_update, RecordUpdateEvent

@on_record_update(collection="orders")
def handle_update(event: RecordUpdateEvent) -> None:
    """Called when a record is updated."""
```

##### on_record_delete

```python
from tinybase.extensions import on_record_delete, RecordDeleteEvent

@on_record_delete(collection="orders")
def handle_delete(event: RecordDeleteEvent) -> None:
    """Called when a record is deleted."""
```

#### Function Hooks

##### on_function_call

```python
from tinybase.extensions import on_function_call, FunctionCallEvent

@on_function_call(name="process_payment")  # or name=None for all
def before_function(event: FunctionCallEvent) -> None:
    """Called before a function executes."""
```

##### on_function_complete

```python
from tinybase.extensions import on_function_complete, FunctionCompleteEvent

@on_function_complete(name="process_payment")
def after_function(event: FunctionCompleteEvent) -> None:
    """Called after a function completes."""
```

#### Event Classes

##### UserLoginEvent

```python
@dataclass
class UserLoginEvent:
    user_id: UUID
    email: str
    is_admin: bool
```

##### UserRegisterEvent

```python
@dataclass
class UserRegisterEvent:
    user_id: UUID
    email: str
```

##### RecordCreateEvent

```python
@dataclass
class RecordCreateEvent:
    collection: str
    record_id: UUID
    data: dict
    owner_id: UUID | None
```

##### RecordUpdateEvent

```python
@dataclass
class RecordUpdateEvent:
    collection: str
    record_id: UUID
    old_data: dict
    new_data: dict
    owner_id: UUID | None
```

##### RecordDeleteEvent

```python
@dataclass
class RecordDeleteEvent:
    collection: str
    record_id: UUID
    data: dict
    owner_id: UUID | None
```

##### FunctionCallEvent

```python
@dataclass
class FunctionCallEvent:
    function_name: str
    user_id: UUID | None
    payload: dict
```

##### FunctionCompleteEvent

```python
@dataclass
class FunctionCompleteEvent:
    function_name: str
    user_id: UUID | None
    status: str  # "succeeded" or "failed"
    duration_ms: int
    error_message: str | None
    error_type: str | None
```

---

## Database Models

### tinybase.db.models

SQLModel database models.

#### User

```python
class User(SQLModel, table=True):
    id: UUID
    email: str
    password_hash: str
    is_admin: bool
    created_at: datetime
    updated_at: datetime
```

#### Collection

```python
class Collection(SQLModel, table=True):
    id: UUID
    name: str
    label: str
    schema_: dict  # JSON schema
    options: dict  # Access rules, etc.
    created_at: datetime
    updated_at: datetime
```

#### Record

```python
class Record(SQLModel, table=True):
    id: UUID
    collection_id: UUID
    owner_id: UUID | None
    data: dict
    created_at: datetime
    updated_at: datetime
```

#### FunctionCall

```python
class FunctionCall(SQLModel, table=True):
    id: UUID
    function_name: str
    user_id: UUID | None
    trigger_type: str
    trigger_id: UUID | None
    status: str
    duration_ms: int
    error_message: str | None
    error_type: str | None
    created_at: datetime
```

#### FunctionSchedule

```python
class FunctionSchedule(SQLModel, table=True):
    id: UUID
    function_name: str
    payload: dict
    schedule: dict
    enabled: bool
    last_run_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime
```

---

## Configuration

### tinybase.settings

Configuration management with static config (environment variables) and runtime settings (database).

#### Config (Static)

```python
from tinybase.settings import config

# Access static configuration (from env vars / TOML)
print(config.server_host)
print(config.db_url)
```

#### Settings (Runtime)

```python
from tinybase.settings import settings

# Access runtime settings (from database)
print(settings.instance_name)
print(settings.storage.enabled)
```

**Properties:**

| Property | Type | Default |
|----------|------|---------|
| `server_host` | `str` | `"0.0.0.0"` |
| `server_port` | `int` | `8000` |
| `debug` | `bool` | `False` |
| `log_level` | `str` | `"info"` |
| `db_url` | `str` | `"sqlite:///./tinybase.db"` |
| `auth_token_ttl_hours` | `int` | `24` |
| `functions_path` | `str` | `"./functions"` |
| `scheduler_enabled` | `bool` | `True` |
| `scheduler_interval_seconds` | `int` | `5` |
| `scheduler_token_cleanup_interval` | `int` | `60` |
| `cors_allow_origins` | `list[str]` | `["*"]` |
| `admin_static_dir` | `str` | `"builtin"` |
| `extensions_enabled` | `bool` | `True` |
| `extensions_path` | `str` | `"~/.tinybase/extensions"` |

---

## Utilities

### tinybase.utils

Utility functions and enums.

#### AuthLevel

```python
from tinybase.utils import AuthLevel

class AuthLevel(str, Enum):
    PUBLIC = "public"
    AUTH = "auth"
    ADMIN = "admin"
```

#### AccessRule

```python
from tinybase.utils import AccessRule

class AccessRule(str, Enum):
    PUBLIC = "public"
    AUTH = "auth"
    OWNER = "owner"
    ADMIN = "admin"
```

#### utcnow

```python
from tinybase.utils import utcnow

now = utcnow()  # Returns datetime in UTC
```

---

## Example: Complete Function

```python
from pydantic import BaseModel, Field
from sqlmodel import select

from tinybase.collections.service import CollectionService
from tinybase.db.models import Record
from tinybase.extensions import on_function_complete, FunctionCompleteEvent
from tinybase.functions import Context, register


class OrderInput(BaseModel):
    product_id: str
    quantity: int = Field(ge=1, le=100)


class OrderOutput(BaseModel):
    order_id: str
    total: float


@register(
    name="create_order",
    description="Create a new order",
    auth="auth",
    input_model=OrderInput,
    output_model=OrderOutput,
    tags=["orders"],
)
def create_order(ctx: Context, payload: OrderInput) -> OrderOutput:
    """Create an order for the authenticated user."""
    # Get product from collection
    service = CollectionService(ctx.db)
    products = service.get_collection_by_name("products")
    
    product = ctx.db.exec(
        select(Record).where(
            Record.collection_id == products.id,
            Record.id == payload.product_id
        )
    ).first()
    
    if not product:
        raise ValueError("Product not found")
    
    # Calculate total
    price = product.data["price"]
    total = price * payload.quantity
    
    # Create order record
    orders = service.get_collection_by_name("orders")
    order = service.create_record(
        orders,
        data={
            "product_id": payload.product_id,
            "quantity": payload.quantity,
            "total": total,
            "status": "pending",
        },
        owner_id=ctx.user_id,
    )
    
    return OrderOutput(order_id=str(order.id), total=total)


@on_function_complete(name="create_order")
def notify_order_created(event: FunctionCompleteEvent):
    """Send notification when order is created."""
    if event.status == "succeeded":
        print(f"Order created successfully in {event.duration_ms}ms")
```

## See Also

- [Functions Guide](../guide/functions.md)
- [Collections Guide](../guide/collections.md)
- [Extensions Guide](../guide/extensions.md)

