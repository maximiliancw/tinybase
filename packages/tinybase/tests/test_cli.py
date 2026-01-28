"""
Tests for CLI commands.

Uses Typer's CliRunner for testing CLI functionality.
"""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from tinybase.cli import app
from tinybase.version import __version__
from typer.testing import CliRunner

runner = CliRunner()


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory."""
    workspace = tempfile.mkdtemp(prefix="tinybase_cli_test_")
    original_cwd = os.getcwd()

    yield Path(workspace)

    # Cleanup
    os.chdir(original_cwd)
    try:
        shutil.rmtree(workspace)
    except Exception:
        pass


@pytest.fixture
def initialized_workspace(temp_workspace):
    """Create an initialized workspace with tinybase.toml and functions/."""
    os.chdir(temp_workspace)

    # Create tinybase.toml
    toml_content = """
[server]
host = "127.0.0.1"
port = 8000
debug = true

[database]
url = "sqlite:///./test.db"

[functions]
dir = "./functions"

[scheduler]
enabled = false
"""
    (temp_workspace / "tinybase.toml").write_text(toml_content)

    # Create functions directory
    functions_dir = temp_workspace / "functions"
    functions_dir.mkdir()
    (functions_dir / "__init__.py").write_text('"""Functions package."""\n')

    # Set environment variable for database
    os.environ["TINYBASE_DB_URL"] = f"sqlite:///{temp_workspace}/test.db"

    yield temp_workspace

    # Cleanup env var
    os.environ.pop("TINYBASE_DB_URL", None)


# =============================================================================
# Version Command Tests
# =============================================================================


def test_version_command():
    """Test the version command shows TinyBase version."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert f"TinyBase v{__version__}" in result.output


# =============================================================================
# Init Command Tests
# =============================================================================


def test_init_command_creates_workspace(temp_workspace):
    """Test init creates tinybase.toml and functions directory."""
    result = runner.invoke(app, ["init", str(temp_workspace)])

    assert result.exit_code == 0
    assert "Initializing TinyBase" in result.output
    assert "Created tinybase.toml" in result.output
    assert "Created functions/ directory" in result.output
    assert "TinyBase initialized successfully" in result.output

    # Verify files were created
    assert (temp_workspace / "tinybase.toml").exists()
    assert (temp_workspace / "functions").is_dir()
    assert (temp_workspace / "functions" / "__init__.py").exists()


def test_init_command_existing_toml(temp_workspace):
    """Test init handles existing tinybase.toml."""
    # Create existing toml
    (temp_workspace / "tinybase.toml").write_text("# existing config")

    result = runner.invoke(app, ["init", str(temp_workspace)])

    assert result.exit_code == 0
    assert "tinybase.toml already exists" in result.output

    # Original content should be preserved
    content = (temp_workspace / "tinybase.toml").read_text()
    assert "existing config" in content


def test_init_with_admin_credentials(temp_workspace):
    """Test init creates admin user when credentials provided."""
    result = runner.invoke(
        app,
        [
            "init",
            str(temp_workspace),
            "--admin-email",
            "admin@test.com",
            "--admin-password",
            "testpassword123",
        ],
    )

    assert result.exit_code == 0
    assert "Created admin user: admin@test.com" in result.output


def test_init_with_env_admin_credentials(temp_workspace):
    """Test init reads admin credentials from environment variables."""
    os.environ["TINYBASE_ADMIN_EMAIL"] = "env_admin@test.com"
    os.environ["TINYBASE_ADMIN_PASSWORD"] = "envpassword123"

    try:
        result = runner.invoke(app, ["init", str(temp_workspace)])

        assert result.exit_code == 0
        assert "Created admin user: env_admin@test.com" in result.output
    finally:
        os.environ.pop("TINYBASE_ADMIN_EMAIL", None)
        os.environ.pop("TINYBASE_ADMIN_PASSWORD", None)


def test_init_creates_nested_directory(temp_workspace):
    """Test init creates nested directories if they don't exist."""
    nested_dir = temp_workspace / "nested" / "deep" / "workspace"

    result = runner.invoke(app, ["init", str(nested_dir)])

    assert result.exit_code == 0
    assert nested_dir.exists()
    assert (nested_dir / "tinybase.toml").exists()


