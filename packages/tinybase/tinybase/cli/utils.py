"""Shared utility functions for CLI commands."""


def snake_to_camel(name: str) -> str:
    """Convert snake_case to CamelCase."""
    return "".join(word.capitalize() for word in name.split("_"))


def create_default_toml() -> str:
    """Generate default tinybase.toml content."""
    return """# TinyBase Configuration
# See documentation for all available options

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
dir = "./functions"

[scheduler]
enabled = true
interval_seconds = 5

[cors]
allow_origins = ["*"]

[admin]
static_dir = "builtin"

# Serve your own frontend/SPA at the root path
# Uncomment and set the directory for your static files
# The directory must contain an index.html file
# [public]
# static_dir = "./dist"

# Environment-specific settings for deployment
# [environments.production]
# url = "https://tinybase.example.com"
# api_token = "your-admin-token"
"""


def create_function_boilerplate(name: str, description: str) -> str:
    """Generate boilerplate code for a new function."""
    return f'''# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "tinybase-sdk",
#     "httpx>=0.28.1",
# ]
# ///

"""
{description}
"""

from tinybase_sdk import register, run
from tinybase_sdk.client import Client


@register(
    name="{name}",
    description="{description}",
    auth="auth",
)
def {name}(client: Client, payload: dict) -> dict:
    """
    {description}

    TODO: Implement function logic

    You can use basic types (str, int, dict, list) or Pydantic models.
    Example with basic types:
        def {name}(client: Client, name: str, age: int) -> dict[str, str]:
            return {{"greeting": f"Hello {{name}}, you are {{age}}"}}

    Example with Pydantic:
        from pydantic import BaseModel

        class Input(BaseModel):
            name: str
            age: int

        def {name}(client: Client, payload: Input) -> dict:
            return {{"greeting": f"Hello {{payload.name}}"}}
    """
    return {{}}


if __name__ == "__main__":
    run()
'''


def get_example_functions() -> list[tuple[str, str]]:
    """Get list of example function files to create during init."""
    return [
        (
            "add_numbers.py",
            '''# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "tinybase-sdk",
#     "httpx>=0.28.1",
# ]
# ///

"""
Add Numbers Function

Example function demonstrating how to define a TinyBase function.
"""

from tinybase_sdk import register, run
from tinybase_sdk.client import Client


@register(
    name="add_numbers",
    description="Add two numbers together",
    auth="public",  # Available without authentication
    tags=["math", "example"],
)
def add_numbers(client: Client, x: int, y: int) -> dict[str, int]:
    """
    Add two numbers and return the sum.

    This is an example function showing how to:
    - Use basic types (int) for input/output
    - Use the @register decorator
    - Access the TinyBase API via client
    """
    return {"sum": x + y}


if __name__ == "__main__":
    run()
''',
        ),
        (
            "hello.py",
            '''# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "tinybase-sdk",
#     "httpx>=0.28.1",
# ]
# ///

"""
Hello World Function

Example function demonstrating user context access via API client.
"""

from pydantic import BaseModel
from tinybase_sdk import register, run
from tinybase_sdk.client import Client


class HelloInput(BaseModel):
    """Input model for hello function."""
    name: str = "World"


class HelloOutput(BaseModel):
    """Output model for hello function."""
    message: str
    user_id: str | None = None


@register(
    name="hello",
    description="Say hello to someone",
    auth="auth",  # Requires authentication
    tags=["example"],
)
def hello(client: Client, payload: HelloInput) -> HelloOutput:
    """
    Return a greeting message.

    Demonstrates using Pydantic models for input/output validation.
    User information is available via the client's authentication context.
    """
    # Note: user_id would be available from the client's auth context
    # For now, we'll return None as the client doesn't expose user_id directly
    return HelloOutput(
        message=f"Hello, {payload.name}!",
        user_id=None,  # Could be accessed via client if needed
    )


if __name__ == "__main__":
    run()
''',
        ),
        (
            "fetch_url.py",
            '''# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "tinybase-sdk",
#     "httpx>=0.28.1",
#     "requests>=2.32.0",
# ]
# ///

"""
Fetch URL Function

Example function demonstrating uv's single-file script feature with inline dependencies.
This function uses the requests library which is automatically installed when loaded.
"""

from pydantic import BaseModel
from tinybase_sdk import register, run
from tinybase_sdk.client import Client
import requests


class FetchUrlInput(BaseModel):
    """Input model for fetch_url function."""
    url: str
    timeout: int = 10  # Timeout in seconds


class FetchUrlOutput(BaseModel):
    """Output model for fetch_url function."""
    status_code: int
    title: str | None = None
    headers: dict[str, str]
    success: bool
    error: str | None = None


@register(
    name="fetch_url",
    description="Fetch a URL and return its status, title, and headers",
    auth="public",  # Available without authentication
    tags=["http", "example"],
)
def fetch_url(client: Client, payload: FetchUrlInput) -> FetchUrlOutput:
    """
    Fetch a URL and return its HTTP status, page title, and response headers.

    This function demonstrates:
    - Using uv's inline dependency feature (requests library)
    - Making HTTP requests
    - Parsing HTML to extract the title
    - Error handling

    The requests library is automatically installed when this function is loaded
    thanks to the inline dependency declaration at the top of the file.
    """
    try:
        response = requests.get(payload.url, timeout=payload.timeout)
        response.raise_for_status()

        # Try to extract title from HTML
        title = None
        if "text/html" in response.headers.get("content-type", ""):
            try:
                import re
                # Simple regex to extract title tag content
                title_match = re.search(r'<title[^>]*>(.*?)</title>', response.text[:10000], re.IGNORECASE | re.DOTALL)
                if title_match:
                    title = title_match.group(1).strip()
            except Exception:
                pass

        # Convert headers to dict (requests returns CaseInsensitiveDict)
        headers_dict = dict(response.headers)

        return FetchUrlOutput(
            status_code=response.status_code,
            title=title,
            headers=headers_dict,
            success=True,
            error=None,
        )
    except requests.exceptions.RequestException as e:
        return FetchUrlOutput(
            status_code=0,
            title=None,
            headers={},
            success=False,
            error=str(e),
        )


if __name__ == "__main__":
    run()
''',
        ),
    ]
