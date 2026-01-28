"""
TinyBase Functions module.

Provides the typed server-side functions system:
- register: Decorator for registering functions
- FunctionRegistry: Central registry for all registered functions

Note: Functions use the SDK's FunctionContext when running in subprocess.
"""

from tinybase.functions.register import register

__all__ = [
    "register",
]
