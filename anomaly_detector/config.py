"""
ABOUTME: Environment variable configuration utilities
ABOUTME: Provides type-safe loading and validation of configuration from environment variables
"""

import os

from .exceptions import ConfigError


def get_env_var(
    key: str, default: str | None = None, required: bool = False
) -> str | None:
    """Get environment variable with validation."""
    value = os.getenv(key, default)
    if required and not value:
        raise ConfigError(f"Required environment variable '{key}' not set")
    return value


def get_env_int(key: str, default: int) -> int:
    """Get integer environment variable with validation."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError as e:
        raise ConfigError(f"Invalid integer value for '{key}': {os.getenv(key)}") from e


def get_env_float(key: str, default: float) -> float:
    """Get float environment variable with validation."""
    try:
        return float(os.getenv(key, str(default)))
    except ValueError as e:
        raise ConfigError(f"Invalid float value for '{key}': {os.getenv(key)}") from e
