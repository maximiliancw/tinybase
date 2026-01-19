"""
SQLModel database models for TinyBase.

Defines all core entities:
- User: Application users with authentication
- AuthToken: Opaque bearer tokens for API authentication
- Collection: Dynamic data collections with JSON schemas
- Record: Individual records within collections
- FunctionCall: Execution metadata for function invocations
- FunctionSchedule: Scheduled function execution configuration
- InstanceSettings: Singleton for instance-wide configuration
- Extension: Installed extensions/plugins
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from tinybase.utils import FunctionCallStatus, TriggerType, utcnow

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
    user_id: UUID | None = Field(default=None, foreign_key="user.id", index=True)
    token: str = Field(index=True, unique=True, max_length=255)
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime | None = Field(default=None)
    # Token scope (None = full access, "internal" = limited to function context)
    scope: str | None = Field(default=None, max_length=50)

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


class PasswordResetToken(SQLModel, table=True):
    """
    Password reset token model.

    Tokens are generated when users request password resets and are used
    to securely reset passwords. Tokens expire after 1 hour and can only
    be used once.
    """

    __tablename__ = "password_reset_token"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    token: str = Field(index=True, unique=True, max_length=255)
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime = Field(default_factory=lambda: utcnow() + timedelta(hours=1))
    used_at: datetime | None = Field(default=None)

    def is_expired(self) -> bool:
        """Check if this token has expired."""
        now = utcnow()
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return now > expires

    def is_used(self) -> bool:
        """Check if this token has already been used."""
        return self.used_at is not None

    def is_valid(self) -> bool:
        """Check if this token is valid (not expired and not used)."""
        return not self.is_expired() and not self.is_used()


class ApplicationToken(SQLModel, table=True):
    """
    Application token model for system-to-system authentication.

    Application tokens are used for authenticating orchestration systems,
    monitoring tools, and other automated services that need to access
    instance metadata, metrics, and health endpoints. Unlike user auth tokens,
    these tokens are not tied to a specific user and are designed for
    long-lived system access.
    """

    __tablename__ = "application_token"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=200, description="Human-readable name for this token")
    token: str = Field(index=True, unique=True, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=utcnow)
    last_used_at: datetime | None = Field(default=None)
    expires_at: datetime | None = Field(default=None)
    is_active: bool = Field(default=True)

    def is_expired(self) -> bool:
        """Check if this token has expired."""
        if self.expires_at is None:
            return False
        now = utcnow()
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return now > expires

    def is_valid(self) -> bool:
        """Check if this token is valid (active and not expired)."""
        return self.is_active and not self.is_expired()


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
    """

    __tablename__ = "function_call"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # The registered function name that was called
    function_name: str = Field(index=True, max_length=100)

    # Execution status
    status: FunctionCallStatus = Field(default=FunctionCallStatus.RUNNING)

    # How the function was triggered
    trigger_type: TriggerType = Field(default=TriggerType.MANUAL)
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

    # Input data to pass to the function when executed
    input_data: dict = Field(default_factory=dict, sa_column=Column(JSON))

    # Whether this schedule is currently active
    is_active: bool = Field(default=True)

    # Execution tracking
    last_run_at: datetime | None = Field(default=None)
    next_run_at: datetime | None = Field(default=None)

    # Audit fields
    created_by_user_id: UUID | None = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


# =============================================================================
# Instance Settings Model (Singleton)
# =============================================================================


