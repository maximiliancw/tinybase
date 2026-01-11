"""
TinyBase Functions module.

Provides the typed server-side functions system:
- Context: Execution context available to all functions
- register: Decorator for registering functions
- FunctionRegistry: Central registry for all registered functions
"""

from tinybase.functions.context import Context
from tinybase.functions.register import register

__all__ = [
    "Context",
    "register",
]
