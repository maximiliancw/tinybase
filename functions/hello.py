# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "tinybase-sdk",
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
