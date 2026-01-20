"""
TinyBase SDK for serverless functions.

Provides decorators, client, and CLI runner for TinyBase functions.
"""

from tinybase_sdk.cli import run
from tinybase_sdk.config import ConfigurationError, DeploymentConfig, load_deployment_config
from tinybase_sdk.decorator import register
from tinybase_sdk.deployment import DeploymentClient, DeploymentError, DeploymentResult
from tinybase_sdk.logging import StructuredLogger

__all__ = [
    "register",
    "run",
    "StructuredLogger",
    "DeploymentClient",
    "DeploymentResult",
    "DeploymentError",
    "DeploymentConfig",
    "load_deployment_config",
    "ConfigurationError",
]
