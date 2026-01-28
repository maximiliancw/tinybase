"""
Tests for extension core functionality.

Tests the extension system including:
- Hook registration and execution
- Extension loading/unloading
- Extension installation/uninstallation
- Manifest validation
"""

import sys
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from tinybase.extensions.hooks import (
    FunctionCallEvent,
    FunctionCompleteEvent,
    HookRegistry,
    RecordCreateEvent,
    RecordDeleteEvent,
    RecordUpdateEvent,
    UserLoginEvent,
    UserRegisterEvent,
    _run_hooks,
    clear_hooks,
    on_function_call,
    on_function_complete,
    on_record_create,
    on_record_delete,
    on_record_update,
    on_shutdown,
    on_startup,
    on_user_login,
    on_user_register,
    run_function_call_hooks,
    run_function_complete_hooks,
    run_record_create_hooks,
    run_shutdown_hooks,
    run_startup_hooks,
    run_user_login_hooks,
    run_user_register_hooks,
)
from tinybase.extensions.installer import (
    ExtensionManifest,
    InstallError,
    parse_github_url,
    validate_manifest,
)
from tinybase.extensions.loader import load_extension_module, unload_extension

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def clear_all_hooks():
    """Clear hooks before and after each test."""
    clear_hooks()
    yield
    clear_hooks()


# =============================================================================
# HookRegistry Tests
# =============================================================================


def test_hook_registry_register():
    """Test registering hooks in registry."""
    registry = HookRegistry()

    def hook1():
        pass

    def hook2():
        pass

    registry.register(hook1)
    registry.register(hook2, filter_value="specific")

    assert len(registry.hooks) == 2


def test_hook_registry_get_hooks_no_filter():
    """Test getting hooks without filter."""
    registry = HookRegistry()

    def hook1():
        pass

    def hook2():
        pass

    registry.register(hook1)
    registry.register(hook2)

    hooks = registry.get_hooks()
    assert len(hooks) == 2


def test_hook_registry_get_hooks_with_filter():
    """Test getting hooks with filter."""
    registry = HookRegistry()

    def general_hook():
        pass

    def specific_hook():
        pass

    def other_hook():
        pass

    registry.register(general_hook)  # No filter - matches all
    registry.register(specific_hook, filter_value="orders")
    registry.register(other_hook, filter_value="users")

    # Get hooks for "orders" - should get general and specific
    hooks = registry.get_hooks("orders")
    assert len(hooks) == 2
    assert general_hook in hooks
    assert specific_hook in hooks
    assert other_hook not in hooks


def test_hook_registry_wildcard_filter():
    """Test hooks with wildcard filter match all."""
    registry = HookRegistry()

    def wildcard_hook():
        pass

    def specific_hook():
        pass

    registry.register(wildcard_hook, filter_value="*")
    registry.register(specific_hook, filter_value="orders")

    # Wildcard should match any filter
    hooks = registry.get_hooks("anything")
    assert wildcard_hook in hooks


def test_hook_registry_clear():
    """Test clearing hook registry."""
    registry = HookRegistry()

    def hook():
        pass

    registry.register(hook)
    assert len(registry.hooks) == 1

    registry.clear()
    assert len(registry.hooks) == 0


# =============================================================================
# Lifecycle Hook Decorator Tests
# =============================================================================


def test_on_startup_decorator():
    """Test on_startup decorator registers function."""
    from tinybase.extensions.hooks import _startup_hooks

    @on_startup
    def my_startup():
        pass

    assert my_startup in _startup_hooks


def test_on_shutdown_decorator():
    """Test on_shutdown decorator registers function."""
    from tinybase.extensions.hooks import _shutdown_hooks

    @on_shutdown
    def my_shutdown():
        pass

    assert my_shutdown in _shutdown_hooks


# =============================================================================
# Authentication Hook Decorator Tests
# =============================================================================


def test_on_user_login_decorator():
    """Test on_user_login decorator registers function."""
    from tinybase.extensions.hooks import _user_login_hooks

    @on_user_login
    def my_login_hook(event: UserLoginEvent):
        pass

    hooks = _user_login_hooks.get_hooks()
    assert my_login_hook in hooks


def test_on_user_register_decorator():
    """Test on_user_register decorator registers function."""
    from tinybase.extensions.hooks import _user_register_hooks

    @on_user_register
    def my_register_hook(event: UserRegisterEvent):
        pass

    hooks = _user_register_hooks.get_hooks()
    assert my_register_hook in hooks


# =============================================================================
# Data Hook Decorator Tests
# =============================================================================


def test_on_record_create_decorator():
    """Test on_record_create decorator."""
    from tinybase.extensions.hooks import _record_create_hooks

    @on_record_create(collection="orders")
    def my_create_hook(event: RecordCreateEvent):
        pass

    hooks = _record_create_hooks.get_hooks("orders")
    assert my_create_hook in hooks


