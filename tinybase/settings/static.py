"""
File-based configuration. Loaded once at startup from environment variables.

Usage:
    from tinybase.settings import config
    
    host = config.server_host
    debug = config.debug
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Handle tomli import for Python < 3.11
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def _load_toml(toml_path: Path | None = None) -> dict[str, Any]:
    """Load and flatten configuration from tinybase.toml."""
    if toml_path is None:
        toml_path = Path.cwd() / "tinybase.toml"

    if not toml_path.exists():
        return {}

    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    # Flatten nested config: {"server": {"host": "0.0.0.0"}} -> {"server_host": "0.0.0.0"}
    result: dict[str, Any] = {}
    for section, values in data.items():
        if isinstance(values, dict):
            for key, value in values.items():
                result[f"{section}_{key}"] = value
        else:
            result[section] = values

    return result


class Config(BaseSettings):
    """
    Static configuration from environment variables and TOML file.
    
    These settings require a server restart to take effect.
    Environment variables (TINYBASE_*) override TOML values.
    """

    model_config = SettingsConfigDict(
        env_prefix="TINYBASE_",
        env_nested_delimiter="_",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Server
    # -------------------------------------------------------------------------
    server_host: str = Field(default="0.0.0.0", description="Server bind host")
    server_port: int = Field(default=8000, description="Server bind port")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="info", description="Logging level")

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------
    db_url: str = Field(
        default="sqlite:///./tinybase.db", description="Database connection URL"
    )

    # -------------------------------------------------------------------------
    # Auth / JWT
    # -------------------------------------------------------------------------
    auth_token_ttl_hours: int = Field(
        default=24, description="Auth token time-to-live in hours"
    )
    jwt_secret_key: str | None = Field(
        default=None,
        description="Secret key for JWT signing (auto-generated if not provided)",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    jwt_access_token_expire_minutes: int = Field(
        default=1440, description="Access token TTL in minutes (default: 24 hours)"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=30, description="Refresh token TTL in days"
    )

    # -------------------------------------------------------------------------
    # Functions
    # -------------------------------------------------------------------------
    functions_dir: str = Field(
        default="./functions",
        description="Directory for function modules",
    )
    function_logging_enabled: bool = Field(
        default=True, description="Enable structured logging for functions"
    )
    function_logging_level: str = Field(
        default="INFO",
        description="Logging level for functions (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    function_logging_format: str = Field(
        default="json",
        description="Logging format: 'json' for structured, 'text' for human-readable",
    )
    function_cold_start_pool_size: int = Field(
        default=3,
        ge=0,
        description="Number of warm function processes to keep in pool (0 = disabled)",
    )
    function_cold_start_ttl_seconds: int = Field(
        default=300,
        ge=0,
        description="Time to keep warm processes alive after last use",
    )

    # -------------------------------------------------------------------------
    # Resource Limits
    # -------------------------------------------------------------------------
    max_function_payload_bytes: int = Field(
        default=10_485_760,
        ge=1024,
        description="Maximum payload size for function calls in bytes",
    )
    max_function_result_bytes: int = Field(
        default=10_485_760,
        ge=1024,
        description="Maximum result size from functions in bytes",
    )

    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------
    rate_limit_backend: str = Field(
        default="diskcache",
        description="Rate limiting backend: 'diskcache' or 'redis'",
    )
    rate_limit_cache_dir: str = Field(
        default="./.tinybase/rate_limit_cache",
        description="Directory for DiskCache rate limiting",
    )
    rate_limit_redis_url: str | None = Field(
        default=None,
        description="Redis URL for rate limiting (required when backend=redis)",
    )

    # -------------------------------------------------------------------------
    # Scheduler
    # -------------------------------------------------------------------------
    scheduler_enabled: bool = Field(
        default=True, description="Enable the background scheduler"
    )
    scheduler_interval_seconds: int = Field(
        default=5, description="Scheduler polling interval in seconds"
    )

    # -------------------------------------------------------------------------
    # CORS
    # -------------------------------------------------------------------------
    cors_allow_origins: list[str] = Field(
        default=["*"], description="CORS allowed origins"
    )

    # -------------------------------------------------------------------------
    # Admin
    # -------------------------------------------------------------------------
    admin_static_dir: str = Field(
        default="builtin",
        description="Path to admin UI static files, or 'builtin' for packaged assets",
    )
    admin_email: str | None = Field(
        default=None, description="Default admin email for bootstrap"
    )
    admin_password: str | None = Field(
        default=None, description="Default admin password for bootstrap"
    )

    # -------------------------------------------------------------------------
    # Extensions
    # -------------------------------------------------------------------------
    extensions_enabled: bool = Field(
        default=True, description="Enable the extension system"
    )
    extensions_dir: str = Field(
        default="./.tinybase/extensions",
        description="Directory for installed extensions (workspace-local)",
    )

    # -------------------------------------------------------------------------
    # Static Files
    # -------------------------------------------------------------------------
    serve_static_files: str | None = Field(
        default=None,
        description="Path to user static files directory (must contain index.html). "
        "When set, files will be served at the root path /",
    )

    # -------------------------------------------------------------------------
    # Email
    # -------------------------------------------------------------------------
    email_enabled: bool = Field(default=False, description="Enable email sending")
    email_smtp_host: str | None = Field(default=None, description="SMTP server hostname")
    email_smtp_port: int = Field(default=587, description="SMTP server port")
    email_smtp_user: str | None = Field(default=None, description="SMTP username")
    email_smtp_password: str | None = Field(default=None, description="SMTP password")
    email_from_address: str | None = Field(default=None, description="From email address")
    email_from_name: str = Field(default="TinyBase", description="From name for emails")

    # -------------------------------------------------------------------------
    # Validators
    # -------------------------------------------------------------------------

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"debug", "info", "warning", "error", "critical"}
        if v.lower() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.lower()

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, v: str | None) -> str:
        if v is None:
            import secrets

            return secrets.token_urlsafe(32)
        return v

    @field_validator("rate_limit_backend")
    @classmethod
    def validate_rate_limit_backend(cls, v: str) -> str:
        valid_backends = {"diskcache", "redis"}
        if v not in valid_backends:
            raise ValueError(f"rate_limit_backend must be one of {valid_backends}")
        return v

    @field_validator("rate_limit_redis_url")
    @classmethod
    def validate_rate_limit_redis_url(
        cls, v: str | None, info: ValidationInfo
    ) -> str | None:
        if info.data.get("rate_limit_backend") == "redis" and not v:
            raise ValueError(
                "rate_limit_redis_url is required when rate_limit_backend is 'redis'"
            )
        return v

    def __init__(self, **kwargs: Any) -> None:
        """Initialize config, loading TOML if available."""
        toml_config = _load_toml()
        # Merge TOML config with kwargs (kwargs take precedence)
        merged = {**toml_config, **kwargs}
        super().__init__(**merged)


config = Config()  # Singleton instance


def _reset_config() -> "Config":
    """
    Reset the config singleton (for testing only).
    
    Creates a new Config instance with fresh environment variables.
    Returns the new config instance (since imports may be cached).
    """
    global config
    config = Config()
    return config
