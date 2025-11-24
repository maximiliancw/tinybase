"""
SQLModel database models for TinyBase.

Defines all core entities:
- User: Application users with authentication
- AuthToken: Opaque bearer tokens for API authentication
- Collection: Dynamic data collections with JSON schemas
- Record: Individual records within collections
- FunctionCall: Execution metadata for function invocations
- FunctionSchedule: Scheduled function execution configuration
"""

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


# =============================================================================
# User & Authentication Models
# =============================================================================


class User(SQLModel, table=True):
    """
    Application user model.
    
    Users can authenticate via email/password and receive bearer tokens.
    Admin users have elevated privileges for managing collections,
    functions, and schedules.
    """
    
    __tablename__ = "user"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(index=True, unique=True, max_length=255)
    password_hash: str = Field(max_length=255)
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class AuthToken(SQLModel, table=True):
    """
    Opaque authentication token model.
    
    Tokens are issued upon successful login and used as Bearer tokens
    for API authentication. Tokens can optionally expire.
    """
    
    __tablename__ = "auth_token"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    token: str = Field(index=True, unique=True, max_length=255)
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime | None = Field(default=None)
    
    def is_expired(self) -> bool:
        """Check if this token has expired."""
        if self.expires_at is None:
            return False
        now = utcnow()
        # Handle both timezone-aware and timezone-naive datetimes from DB
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return now > expires


# =============================================================================
# Collection & Record Models
# =============================================================================


class Collection(SQLModel, table=True):
    """
    Dynamic data collection model.
    
    Collections define a schema for their records using a JSON format.
    The schema is used to generate Pydantic models at runtime for
    validation and OpenAPI documentation.
    """
    
    __tablename__ = "collection"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, unique=True, max_length=100)
    label: str = Field(max_length=200)
    
    # JSON schema defining the collection's fields and constraints
    # Structure: {"fields": [{"name": "...", "type": "...", ...}, ...]}
    schema_: dict = Field(default_factory=dict, sa_column=Column("schema", JSON))
    
    # Additional options (access rules, etc.)
    options: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Record(SQLModel, table=True):
    """
    Individual record within a collection.
    
    Records store their data as JSON, validated against the collection's
    schema. Each record can optionally be associated with an owner user.
    """
    
    __tablename__ = "record"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    collection_id: UUID = Field(foreign_key="collection.id", index=True)
    owner_id: UUID | None = Field(default=None, foreign_key="user.id", index=True)
    
    # JSON payload validated against collection schema
    data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


# =============================================================================
# Function Execution Models
# =============================================================================


class FunctionCall(SQLModel, table=True):
    """
    Function execution metadata record.
    
    Each invocation of a registered function creates a FunctionCall record
    to track execution status, timing, and any errors. Note that actual
    payloads and results are NOT stored - only metadata.
    
    Status values: "running", "succeeded", "failed"
    Trigger types: "manual", "schedule"
    """
    
    __tablename__ = "function_call"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # The registered function name that was called
    function_name: str = Field(index=True, max_length=100)
    
    # Execution status: "running", "succeeded", "failed"
    status: str = Field(default="running", max_length=20)
    
    # How the function was triggered: "manual", "schedule"
    trigger_type: str = Field(default="manual", max_length=20)
    trigger_id: UUID | None = Field(default=None)  # Schedule ID if triggered by scheduler
    
    # User who initiated the call (None for scheduled/system calls)
    requested_by_user_id: UUID | None = Field(default=None, foreign_key="user.id")
    
    # Timing information
    started_at: datetime | None = Field(default=None)
    finished_at: datetime | None = Field(default=None)
    duration_ms: int | None = Field(default=None)
    
    # Error information (only populated on failure)
    error_message: str | None = Field(default=None)
    error_type: str | None = Field(default=None, max_length=200)
    
    created_at: datetime = Field(default_factory=utcnow)


class FunctionSchedule(SQLModel, table=True):
    """
    Scheduled function execution configuration.
    
    Defines when and how often a function should be automatically invoked.
    Supports three schedule methods:
    - once: Single execution at a specific date/time
    - interval: Repeated execution at fixed intervals
    - cron: Repeated execution based on cron expression
    """
    
    __tablename__ = "function_schedule"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # Human-readable name for this schedule
    name: str = Field(max_length=200)
    
    # The function to execute
    function_name: str = Field(index=True, max_length=100)
    
    # Schedule configuration as JSON
    # Validated via Pydantic schedule models (OnceScheduleConfig, IntervalScheduleConfig, CronScheduleConfig)
    schedule: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    # Whether this schedule is currently active
    is_active: bool = Field(default=True)
    
    # Execution tracking
    last_run_at: datetime | None = Field(default=None)
    next_run_at: datetime | None = Field(default=None)
    
    # Audit fields
    created_by_user_id: UUID | None = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