def test_on_record_update_decorator():
    """Test on_record_update decorator."""
    from tinybase.extensions.hooks import _record_update_hooks

    @on_record_update(collection="users")
    def my_update_hook(event: RecordUpdateEvent):
        pass

    hooks = _record_update_hooks.get_hooks("users")
    assert my_update_hook in hooks


def test_on_record_delete_decorator():
    """Test on_record_delete decorator."""
    from tinybase.extensions.hooks import _record_delete_hooks

    @on_record_delete(collection="files")
    def my_delete_hook(event: RecordDeleteEvent):
        pass

    hooks = _record_delete_hooks.get_hooks("files")
    assert my_delete_hook in hooks


# =============================================================================
# Function Hook Decorator Tests
# =============================================================================


def test_on_function_call_decorator():
    """Test on_function_call decorator."""
    from tinybase.extensions.hooks import _function_call_hooks

    @on_function_call(name="process_payment")
    def my_call_hook(event: FunctionCallEvent):
        pass

    hooks = _function_call_hooks.get_hooks("process_payment")
    assert my_call_hook in hooks


def test_on_function_complete_decorator():
    """Test on_function_complete decorator."""
    from tinybase.extensions.hooks import _function_complete_hooks

    @on_function_complete(name="critical_task")
    def my_complete_hook(event: FunctionCompleteEvent):
        pass

    hooks = _function_complete_hooks.get_hooks("critical_task")
    assert my_complete_hook in hooks


# =============================================================================
# Hook Execution Tests
# =============================================================================


@pytest.mark.asyncio
async def test_run_hooks_sync():
    """Test running synchronous hooks."""
    results = []

    def hook1():
        results.append("hook1")

    def hook2():
        results.append("hook2")

    await _run_hooks([hook1, hook2])

    assert results == ["hook1", "hook2"]


@pytest.mark.asyncio
async def test_run_hooks_async():
    """Test running asynchronous hooks."""
    results = []

    async def async_hook():
        results.append("async")

    def sync_hook():
        results.append("sync")

    await _run_hooks([async_hook, sync_hook])

    assert "async" in results
    assert "sync" in results


@pytest.mark.asyncio
async def test_run_hooks_with_event():
    """Test running hooks with event data."""
    received_events = []

    def hook(event):
        received_events.append(event)

    event = UserLoginEvent(user_id=uuid4(), email="test@test.com", is_admin=False)
    await _run_hooks([hook], event)

    assert len(received_events) == 1
    assert received_events[0].email == "test@test.com"


@pytest.mark.asyncio
async def test_run_hooks_error_isolation():
    """Test that hook errors don't affect other hooks."""
    results = []

    def failing_hook():
        raise Exception("Hook failed!")

    def succeeding_hook():
        results.append("success")

    # Should not raise, and second hook should still run
    await _run_hooks([failing_hook, succeeding_hook])

    assert "success" in results


@pytest.mark.asyncio
async def test_run_startup_hooks():
    """Test run_startup_hooks executes registered hooks."""
    executed = []

    @on_startup
    def startup_hook():
        executed.append("started")

    await run_startup_hooks()

    assert "started" in executed


@pytest.mark.asyncio
async def test_run_shutdown_hooks():
    """Test run_shutdown_hooks executes registered hooks."""
    executed = []

    @on_shutdown
    def shutdown_hook():
        executed.append("stopped")

    await run_shutdown_hooks()

    assert "stopped" in executed


@pytest.mark.asyncio
async def test_run_user_login_hooks():
    """Test run_user_login_hooks executes with event."""
    received = []

    @on_user_login
    def login_hook(event: UserLoginEvent):
        received.append(event.email)

    event = UserLoginEvent(user_id=uuid4(), email="user@test.com", is_admin=True)
    await run_user_login_hooks(event)

    assert "user@test.com" in received


@pytest.mark.asyncio
async def test_run_user_register_hooks():
    """Test run_user_register_hooks executes with event."""
    received = []

    @on_user_register
    def register_hook(event: UserRegisterEvent):
        received.append(event.email)

    event = UserRegisterEvent(user_id=uuid4(), email="new@test.com")
    await run_user_register_hooks(event)

    assert "new@test.com" in received


@pytest.mark.asyncio
async def test_run_record_create_hooks():
    """Test run_record_create_hooks filters by collection."""
    received = []

    @on_record_create(collection="orders")
    def orders_hook(event: RecordCreateEvent):
        received.append(f"orders:{event.record_id}")

    @on_record_create(collection="users")
    def users_hook(event: RecordCreateEvent):
        received.append(f"users:{event.record_id}")

    record_id = uuid4()
    event = RecordCreateEvent(
        collection="orders", record_id=record_id, data={"total": 100}, owner_id=None
    )
    await run_record_create_hooks(event)

    # Only orders hook should run
    assert len(received) == 1
    assert f"orders:{record_id}" in received


