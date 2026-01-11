"""
TinyBase SDK for serverless functions.

Provides decorators, client, and CLI runner for TinyBase functions.
"""

from tinybase_sdk.cli import run
from tinybase_sdk.decorator import register

__all__ = ["register", "run"]
