"""
Settings package - provides both file-based config and database-backed settings.

Usage:
    from tinybase.settings import config, settings

    # Static config (env vars)
    config.server_host
    config.db_url

    # Runtime settings (database)
    settings.instance_name          # Returns "TinyBase" (str)
    settings.storage.enabled        # Returns False (bool)
    settings.get("ext.foo.bar")     # Returns AppSetting | None
"""

from tinybase.settings import static as _static_module
from tinybase.settings.core import Settings, settings

# Re-export Config class directly
Config = _static_module.Config

# Dynamic access to config singleton - always returns current instance
# This allows _reset_config() to work correctly in tests
def __getattr__(name: str):
    if name == "config":
        return _static_module.config
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["config", "Config", "settings", "Settings"]
