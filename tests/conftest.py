"""
ABOUTME: Pytest configuration and shared fixtures
ABOUTME: Provides common test fixtures and mock data for all tests
"""

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from rich.console import Console

from anomaly_detector import CacheManager, SleepAnomalyDetector


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_console():
    """Provide a mock Rich console for testing."""
    return MagicMock(spec=Console)


@pytest.fixture
def test_env_vars():
    """Provide test environment variables."""
    return {
        "IFOREST_CONTAM": "0.05",
        "IFOREST_TRAIN_WINDOW": "30",
        "IFOREST_SHOW_N": "3",
        "EMFIT_TOKEN": "test_token",
        "EMFIT_DEVICE_ID": "test_device_123",
        "EMFIT_CACHE_DIR": "./test_cache",
        "EMFIT_CACHE_ENABLED": "true",
        "EMFIT_CACHE_TTL_HOURS": "24",
        "OPENAI_API_KEY": "test_openai_key",
        "PUSHOVER_APIKEY": "test_pushover_token",
        "PUSHOVER_USERKEY": "test_pushover_user",
    }


@pytest.fixture
def mock_env_vars(test_env_vars):
    """Mock environment variables for testing."""
    with patch.dict(os.environ, test_env_vars, clear=False):
        yield test_env_vars


@pytest.fixture
def cache_manager(temp_dir):
    """Provide a CacheManager instance for testing."""
    return CacheManager(temp_dir / "cache", ttl_hours=1)


@pytest.fixture
def detector_instance(mock_console, mock_env_vars):
    """Provide a SleepAnomalyDetector instance for testing."""
    return SleepAnomalyDetector(mock_console)


@pytest.fixture
def sample_sleep_data():
    """Provide sample sleep data for testing."""
    dates = [datetime.now() - timedelta(days=i) for i in range(10, 0, -1)]
    return pd.DataFrame(
        {
            "date": dates,
            "hr": [65, 68, 62, 70, 72, 66, 64, 69, 71, 67],
            "rr": [14.5, 15.2, 14.1, 15.8, 16.1, 14.7, 14.3, 15.5, 15.9, 14.9],
            "sleep_dur": [7.5, 8.2, 7.1, 8.5, 8.8, 7.7, 7.3, 8.1, 8.6, 7.9],
            "score": [85, 88, 82, 90, 92, 86, 83, 89, 91, 87],
            "tnt": [12, 8, 15, 6, 4, 10, 14, 7, 5, 9],
        }
    )


@pytest.fixture
def mock_emfit_api():
    """Provide a mock Emfit API for testing."""
    mock_api = MagicMock()
    mock_api.get_user.return_value = {
        "device_settings": [
            {"device_id": "123", "device_name": "Test Device 1"},
            {"device_id": "456", "device_name": "Test Device 2"},
        ]
    }
    mock_api.get_trends.return_value = {
        "data": [
            {
                "date": "2024-01-15",
                "meas_hr_avg": 68.5,
                "meas_rr_avg": 15.2,
                "sleep_duration": 8.1,
                "sleep_score": 87,
                "tossnturn_count": 8,
            }
        ]
    }
    return mock_api


@pytest.fixture
def mock_openai_client():
    """Provide a mock OpenAI client for testing."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[
        0
    ].message.content = "This anomaly appears to be caused by elevated heart rate and poor sleep quality, suggesting possible illness or stress."
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def sample_features():
    """Fixture for sample feature matrix for ML testing."""
    import numpy as np

    np.random.seed(42)  # Set seed for reproducible tests
    return np.random.rand(20, 4)  # 20 samples, 4 features
