"""
Collection and Record API routes.

Provides endpoints for:
- Collection CRUD (admin-only for create/update/delete)
- Record CRUD with schema validation
"""

import asyncio
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from pydantic import BaseModel, Field, ValidationError

from tinybase.auth import CurrentAdminUser, CurrentUser, CurrentUserOptional, DbSession
from tinybase.collections.service import CollectionService, check_access
from tinybase.extensions.hooks import (
    RecordCreateEvent,
    RecordDeleteEvent,
    RecordUpdateEvent,
    run_record_create_hooks,
    run_record_delete_hooks,
    run_record_update_hooks,
)

router = APIRouter(prefix="/collections", tags=["collections"])


# =============================================================================
# Request/Response Schemas
# =============================================================================


class CollectionCreate(BaseModel):
    """Request to create a new collection."""

    name: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Collection name (lowercase, underscores allowed)",
    )
    label: str = Field(min_length=1, max_length=200, description="Human-readable label")
    schema_: dict[str, Any] = Field(
        alias="schema", description="Collection schema with fields definition"
    )
    options: dict[str, Any] | None = Field(
        default=None, description="Additional options (access rules, etc.)"
    )


class CollectionUpdate(BaseModel):
    """Request to update a collection."""

    label: str | None = Field(default=None, description="New label")
    schema_: dict[str, Any] | None = Field(default=None, alias="schema", description="New schema")
    options: dict[str, Any] | None = Field(default=None, description="New options")


class CollectionResponse(BaseModel):
    """Collection information response."""

    id: str = Field(description="Collection ID")
    name: str = Field(description="Collection name")
    label: str = Field(description="Human-readable label")
    schema_: dict[str, Any] = Field(alias="schema", description="Collection schema")
    options: dict[str, Any] = Field(description="Collection options")
    created_at: str = Field(description="Creation timestamp")
    updated_at: str = Field(description="Last update timestamp")

    model_config = {"populate_by_name": True}


class RecordCreate(BaseModel):
    """Request to create a new record."""

    data: dict[str, Any] = Field(description="Record data")


class RecordUpdate(BaseModel):
    """Request to update a record."""

    data: dict[str, Any] = Field(description="Record data (partial update)")


class RecordResponse(BaseModel):
    """Record response."""

    id: str = Field(description="Record ID")
    collection_id: str = Field(description="Collection ID")
    owner_id: str | None = Field(description="Owner user ID")
    data: dict[str, Any] = Field(description="Record data")
    created_at: str = Field(description="Creation timestamp")
    updated_at: str = Field(description="Last update timestamp")


class RecordListResponse(BaseModel):
    """Paginated record list response."""

    records: list[RecordResponse] = Field(description="List of records")
    total: int = Field(description="Total number of records")
    limit: int = Field(description="Page size")
    offset: int = Field(description="Page offset")


# =============================================================================
# Helper Functions
# =============================================================================


def collection_to_response(collection: Any) -> CollectionResponse:
    """Convert a Collection model to response schema."""
    return CollectionResponse(
        id=str(collection.id),
        name=collection.name,
        label=collection.label,
        schema_=collection.schema_,
        options=collection.options,
        created_at=collection.created_at.isoformat(),
        updated_at=collection.updated_at.isoformat(),
    )


def record_to_response(record: Any) -> RecordResponse:
    """Convert a Record model to response schema."""
    return RecordResponse(
        id=str(record.id),
        collection_id=str(record.collection_id),
        owner_id=str(record.owner_id) if record.owner_id else None,
        data=record.data,
        created_at=record.created_at.isoformat(),
        updated_at=record.updated_at.isoformat(),
    )


# =============================================================================
# Collection Routes
# =============================================================================


@router.get(
    "",
    response_model=list[CollectionResponse],
    summary="List all collections",
    description="Get a list of all collections. Available to all authenticated users.",
)
def list_collections(
    session: DbSession,
    _user: CurrentUserOptional,
) -> list[CollectionResponse]:
    """List all available collections."""
    service = CollectionService(session)
    collections = service.list_collections()
    return [collection_to_response(c) for c in collections]


@router.post(
    "",
    response_model=CollectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new collection",
    description="Create a new collection with the specified schema. Admin only.",
)
def create_collection(
    request: CollectionCreate,
    session: DbSession,
    _admin: CurrentAdminUser,
) -> CollectionResponse:
    """Create a new collection (admin only)."""
    service = CollectionService(session)

    try:
        collection = service.create_collection(
            name=request.name,
            label=request.label,
            schema=request.schema_,
            options=request.options,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return collection_to_response(collection)


@router.get(
    "/{collection_name}",
    response_model=CollectionResponse,
    summary="Get collection details",
    description="Get details of a specific collection by name.",
)
def get_collection(
    collection_name: str,
    session: DbSession,
    _user: CurrentUserOptional,
) -> CollectionResponse:
    """Get collection details by name."""
    service = CollectionService(session)
    collection = service.get_collection_by_name(collection_name)

    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{collection_name}' not found",
        )

    return collection_to_response(collection)


