"""
Configuration management for TinyBase.

Configuration is loaded from (in order of precedence):
1. Environment variables (TINYBASE_*)
2. tinybase.toml in the current working directory
3. Built-in defaults
"""

import sys
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Handle tomli import for Python < 3.11
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def load_toml_config(toml_path: Path | None = None) -> dict[str, Any]:
    """
    Load configuration from tinybase.toml file.
    
    Args:
        toml_path: Optional explicit path to TOML file.
                   If None, looks for tinybase.toml in current directory.
    
    Returns:
        Dictionary of configuration values (flattened for Pydantic settings).
    """
    if toml_path is None:
        toml_path = Path.cwd() / "tinybase.toml"
    
    if not toml_path.exists():
        return {}
    
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)
    
    # Flatten nested config into environment-variable-style keys
    # e.g., {"server": {"host": "0.0.0.0"}} -> {"server_host": "0.0.0.0"}
    result: dict[str, Any] = {}
    
    for section, values in data.items():
        if isinstance(values, dict):
            for key, value in values.items():
                # Convert to flat key format
                flat_key = f"{section}_{key}"
                result[flat_key] = value
        else:
            result[section] = values
    
    return result


class Settings(BaseSettings):
    """
    TinyBase application settings.
    
    Settings can be configured via:
    - Environment variables with TINYBASE_ prefix
    - tinybase.toml configuration file
    - Default values
    """
    
    model_config = SettingsConfigDict(
        env_prefix="TINYBASE_",
        env_nested_delimiter="_",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Server settings
    server_host: str = Field(default="0.0.0.0", description="Server bind host")
    server_port: int = Field(default=8000, description="Server bind port")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="info", description="Logging level")
    
    # Database settings
    db_url: str = Field(
        default="sqlite:///./tinybase.db",
        description="Database connection URL"
    )
    
    # Auth settings
    auth_token_ttl_hours: int = Field(
        default=24,
        description="Auth token time-to-live in hours"
    )
    
    # Functions settings
    functions_path: str = Field(
        default="./functions",
        description="Directory path for function modules"
    )
    functions_file: str = Field(
        default="./functions.py",
        description="Single file path for functions"
    )
    
    # Scheduler settings
    scheduler_enabled: bool = Field(
        default=True,
        description="Enable the background scheduler"
    )
    scheduler_interval_seconds: int = Field(
        default=5,
        description="Scheduler polling interval in seconds"
    )
    
    # CORS settings
    cors_allow_origins: list[str] = Field(
        default=["*"],
        description="CORS allowed origins"
    )
    
    # Admin settings
    admin_static_dir: str = Field(
        default="builtin",
        description="Path to admin UI static files, or 'builtin' for packaged assets"
    )
    admin_email: str | None = Field(
        default=None,
        description="Default admin email for bootstrap"
    )
    admin_password: str | None = Field(
        default=None,
        description="Default admin password for bootstrap"
    )
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is valid."""
        valid_levels = {"debug", "info", "warning", "error", "critical"}
        if v.lower() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.lower()
    
    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            # Handle comma-separated string from env var
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


def get_settings(toml_path: Path | None = None) -> Settings:
    """
    Load and return application settings.
    
    This function loads settings from environment variables and
    optionally from a tinybase.toml file.
    
    Args:
        toml_path: Optional path to TOML configuration file.
    
    Returns:
        Configured Settings instance.
    """
    # Load TOML config first
    toml_config = load_toml_config(toml_path)
    
    # Create settings with TOML values as defaults
    # Environment variables will override TOML values
    return Settings(**toml_config)


# Global settings instance (lazy loaded)
_settings: Settings | None = None


def settings() -> Settings:
    """Get the global settings instance, creating it if needed."""
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings


def reload_settings(toml_path: Path | None = None) -> Settings:
    """Reload settings from configuration sources."""
    global _settings
    _settings = get_settings(toml_path)
    return _settings

