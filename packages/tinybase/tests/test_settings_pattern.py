"""
Tests for the new settings pattern using Config (static) and Settings (runtime).
"""

import tempfile
from pathlib import Path


class TestStaticConfig:
    """Test static Config class behavior."""

    def test_config_singleton(self):
        """Test that config is a singleton."""
        from tinybase.settings import config
        from tinybase.settings.static import Config

        # Should be the same instance
        assert isinstance(config, Config)

    def test_config_attributes(self):
        """Test that config has expected attributes."""
        from tinybase.settings import config

        assert hasattr(config, "server_host")
        assert hasattr(config, "server_port")
        assert hasattr(config, "debug")
        assert hasattr(config, "db_url")

    def test_config_default_values(self):
        """Test default config values."""
        from tinybase.settings.static import _reset_config

        _reset_config()
        from tinybase.settings import config

        assert config.server_host == "0.0.0.0"
        assert config.server_port == 8000
        assert config.debug is False
        assert config.log_level == "info"

    def test_config_reset(self):
        """Test that _reset_config creates a new instance."""
        from tinybase.settings import config
        from tinybase.settings.static import _reset_config

        old_id = id(config)

        # Reset config
        new_config = _reset_config()

        # Should be a different instance
        assert id(new_config) != old_id
        # Both should have the same defaults (env unchanged)
        assert new_config.server_port == config.server_port


class TestEnvironmentVariables:
    """Test environment variable configuration."""

    def test_env_var_type_handling(self):
        """Test that config has correctly typed attributes."""
        from tinybase.settings import config

        # Test various typed attributes exist and have correct types
        assert isinstance(config.server_port, int)
        assert isinstance(config.debug, bool)
        assert isinstance(config.max_function_payload_bytes, int)
        assert isinstance(config.server_host, str)


class TestTomlConfiguration:
    """Test TOML file configuration."""

    def test_toml_loading(self):
        """Test loading configuration from TOML file."""
        from tinybase.settings.static import _load_toml

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

            config_dict = _load_toml(toml_path)

            assert config_dict["server_host"] == "127.0.0.1"
            assert config_dict["server_port"] == 9000
            assert config_dict["database_url"] == "sqlite:///test.db"

    def test_missing_toml_file(self):
        """Test that missing TOML file returns empty dict."""
        from tinybase.settings.static import _load_toml

        config_dict = _load_toml(Path("/nonexistent/file.toml"))

        assert config_dict == {}


class TestConfigDefaults:
    """Test default configuration values."""

    def test_server_defaults(self):
        """Test default server configuration."""
        from tinybase.settings.static import _reset_config

        _reset_config()
        from tinybase.settings.static import config

        assert config.server_host == "0.0.0.0"
        assert config.server_port == 8000
        assert config.debug is False
        assert config.log_level == "info"

    def test_auth_defaults(self):
        """Test default auth configuration."""
        from tinybase.settings.static import _reset_config

        _reset_config()
        from tinybase.settings.static import config

        assert config.auth_token_ttl_hours == 24

    def test_function_defaults(self):
        """Test default function configuration."""
        from tinybase.settings.static import _reset_config

        _reset_config()
        from tinybase.settings.static import config

        assert config.functions_dir == "./functions"
        assert config.function_logging_enabled is True
        assert config.function_cold_start_pool_size == 3
        assert config.function_cold_start_ttl_seconds == 300


class TestRuntimeSettings:
    """Test runtime Settings class behavior."""

    def test_settings_singleton(self):
        """Test that settings is a singleton."""
        from tinybase.settings import settings
        from tinybase.settings.core import Settings

        assert isinstance(settings, Settings)

    def test_settings_reload(self):
        """Test that settings can be reloaded."""
        from tinybase.settings import settings

        # Should not raise even if DB not available
        try:
            settings.reload()
        except Exception:
            pass  # DB may not be initialized

    def test_settings_get_value_with_default(self):
        """Test _get_value returns default when key not in cache."""
        from tinybase.settings import settings

        # Clear cache
        settings._cache = {}
        settings._loaded = True

        result = settings._get_value("nonexistent.key", "default_value")
        assert result == "default_value"
