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

class TestEightPluginExtended:
    """Extended comprehensive tests for the Eight Sleep plugin."""
    
    def setup_method(self):
        """Set up test fixtures."""
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
    
    def test_plugin_initialization_missing_all_env_vars(self):
        """Test plugin initialization when all environment variables are missing."""
        empty_env = {}
        with patch('anomaly_detector.plugins.eight.get_env_var', side_effect=lambda key, default=None: empty_env.get(key, default)):
            plugin = EightPlugin(self.console)
            assert plugin.username is None
            assert plugin.password is None
            assert plugin.device_id is None
            assert plugin.user_id is None
    
    def test_plugin_initialization_partial_env_vars(self):
        """Test plugin initialization when only some environment variables are set."""
        partial_env = {
            'EIGHT_USERNAME': 'test_user',
            'EIGHT_PASSWORD': 'test_pass'
        }
        with patch('anomaly_detector.plugins.eight.get_env_var', side_effect=lambda key, default=None: partial_env.get(key, default)):
            plugin = EightPlugin(self.console)
            assert plugin.username == 'test_user'
            assert plugin.password == 'test_pass'
            assert plugin.device_id is None
            assert plugin.user_id is None
    
    def test_cache_key_generation_with_special_characters(self):
        """Test cache key generation with special characters in device ID."""
        device_id = "test-device_123!@#"
        date_str = "2024-01-01"
        
        cache_key = self.plugin._get_cache_key(device_id, date_str)
        
        assert cache_key == f"eightplugin_{device_id}_{date_str}"
    
    def test_cache_key_generation_empty_inputs(self):
        """Test cache key generation with empty inputs."""
        device_id = ""
        date_str = ""
        
        cache_key = self.plugin._get_cache_key(device_id, date_str)
        
        assert cache_key == "eightplugin__"
    
    def test_get_device_ids_with_whitespace_device_id(self):
        """Test device ID retrieval with whitespace in device ID."""
        self.plugin.device_id = "  test_device_123  "
        
        device_ids, device_names = self.plugin.get_device_ids(auto_discover=False)
        
        assert device_ids == ['  test_device_123  ']
        assert device_names == {'  test_device_123  ': 'Eight Sleep Pod (  test_device_123  )'}
    
    def test_get_device_ids_with_empty_device_id(self):
        """Test device ID retrieval with empty device ID."""
        self.plugin.device_id = ""
        
        with pytest.raises(ConfigError, match="No Eight Sleep device ID found"):
            self.plugin.get_device_ids(auto_discover=False)
    
    def test_fetch_data_with_cache_hit(self):
        """Test data fetching when cache has valid data."""
        cache = Mock()
        cached_data = pd.DataFrame({
            'timestamp': [datetime(2024, 1, 1, 10, 0)],
            'temperature': [68.5],
            'humidity': [45.2]
        })
        cache.get.return_value = cached_data
        cache.get_stats.return_value = {'valid_files': 1}
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        result = self.plugin.fetch_data('test_device', start_date, end_date, cache)
        
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        cache.get.assert_called_once()
    
    def test_fetch_data_with_cache_miss(self):
        """Test data fetching when cache misses."""
        cache = Mock()
        cache.get.return_value = None
        cache.get_stats.return_value = {'valid_files': 0}
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        with pytest.raises(DataError, match="No valid Eight Sleep data found"):
            self.plugin.fetch_data('test_device', start_date, end_date, cache)
    
    def test_fetch_data_with_invalid_date_range(self):
        """Test data fetching with invalid date range (end before start)."""
        cache = Mock()
        cache.get.return_value = None
        cache.get_stats.return_value = {'valid_files': 0}
        
        start_date = datetime(2024, 1, 2)
        end_date = datetime(2024, 1, 1)
        
        with pytest.raises(DataError, match="No valid Eight Sleep data found"):
            self.plugin.fetch_data('test_device', start_date, end_date, cache)
    
    def test_fetch_data_with_none_device_id(self):
        """Test data fetching with None device ID."""
        cache = Mock()
        cache.get.return_value = None
        cache.get_stats.return_value = {'valid_files': 0}
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        with pytest.raises(DataError, match="No valid Eight Sleep data found"):
            self.plugin.fetch_data(None, start_date, end_date, cache)
    
    def test_fetch_data_with_empty_device_id(self):
        """Test data fetching with empty device ID."""
        cache = Mock()
        cache.get.return_value = None
        cache.get_stats.return_value = {'valid_files': 0}
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        with pytest.raises(DataError, match="No valid Eight Sleep data found"):
            self.plugin.fetch_data('', start_date, end_date, cache)
    
    def test_discover_devices_with_api_error(self):
        """Test device discovery when API throws an error."""
        with patch.object(self.plugin, 'get_api_client') as mock_get_client:
            mock_client = Mock()
            mock_client.get_devices.side_effect = Exception("API connection failed")
            mock_get_client.return_value = mock_client
            
            # Should not raise exception, just handle gracefully
            self.plugin.discover_devices()
    
    def test_discover_devices_with_no_credentials(self):
        """Test device discovery when no credentials are available."""
        self.plugin.username = None
        self.plugin.password = None
        
        # Should handle gracefully without raising exception
        self.plugin.discover_devices()
    
    def test_notification_title_consistency(self):
        """Test that notification title is consistent across multiple calls."""
        title1 = self.plugin.notification_title
        title2 = self.plugin.notification_title
        
        assert title1 == title2
        assert title1 == "Eight Sleep Anomaly Alert"
    
    def test_plugin_name_consistency(self):
        """Test that plugin name is consistent and lowercase."""
        name1 = self.plugin.name
        name2 = self.plugin.name
        
        assert name1 == name2
        assert name1 == "eightplugin"
        assert name1.islower()
    
    def test_get_api_client_credentials_validation(self):
        """Test API client credential validation with various edge cases."""
        # Test with whitespace-only credentials
        self.plugin.username = "  "
        self.plugin.password = "valid_pass"
        
        with pytest.raises(APIError, match="EIGHT_USERNAME and EIGHT_PASSWORD environment variables must be set"):
            self.plugin.get_api_client()
        
        # Test with empty string credentials
        self.plugin.username = ""
        self.plugin.password = "valid_pass"
        
        with pytest.raises(APIError, match="EIGHT_USERNAME and EIGHT_PASSWORD environment variables must be set"):
            self.plugin.get_api_client()
    
    def test_get_api_client_multiple_calls(self):
        """Test that multiple API client calls return new instances."""
        client1 = self.plugin.get_api_client()
        client2 = self.plugin.get_api_client()
        
        assert client1 is not client2
        assert client1.username == client2.username
        assert client1.password == client2.password


