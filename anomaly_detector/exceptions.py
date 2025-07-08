"""
ABOUTME: Custom exception classes for Emfit anomaly detection
ABOUTME: Provides specific error types for configuration, API, and data processing issues
"""


class ConfigError(Exception):
    """Configuration validation error."""

    pass


class APIError(Exception):
    """Emfit API related error."""

    pass


class DataError(Exception):
    """Data processing error."""

    pass