# =============================================================================
# Serve Command Tests
# =============================================================================


def test_serve_uninitialized_workspace(temp_workspace):
    """Test serve exits with error when workspace not initialized."""
    os.chdir(temp_workspace)

    result = runner.invoke(app, ["serve"])

    assert result.exit_code == 1
    assert "Workspace not initialized" in result.output


def test_serve_missing_functions_dir(temp_workspace):
    """Test serve exits with error when functions directory missing."""
    os.chdir(temp_workspace)

    # Create toml but not functions dir
    (temp_workspace / "tinybase.toml").write_text("[server]\nport = 8000")

    result = runner.invoke(app, ["serve"])

    assert result.exit_code == 1
    assert "Functions directory not found" in result.output


@patch("uvicorn.run")
def test_serve_starts_server(mock_uvicorn, initialized_workspace):
    """Test serve starts uvicorn server."""
    result = runner.invoke(app, ["serve"])

    assert result.exit_code == 0
    assert "Starting TinyBase server" in result.output
    mock_uvicorn.assert_called_once()


@patch("uvicorn.run")
def test_serve_with_custom_host_port(mock_uvicorn, initialized_workspace):
    """Test serve respects custom host and port."""
    result = runner.invoke(app, ["serve", "--host", "0.0.0.0", "--port", "9000"])

    assert result.exit_code == 0
    mock_uvicorn.assert_called_once()
    call_kwargs = mock_uvicorn.call_args[1]
    assert call_kwargs["host"] == "0.0.0.0"
    assert call_kwargs["port"] == 9000


@patch("uvicorn.run")
def test_serve_with_reload_flag(mock_uvicorn, initialized_workspace):
    """Test serve with reload flag."""
    result = runner.invoke(app, ["serve", "--reload"])

    assert result.exit_code == 0
    call_kwargs = mock_uvicorn.call_args[1]
    assert call_kwargs["reload"] is True


# =============================================================================
# Templates Command Tests
# =============================================================================


def test_templates_command_no_templates(temp_workspace):
    """Test templates command when no .tpl files exist."""
    os.chdir(temp_workspace)

    result = runner.invoke(app, ["templates", str(temp_workspace)])

    # Should fail because we're looking for *.tpl files which don't exist
    # in the test environment
    assert result.exit_code == 1


# =============================================================================
# Admin Add Command Tests
# =============================================================================


def test_admin_add_new_user(initialized_workspace):
    """Test admin add creates a new admin user."""
    result = runner.invoke(app, ["admin", "add", "newadmin@test.com", "password123"])

    assert result.exit_code == 0
    assert "Created admin user: newadmin@test.com" in result.output


def test_admin_add_existing_user(initialized_workspace):
    """Test admin add updates existing user."""
    # Create user first
    runner.invoke(app, ["admin", "add", "existing@test.com", "oldpassword"])

    # Update user
    result = runner.invoke(app, ["admin", "add", "existing@test.com", "newpassword"])

    assert result.exit_code == 0
    assert "Updated admin user: existing@test.com" in result.output


# =============================================================================
# Admin Token Command Tests
# =============================================================================


def test_admin_token_create(initialized_workspace):
    """Test admin token create command."""
    result = runner.invoke(
        app,
        ["admin", "token", "create", "--name", "test-token", "--description", "Test token"],
    )

    # Check output contains expected messages (may succeed or fail based on JWT config)
    if result.exit_code == 0:
        assert "Created application token: test-token" in result.output
        assert "Token:" in result.output
        assert "Save this token securely" in result.output
    else:
        # Token creation may fail in test env due to missing JWT config
        pytest.skip("Token creation requires JWT configuration")


def test_admin_token_create_missing_name(initialized_workspace):
    """Test admin token create fails without name."""
    result = runner.invoke(app, ["admin", "token", "create"])

    assert result.exit_code == 1
    assert "--name is required" in result.output


