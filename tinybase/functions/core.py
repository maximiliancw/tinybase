"""
Function registry and execution helpers.

Provides:
- FunctionMeta: Metadata about registered functions
- FunctionRegistry: Central registry for all functions
- Execution helpers for invoking functions and recording calls
"""

import asyncio
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlmodel import Session

from tinybase.db.models import FunctionCall
from tinybase.utils import AuthLevel, FunctionCallStatus, TriggerType, utcnow

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
        asyncio.get_running_loop()
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
    Execute a registered function via subprocess and record the call.

    This function:
    1. Creates a FunctionCall record with status "running"
    2. Runs on_function_call hooks
    3. Creates internal token for subprocess HTTP callbacks
    4. Executes function in subprocess via uv run --script
    5. Updates the FunctionCall with results
    6. Runs on_function_complete hooks
    7. Returns the result or error information

    Args:
        meta: Function metadata
        payload: Input data (dict)
        session: Database session
        user_id: ID of the user invoking the function
        is_admin: Whether the user has admin privileges
        trigger_type: How the function was triggered
        trigger_id: Schedule ID if scheduled
        request: FastAPI Request object (for manual triggers, unused in subprocess)

    Returns:
        FunctionCallResult with execution status and result/error
    """
    from tinybase.auth import create_internal_token
    from tinybase.config import settings
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

    # Create internal token for subprocess to call back
    config = settings()
    internal_token = create_internal_token(
        session=session,
        user_id=user_id,
        is_admin=is_admin,
        expires_minutes=5,
    )

    # Build context for subprocess (JSON-serializable)
    context_data = {
        "api_base_url": f"http://127.0.0.1:{config.server_port}/api",
        "auth_token": internal_token,
        "user_id": str(user_id) if user_id else None,
        "is_admin": is_admin,
        "request_id": str(request_id),
        "function_name": meta.name,
    }

    # Add logging configuration if enabled
    if getattr(config, "function_logging_enabled", True):
        context_data["logging_enabled"] = True
        context_data["logging_level"] = getattr(config, "function_logging_level", "INFO")
        context_data["logging_format"] = getattr(config, "function_logging_format", "json")
    else:
        context_data["logging_enabled"] = False

    input_json = json.dumps({"context": context_data, "payload": payload_dict})

    # Execute in subprocess
    result = None
    error_message = None
    error_type = None
    status = FunctionCallStatus.SUCCEEDED

    # Capture logs from stderr if logging is enabled
    capture_logs = getattr(config, "function_logging_enabled", True)
    logs: list[dict[str, Any]] = []

    # Check cold start pool for warm process (optimization)
    from tinybase.functions.pool import get_pool

    pool = get_pool()
    warm_process = pool.get_warm_process(Path(meta.file_path))

    try:
        timeout_seconds = getattr(config, "scheduler_function_timeout_seconds", 1800)
        subprocess_result = subprocess.run(
            ["uv", "run", "--script", meta.file_path],
            input=input_json,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )

        # Return warm process to pool for reuse
        if warm_process:
            pool.return_warm_process(Path(meta.file_path), warm_process)
        else:
            # Mark as warm for future calls
            pool.prewarm_function(Path(meta.file_path))

        # Parse structured logs from stderr if logging is enabled
        if capture_logs and subprocess_result.stderr:
            for line in subprocess_result.stderr.strip().split("\n"):
                if line.strip():
                    try:
                        log_entry = json.loads(line)
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        # Not JSON, might be a regular error message
                        if line.strip():
                            logs.append(
                                {
                                    "level": "ERROR",
                                    "message": line,
                                    "function": meta.name,
                                    "request_id": str(request_id),
                                }
                            )

        if subprocess_result.returncode != 0:
            # Subprocess failed
            status = FunctionCallStatus.FAILED
            error_message = subprocess_result.stderr or "Function execution failed"
            error_type = "SubprocessError"
        else:
            # Parse JSON output
            try:
                output = json.loads(subprocess_result.stdout)
                if output.get("status") == "succeeded":
                    result = output.get("result")
                else:
                    status = FunctionCallStatus.FAILED
                    error_message = output.get("error", "Unknown error")
                    error_type = output.get("error_type", "Error")
            except json.JSONDecodeError as e:
                status = FunctionCallStatus.FAILED
                error_message = f"Failed to parse function output: {e}"
                error_type = "JSONDecodeError"

    except subprocess.TimeoutExpired:
        status = FunctionCallStatus.FAILED
        error_message = "Function execution timed out"
        error_type = "TimeoutError"
    except Exception as e:
        status = FunctionCallStatus.FAILED
        error_message = str(e)
        error_type = type(e).__name__
        logger.exception(f"Error executing function {meta.name}")

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

    # Log structured logs if captured
    if capture_logs and logs:
        for log_entry in logs:
            log_level = log_entry.get("level", "INFO").upper()
            log_message = log_entry.get("message", "")
            if log_level == "ERROR" or log_level == "CRITICAL":
                logger.error(f"[{meta.name}] {log_message}", extra=log_entry)
            elif log_level == "WARNING":
                logger.warning(f"[{meta.name}] {log_message}", extra=log_entry)
            elif log_level == "DEBUG":
                logger.debug(f"[{meta.name}] {log_message}", extra=log_entry)
            else:
                logger.info(f"[{meta.name}] {log_message}", extra=log_entry)

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
