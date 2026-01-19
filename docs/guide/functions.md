# Functions

Functions are the heart of TinyBase's extensibility. They let you define server-side logic with full type safety, automatic API exposure, and execution tracking.

## Overview

A TinyBase function is:

- A **Python callable** decorated with `@register`
- **Typed** with Pydantic input/output models
- **Exposed** as an HTTP endpoint at `/api/functions/{name}`
- **Tracked** with execution metadata (status, duration, errors)
- **Schedulable** for automated execution

## Defining Functions

Functions are defined in individual files within the `functions/` package directory using the TinyBase SDK. Each function should live in its own file, allowing you to use uv's single-file script feature for inline dependencies.

Functions execute in isolated subprocess environments, providing better isolation and automatic dependency management.

### Basic Structure

```python title="functions/my_function.py"
# /// script
# dependencies = [
#   "tinybase-sdk",
# ]
# ///

from pydantic import BaseModel
from tinybase_sdk import register
from tinybase_sdk.cli import run


class MyInput(BaseModel):
    """Input model - define expected parameters."""
    param1: str
    param2: int = 0  # Optional with default


class MyOutput(BaseModel):
    """Output model - define response structure."""
    result: str
    success: bool


@register(
    name="my_function",           # Unique name (used in URLs)
    description="What it does",    # For documentation
    auth="auth",                   # Access level
    tags=["category"],             # For grouping
)
def my_function(client, payload: MyInput) -> MyOutput:
    """Implementation goes here."""
    # Use client to make API calls back to TinyBase if needed
    return MyOutput(result=f"Got {payload.param1}", success=True)


if __name__ == "__main__":
    run()
```

### The @register Decorator

The SDK's `@register` decorator automatically extracts type hints from your function signature to generate JSON schemas for input and output validation.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Unique function identifier |
| `description` | `str` | Human-readable description |
| `auth` | `str` | Access level: `"public"`, `"auth"`, `"admin"` |
| `tags` | `list[str]` | Categorization tags |

**Note:** Input and output schemas are automatically generated from Python type hints. You can use Pydantic models or basic types (str, int, dict, list, etc.).

### Authentication Levels

| Level | Description |
|-------|-------------|
| `public` | No authentication required |
| `auth` | Any authenticated user |
| `admin` | Admin users only |

## The Client Object

Every function receives a `Client` object that provides authenticated access to the TinyBase API:

```python
from tinybase_sdk.client import Client

# Client is automatically created and passed to your function
def my_function(client: Client, payload: MyInput) -> MyOutput:
    # Use client to make API calls
    response = client.get("/api/collections")
    collections = response.json()
    
    return MyOutput(result="ok")
```

The client is pre-configured with:
- Base URL pointing to the TinyBase API
- Authentication token with the same permissions as the calling user
- Automatic request/response handling

### Structured Logging

Functions can use structured logging for better observability:

```python
from tinybase_sdk import register, StructuredLogger

@register(name="logged_function")
def logged_function(client, payload: dict) -> dict:
    # Logger is automatically available if logging is enabled
    # Logs are sent to stderr in JSON format
    logger = StructuredLogger(
        function_name="logged_function",
        request_id="...",  # Automatically provided
        user_id="...",     # Automatically provided
    )
    
    logger.info("Processing request", extra_data=payload)
    logger.debug("Debug information")
    logger.error("Error occurred", exc_info=True)
    
    return {"result": "ok"}
```

## Input and Output Models

Use Pydantic models for type-safe inputs and outputs:

### Complex Input Models

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class OrderInput(BaseModel):
    """Create a new order."""
    product_id: str = Field(..., description="Product UUID")
    quantity: int = Field(ge=1, le=100, description="Quantity (1-100)")
    notes: Optional[str] = Field(None, max_length=500)
    
    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v):
        if v < 1:
            raise ValueError("Quantity must be at least 1")
        return v


class OrderOutput(BaseModel):
    """Order creation result."""
    order_id: str
    total_price: float
    estimated_delivery: datetime
```

### Nested Models

```python
class Address(BaseModel):
    street: str
    city: str
    country: str
    postal_code: str


class ShippingInput(BaseModel):
    order_id: str
    shipping_address: Address
    billing_address: Optional[Address] = None


class ShippingOutput(BaseModel):
    tracking_number: str
    carrier: str