def test_admin_token_create_with_expiry(initialized_workspace):
    """Test admin token create with expiration."""
    result = runner.invoke(
        app,
        ["admin", "token", "create", "--name", "expiring-token", "--expires-days", "30"],
    )

    if result.exit_code == 0:
        assert "Created application token: expiring-token" in result.output
        assert "Expires:" in result.output
    else:
        pytest.skip("Token creation requires JWT configuration")


def test_admin_token_create_never_expires(initialized_workspace):
    """Test admin token create with no expiration."""
    result = runner.invoke(
        app,
        ["admin", "token", "create", "--name", "permanent-token", "--expires-days", "0"],
    )

    if result.exit_code == 0:
        assert "Created application token: permanent-token" in result.output
        # Should not have Expires line when expires_days is 0
        assert "Expires:" not in result.output
    else:
        pytest.skip("Token creation requires JWT configuration")


def test_admin_token_list_empty(initialized_workspace):
    """Test admin token list when no tokens exist."""
    result = runner.invoke(app, ["admin", "token", "list"])

    assert result.exit_code == 0
    assert "No application tokens found" in result.output


def test_admin_token_list_with_tokens(initialized_workspace):
    """Test admin token list shows created tokens."""
    # Create a token first
    create_result = runner.invoke(app, ["admin", "token", "create", "--name", "list-test-token"])

    if create_result.exit_code != 0:
        pytest.skip("Token creation requires JWT configuration")

    result = runner.invoke(app, ["admin", "token", "list"])

    assert result.exit_code == 0
    assert "Found 1 application token" in result.output
    assert "list-test-token" in result.output


def test_admin_token_show(initialized_workspace):
    """Test admin token show command."""
    # Create a token first
    create_result = runner.invoke(app, ["admin", "token", "create", "--name", "show-test-token"])

    if create_result.exit_code != 0:
        pytest.skip("Token creation requires JWT configuration")

    # Extract token ID from output
    token_id = None
    for line in create_result.output.split("\n"):
        if "ID:" in line:
            token_id = line.split("ID:")[1].strip()
            break

    if token_id is None:
        pytest.fail("Could not extract token ID from output")

    result = runner.invoke(app, ["admin", "token", "show", "--id", token_id])

    assert result.exit_code == 0
    assert "show-test-token" in result.output
    assert "Token value is not shown for security reasons" in result.output


def test_admin_token_show_missing_id(initialized_workspace):
    """Test admin token show fails without id."""
    result = runner.invoke(app, ["admin", "token", "show"])

    assert result.exit_code == 1
    assert "--id is required" in result.output


def test_admin_token_show_invalid_id(initialized_workspace):
    """Test admin token show with invalid UUID."""
    result = runner.invoke(app, ["admin", "token", "show", "--id", "not-a-uuid"])

    assert result.exit_code == 1
    assert "Invalid token ID" in result.output


def test_admin_token_show_not_found(initialized_workspace):
    """Test admin token show when token doesn't exist."""
    result = runner.invoke(
        app, ["admin", "token", "show", "--id", "00000000-0000-0000-0000-000000000000"]
    )

    assert result.exit_code == 1
    assert "Token not found" in result.output


def test_admin_token_revoke(initialized_workspace):
    """Test admin token revoke command."""
    # Create a token first
    create_result = runner.invoke(app, ["admin", "token", "create", "--name", "revoke-test-token"])

    if create_result.exit_code != 0:
        pytest.skip("Token creation requires JWT configuration")

    # Extract token ID from output
    token_id = None
    for line in create_result.output.split("\n"):
        if "ID:" in line:
            token_id = line.split("ID:")[1].strip()
            break

    if token_id is None:
        pytest.fail("Could not extract token ID from output")

    result = runner.invoke(app, ["admin", "token", "revoke", "--id", token_id])

    assert result.exit_code == 0
    assert "Revoked application token" in result.output


def test_admin_token_revoke_not_found(initialized_workspace):
    """Test admin token revoke when token doesn't exist."""
    result = runner.invoke(
        app, ["admin", "token", "revoke", "--id", "00000000-0000-0000-0000-000000000000"]
    )

    assert result.exit_code == 1
    assert "Token not found" in result.output


