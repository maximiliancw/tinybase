"""
TinyBase Extension System.

Provides functionality for installing and managing extensions from GitHub repositories.
Extensions can register functions, add lifecycle hooks, and integrate third-party services.

Usage for extension developers:

    from tinybase.functions import Context, register
    from tinybase.extensions import (
        on_startup, on_shutdown,
        on_user_login, on_user_register,
        on_record_create, on_record_update, on_record_delete,
        on_function_call, on_function_complete,
        UserLoginEvent, RecordCreateEvent, FunctionCompleteEvent,
    )

    # Lifecycle hooks
    @on_startup
    def initialize():
        print("Extension loaded!")

    @on_shutdown
    def cleanup():
        print("Extension unloading!")

    # Authentication hooks
    @on_user_login
    def notify_login(event: UserLoginEvent):
        if event.is_admin:
            send_alert(f"Admin {event.email} logged in")

    # Data hooks
    @on_record_create(collection="orders")
    def handle_new_order(event: RecordCreateEvent):
        send_notification(f"New order: {event.record_id}")

    # Function hooks
    @on_function_complete()
    def track_metrics(event: FunctionCompleteEvent):
        log_metric(event.function_name, event.duration_ms)

    # Register custom functions
    @register(name="my_function", description="My extension function", auth="auth")
    def my_function(ctx: Context, payload: MyInput) -> MyOutput:
        return MyOutput(...)

    # Activity logging (for audit trails)
    from tinybase.extensions import log_extension_activity

    log_extension_activity(
        extension_name="my_extension",
        action_name="sync_completed",
        meta_data={"records": 150},
    )
    # Logs as action: "ext.my_extension.sync_completed"
"""

from tinybase.extensions.hooks import (
    FunctionCallEvent,
    FunctionCompleteEvent,
    RecordCreateEvent,
    RecordDeleteEvent,
    RecordUpdateEvent,
    # Event data classes
    UserLoginEvent,
    UserRegisterEvent,
    # Utilities
    clear_hooks,
    # Function hooks
    on_function_call,
    on_function_complete,
    # Data hooks
    on_record_create,
    on_record_delete,
    on_record_update,
    on_shutdown,
    # Lifecycle hooks
    on_startup,
    # Authentication hooks
    on_user_login,
    on_user_register,
    run_function_call_hooks,
    run_function_complete_hooks,
    run_record_create_hooks,
    run_record_delete_hooks,
    run_record_update_hooks,
    run_shutdown_hooks,
    run_startup_hooks,
    run_user_login_hooks,
    run_user_register_hooks,
)
from tinybase.extensions.installer import (
    ExtensionManifest,
    InstallError,
    check_for_updates,
    install_extension,
    parse_github_url,
    uninstall_extension,
    validate_manifest,
)
from tinybase.extensions.loader import (
    get_extensions_directory,
    load_enabled_extensions,
    load_extension_module,
    unload_extension,
)
from tinybase.activity import log_extension_activity

__all__ = [
    # Lifecycle hooks (for extension developers)
    "on_startup",
    "on_shutdown",
    # Authentication hooks
    "on_user_login",
    "on_user_register",
    # Data hooks
    "on_record_create",
    "on_record_update",
    "on_record_delete",
    # Function hooks
    "on_function_call",
    "on_function_complete",
    # Event data classes
    "UserLoginEvent",
    "UserRegisterEvent",
    "RecordCreateEvent",
    "RecordUpdateEvent",
    "RecordDeleteEvent",
    "FunctionCallEvent",
    "FunctionCompleteEvent",
    # Hook runners (for internal use)
    "run_startup_hooks",
    "run_shutdown_hooks",
    "run_user_login_hooks",
    "run_user_register_hooks",
    "run_record_create_hooks",
    "run_record_update_hooks",
    "run_record_delete_hooks",
    "run_function_call_hooks",
    "run_function_complete_hooks",
    "clear_hooks",
    # Loader
    "load_enabled_extensions",
    "load_extension_module",
    "unload_extension",
    "get_extensions_directory",
    # Installer
    "install_extension",
    "uninstall_extension",
    "check_for_updates",
    "validate_manifest",
    "parse_github_url",
    "InstallError",
    "ExtensionManifest",
    # Activity logging
    "log_extension_activity",
]