```

## Calling Functions

### Via REST API

```bash
curl -X POST http://localhost:8000/api/functions/my_function \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"param1": "hello", "param2": 42}'
```

Response:

```json
{
  "call_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "succeeded",
  "result": {
    "result": "Got hello",
    "success": true
  }
}
```

### Response Structure

| Field | Description |
|-------|-------------|
| `call_id` | Unique execution ID |
| `status` | `"succeeded"` or `"failed"` |
| `result` | Output data (on success) |
| `error` | Error message (on failure) |
| `error_type` | Exception type (on failure) |

### Error Responses

```json
{
  "call_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "error": "Product not found",
  "error_type": "ValueError"
}
```

## API Operations

Access TinyBase resources through the `client` object:

```python
@register(name="user_stats", auth="admin")
def user_stats(client, payload: dict) -> dict:
    # Get collections
    collections_response = client.get("/api/collections")
    collections = collections_response.json()
    
    # Get users (admin endpoint)
    users_response = client.get("/api/admin/users")
    users = users_response.json()
    
    return {
        "total_users": len(users),
        "total_collections": len(collections)
    }
```

### Creating Records

```python
@register(name="create_item", auth="auth")
def create_item(client, payload: CreateInput) -> CreateOutput:
    # Create a record via API
    response = client.post(
        "/api/collections/items/records",
        json={"data": {"title": payload.title, "value": payload.value}}
    )
    
    record = response.json()
    return CreateOutput(id=record["id"])
```

## Error Handling

Raise exceptions to report errors:

```python
@register(name="divide", auth="public", ...)
def divide(ctx: Context, payload: DivideInput) -> DivideOutput:
    if payload.divisor == 0:
        raise ValueError("Cannot divide by zero")
    
    return DivideOutput(result=payload.dividend / payload.divisor)
```

### Custom Exceptions

```python
class InsufficientFundsError(Exception):
    """Raised when account balance is too low."""
    pass


@register(name="withdraw", auth="auth", ...)
def withdraw(ctx: Context, payload: WithdrawInput) -> WithdrawOutput:
    balance = get_balance(ctx.user_id)
    
    if payload.amount > balance:
        raise InsufficientFundsError(
            f"Balance ({balance}) is less than withdrawal ({payload.amount})"
        )
    
    # Process withdrawal...
```

## Function Call Tracking

Every function execution creates a `FunctionCall` record:

```python
@dataclass
class FunctionCall:
    id: UUID                    # Unique call ID
    function_name: str          # Function name
    user_id: UUID | None        # Who called it
    trigger_type: str           # "manual" or "schedule"
    trigger_id: UUID | None     # Schedule ID
    status: str                 # "succeeded" or "failed"
    duration_ms: int            # Execution time
    error_message: str | None   # Error details
    error_type: str | None      # Exception type
    created_at: datetime        # When it ran
```

View function calls in the Admin UI under **Function Calls**.

## Rate Limiting

TinyBase enforces **concurrent execution limits** to prevent resource exhaustion. This is different from traditional time-window rate limiting - it limits how many functions can run simultaneously per user.

### How It Works

- Each user can have a maximum number of concurrent function executions
- When a user tries to execute more functions than allowed, they receive a `429 Too Many Requests` error
- The counter automatically decrements when functions complete (even on errors)
- System and scheduled functions are not rate limited

### Configuration

Set the maximum concurrent executions per user:

**In `tinybase.toml`**:

```toml
[functions]
max_concurrent_functions_per_user = 10
```

**In Admin UI**:

Navigate to **Settings** → **Instance Settings** → **Rate Limiting** to configure at runtime.

### Backend Options

Rate limiting uses a backend to track concurrent executions:

**DiskCache (Default)** - Local file-based storage:

```toml
[rate_limit]
backend = "diskcache"
cache_dir = "./.tinybase/rate_limit_cache"
```

**Redis** - For distributed/multi-instance deployments:

```toml
[rate_limit]
backend = "redis"
redis_url = "redis://localhost:6379/0"
```

### Error Response

When rate limit is exceeded:

```json
{
  "detail": "Rate limit exceeded: maximum 10 concurrent functions per user",
  "status_code": 429
}
```

Response includes `Retry-After: 60` header suggesting when to retry.

### Best Practices

- Use Redis backend for multi-instance deployments
- Set limits based on your server capacity
- Monitor rate limit rejections in logs
- Consider increasing limits for trusted users via custom middleware

## Generating Function Boilerplate

Use the CLI to create new functions:

```bash
tinybase functions new calculate_tax -d "Calculate tax for an order"
```

This creates a new file `functions/calculate_tax.py` using the SDK format:

```python title="functions/calculate_tax.py"
# /// script
# dependencies = [
#   "tinybase-sdk",
# ]
# ///