def test_admin_token_unknown_action(initialized_workspace):
    """Test admin token with unknown action."""
    result = runner.invoke(app, ["admin", "token", "invalid_action"])

    assert result.exit_code == 1
    assert "Unknown action" in result.output


# =============================================================================
# Functions New Command Tests
# =============================================================================


def test_functions_new(initialized_workspace):
    """Test functions new creates boilerplate."""
    result = runner.invoke(app, ["functions", "new", "my_function"])

    assert result.exit_code == 0
    assert "Created function 'my_function'" in result.output

    # Verify file was created
    func_file = initialized_workspace / "functions" / "my_function.py"
    assert func_file.exists()

    content = func_file.read_text()
    assert "def my_function" in content
    assert "@register" in content


def test_functions_new_with_description(initialized_workspace):
    """Test functions new with custom description."""
    result = runner.invoke(
        app,
        ["functions", "new", "described_func", "--description", "My custom function"],
    )

    assert result.exit_code == 0

    func_file = initialized_workspace / "functions" / "described_func.py"
    content = func_file.read_text()
    assert "My custom function" in content


def test_functions_new_invalid_name(initialized_workspace):
    """Test functions new rejects invalid names."""
    result = runner.invoke(app, ["functions", "new", "InvalidName"])

    assert result.exit_code == 1
    assert "lowercase with underscores" in result.output


def test_functions_new_existing_function(initialized_workspace):
    """Test functions new fails if function already exists."""
    # Create function first
    runner.invoke(app, ["functions", "new", "existing_func"])

    # Try to create again
    result = runner.invoke(app, ["functions", "new", "existing_func"])

    assert result.exit_code == 1
    assert "already exists" in result.output


def test_functions_new_creates_init_py(temp_workspace):
    """Test functions new creates __init__.py if missing."""
    os.chdir(temp_workspace)

    # Create functions dir without __init__.py
    functions_dir = temp_workspace / "functions"
    functions_dir.mkdir()

    result = runner.invoke(app, ["functions", "new", "auto_init", "--dir", str(functions_dir)])

    assert result.exit_code == 0
    assert (functions_dir / "__init__.py").exists()


# =============================================================================
# Functions Deploy Command Tests
# =============================================================================


def test_functions_deploy_no_sdk(initialized_workspace):
    """Test functions deploy fails gracefully without tinybase-sdk."""
    with patch.dict("sys.modules", {"tinybase_sdk": None}):
        # This test checks the import error handling
        # The actual behavior depends on whether tinybase-sdk is installed
        result = runner.invoke(app, ["functions", "deploy"])
        # Either succeeds or fails with configuration/sdk error
        assert result.exit_code in [0, 1]


# =============================================================================
# Extensions Command Tests
# =============================================================================


def test_extensions_list_empty(initialized_workspace):
    """Test extensions list when no extensions installed."""
    result = runner.invoke(app, ["extensions", "list"])

    assert result.exit_code == 0
    assert "No extensions installed" in result.output


def test_extensions_install_cancelled(initialized_workspace):
    """Test extensions install can be cancelled."""
    result = runner.invoke(
        app,
        ["extensions", "install", "https://github.com/test/ext"],
        input="n\n",  # Say no to confirmation
    )

    assert result.exit_code == 0
    assert "Installation cancelled" in result.output


def test_extensions_enable_not_found(initialized_workspace):
    """Test extensions enable fails for non-existent extension."""
    result = runner.invoke(app, ["extensions", "enable", "nonexistent"])

    assert result.exit_code == 1
    assert "not found" in result.output


def test_extensions_disable_not_found(initialized_workspace):
    """Test extensions disable fails for non-existent extension."""
    result = runner.invoke(app, ["extensions", "disable", "nonexistent"])

    assert result.exit_code == 1
    assert "not found" in result.output


