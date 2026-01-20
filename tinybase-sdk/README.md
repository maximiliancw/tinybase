# TinyBase SDK

Python SDK for building and deploying serverless functions on TinyBase.

## Installation

```bash
pip install tinybase-sdk
```

## Usage

### Writing Functions

Create a Python file with the `@register` decorator:

```python
# /// script
# dependencies = ["tinybase-sdk"]
# ///

from pydantic import BaseModel
from tinybase_sdk import register
from tinybase_sdk.client import Client


class MyInput(BaseModel):
    name: str


class MyOutput(BaseModel):
    greeting: str


@register(
    name="greet",
    description="Greet a user by name",
    auth="auth",  # Requires authentication
)
def greet(client: Client, payload: MyInput) -> MyOutput:
    """Greet a user."""
    return MyOutput(greeting=f"Hello, {payload.name}!")


if __name__ == "__main__":
    from tinybase_sdk import run
    run()
```

### Deploying Functions

Functions are deployed using the TinyBase CLI (installed with the `tinybase` package):

```bash
# Deploy a single function
tinybase functions deploy my_function.py

# Deploy all functions in a directory
tinybase functions deploy functions/

# Deploy to a specific environment
tinybase functions deploy --env staging
```

See the [TinyBase documentation](https://maximiliancw.github.io/TinyBase/) for more details.

## Features

- **Type-safe function definitions** with Pydantic models
- **Multiple authentication modes**: public, authenticated, or admin-only
- **Structured logging** with automatic context injection
- **Auto-generated client** for calling TinyBase APIs from within functions
- **Hot-reload support** for rapid development

## Development

### Generating the API Client

The SDK includes an auto-generated client for the TinyBase API:

```bash
# From the tinybase-sdk directory
python scripts/generate_client.py
```

This will start a TinyBase server, fetch the OpenAPI spec, and generate a type-safe client.

## Package Structure

- `tinybase_sdk/` - Core SDK modules
  - `decorator.py` - `@register` decorator for function definitions
  - `cli.py` - Runtime for function execution
  - `client/` - Auto-generated API client (run `scripts/generate_client.py`)
  - `logging.py` - Structured logging utilities
  - `deployment.py` - Deployment helpers (used by TinyBase CLI)
  - `config.py` - Configuration management (used by TinyBase CLI)

## License

MIT
