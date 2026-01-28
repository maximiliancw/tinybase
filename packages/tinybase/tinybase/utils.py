"""
Shared utilities for TinyBase.

Provides common functions and enums used across the codebase.
"""

import hashlib
import re
from datetime import datetime, timezone
from enum import Enum


def utcnow() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def generate_operation_id(route) -> str:
    """
    Generate a concise, stable operationId for OpenAPI client generation.

    Format: {tag}_{endpoint_name}
    - tag: router's primary tag (lowercased, sanitized)
    - endpoint_name: Python function name (lowercased, sanitized)

    Collision handling:
    - If collision: append _{method}
    - If still collision: append _{path_hash4} (4-char hash of path)

    This ensures short, predictable operation IDs for generated clients.

    Args:
        route: FastAPI APIRoute instance

    Returns:
        A unique, concise operation ID string
    """
    # Get tag from route (default to 'default' if no tags)
    tag = route.tags[0] if route.tags else "default"
    tag = re.sub(r"[^a-z0-9_]+", "_", tag.lower()).strip("_")

    # Get endpoint name from route name
    endpoint_name = route.name or "unknown"
    endpoint_name = re.sub(r"[^a-z0-9_]+", "_", endpoint_name.lower()).strip("_")

    # Build base operation ID
    operation_id = f"{tag}_{endpoint_name}"

    # Check for collisions using a set stored in the function state
    # We'll populate this during OpenAPI generation
    if not hasattr(generate_operation_id, "_seen_ids"):
        generate_operation_id._seen_ids = set()  # type: ignore

    seen_ids = generate_operation_id._seen_ids  # type: ignore

    # Only handle actual collisions - don't add method unnecessarily
    original_id = operation_id
    collision_count = 0

    while operation_id in seen_ids:
        collision_count += 1
        if collision_count == 1:
            # First collision: append method
            method = list(route.methods)[0].lower() if route.methods else "get"
            operation_id = f"{original_id}_{method}"
        else:
            # Subsequent collision: append path hash
            path_hash = hashlib.md5(route.path.encode()).hexdigest()[:4]
            method = list(route.methods)[0].lower() if route.methods else "get"
            operation_id = f"{original_id}_{method}_{path_hash}"
            break

    # Track this ID
    seen_ids.add(operation_id)

    return operation_id


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
