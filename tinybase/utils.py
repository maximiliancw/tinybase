"""
Shared utilities for TinyBase.

Provides common functions and enums used across the codebase.
"""

from datetime import datetime, timezone
from enum import Enum


def utcnow() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


class FunctionCallStatus(str, Enum):
    """Status of a function call execution."""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class TriggerType(str, Enum):
    """How a function was triggered."""

    MANUAL = "manual"
    SCHEDULE = "schedule"


class AuthLevel(str, Enum):
    """Authentication level required for a resource."""

    PUBLIC = "public"
    AUTH = "auth"
    ADMIN = "admin"


class AccessRule(str, Enum):
    """Access control rules for collections."""

    PUBLIC = "public"  # Anyone can access
    AUTH = "auth"  # Any authenticated user
    OWNER = "owner"  # Only the record owner
    ADMIN = "admin"  # Only admins


class ScheduleMethod(str, Enum):
    """Schedule timing method."""

    ONCE = "once"
    INTERVAL = "interval"
    CRON = "cron"


class IntervalUnit(str, Enum):
    """Time unit for interval schedules."""

    SECONDS = "seconds"
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
