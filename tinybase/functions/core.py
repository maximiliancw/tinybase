"""
Function registry and execution helpers.

Provides:
- FunctionMeta: Metadata about registered functions
- FunctionRegistry: Central registry for all functions
- Execution helpers for invoking functions and recording calls
"""

import asyncio
import inspect
import logging
import traceback
from inspect import iscoroutinefunction
from datetime import datetime
from typing import Any, Callable
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlmodel import Session

from tinybase.db.models import FunctionCall
from tinybase.functions.context import Context
from tinybase.utils import utcnow, FunctionCallStatus, TriggerType, AuthLevel

logger = logging.getLogger(__name__)


class FunctionMeta(BaseModel):
    """
    Metadata for a registered function.
    
    Attributes:
        name: Unique function name (used in URLs and scheduling)
        description: Human-readable description
        auth: Authentication requirement (public, auth, or admin)
        tags: Categorization tags
        input_schema: JSON Schema for input validation (from Pydantic model or type hints)
        output_schema: JSON Schema for output (from Pydantic model or type hints)
        file_path: File path where the function is defined
        last_loaded_at: When the function was last loaded/registered
    """
    
    name: str
    description: str | None = None
    auth: AuthLevel = AuthLevel.AUTH
    tags: list[str] = []
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    file_path: str = ""
    last_loaded_at: datetime | None = None
    
    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if self.last_loaded_at is None:
            self.last_loaded_at = utcnow()


class FunctionRegistry:
    """
    Central registry for TinyBase functions.
    
    Manages the registration, lookup, and execution of server-side functions.
    Functions are registered using the @register decorator and can be invoked
    via HTTP or the scheduler.
    """
    
    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._functions: dict[str, FunctionMeta] = {}
    
    def register(self, meta: FunctionMeta) -> None:
        """
        Register a function with its metadata.
        
        Args:
            meta: Function metadata including the callable
        """
        self._functions[meta.name] = meta
    
    def get(self, name: str) -> FunctionMeta | None:
        """
        Get metadata for a function by name.
        
        Args:
            name: Function name
        
        Returns:
            FunctionMeta or None if not found
        """
        return self._functions.get(name)
    
    def all(self) -> dict[str, FunctionMeta]:
        """
        Get all registered functions.
        
        Returns:
            Dictionary mapping function names to metadata
        """
        return self._functions.copy()
    
    def names(self) -> list[str]:
        """
        Get all registered function names.
        
        Returns:
            List of function names
        """
        return list(self._functions.keys())
    
    def unregister(self, name: str) -> None:
        """
        Remove a function from the registry.
        
        Args:
            name: Function name to remove
        """
        self._functions.pop(name, None)
    
    def clear(self) -> None:
        """Clear all registered functions."""
        self._functions.clear()


# Global registry instance
_registry: FunctionRegistry | None = None


def get_global_registry() -> FunctionRegistry:
    """Get the global function registry, creating it if needed."""
    global _registry
    if _registry is None:
        _registry = FunctionRegistry()
    return _registry


def reset_global_registry() -> None:
    """Reset the global registry (primarily for testing)."""
    global _registry
    if _registry is not None:
        _registry.clear()
    _registry = None


# =============================================================================
# Function Execution
# =============================================================================


class FunctionCallResult(BaseModel):
    """Result of a function execution."""
    
    call_id: str
    status: FunctionCallStatus
    result: Any = None
    error_message: str | None = None
    error_type: str | None = None
    duration_ms: int | None = None


def _run_async_hook(coro: Any) -> None:
    """Run an async hook, handling existing event loops gracefully."""
    try:
        loop = asyncio.get_running_loop()
        # We're in an async context, schedule it
        asyncio.ensure_future(coro)
    except RuntimeError:
        # No running loop, we can use asyncio.run directly
        try:
            asyncio.run(coro)
        except Exception as e:
            logger.error(f"Error running async hook: {e}")


