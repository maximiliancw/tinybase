"""
Extension lifecycle and event hooks.

Provides decorators and a registry for extension events:

Lifecycle hooks:
- on_startup: Called when TinyBase starts
- on_shutdown: Called when TinyBase shuts down

Authentication hooks:
- on_user_login: Called when a user logs in
- on_user_register: Called when a new user registers

Data hooks:
- on_record_create: Called when a record is created
- on_record_update: Called when a record is updated
- on_record_delete: Called when a record is deleted

Function hooks:
- on_function_call: Called before a function executes
- on_function_complete: Called after a function completes
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable
from uuid import UUID

logger = logging.getLogger(__name__)

# =============================================================================
# Hook Data Classes
# =============================================================================


@dataclass
class UserLoginEvent:
    """Data passed to on_user_login hooks."""
    user_id: UUID
    email: str
    is_admin: bool


@dataclass
class UserRegisterEvent:
    """Data passed to on_user_register hooks."""
    user_id: UUID
    email: str


@dataclass
class RecordCreateEvent:
    """Data passed to on_record_create hooks."""
    collection: str
    record_id: UUID
    data: dict
    owner_id: UUID | None


@dataclass
class RecordUpdateEvent:
    """Data passed to on_record_update hooks."""
    collection: str
    record_id: UUID
    old_data: dict
    new_data: dict
    owner_id: UUID | None


@dataclass
class RecordDeleteEvent:
    """Data passed to on_record_delete hooks."""
    collection: str
    record_id: UUID
    data: dict
    owner_id: UUID | None


@dataclass
class FunctionCallEvent:
    """Data passed to on_function_call hooks (before execution)."""
    function_name: str
    user_id: UUID | None
    payload: dict


@dataclass
class FunctionCompleteEvent:
    """Data passed to on_function_complete hooks (after execution)."""
    function_name: str
    user_id: UUID | None
    status: str  # "succeeded" or "failed"
    duration_ms: int
    error_message: str | None = None
    error_type: str | None = None


# =============================================================================
# Hook Registries
# =============================================================================


@dataclass
class HookRegistry:
    """Registry for a specific hook type with optional filtering."""
    hooks: list[tuple[Callable, str | None]] = field(default_factory=list)
    
    def register(self, func: Callable, filter_value: str | None = None) -> None:
        """Register a hook function with optional filter."""
        self.hooks.append((func, filter_value))
    
    def get_hooks(self, filter_value: str | None = None) -> list[Callable]:
        """Get all hooks matching the filter (None matches all)."""
        result = []
        for func, hook_filter in self.hooks:
            # Include if no filter on hook, or filter matches
            if hook_filter is None or hook_filter == filter_value or hook_filter == "*":
                result.append(func)
        return result
    
    def clear(self) -> None:
        """Clear all registered hooks."""
        self.hooks = []


# Global registries
_startup_hooks: list[Callable[[], None]] = []
_shutdown_hooks: list[Callable[[], None]] = []
_user_login_hooks = HookRegistry()
_user_register_hooks = HookRegistry()
_record_create_hooks = HookRegistry()
_record_update_hooks = HookRegistry()
_record_delete_hooks = HookRegistry()
_function_call_hooks = HookRegistry()
_function_complete_hooks = HookRegistry()


# =============================================================================
# Lifecycle Hook Decorators
# =============================================================================


def on_startup(func: Callable[[], None]) -> Callable[[], None]:
    """
    Decorator to register a function to run on TinyBase startup.
    
    The decorated function will be called after all extensions are loaded,
    before the server starts accepting requests.
    
    Example:
        from tinybase.extensions import on_startup
        
        @on_startup
        def initialize_my_extension():
            print("Extension initialized!")
    """
    _startup_hooks.append(func)
    return func


def on_shutdown(func: Callable[[], None]) -> Callable[[], None]:
    """
    Decorator to register a function to run on TinyBase shutdown.
    
    The decorated function will be called when the server is shutting down,
    before the process exits.
    
    Example:
        from tinybase.extensions import on_shutdown
        
        @on_shutdown
        def cleanup_my_extension():
            print("Extension shutting down!")
    """
    _shutdown_hooks.append(func)
    return func


# =============================================================================
# Authentication Hook Decorators
# =============================================================================


def on_user_login(func: Callable[[UserLoginEvent], None]) -> Callable[[UserLoginEvent], None]:
    """
    Decorator to register a function to run when a user logs in.
    
    Example:
        from tinybase.extensions import on_user_login, UserLoginEvent
        
        @on_user_login
        def notify_login(event: UserLoginEvent):
            print(f"User {event.email} logged in!")
            if event.is_admin:
                send_admin_alert(event.email)
    """
    _user_login_hooks.register(func)
    return func


def on_user_register(func: Callable[[UserRegisterEvent], None]) -> Callable[[UserRegisterEvent], None]:
    """
    Decorator to register a function to run when a new user registers.
    
    Example:
        from tinybase.extensions import on_user_register, UserRegisterEvent
        
        @on_user_register
        def welcome_user(event: UserRegisterEvent):
            print(f"Welcome {event.email}!")
            create_default_data(event.user_id)
    """
    _user_register_hooks.register(func)
    return func


# =============================================================================
# Data Hook Decorators
# =============================================================================


def on_record_create(
    collection: str | None = None,
) -> Callable[[Callable[[RecordCreateEvent], None]], Callable[[RecordCreateEvent], None]]:
    """
    Decorator to register a function to run when a record is created.
    
    Args:
        collection: Optional collection name to filter. Use "*" for all collections.
                   If None, matches all collections.
    
    Example:
        from tinybase.extensions import on_record_create, RecordCreateEvent
        
        @on_record_create(collection="orders")
        def handle_new_order(event: RecordCreateEvent):
            print(f"New order {event.record_id} created!")
            send_notification(event.data)
        
        @on_record_create()  # All collections
        def audit_creates(event: RecordCreateEvent):
            log_audit("create", event.collection, event.record_id)
    """
    def decorator(func: Callable[[RecordCreateEvent], None]) -> Callable[[RecordCreateEvent], None]:
        _record_create_hooks.register(func, collection)
        return func
    return decorator


def on_record_update(
    collection: str | None = None,
) -> Callable[[Callable[[RecordUpdateEvent], None]], Callable[[RecordUpdateEvent], None]]:
    """
    Decorator to register a function to run when a record is updated.
    
    Args:
        collection: Optional collection name to filter. Use "*" for all collections.
                   If None, matches all collections.
    
    Example:
        from tinybase.extensions import on_record_update, RecordUpdateEvent
        
        @on_record_update(collection="users")
        def handle_user_update(event: RecordUpdateEvent):
            if event.old_data.get("status") != event.new_data.get("status"):
                notify_status_change(event.record_id, event.new_data["status"])
    """
    def decorator(func: Callable[[RecordUpdateEvent], None]) -> Callable[[RecordUpdateEvent], None]:
        _record_update_hooks.register(func, collection)
        return func
    return decorator


def on_record_delete(
    collection: str | None = None,
) -> Callable[[Callable[[RecordDeleteEvent], None]], Callable[[RecordDeleteEvent], None]]:
    """
    Decorator to register a function to run when a record is deleted.
    
    Args:
        collection: Optional collection name to filter. Use "*" for all collections.
                   If None, matches all collections.
    
    Example:
        from tinybase.extensions import on_record_delete, RecordDeleteEvent
        
        @on_record_delete(collection="files")
        def cleanup_file(event: RecordDeleteEvent):
            delete_from_storage(event.data["file_path"])
    """
    def decorator(func: Callable[[RecordDeleteEvent], None]) -> Callable[[RecordDeleteEvent], None]:
        _record_delete_hooks.register(func, collection)
        return func
    return decorator


# =============================================================================
# Function Hook Decorators
# =============================================================================


def on_function_call(
    name: str | None = None,
) -> Callable[[Callable[[FunctionCallEvent], None]], Callable[[FunctionCallEvent], None]]:
    """
    Decorator to register a function to run before a function executes.
    
    Args:
        name: Optional function name to filter. Use "*" for all functions.
              If None, matches all functions.
    
    Example:
        from tinybase.extensions import on_function_call, FunctionCallEvent
        
        @on_function_call(name="process_payment")
        def log_payment_attempt(event: FunctionCallEvent):
            print(f"Payment attempt by user {event.user_id}")
            audit_log("payment_attempt", event.payload)
        
        @on_function_call()  # All functions
        def log_all_calls(event: FunctionCallEvent):
            print(f"Function {event.function_name} called")
    """
    def decorator(func: Callable[[FunctionCallEvent], None]) -> Callable[[FunctionCallEvent], None]:
        _function_call_hooks.register(func, name)
        return func
    return decorator


def on_function_complete(
    name: str | None = None,
) -> Callable[[Callable[[FunctionCompleteEvent], None]], Callable[[FunctionCompleteEvent], None]]:
    """
    Decorator to register a function to run after a function completes.
    
    Args:
        name: Optional function name to filter. Use "*" for all functions.
              If None, matches all functions.
    
    Example:
        from tinybase.extensions import on_function_complete, FunctionCompleteEvent
        
        @on_function_complete()
        def track_function_metrics(event: FunctionCompleteEvent):
            metrics.record(
                function=event.function_name,
                duration=event.duration_ms,
                success=event.status == "succeeded"
            )
        
        @on_function_complete(name="critical_task")
        def alert_on_failure(event: FunctionCompleteEvent):
            if event.status == "failed":
                send_alert(f"Critical task failed: {event.error_message}")
    """
    def decorator(func: Callable[[FunctionCompleteEvent], None]) -> Callable[[FunctionCompleteEvent], None]:
        _function_complete_hooks.register(func, name)
        return func
    return decorator


# =============================================================================
# Hook Execution Functions
# =============================================================================


async def _run_hooks(hooks: list[Callable], event: Any = None) -> None:
    """Execute a list of hooks with optional event data."""
    for hook in hooks:
        try:
            if event is not None:
                result = hook(event)
            else:
                result = hook()
            # Handle async hooks
            if hasattr(result, "__await__"):
                await result
        except Exception as e:
            logger.error(f"Error in hook {hook.__name__}: {e}")


async def run_startup_hooks() -> None:
    """Execute all registered startup hooks."""
    await _run_hooks(_startup_hooks)


async def run_shutdown_hooks() -> None:
    """Execute all registered shutdown hooks."""
    await _run_hooks(_shutdown_hooks)


async def run_user_login_hooks(event: UserLoginEvent) -> None:
    """Execute all registered user login hooks."""
    hooks = _user_login_hooks.get_hooks()
    await _run_hooks(hooks, event)


async def run_user_register_hooks(event: UserRegisterEvent) -> None:
    """Execute all registered user register hooks."""
    hooks = _user_register_hooks.get_hooks()
    await _run_hooks(hooks, event)


async def run_record_create_hooks(event: RecordCreateEvent) -> None:
    """Execute all registered record create hooks for the collection."""
    hooks = _record_create_hooks.get_hooks(event.collection)
    await _run_hooks(hooks, event)


async def run_record_update_hooks(event: RecordUpdateEvent) -> None:
    """Execute all registered record update hooks for the collection."""
    hooks = _record_update_hooks.get_hooks(event.collection)
    await _run_hooks(hooks, event)


async def run_record_delete_hooks(event: RecordDeleteEvent) -> None:
    """Execute all registered record delete hooks for the collection."""
    hooks = _record_delete_hooks.get_hooks(event.collection)
    await _run_hooks(hooks, event)


async def run_function_call_hooks(event: FunctionCallEvent) -> None:
    """Execute all registered function call hooks."""
    hooks = _function_call_hooks.get_hooks(event.function_name)
    await _run_hooks(hooks, event)


async def run_function_complete_hooks(event: FunctionCompleteEvent) -> None:
    """Execute all registered function complete hooks."""
    hooks = _function_complete_hooks.get_hooks(event.function_name)
    await _run_hooks(hooks, event)


# =============================================================================
# Utility Functions
# =============================================================================


def clear_hooks() -> None:
    """Clear all registered hooks. Used for testing."""
    global _startup_hooks, _shutdown_hooks
    _startup_hooks = []
    _shutdown_hooks = []
    _user_login_hooks.clear()
    _user_register_hooks.clear()
    _record_create_hooks.clear()
    _record_update_hooks.clear()
    _record_delete_hooks.clear()
    _function_call_hooks.clear()
    _function_complete_hooks.clear()
