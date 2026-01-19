"""
Configuration management for TinyBase.

Configuration is loaded from (in order of precedence):
1. Environment variables (TINYBASE_*)
2. tinybase.toml in the current working directory
3. Built-in defaults
"""

import sys
from functools import lru_cache
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
    db_url: str = Field(default="sqlite:///./tinybase.db", description="Database connection URL")

    # Auth settings
    auth_token_ttl_hours: int = Field(default=24, description="Auth token time-to-live in hours")

    # Functions settings
    functions_path: str = Field(
        default="./functions",
        description="Directory path for function modules (must be a Python package)",
    )
    function_logging_enabled: bool = Field(
        default=True, description="Enable structured logging for functions"
    )
    function_logging_level: str = Field(
        default="INFO",
        description="Default logging level for functions (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    function_logging_format: str = Field(
        default="json",
        description="Logging format: 'json' for structured logs, 'text' for human-readable",
    )
    function_cold_start_pool_size: int = Field(
        default=3,
        ge=0,
        description="Number of warm function processes to keep in pool (0 = disabled)",
    )
    function_cold_start_ttl_seconds: int = Field(
        default=300,
        ge=0,
        description="Time to keep warm processes alive after last use (0 = disabled)",
    )

    # Resource limits
    max_function_payload_bytes: int = Field(
        default=10_485_760,  # 10 MB
        ge=1024,  # Min 1 KB
        description="Maximum payload size for function calls in bytes",
    )
    max_function_result_bytes: int = Field(
        default=10_485_760,  # 10 MB
        ge=1024,
        description="Maximum result size from functions in bytes",
    )
    max_concurrent_functions_per_user: int = Field(
        default=10,
        ge=1,
        description="Maximum concurrent function executions per user",
    )

    # Scheduler settings
    scheduler_enabled: bool = Field(default=True, description="Enable the background scheduler")
    scheduler_interval_seconds: int = Field(
        default=5, description="Scheduler polling interval in seconds"
    )
    scheduler_token_cleanup_interval: int = Field(
        default=60,
        ge=1,
        description="Token cleanup interval in scheduler ticks (e.g., 60 = every 60 scheduler intervals)",
    )
    scheduler_function_timeout_seconds: int = Field(
        default=1800,
        ge=1,
        description="Maximum execution time for scheduled functions in seconds (default: 30 minutes)",
    )
    scheduler_max_schedules_per_tick: int = Field(
        default=100, ge=1, description="Maximum number of schedules to process per scheduler tick"
    )
    scheduler_max_concurrent_executions: int = Field(
        default=10, ge=1, description="Maximum number of schedules to execute concurrently"
    )

    # CORS settings
    cors_allow_origins: list[str] = Field(default=["*"], description="CORS allowed origins")

    # Admin settings
    admin_static_dir: str = Field(
        default="builtin",
        description="Path to admin UI static files, or 'builtin' for packaged assets",
    )
    admin_email: str | None = Field(default=None, description="Default admin email for bootstrap")
    admin_password: str | None = Field(
        default=None, description="Default admin password for bootstrap"
    )

    # Extensions settings
    extensions_enabled: bool = Field(default=True, description="Enable the extension system")
    extensions_path: str = Field(
        default="~/.tinybase/extensions", description="Directory path for installed extensions"
    )

    # Email settings
    email_enabled: bool = Field(default=False, description="Enable email sending")
    email_smtp_host: str | None = Field(default=None, description="SMTP server hostname")
    email_smtp_port: int = Field(default=587, description="SMTP server port")
    email_smtp_user: str | None = Field(default=None, description="SMTP username")
    email_smtp_password: str | None = Field(default=None, description="SMTP password")
    email_from_address: str | None = Field(default=None, description="From email address")
    email_from_name: str = Field(default="TinyBase", description="From name for emails")

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


@lru_cache(maxsize=1)
def get_settings(toml_path: Path | None = None) -> Settings:
    """
    Load and return cached application settings.

    Uses lru_cache for singleton behavior while remaining testable.
    Tests can clear cache with get_settings.cache_clear().

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


def settings() -> Settings:
    """Get the cached settings instance."""
    return get_settings()


def reload_settings(toml_path: Path | None = None) -> Settings:
    """Reload settings by clearing cache and loading fresh."""
    get_settings.cache_clear()
    return get_settings(toml_path)
