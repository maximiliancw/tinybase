# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "tinybase-sdk",
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
