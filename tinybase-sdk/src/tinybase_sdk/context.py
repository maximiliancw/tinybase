"""Execution context for TinyBase functions."""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class FunctionContext:
    """Execution context passed to functions."""

    api_base_url: str
    auth_token: str
    user_id: UUID | None
    is_admin: bool
    request_id: UUID
    function_name: str
