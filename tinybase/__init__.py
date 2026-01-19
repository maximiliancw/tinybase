"""
TinyBase - A lightweight, self-hosted Backend-as-a-Service framework for Python developers.

TinyBase provides:
- SQLite-backed data storage with dynamic collections
- User authentication with JWT tokens
- Typed server-side functions with Pydantic models
- Scheduling (once, interval, cron)
- Admin UI built with Vue 3
- OpenAPI documentation
"""

from tinybase.version import __version__

__all__ = ["__version__"]
