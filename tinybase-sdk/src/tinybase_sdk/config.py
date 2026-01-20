"""
Configuration management for TinyBase SDK.

Handles reading deployment configuration from environment variables and config files.
"""

import os
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback for Python 3.10


@dataclass
class DeploymentConfig:
    """Configuration for deploying functions to TinyBase."""

    api_url: str
    api_token: str
    functions_dir: Path = Path("./functions")
    timeout: float = 30.0


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""

    pass


def load_deployment_config(env: str = "production") -> DeploymentConfig:
    """
    Load deployment configuration from environment or tinybase.toml.

    Priority (highest to lowest):
    1. Environment variables (TINYBASE_API_URL, TINYBASE_API_TOKEN)
    2. tinybase.toml file in current directory
    3. ~/.config/tinybase/config.toml

    Args:
        env: Environment name to load from config file (e.g., "production", "staging")

    Returns:
        DeploymentConfig with API URL and token

    Raises:
        ConfigurationError: If required configuration is missing
    """
    # Try environment variables first
    api_url = os.getenv("TINYBASE_API_URL")
    api_token = os.getenv("TINYBASE_API_TOKEN")

    if api_url and api_token:
        functions_dir = Path(os.getenv("TINYBASE_FUNCTIONS_DIR", "./functions"))
        timeout = float(os.getenv("TINYBASE_TIMEOUT", "30.0"))
        return DeploymentConfig(
            api_url=api_url,
            api_token=api_token,
            functions_dir=functions_dir,
            timeout=timeout,
        )

    # Try local tinybase.toml
    config_path = Path.cwd() / "tinybase.toml"
    if not config_path.exists():
        # Try user config directory
        config_path = Path.home() / ".config" / "tinybase" / "config.toml"

    if config_path.exists():
        try:
            with open(config_path, "rb") as f:
                config_data = tomllib.load(f)

            # Look for environment-specific config
            env_config = config_data.get("environments", {}).get(env)
            if not env_config:
                raise ConfigurationError(
                    f"Environment '{env}' not found in {config_path}. "
                    f"Available: {list(config_data.get('environments', {}).keys())}"
                )

            api_url = env_config.get("api_url")
            api_token = env_config.get("api_token")

            if not api_url:
                raise ConfigurationError(
                    f"Missing 'api_url' for environment '{env}' in {config_path}"
                )

            if not api_token:
                raise ConfigurationError(
                    f"Missing 'api_token' for environment '{env}' in {config_path}"
                )

            # Get functions directory from general config or use default
            functions_dir = Path(config_data.get("functions_path", "./functions"))
            timeout = float(env_config.get("timeout", 30.0))

            return DeploymentConfig(
                api_url=api_url,
                api_token=api_token,
                functions_dir=functions_dir,
                timeout=timeout,
            )
        except ConfigurationError:
            raise
        except Exception as e:
            raise ConfigurationError(f"Failed to parse {config_path}: {e}") from e

    # No configuration found
    raise ConfigurationError(
        "No deployment configuration found. Please either:\n"
        "1. Set TINYBASE_API_URL and TINYBASE_API_TOKEN environment variables, or\n"
        "2. Create a tinybase.toml file with environment configuration:\n\n"
        "[environments.production]\n"
        'api_url = "https://your-api.tinybase.com"\n'
        'api_token = "your-admin-token"\n'
    )


def get_functions_dir() -> Path:
    """
    Get the functions directory path.

    Returns:
        Path to functions directory
    """
    # Check environment variable
    if env_dir := os.getenv("TINYBASE_FUNCTIONS_DIR"):
        return Path(env_dir)

    # Check tinybase.toml
    config_path = Path.cwd() / "tinybase.toml"
    if config_path.exists():
        try:
            with open(config_path, "rb") as f:
                config_data = tomllib.load(f)
            if functions_path := config_data.get("functions_path"):
                return Path(functions_path)
        except Exception:
            pass

    # Default
    return Path("./functions")
