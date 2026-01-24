"""
Function registration decorator.

Provides the @register decorator for defining server-side functions
that are exposed via HTTP and can be scheduled.
"""

import inspect
from typing import Callable

from pydantic import BaseModel

from tinybase.functions.core import FunctionMeta, get_function_registry
from tinybase.utils import AuthLevel, utcnow


def register(
    name: str,
    description: str | None = None,
    auth: AuthLevel | str = AuthLevel.AUTH,
    input_model: type[BaseModel] | None = None,
    output_model: type[BaseModel] | None = None,
    tags: list[str] | None = None,
) -> Callable[[Callable], Callable]:
    """
    Decorator to register a function with TinyBase.

    Registered functions are:
    - Exposed as HTTP endpoints at POST /api/functions/{name}
    - Available for scheduling via the scheduler
    - Documented in the OpenAPI schema

    Args:
        name: Unique function name (used in URLs and scheduling)
        description: Human-readable description for docs
        auth: Authentication requirement:
            - "public": No authentication required
            - "auth": Any authenticated user
            - "admin": Admin users only
        input_model: Pydantic model for input validation
        output_model: Pydantic model for output (used in OpenAPI)
        tags: Categorization tags for grouping in docs

    Returns:
        Decorator function

    Example:
        from pydantic import BaseModel
        from tinybase.functions import register

        class AddInput(BaseModel):
            x: int
            y: int

        class AddOutput(BaseModel):
            sum: int

        @register(
            name="add_numbers",
            description="Add two numbers together",
            auth="auth",
            input_model=AddInput,
            output_model=AddOutput,
            tags=["math"],
        )
        def add_numbers(payload: AddInput) -> AddOutput:
            return AddOutput(sum=payload.x + payload.y)
    """

    def decorator(func: Callable) -> Callable:
        # Get module and file information
        module = func.__module__

        try:
            file_path = inspect.getfile(func)
        except (TypeError, OSError):
            file_path = ""

        # Convert string auth to enum if needed
        auth_level = auth if isinstance(auth, AuthLevel) else AuthLevel(auth)

        # Create function metadata
        meta = FunctionMeta(
            name=name,
            description=description,
            auth=auth_level,
            tags=tags or [],
            input_model=input_model,
            output_model=output_model,
            module=module,
            file_path=file_path,
            last_loaded_at=utcnow(),
            callable=func,
        )

        # Register with global registry
        registry = get_function_registry()
        registry.register(meta)

        # Store metadata on the function for inspection
        func._tinybase_meta = meta  # type: ignore

        return func

    return decorator