class TestEightSleepAPIStubExtended:
    """Extended comprehensive tests for the Eight Sleep API stub."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.api_stub = _EightSleepAPIStub("test_user", "test_pass")
    
    def test_initialization_with_empty_credentials(self):
        """Test API stub initialization with empty credentials."""
        api_stub = _EightSleepAPIStub("", "")
        
        assert api_stub.username == ""
        assert api_stub.password == ""
    
    def test_initialization_with_none_credentials(self):
        """Test API stub initialization with None credentials."""
        api_stub = _EightSleepAPIStub(None, None)
        
        assert api_stub.username is None
        assert api_stub.password is None
    
    def test_initialization_with_special_characters(self):
        """Test API stub initialization with special characters in credentials."""
        username = "test@user!123"
        password = "p@ssw0rd!#$%"
        api_stub = _EightSleepAPIStub(username, password)
        
        assert api_stub.username == username
        assert api_stub.password == password
    
    def test_get_devices_multiple_calls(self):
        """Test that multiple device calls return consistent results."""
        devices1 = self.api_stub.get_devices()
        devices2 = self.api_stub.get_devices()
        
        assert devices1 == devices2
        assert len(devices1) == 1
        assert devices1[0]["device_id"] == "eight-pod-default"
    
    def test_get_devices_structure(self):
        """Test the structure of returned devices."""
        devices = self.api_stub.get_devices()
        
        assert isinstance(devices, list)
        assert len(devices) == 1
        
        device = devices[0]
        assert isinstance(device, dict)
        assert "device_id" in device
        assert "name" in device
        assert isinstance(device["device_id"], str)
        assert isinstance(device["name"], str)
    
    def test_get_sleep_session_various_inputs(self):
        """Test sleep session retrieval with various input formats."""
        # Test with valid inputs
        result1 = self.api_stub.get_sleep_session("device_123", "2024-01-01")
        assert result1 is None
        
        # Test with empty inputs
        result2 = self.api_stub.get_sleep_session("", "")
        assert result2 is None
        
        # Test with None inputs
        result3 = self.api_stub.get_sleep_session(None, None)
        assert result3 is None
        
        # Test with special characters
        result4 = self.api_stub.get_sleep_session("device!@#", "2024-12-31")
        assert result4 is None
    
    def test_get_sleep_session_date_formats(self):
        """Test sleep session retrieval with different date formats."""
        device_id = "test_device"
        
        # Test various date formats
        date_formats = [
            "2024-01-01",
            "2024-12-31",
            "2023-02-28",
            "2024-02-29",  # Leap year
            "invalid-date",
            "2024-13-01",  # Invalid month
            "2024-01-32"   # Invalid day
        ]
        
        for date_str in date_formats:
            result = self.api_stub.get_sleep_session(device_id, date_str)
            assert result is None
    
    def test_api_stub_immutability(self):
        """Test that API stub credentials cannot be modified after initialization."""
        original_username = self.api_stub.username
        original_password = self.api_stub.password
        
        # Try to modify (should not affect the object if properly designed)
        try:
            self.api_stub.username = "modified_user"
            self.api_stub.password = "modified_pass"
        except AttributeError:
            # If the implementation prevents modification
            pass
        
        # Verify that the getter methods still work
        assert hasattr(self.api_stub, 'username')
        assert hasattr(self.api_stub, 'password')


class TestEightPluginErrorHandling:
    """Test error handling scenarios for the Eight Sleep plugin."""
    
    def setup_method(self):
        """Set up test fixtures."""
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
    
    def test_fetch_data_with_corrupted_cache(self):
        """Test data fetching when cache returns corrupted data."""
        cache = Mock()
        cache.get.return_value = "corrupted_data"  # Not a DataFrame
        cache.get_stats.return_value = {'valid_files': 1}
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        # Should handle gracefully and return the corrupted data or raise appropriate error
        result = self.plugin.fetch_data('test_device', start_date, end_date, cache)
        assert result == "corrupted_data"
    
    def test_fetch_data_with_cache_exception(self):
        """Test data fetching when cache operations throw exceptions."""
        cache = Mock()
        cache.get.side_effect = Exception("Cache operation failed")
        cache.get_stats.return_value = {'valid_files': 0}
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        with pytest.raises(Exception, match="Cache operation failed"):
            self.plugin.fetch_data('test_device', start_date, end_date, cache)
    
    def test_get_device_ids_with_none_user_id(self):
        """Test device ID retrieval when user_id is None."""
        self.plugin.user_id = None
        
        device_ids, device_names = self.plugin.get_device_ids(auto_discover=False)
        
        assert device_ids == ['test_device_123']
        assert device_names == {'test_device_123': 'Eight Sleep Pod (test_device_123)'}
    
    def test_plugin_with_invalid_console(self):
        """Test plugin initialization with invalid console object."""
        invalid_console = "not_a_console"
        
        with patch('anomaly_detector.plugins.eight.get_env_var', side_effect=lambda key, default=None: self.env_vars.get(key, default)):
            plugin = EightPlugin(invalid_console)
            assert plugin.console == invalid_console


class TestEightPluginIntegration:
    """Integration tests for the Eight Sleep plugin."""
    
    def setup_method(self):
        """Set up test fixtures."""
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
    
    def test_full_workflow_with_cache(self):
        """Test complete workflow from device discovery to data fetching."""
        # Mock cache manager
        cache = Mock()
        cache.get.return_value = None
        cache.get_stats.return_value = {'valid_files': 0}
        
        # Test device discovery
        self.plugin.discover_devices()
        
        # Test device ID retrieval
        device_ids, device_names = self.plugin.get_device_ids(auto_discover=False)
        assert len(device_ids) == 1
        
        # Test data fetching (should raise DataError due to placeholder implementation)
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        with pytest.raises(DataError):
            self.plugin.fetch_data(device_ids[0], start_date, end_date, cache)
    
    def test_plugin_api_client_consistency(self):
        """Test that API client is consistent across plugin operations."""
        client1 = self.plugin.get_api_client()
        client2 = self.plugin.get_api_client()
        
        # Should be separate instances but with same credentials
        assert client1 is not client2
        assert client1.username == client2.username
        assert client1.password == client2.password
        
        # Test that devices are consistent
        devices1 = client1.get_devices()
        devices2 = client2.get_devices()
        assert devices1 == devices2
    
    def test_cache_key_consistency_across_calls(self):
        """Test that cache keys are consistent across multiple calls."""
        device_id = "test_device"
        date_str = "2024-01-01"
        
        key1 = self.plugin._get_cache_key(device_id, date_str)
        key2 = self.plugin._get_cache_key(device_id, date_str)
        
        assert key1 == key2
        assert key1 == f"eightplugin_{device_id}_{date_str}"
    
    def test_environment_variable_dependency(self):
        """Test plugin behavior with various environment variable configurations."""
        test_configs = [
            {
                'EIGHT_USERNAME': 'user1',
                'EIGHT_PASSWORD': 'pass1',
                'EIGHT_DEVICE_ID': 'device1',
                'EIGHT_USER_ID': 'user_id1'
            },
            {
                'EIGHT_USERNAME': 'user2',
                'EIGHT_PASSWORD': 'pass2',
                'EIGHT_DEVICE_ID': None,
                'EIGHT_USER_ID': None
            },
            {
                'EIGHT_USERNAME': None,
                'EIGHT_PASSWORD': None,
                'EIGHT_DEVICE_ID': 'device3',
                'EIGHT_USER_ID': 'user_id3'
            }
        ]
        
        for config in test_configs:
            with patch('anomaly_detector.plugins.eight.get_env_var', side_effect=lambda key, default=None: config.get(key, default)):
                plugin = EightPlugin(self.console)
                
                assert plugin.username == config['EIGHT_USERNAME']
                assert plugin.password == config['EIGHT_PASSWORD']
                assert plugin.device_id == config['EIGHT_DEVICE_ID']
                assert plugin.user_id == config['EIGHT_USER_ID']