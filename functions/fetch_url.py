# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "tinybase-sdk",
#     "requests>=2.32.0",
# ]
# ///

"""
Fetch URL Function

Example function demonstrating uv's single-file script feature with inline dependencies.
This function uses the requests library which is automatically installed when loaded.
"""

import requests
from pydantic import BaseModel
from tinybase_sdk import register, run
from tinybase_sdk.client import Client


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
                title_match = re.search(
                    r"<title[^>]*>(.*?)</title>", response.text[:10000], re.IGNORECASE | re.DOTALL
                )
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