@pytest.mark.asyncio
async def test_run_function_call_hooks():
    """Test run_function_call_hooks executes with event."""
    received = []

    @on_function_call()
    def call_hook(event: FunctionCallEvent):
        received.append(event.function_name)

    event = FunctionCallEvent(function_name="test_func", user_id=uuid4(), payload={"arg": "value"})
    await run_function_call_hooks(event)

    assert "test_func" in received


@pytest.mark.asyncio
async def test_run_function_complete_hooks():
    """Test run_function_complete_hooks executes with event."""
    received = []

    @on_function_complete()
    def complete_hook(event: FunctionCompleteEvent):
        received.append((event.function_name, event.status))

    event = FunctionCompleteEvent(
        function_name="test_func",
        user_id=uuid4(),
        status="succeeded",
        duration_ms=150,
    )
    await run_function_complete_hooks(event)

    assert ("test_func", "succeeded") in received


# =============================================================================
# Event Data Class Tests
# =============================================================================


def test_user_login_event():
    """Test UserLoginEvent data class."""
    event = UserLoginEvent(user_id=uuid4(), email="test@test.com", is_admin=True)

    assert event.email == "test@test.com"
    assert event.is_admin is True


def test_function_complete_event_with_error():
    """Test FunctionCompleteEvent with error details."""
    event = FunctionCompleteEvent(
        function_name="failing_func",
        user_id=uuid4(),
        status="failed",
        duration_ms=50,
        error_message="Something went wrong",
        error_type="ValueError",
    )

    assert event.status == "failed"
    assert event.error_message == "Something went wrong"
    assert event.error_type == "ValueError"


# =============================================================================
# GitHub URL Parsing Tests
# =============================================================================


def test_parse_github_url_full_url():
    """Test parsing full GitHub URL."""
    owner, repo, branch = parse_github_url("https://github.com/user/my-extension")

    assert owner == "user"
    assert repo == "my-extension"
    assert branch is None


def test_parse_github_url_with_git_suffix():
    """Test parsing GitHub URL with .git suffix."""
    owner, repo, branch = parse_github_url("https://github.com/user/repo.git")

    assert owner == "user"
    assert repo == "repo"


def test_parse_github_url_with_branch():
    """Test parsing GitHub URL with branch."""
    owner, repo, branch = parse_github_url("https://github.com/user/repo/tree/develop")

    assert owner == "user"
    assert repo == "repo"
    assert branch == "develop"


def test_parse_github_url_shorthand():
    """Test parsing shorthand format."""
    owner, repo, branch = parse_github_url("user/my-extension")

    assert owner == "user"
    assert repo == "my-extension"
    assert branch is None


def test_parse_github_url_without_https():
    """Test parsing URL without https prefix."""
    owner, repo, branch = parse_github_url("github.com/user/repo")

    assert owner == "user"
    assert repo == "repo"


def test_parse_github_url_invalid():
    """Test parsing invalid URL raises error."""
    with pytest.raises(InstallError, match="Invalid GitHub URL format"):
        parse_github_url("not-a-valid-url")


# =============================================================================
# Manifest Validation Tests
# =============================================================================


def test_validate_manifest_success():
    """Test validating a valid manifest."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "extension.toml"
        manifest_path.write_text("""
[extension]
name = "my-extension"
version = "1.0.0"
description = "A test extension"
author = "Test Author"
entry_point = "main.py"
""")

        result = validate_manifest(manifest_path)

        assert result.name == "my-extension"
        assert result.version == "1.0.0"
        assert result.description == "A test extension"
        assert result.author == "Test Author"
        assert result.entry_point == "main.py"


def test_validate_manifest_minimal():
    """Test validating manifest with only required fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "extension.toml"
        manifest_path.write_text("""
[extension]
name = "minimal-ext"
version = "0.1.0"
""")

        result = validate_manifest(manifest_path)

        assert result.name == "minimal-ext"
        assert result.version == "0.1.0"
        assert result.description is None
        assert result.entry_point == "main.py"  # Default


def test_validate_manifest_not_found():
    """Test validation fails for missing manifest."""
    with pytest.raises(InstallError, match="Manifest not found"):
        validate_manifest(Path("/nonexistent/extension.toml"))


def test_validate_manifest_missing_name():
    """Test validation fails for missing name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "extension.toml"
        manifest_path.write_text("""
