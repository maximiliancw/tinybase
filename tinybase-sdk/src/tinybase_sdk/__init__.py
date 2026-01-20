"""
TinyBase SDK for serverless functions.

Provides decorators, client, and runtime for TinyBase functions.
Also includes deployment helpers for use by the TinyBase CLI.
"""

from tinybase_sdk.cli import run
from tinybase_sdk.config import ConfigurationError, DeploymentConfig, load_deployment_config
from tinybase_sdk.decorator import register
from tinybase_sdk.deployment import DeploymentClient, DeploymentError, DeploymentResult
from tinybase_sdk.logging import StructuredLogger

__version__ = "0.3.0"

__all__ = [
    # Function runtime
    "register",
    "run",
    "StructuredLogger",
    # Deployment (used by TinyBase CLI)
    "DeploymentClient",
    "DeploymentResult",
    "DeploymentError",
    "DeploymentConfig",
    "load_deployment_config",
    "ConfigurationError",
]