from pydantic import BaseModel
from tinybase_sdk import register
from tinybase_sdk.cli import run


class CalculateTaxInput(BaseModel):
    """Input model for calculate_tax function."""
    # TODO: Define input fields
    pass


class CalculateTaxOutput(BaseModel):
    """Output model for calculate_tax function."""
    # TODO: Define output fields
    pass


@register(
    name="calculate_tax",
    description="Calculate tax for an order",
    auth="auth",
    tags=[],
)
def calculate_tax(client, payload: CalculateTaxInput) -> CalculateTaxOutput:
    """
    Calculate tax for an order
    
    TODO: Implement function logic
    """
    return CalculateTaxOutput()


if __name__ == "__main__":
    run()
```

## Organizing Functions

All user-defined functions must live in the `functions/` package directory. Each function should be in its own file:

```
my-app/
├── functions/
│   ├── __init__.py        # Package marker (auto-generated)
│   ├── add_numbers.py     # One function per file
│   ├── hello.py
│   ├── orders.py          # Order-related functions
│   ├── users.py           # User-related functions
│   └── reports.py         # Reporting functions
└── tinybase.toml
```

Each file can define functions independently:

```python title="functions/orders.py"
from pydantic import BaseModel
from tinybase.functions import Context, register


class CreateOrderInput(BaseModel):
    ...


@register(name="create_order", ...)
def create_order(ctx: Context, payload: CreateOrderInput) -> ...:
    ...
```

### Using uv's Single-File Script Feature

Each function file uses uv's single-file script feature to define inline dependencies. This allows you to use third-party libraries without manually managing dependencies:

```python title="functions/send_email.py"
# /// script
# dependencies = [
#   "tinybase-sdk",
#   "requests>=2.31.0",
#   "python-dotenv>=1.0.0",
# ]
# ///

from pydantic import BaseModel
from tinybase_sdk import register
from tinybase_sdk.cli import run
import requests


class SendEmailInput(BaseModel):
    to: str
    subject: str
    body: str


class SendEmailOutput(BaseModel):
    success: bool
    message_id: str | None = None


@register(
    name="send_email",
    description="Send an email using an external service",
    auth="auth",
    tags=["communication"],
)
def send_email(client, payload: SendEmailInput) -> SendEmailOutput:
    """Send email using requests library."""
    response = requests.post(
        "https://api.example.com/send",
        json={"to": payload.to, "subject": payload.subject, "body": payload.body}
    )
    return SendEmailOutput(
        success=response.status_code == 200,
        message_id=response.json().get("id") if response.ok else None,
    )


if __name__ == "__main__":
    run()
```

When TinyBase loads this function, it will automatically detect and install the dependencies using `uv`. Functions execute in isolated subprocess environments, ensuring dependency isolation and better security.

## Best Practices

### 1. Keep Functions Focused

Each function should do one thing well:

```python
# Good: Focused function
@register(name="send_welcome_email", ...)
def send_welcome_email(ctx: Context, payload: Input) -> Output:
    ...

# Bad: Function doing too much
@register(name="register_user_and_send_email_and_create_profile", ...)
def register_user_and_send_email_and_create_profile(...):
    ...
```

### 2. Use Descriptive Names

```python
# Good
@register(name="calculate_order_total", ...)
@register(name="send_password_reset", ...)

# Bad
@register(name="calc", ...)
@register(name="do_stuff", ...)
```

### 3. Document Your Functions

```python
@register(name="process_refund", ...)
def process_refund(ctx: Context, payload: RefundInput) -> RefundOutput:
    """
    Process a refund for an order.
    
    This function:
    1. Validates the order exists and is eligible
    2. Calculates the refund amount
    3. Updates the order status
    4. Triggers payment processor refund
    
    Raises:
        ValueError: If order not found or not eligible
        PaymentError: If refund processing fails
    """
    ...
```

### 4. Handle Errors Gracefully

```python
@register(name="external_api_call", ...)
def external_api_call(ctx: Context, payload: Input) -> Output:
    try:
        response = call_external_api(payload.data)
        return Output(result=response)
    except ConnectionError:
        raise RuntimeError("External API unavailable, please try again")
    except TimeoutError:
        raise RuntimeError("Request timed out, please try again")
```

## See Also

- [Scheduling Guide](scheduling.md) - Run functions automatically
- [Extensions Guide](extensions.md) - Hook into function lifecycle
- [Python API Reference](../reference/python-api.md) - Full API documentation