[extension]
version = "1.0.0"
""")

        with pytest.raises(InstallError, match="missing required field: name"):
            validate_manifest(manifest_path)


def test_validate_manifest_missing_version():
    """Test validation fails for missing version."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "extension.toml"
        manifest_path.write_text("""
[extension]
name = "test-ext"
""")

        with pytest.raises(InstallError, match="missing required field: version"):
            validate_manifest(manifest_path)


def test_validate_manifest_invalid_name():
    """Test validation fails for invalid name format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "extension.toml"
        manifest_path.write_text("""
[extension]
name = "Invalid_Name"
version = "1.0.0"
""")

        with pytest.raises(InstallError, match="Invalid extension name"):
            validate_manifest(manifest_path)


def test_validate_manifest_invalid_toml():
    """Test validation fails for invalid TOML."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "extension.toml"
        manifest_path.write_text("this is not valid toml {{{{")

        with pytest.raises(InstallError, match="Failed to parse manifest"):
            validate_manifest(manifest_path)


# =============================================================================
# Extension Loader Tests
# =============================================================================


def test_load_extension_module_success():
    """Test loading a valid extension module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ext_path = Path(tmpdir)

        # Create a simple extension module
        (ext_path / "main.py").write_text("""
LOADED = True

def init():
    return "initialized"
""")

        result = load_extension_module(ext_path, "main.py")

        assert result is True

        # Verify module was loaded
        module_name = f"tinybase_extension_{ext_path.name}"
        assert module_name in sys.modules

        # Clean up
        del sys.modules[module_name]


def test_load_extension_module_not_found():
    """Test loading fails when entry point missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ext_path = Path(tmpdir)

        result = load_extension_module(ext_path, "missing.py")

        assert result is False


def test_load_extension_module_syntax_error():
    """Test loading handles syntax errors gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ext_path = Path(tmpdir)

        # Create a module with syntax error
        (ext_path / "main.py").write_text("def broken( invalid syntax")

        result = load_extension_module(ext_path, "main.py")

        assert result is False


def test_unload_extension():
    """Test unloading an extension module."""
    # First load a module
    with tempfile.TemporaryDirectory() as tmpdir:
        ext_path = Path(tmpdir)
        (ext_path / "main.py").write_text("LOADED = True")

        load_extension_module(ext_path, "main.py")

        module_name = f"tinybase_extension_{ext_path.name}"
        assert module_name in sys.modules

        # Unload it
        result = unload_extension(ext_path.name)

        assert result is True
        assert module_name not in sys.modules


def test_unload_extension_not_found():
    """Test unloading returns False when module not found."""
    result = unload_extension("nonexistent_extension")

    assert result is False


def test_load_extension_module_reloads():
    """Test loading replaces existing module."""
    import time

    with tempfile.TemporaryDirectory() as tmpdir:
        ext_path = Path(tmpdir)

        # Create initial module
        (ext_path / "main.py").write_text("VERSION = 1")
        load_extension_module(ext_path, "main.py")

        module_name = f"tinybase_extension_{ext_path.name}"
        module1 = sys.modules[module_name]
        assert module1.VERSION == 1

        # Ensure file modification time changes
        time.sleep(0.1)

        # Update and reload - clear __pycache__ to avoid caching issues
        pycache_dir = ext_path / "__pycache__"
        if pycache_dir.exists():
            import shutil

            shutil.rmtree(pycache_dir)

        (ext_path / "main.py").write_text("VERSION = 2")

        # Force module removal before reload
        if module_name in sys.modules:
            del sys.modules[module_name]

        load_extension_module(ext_path, "main.py")

        module2 = sys.modules[module_name]
        assert module2.VERSION == 2

        # Clean up
        if module_name in sys.modules:
            del sys.modules[module_name]


# =============================================================================
# InstallError Tests
# =============================================================================


def test_install_error():
    """Test InstallError exception."""
    error = InstallError("Installation failed")
    assert str(error) == "Installation failed"
    assert isinstance(error, Exception)


# =============================================================================
# ExtensionManifest Tests
# =============================================================================


def test_extension_manifest_defaults():
    """Test ExtensionManifest default values."""
    manifest = ExtensionManifest(name="test", version="1.0.0")

    assert manifest.name == "test"
    assert manifest.version == "1.0.0"
    assert manifest.description is None
    assert manifest.author is None
    assert manifest.entry_point == "main.py"


def test_extension_manifest_all_fields():
    """Test ExtensionManifest with all fields."""
    manifest = ExtensionManifest(
        name="full-ext",
        version="2.0.0",
        description="Full description",
        author="Test Author",
        entry_point="custom.py",
    )

    assert manifest.name == "full-ext"
    assert manifest.version == "2.0.0"
    assert manifest.description == "Full description"
    assert manifest.author == "Test Author"
    assert manifest.entry_point == "custom.py"
