"""
Schedule management API routes.

Provides admin-only endpoints for managing function schedules.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlmodel import select

from tinybase.auth import CurrentAdminUser, DbSession
from tinybase.db.models import FunctionSchedule, utcnow
from tinybase.functions.core import get_global_registry
from tinybase.schedule import parse_schedule_config

router = APIRouter(prefix="/admin/schedules", tags=["Schedules"])


# =============================================================================
# Request/Response Schemas
# =============================================================================


class ScheduleCreate(BaseModel):
    """Create schedule request."""

    name: str = Field(min_length=1, max_length=200, description="Schedule name")
    function_name: str = Field(description="Function to execute")
    schedule: dict[str, Any] = Field(description="Schedule configuration")
    input_data: dict[str, Any] = Field(
        default_factory=dict, description="Input data for the function"
    )
    is_active: bool = Field(default=True, description="Whether schedule is active")


class ScheduleUpdate(BaseModel):
    """Update schedule request."""

    name: str | None = Field(default=None, description="New name")
    schedule: dict[str, Any] | None = Field(default=None, description="New schedule config")
    input_data: dict[str, Any] | None = Field(default=None, description="New input data")
    is_active: bool | None = Field(default=None, description="New active status")


class ScheduleResponse(BaseModel):
    """Schedule information response."""

    id: str = Field(description="Schedule ID")
    name: str = Field(description="Schedule name")
    function_name: str = Field(description="Function name")
    schedule: dict[str, Any] = Field(description="Schedule configuration")
    input_data: dict[str, Any] = Field(
        default_factory=dict, description="Input data for the function"
    )
    is_active: bool = Field(description="Whether schedule is active")
    last_run_at: str | None = Field(default=None, description="Last execution time")
    next_run_at: str | None = Field(default=None, description="Next scheduled run")
    created_by_user_id: str | None = Field(default=None, description="Creator user ID")
    created_at: str = Field(description="Created timestamp")
    updated_at: str = Field(description="Updated timestamp")


class ScheduleListResponse(BaseModel):
    """Paginated schedule list response."""

    schedules: list[ScheduleResponse] = Field(description="Schedules")
    total: int = Field(description="Total count")
    limit: int = Field(description="Page size")
    offset: int = Field(description="Page offset")


# =============================================================================
# Helper Functions
# =============================================================================


def schedule_to_response(schedule: FunctionSchedule) -> ScheduleResponse:
    """Convert a FunctionSchedule model to response schema."""
    return ScheduleResponse(
        id=str(schedule.id),
        name=schedule.name,
        function_name=schedule.function_name,
        schedule=schedule.schedule,
        input_data=schedule.input_data,
        is_active=schedule.is_active,
        last_run_at=schedule.last_run_at.isoformat() if schedule.last_run_at else None,
        next_run_at=schedule.next_run_at.isoformat() if schedule.next_run_at else None,
        created_by_user_id=str(schedule.created_by_user_id)
        if schedule.created_by_user_id
        else None,
        created_at=schedule.created_at.isoformat(),
        updated_at=schedule.updated_at.isoformat(),
    )


# =============================================================================
# Routes
# =============================================================================


@router.get(
    "",
    response_model=ScheduleListResponse,
    summary="List schedules",
    description="Get a paginated list of function schedules.",
)
def list_schedules(
    session: DbSession,
    _admin: CurrentAdminUser,
    function_name: str | None = Query(default=None, description="Filter by function name"),
    is_active: bool | None = Query(default=None, description="Filter by active status"),
    limit: int = Query(default=100, ge=1, le=1000, description="Page size"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
) -> ScheduleListResponse:
    """List all schedules with optional filtering."""
    # Build query
    query = select(FunctionSchedule)

    if function_name:
        query = query.where(FunctionSchedule.function_name == function_name)
    if is_active is not None:
        query = query.where(FunctionSchedule.is_active == is_active)

    # Get total count
    all_results = list(session.exec(query).all())
    total = len(all_results)

    # Apply pagination
    query = query.offset(offset).limit(limit)
    schedules = list(session.exec(query).all())

    return ScheduleListResponse(
        schedules=[schedule_to_response(s) for s in schedules],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create schedule",
    description="Create a new function schedule.",
)
def create_schedule(
    request: ScheduleCreate,
    session: DbSession,
    admin: CurrentAdminUser,
) -> ScheduleResponse:
    """Create a new schedule."""
    # Verify function exists
    registry = get_global_registry()
    if registry.get(request.function_name) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Function '{request.function_name}' not found",
        )

    # Validate schedule configuration
    try:
        config = parse_schedule_config(request.schedule)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid schedule configuration: {e}",
        )

    # Calculate initial next_run_at
    now = utcnow()
    next_run_at = config.next_run_after(now) if request.is_active else None

    # Create schedule
    schedule = FunctionSchedule(
        name=request.name,
        function_name=request.function_name,
        schedule=request.schedule,
        input_data=request.input_data,
        is_active=request.is_active,
        next_run_at=next_run_at,
        created_by_user_id=admin.id,
    )
    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    return schedule_to_response(schedule)


@router.get(
    "/{schedule_id}",
    response_model=ScheduleResponse,
    summary="Get schedule",
    description="Get details of a specific schedule.",
)
def get_schedule(
    schedule_id: UUID,
    session: DbSession,
    _admin: CurrentAdminUser,
) -> ScheduleResponse:
    """Get a specific schedule by ID."""
    schedule = session.get(FunctionSchedule, schedule_id)

    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule '{schedule_id}' not found",
        )

    return schedule_to_response(schedule)


@router.patch(
    "/{schedule_id}",
    response_model=ScheduleResponse,
    summary="Update schedule",
    description="Update a schedule's configuration.",
)
def update_schedule(
    schedule_id: UUID,
    request: ScheduleUpdate,
    session: DbSession,
    _admin: CurrentAdminUser,
) -> ScheduleResponse:
    """Update a schedule."""
    schedule = session.get(FunctionSchedule, schedule_id)

    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule '{schedule_id}' not found",
        )

    if request.name is not None:
        schedule.name = request.name

    if request.input_data is not None:
        schedule.input_data = request.input_data

    if request.schedule is not None:
        # Validate new schedule configuration
        try:
            config = parse_schedule_config(request.schedule)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid schedule configuration: {e}",
            )

        schedule.schedule = request.schedule

        # Recalculate next_run_at
        now = utcnow()
        schedule.next_run_at = config.next_run_after(now) if schedule.is_active else None

    if request.is_active is not None:
        schedule.is_active = request.is_active

        # Update next_run_at based on active status
        if request.is_active and schedule.next_run_at is None:
            config = parse_schedule_config(schedule.schedule)
            now = utcnow()
            schedule.next_run_at = config.next_run_after(now)
        elif not request.is_active:
            schedule.next_run_at = None

    schedule.updated_at = utcnow()
    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    return schedule_to_response(schedule)


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete schedule",
    description="Delete a schedule.",
)
def delete_schedule(
    schedule_id: UUID,
    session: DbSession,
    _admin: CurrentAdminUser,
) -> None:
    """Delete a schedule."""
    schedule = session.get(FunctionSchedule, schedule_id)

    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule '{schedule_id}' not found",
        )

    session.delete(schedule)
    session.commit()
