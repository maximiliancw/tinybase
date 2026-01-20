"""Tests for SDK configuration management."""

import os
import tempfile
from pathlib import Path

import pytest
from tinybase_sdk.config import ConfigurationError, get_functions_dir, load_deployment_config


def test_load_from_environment_variables():
    """Test loading configuration from environment variables."""
    os.environ["TINYBASE_API_URL"] = "https://test.api.com"
    os.environ["TINYBASE_API_TOKEN"] = "test-token-123"
    os.environ["TINYBASE_FUNCTIONS_DIR"] = "/tmp/functions"
    os.environ["TINYBASE_TIMEOUT"] = "60.0"

    try:
        config = load_deployment_config()

        assert config.api_url == "https://test.api.com"
        assert config.api_token == "test-token-123"
        assert config.functions_dir == Path("/tmp/functions")
        assert config.timeout == 60.0
    finally:
        # Cleanup
        del os.environ["TINYBASE_API_URL"]
        del os.environ["TINYBASE_API_TOKEN"]
        del os.environ["TINYBASE_FUNCTIONS_DIR"]
        del os.environ["TINYBASE_TIMEOUT"]


def test_load_from_toml_file():
    """Test loading configuration from tinybase.toml file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "tinybase.toml"
        config_path.write_text(
            """
functions_path = "./my_functions"

[environments.production]
api_url = "https://prod.api.com"
api_token = "prod-token"
timeout = 45.0

[environments.staging]
api_url = "https://staging.api.com"
api_token = "staging-token"
"""
        )

        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            config = load_deployment_config("production")

            assert config.api_url == "https://prod.api.com"
            assert config.api_token == "prod-token"
            assert config.functions_dir == Path("./my_functions")
            assert config.timeout == 45.0

            # Test staging environment
            staging_config = load_deployment_config("staging")
            assert staging_config.api_url == "https://staging.api.com"
            assert staging_config.api_token == "staging-token"
        finally:
            os.chdir(original_cwd)


def test_missing_environment_in_toml():
    """Test error when specified environment doesn't exist in config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "tinybase.toml"
        config_path.write_text(
            """
[environments.production]
api_url = "https://prod.api.com"
api_token = "prod-token"
"""
        )

        original_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            with pytest.raises(ConfigurationError, match="Environment 'dev' not found"):
                load_deployment_config("dev")
        finally:
            os.chdir(original_cwd)


def test_missing_api_url_in_environment():
    """Test error when api_url is missing from environment config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "tinybase.toml"
        config_path.write_text(
            """
[environments.production]
api_token = "prod-token"
"""
        )

        original_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            with pytest.raises(ConfigurationError, match="Missing 'api_url'"):
                load_deployment_config("production")
        finally:
            os.chdir(original_cwd)


def test_missing_api_token_in_environment():
    """Test error when api_token is missing from environment config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "tinybase.toml"
        config_path.write_text(
            """
[environments.production]
api_url = "https://prod.api.com"
"""
        )

        original_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            with pytest.raises(ConfigurationError, match="Missing 'api_token'"):
                load_deployment_config("production")
        finally:
            os.chdir(original_cwd)


def test_no_configuration_found():
    """Test error when no configuration is found."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            # Make sure no env vars are set
            for key in ["TINYBASE_API_URL", "TINYBASE_API_TOKEN"]:
                if key in os.environ:
                    del os.environ[key]

            with pytest.raises(ConfigurationError, match="No deployment configuration found"):
                load_deployment_config()
        finally:
            os.chdir(original_cwd)


def test_get_functions_dir_from_env():
    """Test getting functions directory from environment variable."""
    os.environ["TINYBASE_FUNCTIONS_DIR"] = "/custom/functions"

    try:
        assert get_functions_dir() == Path("/custom/functions")
    finally:
        del os.environ["TINYBASE_FUNCTIONS_DIR"]


def test_get_functions_dir_from_toml():
    """Test getting functions directory from tinybase.toml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "tinybase.toml"
        config_path.write_text('functions_path = "./my_funcs"')

        original_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            assert get_functions_dir() == Path("./my_funcs")
        finally:
            os.chdir(original_cwd)


def test_get_functions_dir_default():
    """Test getting functions directory returns default when no config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            # Make sure no env var is set
            if "TINYBASE_FUNCTIONS_DIR" in os.environ:
                del os.environ["TINYBASE_FUNCTIONS_DIR"]

            assert get_functions_dir() == Path("./functions")
        finally:
            os.chdir(original_cwd)


def test_environment_variables_take_precedence():
    """Test that environment variables take precedence over config file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "tinybase.toml"
        config_path.write_text(
            """
[environments.production]
api_url = "https://toml.api.com"
api_token = "toml-token"
"""
        )

        os.environ["TINYBASE_API_URL"] = "https://env.api.com"
        os.environ["TINYBASE_API_TOKEN"] = "env-token"

        original_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            config = load_deployment_config("production")

            # Env vars should take precedence
            assert config.api_url == "https://env.api.com"
            assert config.api_token == "env-token"
        finally:
            os.chdir(original_cwd)
            del os.environ["TINYBASE_API_URL"]
            del os.environ["TINYBASE_API_TOKEN"]
