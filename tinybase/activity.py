"""
Activity logging utilities.

Provides helpers for logging user actions and system events to the ActivityLog table.
Activity logging is designed to be non-blocking and fire-and-forget.
"""

import logging
from uuid import UUID

from sqlmodel import Session

from tinybase.db.core import get_db_engine
from tinybase.db.models import ActivityLog

logger = logging.getLogger(__name__)


# Common action types
class Actions:
    """Standard action types for activity logging."""

    # User authentication
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_REGISTER = "user.register"
    USER_PASSWORD_RESET_REQUEST = "user.password_reset.request"
    USER_PASSWORD_RESET_CONFIRM = "user.password_reset.confirm"

    # User management (admin)
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"

    # Record operations
    RECORD_CREATE = "record.create"
    RECORD_UPDATE = "record.update"
    RECORD_DELETE = "record.delete"

    # Collection management
    COLLECTION_CREATE = "collection.create"
    COLLECTION_UPDATE = "collection.update"
    COLLECTION_DELETE = "collection.delete"

    # Settings
    SETTINGS_UPDATE = "settings.update"

    # Extensions
    EXTENSION_INSTALL = "extension.install"
    EXTENSION_UNINSTALL = "extension.uninstall"
    EXTENSION_ENABLE = "extension.enable"
    EXTENSION_DISABLE = "extension.disable"


def log_activity(
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    user_id: UUID | None = None,
    meta_data: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """
    Log an activity to the database.

    This function is designed to be called synchronously but is non-blocking.
    It uses a new database session to avoid interfering with the caller's transaction.

    Args:
        action: The action being performed (e.g., "user.login", "record.create")
        resource_type: Type of resource being acted upon (e.g., "user", "record")
        resource_id: Identifier of the resource (e.g., user ID, record ID)
        user_id: User who performed the action (None for system actions)
        meta_data: Additional context as a dictionary
        ip_address: Client IP address

    Example:
        log_activity(
            action=Actions.USER_LOGIN,
            resource_type="user",
            resource_id=str(user.id),
            user_id=user.id,
            ip_address=request.client.host,
        )
    """
    try:
        engine = get_db_engine()
        with Session(engine) as session:
            activity = ActivityLog(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                user_id=user_id,
                meta_data=meta_data or {},
                ip_address=ip_address,
            )
            session.add(activity)
            session.commit()
    except Exception as e:
        # Log but don't raise - activity logging should never break the main flow
        logger.warning(f"Failed to log activity: {e}")


def log_activity_background(
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    user_id: UUID | None = None,
    meta_data: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """
    Log an activity to the database (alias for log_activity).

    This is the same as log_activity but named explicitly for use in
    background tasks. The function is already non-blocking.
    """
    log_activity(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        meta_data=meta_data,
        ip_address=ip_address,
    )


def log_extension_activity(
    extension_name: str,
    action_name: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    user_id: UUID | None = None,
    meta_data: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """
    Log an activity from an extension with a standardized action format.

    This wrapper ensures extension activities follow the naming convention:
    `ext.<extension_name>.<action_name>`

    Args:
        extension_name: Name of the extension (e.g., "my_extension")
        action_name: Name of the action (e.g., "sync_completed")
        resource_type: Type of resource being acted upon
        resource_id: Identifier of the resource
        user_id: User who performed the action
        meta_data: Additional context as a dictionary
        ip_address: Client IP address

    Example:
        log_extension_activity(
            extension_name="stripe_sync",
            action_name="payment_received",
            resource_type="payment",
            resource_id="pay_123",
            meta_data={"amount": 99.99},
        )
        # Logs as action: "ext.stripe_sync.payment_received"
    """
    action = f"ext.{extension_name}.{action_name}"
    log_activity(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        meta_data=meta_data,
        ip_address=ip_address,
    )
