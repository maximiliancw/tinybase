"""
TinyBase API module.

Contains the FastAPI application factory and all API route definitions.
"""

from tinybase.api.app import create_app

# Create a default app instance for `uvicorn tinybase.api:app`
app = create_app()

__all__ = ["create_app", "app"]
