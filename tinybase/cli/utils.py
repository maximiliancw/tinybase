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
path = "./functions"

[scheduler]
enabled = true
interval_seconds = 5

[cors]
allow_origins = ["*"]

[admin]
static_dir = "builtin"

# Environment-specific settings for deployment
# [environments.production]
# url = "https://tinybase.example.com"
# api_token = "your-admin-token"
"""


def create_function_boilerplate(name: str, description: str) -> str:
    """Generate boilerplate code for a new function."""
    camel_name = snake_to_camel(name)

    return f'''"""
{description}
"""

from pydantic import BaseModel
from tinybase.functions import Context, register


class {camel_name}Input(BaseModel):
    """Input model for {name} function."""
    # TODO: Define input fields
    pass


class {camel_name}Output(BaseModel):
    """Output model for {name} function."""
    # TODO: Define output fields
    pass


@register(
    name="{name}",
    description="{description}",
    auth="auth",
    input_model={camel_name}Input,
    output_model={camel_name}Output,
    tags=[],
)
def {name}(ctx: Context, payload: {camel_name}Input) -> {camel_name}Output:
    """
    {description}

    TODO: Implement function logic
    """
    return {camel_name}Output()
'''


def get_example_functions() -> list[tuple[str, str]]:
    """Get list of example function files to create during init."""
    return [
        (
            "add_numbers.py",
            '''"""
Add Numbers Function

Example function demonstrating how to define a TinyBase function.
"""

from pydantic import BaseModel
from tinybase.functions import Context, register


class AddInput(BaseModel):
    """Input model for add_numbers function."""
    x: int
    y: int


class AddOutput(BaseModel):
    """Output model for add_numbers function."""
    sum: int


@register(
    name="add_numbers",
    description="Add two numbers together",
    auth="public",  # Available without authentication
    input_model=AddInput,
    output_model=AddOutput,
    tags=["math", "example"],
)
def add_numbers(ctx: Context, payload: AddInput) -> AddOutput:
    """
    Add two numbers and return the sum.

    This is an example function showing how to:
    - Define input/output models with Pydantic
    - Use the @register decorator
    - Access the Context object
    """
    return AddOutput(sum=payload.x + payload.y)
''',
        ),
        (
            "hello.py",
            '''"""
Hello World Function

Example function demonstrating user context access.
"""

from pydantic import BaseModel
from tinybase.functions import Context, register


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
    input_model=HelloInput,
    output_model=HelloOutput,
    tags=["example"],
)
def hello(ctx: Context, payload: HelloInput) -> HelloOutput:
    """
    Return a greeting message.

    Demonstrates accessing user information from the context.
    """
    return HelloOutput(
        message=f"Hello, {payload.name}!",
        user_id=str(ctx.user_id) if ctx.user_id else None,
    )
''',
        ),
        (
            "fetch_url.py",
            '''# /// script
# dependencies = [
#   "requests>=2.32.0",
# ]
# ///

"""
Fetch URL Function

Example function demonstrating uv's single-file script feature with inline dependencies.
This function uses the requests library which is automatically installed when loaded.
"""

from pydantic import BaseModel
from tinybase.functions import Context, register
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
    input_model=FetchUrlInput,
    output_model=FetchUrlOutput,
    tags=["http", "example"],
)
def fetch_url(ctx: Context, payload: FetchUrlInput) -> FetchUrlOutput:
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
''',
        ),
    ]
