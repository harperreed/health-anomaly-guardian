"""
ABOUTME: Tests for the Eight Sleep tracker plugin
ABOUTME: Tests Eight Sleep-specific functionality and placeholder implementation
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import pandas as pd
from rich.console import Console

from anomaly_detector.plugins.eight import EightPlugin, _EightSleepAPIStub
from anomaly_detector.exceptions import APIError, ConfigError, DataError
from anomaly_detector.cache import CacheManager


class TestEightPlugin:
    """Test the Eight Sleep plugin functionality."""
    
    def setup_method(self):
        """
        Initializes the test environment by setting up a console, mocking environment variables, and instantiating the Eight Sleep plugin with these mocks.
        """
        self.console = Console()
        
        # Mock environment variables
        self.env_vars = {
            'EIGHT_USERNAME': 'test_user',
            'EIGHT_PASSWORD': 'test_pass',
            'EIGHT_DEVICE_ID': 'test_device_123',
            'EIGHT_USER_ID': 'test_user_456'
        }
        
        with patch('anomaly_detector.plugins.eight.get_env_var', side_effect=lambda key, default=None: self.env_vars.get(key, default)):
            self.plugin = EightPlugin(self.console)
    
    def test_plugin_initialization(self):
        """Test plugin initializes with correct name and configuration."""
        assert self.plugin.name == "eightplugin"
        assert self.plugin.console == self.console
        assert self.plugin.username == 'test_user'
        assert self.plugin.password == 'test_pass'
        assert self.plugin.device_id == 'test_device_123'
        assert self.plugin.user_id == 'test_user_456'
    
    def test_notification_title(self):
        """
        Verifies that the plugin's notification title property returns the expected alert string.
        """
        assert self.plugin.notification_title == "Eight Sleep Anomaly Alert"
    
    def test_cache_key_generation(self):
        """
        Tests that the plugin's cache key generation method returns a key prefixed with the plugin name, device ID, and date string.
        """
        device_id = "test_device"
        date_str = "2024-01-01"
        
        cache_key = self.plugin._get_cache_key(device_id, date_str)
        
        assert cache_key == f"eightplugin_{device_id}_{date_str}"
    
    def test_get_api_client_with_credentials(self):
        """
        Verify that the API client is correctly initialized with the provided username and password credentials.
        """
        api_client = self.plugin.get_api_client()
        
        assert isinstance(api_client, _EightSleepAPIStub)
        assert api_client.username == 'test_user'
        assert api_client.password == 'test_pass'
    
    def test_get_api_client_no_username(self):
        """
        Test that initializing the API client without a username raises an APIError indicating missing credentials.
        """
        self.plugin.username = None
        
        with pytest.raises(APIError, match="EIGHT_USERNAME and EIGHT_PASSWORD environment variables must be set"):
            self.plugin.get_api_client()
    
    def test_get_api_client_no_password(self):
        """
        Test that initializing the API client without a password raises an APIError indicating missing credentials.
        """
        self.plugin.password = None
        
        with pytest.raises(APIError, match="EIGHT_USERNAME and EIGHT_PASSWORD environment variables must be set"):
            self.plugin.get_api_client()
    
    def test_get_device_ids_with_config(self):
        """
        Test that device IDs and names are correctly retrieved when a device ID is configured and auto-discovery is disabled.
        """
        device_ids, device_names = self.plugin.get_device_ids(auto_discover=False)
        
        assert device_ids == ['test_device_123']
        assert device_names == {'test_device_123': 'Eight Sleep Pod (test_device_123)'}
    
    def test_get_device_ids_auto_discovery(self):
        """
        Test that device IDs are correctly retrieved using auto-discovery when no device ID is configured.
        
        Verifies that enabling auto-discovery returns the default device ID and name.
        """
        self.plugin.device_id = None
        
        device_ids, device_names = self.plugin.get_device_ids(auto_discover=True)
        
        assert device_ids == ['eight-pod-default']
        assert device_names == {'eight-pod-default': 'Eight Sleep Pod'}
    
    def test_get_device_ids_no_config_no_discovery(self):
        """
        Test that retrieving device IDs without configuration and with auto-discovery disabled raises a ConfigError.
        """
        self.plugin.device_id = None
        
        with pytest.raises(ConfigError, match="No Eight Sleep device ID found"):
            self.plugin.get_device_ids(auto_discover=False)
    
    def test_fetch_data_placeholder(self):
        """
        Test that the placeholder fetch_data method raises a DataError when no valid data is found in the cache.
        """
        cache = Mock()
        cache.get.return_value = None
        cache.get_stats.return_value = {'valid_files': 0}
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        # Should raise DataError since it's a placeholder
        with pytest.raises(DataError, match="No valid Eight Sleep data found"):
            self.plugin.fetch_data('test_device', start_date, end_date, cache)
    
    def test_discover_devices(self):
        """
        Tests that the device discovery method completes without raising exceptions.
        """
        # Should not raise any exceptions
        self.plugin.discover_devices()


class TestEightSleepAPIStub:
    """Test the Eight Sleep API stub functionality."""
    
    def setup_method(self):
        """
        Set up the API stub instance for each test method.
        """
        self.api_stub = _EightSleepAPIStub("test_user", "test_pass")
    
    def test_initialization(self):
        """
        Verify that the API stub is initialized with the correct username and password.
        """
        assert self.api_stub.username == "test_user"
        assert self.api_stub.password == "test_pass"
    
    def test_get_devices(self):
        """
        Tests that the API stub returns a list containing the default Eight Sleep device with the expected device ID and name.
        """
        devices = self.api_stub.get_devices()
        
        assert isinstance(devices, list)
        assert len(devices) == 1
        assert devices[0]["device_id"] == "eight-pod-default"
        assert devices[0]["name"] == "Eight Sleep Pod"
    
    def test_get_sleep_session(self):
        """
        Tests that retrieving a sleep session with the API stub returns None, reflecting the placeholder implementation.
        """
        sleep_data = self.api_stub.get_sleep_session("device_id", "2024-01-01")
        
        assert sleep_data is None  # Placeholder implementation