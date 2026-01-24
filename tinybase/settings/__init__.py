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

from tinybase.settings.static import config, Config
from tinybase.settings.core import settings, Settings

__all__ = ["config", "Config", "settings", "Settings"]