def execute_function(
    meta: FunctionMeta,
    payload: Any,
    session: Session,
    user_id: UUID | None = None,
    is_admin: bool = False,
    trigger_type: TriggerType = TriggerType.MANUAL,
    trigger_id: UUID | None = None,
    request: Any = None,
) -> FunctionCallResult:
    """
    Execute a registered function and record the call.
    
    This function:
    1. Creates a FunctionCall record with status "running"
    2. Runs on_function_call hooks
    3. Builds the Context object
    4. Validates and converts the input payload
    5. Calls the underlying function
    6. Updates the FunctionCall with results
    7. Runs on_function_complete hooks
    8. Returns the result or error information
    
    Args:
        meta: Function metadata
        payload: Input data (dict or Pydantic model)
        session: Database session
        user_id: ID of the user invoking the function
        is_admin: Whether the user has admin privileges
        trigger_type: How the function was triggered
        trigger_id: Schedule ID if scheduled
        request: FastAPI Request object (for manual triggers)
    
    Returns:
        FunctionCallResult with execution status and result/error
    """
    from tinybase.extensions.hooks import (
        FunctionCallEvent,
        FunctionCompleteEvent,
        run_function_call_hooks,
        run_function_complete_hooks,
    )
    
    # Generate request ID for this execution
    request_id = uuid4()
    now = utcnow()
    
    # Create function call record
    function_call = FunctionCall(
        id=request_id,
        function_name=meta.name,
        status=FunctionCallStatus.RUNNING,
        trigger_type=trigger_type,
        trigger_id=trigger_id,
        requested_by_user_id=user_id,
        started_at=now,
    )
    session.add(function_call)
    session.commit()
    
    # Run function call hooks (before execution)
    payload_dict = payload if isinstance(payload, dict) else {}
    if isinstance(payload, BaseModel):
        payload_dict = payload.model_dump()
    
    call_event = FunctionCallEvent(
        function_name=meta.name,
        user_id=user_id,
        payload=payload_dict,
    )
    _run_async_hook(run_function_call_hooks(call_event))
    
    # Build context
    ctx = Context(
        function_name=meta.name,
        trigger_type=trigger_type,
        trigger_id=trigger_id,
        request_id=request_id,
        user_id=user_id,
        is_admin=is_admin,
        now=now,
        db=session,
        request=request,
    )
    
    # Validate input if model is specified
    validated_payload = None
    if meta.input_model is not None:
        if isinstance(payload, dict):
            validated_payload = meta.input_model.model_validate(payload)
        elif isinstance(payload, meta.input_model):
            validated_payload = payload
        else:
            validated_payload = meta.input_model.model_validate(payload)
    
    # Execute the function
    result = None
    error_message = None
    error_type = None
    status = FunctionCallStatus.SUCCEEDED
    
    try:
        if meta.callable is None:
            raise ValueError(f"Function '{meta.name}' has no callable")
        
        # Call with or without payload based on input model
        if validated_payload is not None:
            raw_result = meta.callable(ctx, validated_payload)
        elif meta.input_model is not None:
            # Input model specified but no payload - use defaults
            raw_result = meta.callable(ctx, meta.input_model())
        else:
            # No input model - call with just context
            raw_result = meta.callable(ctx)
        
        # Handle async functions
        if asyncio.iscoroutine(raw_result):
            # If we're already in an async context, await directly
            # Otherwise, run in event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, need to run in executor
                # Since we can't await from sync, schedule it
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, raw_result)
                    result = future.result()
            except RuntimeError:
                # No running loop, we can use asyncio.run directly
                result = asyncio.run(raw_result)
        else:
            result = raw_result
        
        # Convert result to dict if it's a Pydantic model
        if isinstance(result, BaseModel):
            result = result.model_dump()
        
    except Exception as e:
        status = FunctionCallStatus.FAILED
        error_message = str(e)
        error_type = type(e).__name__
        # Log the full traceback for debugging
        traceback.print_exc()
    
    # Calculate duration
    finished_at = utcnow()
    duration_ms = int((finished_at - now).total_seconds() * 1000)
    
    # Update function call record
    function_call.status = status
    function_call.finished_at = finished_at
    function_call.duration_ms = duration_ms
    function_call.error_message = error_message
    function_call.error_type = error_type
    session.add(function_call)
    session.commit()
    
    # Run function complete hooks (after execution)
    complete_event = FunctionCompleteEvent(
        function_name=meta.name,
        user_id=user_id,
        status=status,
        duration_ms=duration_ms,
        error_message=error_message,
        error_type=error_type,
    )
    _run_async_hook(run_function_complete_hooks(complete_event))
    
    return FunctionCallResult(
        call_id=str(request_id),
        status=status,
        result=result,
        error_message=error_message,
        error_type=error_type,
        duration_ms=duration_ms,
    )