@router.patch(
    "/{collection_name}",
    response_model=CollectionResponse,
    summary="Update a collection",
    description="Update a collection's label, schema, or options. Admin only.",
)
def update_collection(
    collection_name: str,
    request: CollectionUpdate,
    session: DbSession,
    _admin: CurrentAdminUser,
) -> CollectionResponse:
    """Update a collection (admin only)."""
    service = CollectionService(session)
    collection = service.get_collection_by_name(collection_name)

    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{collection_name}' not found",
        )

    try:
        updated = service.update_collection(
            collection=collection,
            label=request.label,
            schema=request.schema_,
            options=request.options,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return collection_to_response(updated)


@router.delete(
    "/{collection_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a collection",
    description="Delete a collection and all its records. Admin only.",
)
def delete_collection(
    collection_name: str,
    session: DbSession,
    _admin: CurrentAdminUser,
) -> None:
    """Delete a collection (admin only)."""
    service = CollectionService(session)
    collection = service.get_collection_by_name(collection_name)

    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{collection_name}' not found",
        )

    service.delete_collection(collection)


# =============================================================================
# Record Routes
# =============================================================================


@router.get(
    "/{collection_name}/records",
    response_model=RecordListResponse,
    summary="List records in a collection",
    description="Get a paginated list of records in a collection.",
)
def list_records(
    collection_name: str,
    session: DbSession,
    _user: CurrentUserOptional,
    limit: int = Query(default=100, ge=1, le=1000, description="Page size"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
    sort_by: str | None = Query(default=None, description="Sort by field (created_at, updated_at)"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$", description="Sort order"),
) -> RecordListResponse:
    """List records in a collection with pagination."""
    service = CollectionService(session)
    collection = service.get_collection_by_name(collection_name)

    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{collection_name}' not found",
        )

    # Check access
    if not check_access(
        collection,
        "list",
        user_id=_user.id if _user else None,
        is_admin=_user.is_admin if _user else False,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    records, total = service.list_records(
        collection=collection,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return RecordListResponse(
        records=[record_to_response(r) for r in records],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/{collection_name}/records",
    response_model=RecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new record",
    description="Create a new record in a collection. Data is validated against the collection schema.",
)
def create_record(
    collection_name: str,
    request: RecordCreate,
    session: DbSession,
    user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> RecordResponse:
    """Create a new record in a collection."""
    service = CollectionService(session)
    collection = service.get_collection_by_name(collection_name)

    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{collection_name}' not found",
        )

    # Check access
    if not check_access(
        collection,
        "create",
        user_id=user.id,
        is_admin=user.is_admin,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    try:
        record = service.create_record(
            collection=collection,
            data=request.data,
            owner_id=user.id,
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {e}",
        )

    # Run record create hooks in background
    event = RecordCreateEvent(
        collection=collection_name,
        record_id=record.id,
        data=record.data,
        owner_id=record.owner_id,
    )
    background_tasks.add_task(asyncio.run, run_record_create_hooks(event))

    return record_to_response(record)


@router.get(
    "/{collection_name}/records/{record_id}",
    response_model=RecordResponse,
    summary="Get a record",
    description="Get a specific record by ID.",
)
def get_record(
    collection_name: str,
    record_id: UUID,
    session: DbSession,
    _user: CurrentUserOptional,
) -> RecordResponse:
    """Get a specific record by ID."""
    service = CollectionService(session)
    collection = service.get_collection_by_name(collection_name)

    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{collection_name}' not found",
        )

    record = service.get_record_in_collection(collection, record_id)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record '{record_id}' not found",
        )

    # Check access
    if not check_access(
        collection,
        "read",
        user_id=_user.id if _user else None,
        is_admin=_user.is_admin if _user else False,
        record_owner_id=record.owner_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return record_to_response(record)


@router.patch(
    "/{collection_name}/records/{record_id}",
    response_model=RecordResponse,
    summary="Update a record",
    description="Partially update a record. Data is validated against the collection schema.",
)
def update_record(
    collection_name: str,
    record_id: UUID,
    request: RecordUpdate,
    session: DbSession,
    user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> RecordResponse:
    """Update a record (partial update)."""
    service = CollectionService(session)
    collection = service.get_collection_by_name(collection_name)

    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{collection_name}' not found",
        )

    record = service.get_record_in_collection(collection, record_id)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record '{record_id}' not found",
        )

    # Check access using collection rules
    if not check_access(
        collection,
        "update",
        user_id=user.id,
        is_admin=user.is_admin,
        record_owner_id=record.owner_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this record",
        )

    # Capture old data for the hook
    old_data = dict(record.data)

    try:
        updated = service.update_record(
            collection=collection,
            record=record,
            data=request.data,
            partial=True,
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {e}",
        )

    # Run record update hooks in background
    event = RecordUpdateEvent(
        collection=collection_name,
        record_id=updated.id,
        old_data=old_data,
        new_data=updated.data,
        owner_id=updated.owner_id,
    )
    background_tasks.add_task(asyncio.run, run_record_update_hooks(event))

    return record_to_response(updated)


@router.delete(
    "/{collection_name}/records/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a record",
    description="Delete a specific record.",
)
def delete_record(
    collection_name: str,
    record_id: UUID,
    session: DbSession,
    user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> None:
    """Delete a record."""
    service = CollectionService(session)
    collection = service.get_collection_by_name(collection_name)

    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{collection_name}' not found",
        )

    record = service.get_record_in_collection(collection, record_id)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record '{record_id}' not found",
        )

    # Check access using collection rules
    if not check_access(
        collection,
        "delete",
        user_id=user.id,
        is_admin=user.is_admin,
        record_owner_id=record.owner_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this record",
        )

    # Capture data for the hook before deletion
    record_data = dict(record.data)
    record_owner_id = record.owner_id

    service.delete_record(record)

    # Run record delete hooks in background
    event = RecordDeleteEvent(
        collection=collection_name,
        record_id=record_id,
        data=record_data,
        owner_id=record_owner_id,
    )
    background_tasks.add_task(asyncio.run, run_record_delete_hooks(event))
