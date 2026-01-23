"""
Functions API routes.

Provides endpoints for:
- Function invocation (POST /api/functions/{name})
- Function listing (GET /api/functions)
"""

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from tinybase.auth import CurrentAdminUser, CurrentUserOptional, DBSession
from tinybase.functions.core import execute_function, get_global_registry
from tinybase.rate_limit import check_rate_limit
from tinybase.utils import AuthLevel, FunctionCallStatus, TriggerType

router = APIRouter(prefix="/functions", tags=["functions"])


# =============================================================================
# Response Schemas
# =============================================================================


class FunctionInfo(BaseModel):
    """Public function information."""

    name: str = Field(description="Function name")
    description: str | None = Field(default=None, description="Function description")
    auth: AuthLevel = Field(description="Auth requirement")
    tags: list[str] = Field(default_factory=list, description="Function tags")


class FunctionCallResponse(BaseModel):
    """Function call response."""

    call_id: str = Field(description="Unique call ID")
    status: FunctionCallStatus = Field(description="Execution status")
    result: Any = Field(default=None, description="Function result (if succeeded)")
    error_message: str | None = Field(default=None, description="Error message (if failed)")
    error_type: str | None = Field(default=None, description="Error type (if failed)")
    duration_ms: int | None = Field(default=None, description="Execution duration in ms")


# =============================================================================
# Routes
# =============================================================================


@router.get(
    "",
    response_model=list[FunctionInfo],
    summary="List available functions",
    description="Get a list of all registered functions that the current user can access.",
)
def list_functions(user: CurrentUserOptional) -> list[FunctionInfo]:
    """
    List all available functions.

    Returns functions filtered by the user's access level:
    - Anonymous users: only "public" functions
    - Authenticated users: "public" and "auth" functions
    - Admin users: all functions
    """
    registry = get_global_registry()
    functions = registry.all()

    result = []
    for meta in functions.values():
        # Filter based on auth level
        if meta.auth == AuthLevel.PUBLIC:
            # Everyone can see public functions
            pass
        elif meta.auth == AuthLevel.AUTH:
            # Only authenticated users can see auth functions
            if user is None:
                continue
        elif meta.auth == AuthLevel.ADMIN:
            # Only admins can see admin functions
            if user is None or not user.is_admin:
                continue

        result.append(
            FunctionInfo(
                name=meta.name,
                description=meta.description,
                auth=meta.auth,
                tags=meta.tags,
            )
        )

    return result


@router.post(
    "/{function_name}",
    response_model=FunctionCallResponse,
    summary="Call a function",
    description="Invoke a registered function with the provided payload.",
)
async def call_function(
    function_name: str,
    request: Request,
    session: DBSession,
    user: CurrentUserOptional,
    payload: dict[str, Any] | None = None,
    _rate_limit: None = Depends(check_rate_limit),
) -> FunctionCallResponse:
    """
    Call a registered function with rate limiting.

    The function is invoked with the provided payload, validated against
    the function's input model. A FunctionCall record is created to track
    the execution.

    Rate limiting is enforced per user to prevent excessive concurrent executions.
    """
    registry = get_global_registry()
    meta = registry.get(function_name)

    if meta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Function '{function_name}' not found",
        )

    # Check authentication
    if meta.auth == AuthLevel.AUTH and user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if meta.auth == AuthLevel.ADMIN:
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )

    # Input validation will be done in the subprocess by the SDK
    # We just pass the payload through here

    # Validate payload size
    from tinybase.config import settings

    config = settings()
    payload_json = json.dumps(payload or {})
    payload_size = len(payload_json.encode("utf-8"))

    if payload_size > config.max_function_payload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Payload exceeds maximum size of {config.max_function_payload_bytes} bytes",
        )

    # Execute the function
    result = execute_function(
        meta=meta,
        payload=payload or {},
        session=session,
        user_id=user.id if user else None,
        is_admin=user.is_admin if user else False,
        trigger_type=TriggerType.MANUAL,
        request=request,
    )

    # Handle failed execution
    if result.status == "failed":
        # Return error response but with 200 status
        # The actual error is in the response body
        pass

    return FunctionCallResponse(
        call_id=result.call_id,
        status=result.status,
        result=result.result,
        error_message=result.error_message,
        error_type=result.error_type,
        duration_ms=result.duration_ms,
    )


# =============================================================================
# Admin Function Info Route
# =============================================================================


class AdminFunctionInfo(FunctionInfo):
    """Extended function information for admins."""

    module: str = Field(description="Python module name")
    file_path: str = Field(description="Source file path")
    last_loaded_at: str = Field(description="When function was last loaded")
    has_input_model: bool = Field(description="Whether function has input validation")
    has_output_model: bool = Field(description="Whether function has output schema")
    is_async: bool = Field(default=False, description="Whether function is async")


class FunctionSchemaResponse(BaseModel):
    """Function schema information."""

    name: str = Field(description="Function name")
    has_input_model: bool = Field(description="Whether function has input validation")
    has_output_model: bool = Field(description="Whether function has output schema")
    input_schema: dict[str, Any] | None = Field(default=None, description="JSON Schema for input")
    output_schema: dict[str, Any] | None = Field(default=None, description="JSON Schema for output")


@router.get(
    "/{function_name}/schema",
    response_model=FunctionSchemaResponse,
    summary="Get function schema",
    description="Get the input/output JSON schema for a function.",
)
def get_function_schema(
    function_name: str,
    user: CurrentUserOptional,
) -> FunctionSchemaResponse:
    """
    Get the JSON schema for a function's input and output models.

    Returns the Pydantic model JSON schemas, which can be used to
    generate form UIs or validate input before calling.
    """
    registry = get_global_registry()
    meta = registry.get(function_name)

    if meta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Function '{function_name}' not found",
        )

    # Check authentication
    if meta.auth == AuthLevel.AUTH and user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if meta.auth == AuthLevel.ADMIN:
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )

    return FunctionSchemaResponse(
        name=meta.name,
        has_input_model=meta.input_schema is not None,
        has_output_model=meta.output_schema is not None,
        input_schema=meta.input_schema,
        output_schema=meta.output_schema,
    )


@router.get(
    "/admin/list",
    response_model=list[AdminFunctionInfo],
    summary="List functions (admin)",
    description="Get detailed information about all registered functions. Admin only.",
)
def list_functions_admin(_admin: CurrentAdminUser) -> list[AdminFunctionInfo]:
    """
    List all functions with detailed information (admin only).

    Returns extended metadata including module, file path, and timestamps.
    """
    registry = get_global_registry()
    functions = registry.all()

    return [
        AdminFunctionInfo(
            name=meta.name,
            description=meta.description,
            auth=meta.auth,
            tags=meta.tags,
            module="",  # No longer tracked
            file_path=meta.file_path,
            last_loaded_at=meta.last_loaded_at.isoformat() if meta.last_loaded_at else "",
            has_input_model=meta.input_schema is not None,
            has_output_model=meta.output_schema is not None,
            is_async=False,  # Functions run in subprocess, async not applicable
        )
        for meta in functions.values()
    ]
