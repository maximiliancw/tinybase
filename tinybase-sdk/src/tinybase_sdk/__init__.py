"""
TinyBase SDK for serverless functions.

Provides decorators, client, and CLI runner for TinyBase functions.
"""

from tinybase_sdk.decorator import register
from tinybase_sdk.cli import run

__all__ = ["register", "run"]
