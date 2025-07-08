"""
Pytest configuration and shared fixtures for plugins_eight tests.
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch

# Add source directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def mock_plugins_eight():
    """Fixture providing a mock plugins_eight module"""
    with patch('plugins_eight') as mock_module:
        mock_module.configure_mock(**{
            'initialize.return_value': True,
            'process.return_value': 'processed',
            'cleanup.return_value': None
        })
        yield mock_module


@pytest.fixture
def sample_data():
    """Fixture providing sample test data"""
    return {
        'string_data': 'test_string',
        'numeric_data': 42,
        'list_data': [1, 2, 3, 4, 5],
        'dict_data': {'key1': 'value1', 'key2': 'value2'},
        'boolean_data': True,
        'none_data': None
    }


@pytest.fixture
def temp_directory(tmp_path):
    """Fixture providing a temporary directory for file operations"""
    return tmp_path


@pytest.fixture(autouse=True)
def reset_environment():
    """Auto-use fixture to reset environment between tests"""
    # Store original environment
    original_env = dict(os.environ)
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture(scope="session")
def session_data():
    """Session-scoped fixture for data that persists across tests"""
    return {
        'session_id': 'test_session_123',
        'start_time': '2023-01-01T00:00:00Z'
    }


# Pytest markers for test categorization
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "security: marks tests as security-related"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance-related"
    )


# Custom pytest hooks
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names"""
    for item in items:
        # Add markers based on test names
        if "performance" in item.name or "benchmark" in item.name:
            item.add_marker(pytest.mark.performance)
        
        if "security" in item.name:
            item.add_marker(pytest.mark.security)
        
        if "integration" in item.name:
            item.add_marker(pytest.mark.integration)
        elif "test_" in item.name:
            item.add_marker(pytest.mark.unit)


# Error handling for missing dependencies
def pytest_runtest_setup(item):
    """Setup hook to handle missing dependencies"""
    # Check for required dependencies
    try:
        import plugins_eight
    except ImportError:
        pytest.skip("plugins_eight module not available")
