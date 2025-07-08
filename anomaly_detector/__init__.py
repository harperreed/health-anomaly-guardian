"""
ABOUTME: Sleep anomaly detection package for identifying unusual patterns in sleep data
ABOUTME: Provides modular components for configuration, caching, detection, and reporting
"""

from .cache import CacheManager
from .detector import SleepAnomalyDetector
from .exceptions import APIError, ConfigError, DataError

__version__ = "0.1.0"
__all__ = [
    "SleepAnomalyDetector",
    "CacheManager",
    "ConfigError",
    "APIError",
    "DataError",
]