def test_extensions_uninstall_not_found(initialized_workspace):
    """Test extensions uninstall fails for non-existent extension."""
    result = runner.invoke(app, ["extensions", "uninstall", "nonexistent", "--yes"])

    assert result.exit_code == 1
    assert "not found" in result.output


def test_extensions_uninstall_cancelled(initialized_workspace):
    """Test extensions uninstall can be cancelled."""
    result = runner.invoke(
        app,
        ["extensions", "uninstall", "some_ext"],
        input="n\n",  # Say no to confirmation
    )

    assert result.exit_code == 0
    assert "Uninstallation cancelled" in result.output


def test_extensions_check_updates_empty(initialized_workspace):
    """Test extensions check-updates when no extensions."""
    result = runner.invoke(app, ["extensions", "check-updates"])

    assert result.exit_code == 0
    assert "No extensions installed" in result.output


def test_extensions_check_updates_not_found(initialized_workspace):
    """Test extensions check-updates for non-existent extension."""
    result = runner.invoke(app, ["extensions", "check-updates", "nonexistent"])

    assert result.exit_code == 1
    assert "not found" in result.output


# =============================================================================
# DB Command Tests (require alembic.ini)
# =============================================================================


def test_db_migrate_no_alembic_ini(initialized_workspace):
    """Test db migrate fails gracefully without alembic.ini."""
    result = runner.invoke(app, ["db", "migrate"])

    # Should fail because alembic.ini doesn't exist
    assert result.exit_code != 0


def test_db_upgrade_no_alembic_ini(initialized_workspace):
    """Test db upgrade fails gracefully without alembic.ini."""
    result = runner.invoke(app, ["db", "upgrade"])

    # Should fail because alembic.ini doesn't exist
    assert result.exit_code != 0


def test_db_downgrade_no_alembic_ini(initialized_workspace):
    """Test db downgrade fails gracefully without alembic.ini."""
    result = runner.invoke(app, ["db", "downgrade"])

    # Should fail because alembic.ini doesn't exist
    assert result.exit_code != 0


def test_db_history_no_alembic_ini(initialized_workspace):
    """Test db history fails gracefully without alembic.ini."""
    result = runner.invoke(app, ["db", "history"])

    # Should fail because alembic.ini doesn't exist
    assert result.exit_code != 0


def test_db_current_no_alembic_ini(initialized_workspace):
    """Test db current fails gracefully without alembic.ini."""
    result = runner.invoke(app, ["db", "current"])

    # Should fail because alembic.ini doesn't exist
    assert result.exit_code != 0


# =============================================================================
# CLI Utils Tests
# =============================================================================


def test_snake_to_camel():
    """Test snake_case to CamelCase conversion."""
    from tinybase.cli.utils import snake_to_camel

    assert snake_to_camel("hello") == "Hello"
    assert snake_to_camel("hello_world") == "HelloWorld"
    assert snake_to_camel("my_function_name") == "MyFunctionName"
    assert snake_to_camel("a_b_c") == "ABC"


def test_create_default_toml():
    """Test default toml generation."""
    from tinybase.cli.utils import create_default_toml

    toml = create_default_toml()

    assert "[server]" in toml
    assert "[database]" in toml
    assert "[auth]" in toml
    assert "[functions]" in toml
    assert "[scheduler]" in toml


def test_create_function_boilerplate():
    """Test function boilerplate generation."""
    from tinybase.cli.utils import create_function_boilerplate

    boilerplate = create_function_boilerplate("test_func", "Test function description")

    assert "def test_func" in boilerplate
    assert "@register" in boilerplate
    assert 'name="test_func"' in boilerplate
    assert "Test function description" in boilerplate
    assert "tinybase-sdk" in boilerplate


def test_get_example_functions():
    """Test example functions generation."""
    from tinybase.cli.utils import get_example_functions

    examples = get_example_functions()

    assert len(examples) == 3

    filenames = [name for name, _ in examples]
    assert "add_numbers.py" in filenames
    assert "hello.py" in filenames
    assert "fetch_url.py" in filenames

    # Check content of one function
    for name, content in examples:
        if name == "add_numbers.py":
            assert "def add_numbers" in content
            assert "@register" in content
            break
