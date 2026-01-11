"""
Function execution context model.

The Context object is passed to all registered functions and provides
access to execution metadata, the database session, and the HTTP request.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import Request
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session


class Context(BaseModel):
    """
    Execution context for TinyBase functions.

    This object is automatically created and passed to registered functions
    when they are invoked. It provides:

    - Execution metadata (function name, trigger type, request ID)
    - User information (user_id, is_admin)
    - Timing information (current UTC time)
    - Database access (db session)
    - HTTP request access (when triggered via HTTP)

    Attributes:
        function_name: Name of the function being executed
        trigger_type: How the function was triggered ("manual" or "schedule")
        trigger_id: Schedule ID if triggered by scheduler
        request_id: Unique ID for this execution (same as FunctionCall.id)
        user_id: ID of the user who triggered the function (None for scheduled)
        is_admin: Whether the triggering user has admin privileges
        now: Current UTC datetime at execution start
        db: SQLModel database session
        request: FastAPI Request object (None for scheduled functions)

    Example:
        @register(name="my_function", ...)
        def my_function(ctx: Context, payload: MyInput) -> MyOutput:
            # Access the database
            users = ctx.db.exec(select(User)).all()

            # Check who's calling
            if ctx.user_id:
                print(f"Called by user {ctx.user_id}")

            # Check trigger type
            if ctx.trigger_type == "schedule":
                print("Running as scheduled task")

            return MyOutput(...)
    """

    # Allow arbitrary types for Session and Request objects
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Execution metadata
    function_name: str
    trigger_type: Literal["manual", "schedule"]
    trigger_id: UUID | None = None
    request_id: UUID

    # User information
    user_id: UUID | None = None
    is_admin: bool = False

    # Timing
    now: datetime

    # Database session (from SQLModel/SQLAlchemy)
    db: Session

    # HTTP request (available for manual triggers)
    request: Request | None = None
