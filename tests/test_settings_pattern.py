"""
Tests for improved settings pattern using lru_cache.
"""

import os
import tempfile
from pathlib import Path

import pytest


class TestSettingsCaching:
    """Test LRU cache behavior for settings."""

    def test_settings_cached(self):
        """Test that settings are cached and return same instance."""
        from tinybase.config import get_settings

        settings1 = get_settings()
        settings2 = get_settings()

        # Should return the same instance
        assert settings1 is settings2

    def test_cache_clear(self):
        """Test that cache can be cleared."""
        from tinybase.config import get_settings

        settings1 = get_settings()

        # Clear cache
        get_settings.cache_clear()

        settings2 = get_settings()

        # Should return different instances after clear
        assert settings1 is not settings2

    def test_settings_wrapper(self):
        """Test that settings() wrapper works."""
        from tinybase.config import settings

        config = settings()
        assert config is not None
        assert hasattr(config, "server_host")
        assert hasattr(config, "server_port")

    def test_reload_settings(self):
        """Test that reload_settings clears cache and loads fresh."""
        from tinybase.config import get_settings, reload_settings

        settings1 = get_settings()

        # Reload should clear cache and return new instance
        settings2 = reload_settings()

        # Different instances
        assert settings1 is not settings2


class TestEnvironmentVariables:
    """Test environment variable configuration."""

    def test_env_var_precedence(self, monkeypatch):
        """Test that environment variables override defaults."""
        monkeypatch.setenv("TINYBASE_SERVER_PORT", "9000")

        from tinybase.config import reload_settings

        config = reload_settings()

        assert config.server_port == 9000

    def test_env_var_type_conversion(self, monkeypatch):
        """Test that environment variables are properly type-converted."""
        monkeypatch.setenv("TINYBASE_DEBUG", "true")
        monkeypatch.setenv("TINYBASE_MAX_FUNCTION_PAYLOAD_BYTES", "5242880")

        from tinybase.config import reload_settings

        config = reload_settings()

        assert config.debug is True
        assert config.max_function_payload_bytes == 5242880


class TestTomlConfiguration:
    """Test TOML file configuration."""

    def test_toml_loading(self):
        """Test loading configuration from TOML file."""
        from tinybase.config import load_toml_config

        with tempfile.TemporaryDirectory() as tmpdir:
            toml_path = Path(tmpdir) / "test.toml"
            toml_path.write_text(
                """
[server]
host = "127.0.0.1"
port = 9000

[database]
url = "sqlite:///test.db"
"""
            )

            config = load_toml_config(toml_path)

            assert config["server_host"] == "127.0.0.1"
            assert config["server_port"] == 9000
            assert config["database_url"] == "sqlite:///test.db"

    def test_missing_toml_file(self):
        """Test that missing TOML file returns empty dict."""
        from tinybase.config import load_toml_config

        config = load_toml_config(Path("/nonexistent/file.toml"))

        assert config == {}


class TestConfigDefaults:
    """Test default configuration values."""

    def test_server_defaults(self):
        """Test default server configuration."""
        from tinybase.config import get_settings

        get_settings.cache_clear()
        config = get_settings()

        assert config.server_host == "0.0.0.0"
        assert config.server_port == 8000
        assert config.debug is False
        assert config.log_level == "info"

    def test_auth_defaults(self):
        """Test default auth configuration."""
        from tinybase.config import get_settings

        get_settings.cache_clear()
        config = get_settings()

        assert config.auth_token_ttl_hours == 24

    def test_function_defaults(self):
        """Test default function configuration."""
        from tinybase.config import get_settings

        get_settings.cache_clear()
        config = get_settings()

        assert config.functions_path == "./functions"
        assert config.function_logging_enabled is True
        assert config.function_cold_start_pool_size == 3
        assert config.function_cold_start_ttl_seconds == 300


class TestFixtureCacheClearing:
    """Test that the autouse fixture clears cache properly."""

    def test_cache_cleared_between_tests_1(self, monkeypatch):
        """First test that sets an env var."""
        monkeypatch.setenv("TINYBASE_SERVER_PORT", "8888")

        from tinybase.config import reload_settings

        config = reload_settings()
        assert config.server_port == 8888

    def test_cache_cleared_between_tests_2(self):
        """Second test that should not see the previous env var."""
        from tinybase.config import get_settings

        config = get_settings()

        # Should be back to default (or whatever env has, but not 8888 from previous test)
        assert config.server_port == int(os.getenv("TINYBASE_SERVER_PORT", "8000"))