class InstanceSettings(SQLModel, table=True):
    """
    Singleton model for instance-wide configuration.

    There should only ever be one row in this table (id=1).
    Settings here can be modified at runtime via the admin UI.
    """

    __tablename__ = "instance_settings"

    id: int = Field(default=1, primary_key=True)  # Always 1 (singleton)

    # General settings
    instance_name: str = Field(default="TinyBase", max_length=100)

    # Auth settings
    allow_public_registration: bool = Field(default=True)

    # Auth Portal settings
    auth_portal_enabled: bool = Field(default=False)
    auth_portal_logo_url: str | None = Field(default=None, max_length=500)
    auth_portal_primary_color: str | None = Field(default=None, max_length=50)
    auth_portal_background_image_url: str | None = Field(default=None, max_length=500)
    auth_portal_login_redirect_url: str | None = Field(
        default=None, max_length=500, description="Default redirect URL after login"
    )
    auth_portal_register_redirect_url: str | None = Field(
        default=None, max_length=500, description="Default redirect URL after registration"
    )

    # Server timezone (used for schedule defaults)
    # If empty, schedules use UTC by default
    server_timezone: str = Field(default="UTC", max_length=50)

    # Scheduler settings
    # How often to run token cleanup (every N scheduler intervals)
    # Default: 60 intervals (e.g., 60 * 5s = 5 minutes if scheduler_interval_seconds=5)
    token_cleanup_interval: int = Field(
        default=60, ge=1, description="Token cleanup interval in scheduler ticks"
    )
    # How often to collect metrics (every N scheduler intervals)
    # Default: 360 intervals (e.g., 360 * 5s = 30 minutes if scheduler_interval_seconds=5)
    metrics_collection_interval: int = Field(
        default=360, ge=1, description="Metrics collection interval in scheduler ticks"
    )
    # Maximum execution time for scheduled functions (in seconds)
    scheduler_function_timeout_seconds: int | None = Field(
        default=None, ge=1, description="Function execution timeout in seconds"
    )
    # Maximum number of schedules to process per tick
    scheduler_max_schedules_per_tick: int | None = Field(
        default=None, ge=1, description="Max schedules per tick"
    )
    # Maximum concurrent schedule executions
    scheduler_max_concurrent_executions: int | None = Field(
        default=None, ge=1, description="Max concurrent executions"
    )

    # File storage settings (S3-compatible)
    storage_enabled: bool = Field(default=False)
    storage_endpoint: str | None = Field(default=None, max_length=500)
    storage_bucket: str | None = Field(default=None, max_length=100)
    storage_access_key: str | None = Field(default=None, max_length=200)
    storage_secret_key: str | None = Field(default=None, max_length=200)
    storage_region: str | None = Field(default=None, max_length=50)

    updated_at: datetime = Field(default_factory=utcnow)


# =============================================================================
# Metrics Model
# =============================================================================


class Metrics(SQLModel, table=True):
    """
    Metrics snapshot model.

    Stores periodic snapshots of system metrics collected by the scheduler.
    Metrics include collection sizes and function execution statistics.
    """

    __tablename__ = "metrics"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Metric type: "collection_sizes" or "function_stats"
    metric_type: str = Field(index=True, max_length=50)

    # Metric data as JSON
    # For collection_sizes: {"collection_name": count, ...}
    # For function_stats: {"function_name": {"avg_runtime_ms": ..., "error_rate": ..., "total_calls": ...}, ...}
    data: dict = Field(default_factory=dict, sa_column=Column(JSON))

    # When this metric snapshot was collected
    collected_at: datetime = Field(default_factory=utcnow, index=True)

    created_at: datetime = Field(default_factory=utcnow)


# =============================================================================
# Extension Model
# =============================================================================


class Extension(SQLModel, table=True):
    """
    Installed extension/plugin model.

    Tracks extensions installed from GitHub repositories. Extensions can
    register functions, add lifecycle hooks, and integrate third-party services.
    """

    __tablename__ = "extension"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Extension metadata from extension.toml
    name: str = Field(index=True, unique=True, max_length=100)
    version: str = Field(max_length=50)
    description: str | None = Field(default=None, max_length=500)
    author: str | None = Field(default=None, max_length=200)

    # Installation source
    repo_url: str = Field(max_length=500)

    # Local installation path (relative to extensions directory)
    install_path: str = Field(max_length=500)

    # Entry point module (from extension.toml)
    entry_point: str = Field(default="main.py", max_length=200)

    # Whether extension is currently enabled
    is_enabled: bool = Field(default=True)

    # Audit fields
    installed_at: datetime = Field(default_factory=utcnow)
    installed_by_user_id: UUID | None = Field(default=None, foreign_key="user.id")
    updated_at: datetime = Field(default_factory=utcnow)
