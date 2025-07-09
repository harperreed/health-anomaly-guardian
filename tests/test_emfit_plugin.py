"""
ABOUTME: Tests for the Emfit sleep tracker plugin
ABOUTME: Tests Emfit-specific functionality, API integration, and data processing
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd
from rich.console import Console

from anomaly_detector.plugins.emfit import EmfitPlugin
from anomaly_detector.exceptions import APIError, ConfigError, DataError
from anomaly_detector.cache import CacheManager


class TestEmfitPlugin:
    """Test the Emfit plugin functionality."""
    
    def setup_method(self):
        """
        Initializes test fixtures and mocks environment variables for EmfitPlugin tests.
        
        Sets up a Console instance, prepares mock environment variables for Emfit credentials and device IDs, patches environment variable retrieval, and instantiates the EmfitPlugin with the mocked configuration.
        """
        self.console = Console()
        
        # Mock environment variables
        self.env_vars = {
            'EMFIT_TOKEN': 'test_token',
            'EMFIT_DEVICE_ID': 'test_device_123',
            'EMFIT_USERNAME': 'test_user',
            'EMFIT_PASSWORD': 'test_pass',
            'EMFIT_DEVICE_IDS': 'device1,device2,device3'
        }
        
        with patch('anomaly_detector.plugins.emfit.get_env_var', side_effect=lambda key, default=None: self.env_vars.get(key, default)):
            self.plugin = EmfitPlugin(self.console)
    
    def test_plugin_initialization(self):
        """
        Verify that the EmfitPlugin initializes with the expected name, console, and configuration values.
        """
        assert self.plugin.name == "emfitplugin"
        assert self.plugin.console == self.console
        assert self.plugin.token == 'test_token'
        assert self.plugin.device_id == 'test_device_123'
        assert self.plugin.username == 'test_user'
        assert self.plugin.password == 'test_pass'
        assert self.plugin.device_ids == 'device1,device2,device3'
    
    def test_notification_title(self):
        """Test notification title property."""
        assert self.plugin.notification_title == "Emfit Anomaly Alert"
    
    def test_cache_key_generation(self):
        """
        Test that the plugin's cache key generation method produces the expected key format using the plugin prefix, device ID, and date string.
        """
        device_id = "test_device"
        date_str = "2024-01-01"
        
        cache_key = self.plugin._get_cache_key(device_id, date_str)
        
        assert cache_key == f"emfitplugin_{device_id}_{date_str}"
    
    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_get_api_client_with_token(self, mock_emfit_api):
        """
        Tests that the API client is initialized with the provided token and returns the correct client instance.
        """
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        
        api_client = self.plugin.get_api_client()
        
        assert api_client == mock_api
        mock_emfit_api.assert_called_once_with('test_token')
    
    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_get_api_client_with_username_password(self, mock_emfit_api):
        """
        Test that the API client is initialized using username and password authentication when no token is present.
        
        Verifies that the login method is called with the correct credentials and the API client is returned.
        """
        # Remove token to force username/password auth
        self.plugin.token = None
        
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.login.return_value = {'token': 'login_token'}
        
        api_client = self.plugin.get_api_client()
        
        assert api_client == mock_api
        mock_emfit_api.assert_called_once_with(None)
        mock_api.login.assert_called_once_with('test_user', 'test_pass')
    
    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_get_api_client_auth_failure(self, mock_emfit_api):
        """
        Test that an APIError is raised when API client authentication fails due to unsuccessful login.
        """
        self.plugin.token = None
        
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.login.return_value = None
        
        with pytest.raises(APIError, match="Authentication failed"):
            self.plugin.get_api_client()
    
    def test_get_api_client_no_credentials(self):
        """
        Test that an APIError is raised when attempting to initialize the API client without any credentials configured.
        """
        self.plugin.token = None
        self.plugin.username = None
        self.plugin.password = None
        
        with pytest.raises(APIError, match="Either EMFIT_TOKEN or EMFIT_USERNAME/PASSWORD must be set"):
            self.plugin.get_api_client()
    
    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_get_device_ids_auto_discovery(self, mock_emfit_api):
        """
        Tests that device IDs and names are correctly discovered from the API when auto-discovery is enabled.
        """
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_user.return_value = {
            'device_settings': [
                {'device_id': 'device1', 'device_name': 'Bedroom'},
                {'device_id': 'device2', 'device_name': 'Guest Room'}
            ]
        }
        
        device_ids, device_names = self.plugin.get_device_ids(auto_discover=True)
        
        assert device_ids == ['device1', 'device2']
        assert device_names == {'device1': 'Bedroom', 'device2': 'Guest Room'}
    
    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_get_device_ids_manual_list(self, mock_emfit_api):
        """
        Test that device IDs are correctly retrieved from manual configuration when API discovery fails.
        
        Simulates an API error and verifies that the plugin falls back to the manually configured comma-separated device ID list, assigning device names to match the IDs.
        """
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_user.side_effect = Exception("API error")
        
        device_ids, device_names = self.plugin.get_device_ids(auto_discover=True)
        
        assert device_ids == ['device1', 'device2', 'device3']
        assert device_names == {'device1': 'device1', 'device2': 'device2', 'device3': 'device3'}
    
    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_get_device_ids_single_device(self, mock_emfit_api):
        """
        Test that a single configured device ID is returned with its name when API device discovery fails.
        
        Simulates an API error during device discovery and verifies that the plugin falls back to the single configured device ID, assigning its name as the device ID itself.
        """
        self.plugin.device_ids = None
        
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_user.side_effect = Exception("API error")
        
        device_ids, device_names = self.plugin.get_device_ids(auto_discover=True)
        
        assert device_ids == ['test_device_123']
        assert device_names == {'test_device_123': 'test_device_123'}
    
    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_get_device_ids_no_config(self, mock_emfit_api):
        """
        Test that `get_device_ids` raises a `ConfigError` when no device IDs are configured and device discovery via the API fails.
        """
        self.plugin.device_ids = None
        self.plugin.device_id = None
        
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_user.side_effect = Exception("API error")
        
        with pytest.raises(ConfigError, match="No device IDs found"):
            self.plugin.get_device_ids(auto_discover=True)
    
    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_fetch_data_success(self, mock_emfit_api):
        """
        Test that `fetch_data` successfully retrieves and processes valid sleep trend data from the API, returning a DataFrame with expected values.
        """
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_trends.return_value = {
            'data': [{
                'date': '2024-01-01',
                'meas_hr_avg': 65,
                'meas_rr_avg': 16,
                'sleep_duration': 8.5,
                'sleep_score': 85,
                'tossnturn_count': 12
            }]
        }
        
        cache = Mock()
        cache.get.return_value = None
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        result = self.plugin.fetch_data('test_device', start_date, end_date, cache)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]['hr'] == 65
        assert result.iloc[0]['rr'] == 16
        assert result.iloc[0]['sleep_dur'] == 8.5
        assert result.iloc[0]['score'] == 85
        assert result.iloc[0]['tnt'] == 12
    
    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_fetch_data_with_cache(self, mock_emfit_api):
        """
        Test that `fetch_data` returns cached data as a DataFrame and does not call the API when cache is available.
        
        Verifies that when valid data is present in the cache, the plugin retrieves and returns it as a pandas DataFrame, and the API client is not used.
        """
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        
        cache = Mock()
        cache.get.return_value = {
            'data': [{
                'date': '2024-01-01',
                'meas_hr_avg': 65,
                'meas_rr_avg': 16,
                'sleep_duration': 8.5,
                'sleep_score': 85,
                'tossnturn_count': 12
            }]
        }
        cache.get_stats.return_value = {'valid_files': 1}
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        result = self.plugin.fetch_data('test_device', start_date, end_date, cache)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        # Should not call API since cache hit
        mock_api.get_trends.assert_not_called()
    
    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_fetch_data_validation_failure(self, mock_emfit_api):
        """
        Test that `fetch_data` raises a DataError when the API returns invalid or incomplete sleep data.
        
        This test simulates a scenario where the API returns a data record with missing required fields (e.g., average heart rate is None), and verifies that the plugin correctly identifies the validation failure and raises a DataError with the expected message.
        """
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_trends.return_value = {
            'data': [{
                'date': '2024-01-01',
                'meas_hr_avg': None,  # Invalid data
                'meas_rr_avg': 16,
                'sleep_duration': 8.5,
                'sleep_score': 85,
                'tossnturn_count': 12
            }]
        }
        
        cache = Mock()
        cache.get.return_value = None
        cache.get_stats.return_value = {'valid_files': 0}
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        with pytest.raises(DataError, match="No valid sleep data found"):
            self.plugin.fetch_data('test_device', start_date, end_date, cache)
    
    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_discover_devices(self, mock_emfit_api):
        """
        Verifies that the device discovery method retrieves device information from the API without raising exceptions.
        """
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_user.return_value = {
            'device_settings': [
                {'device_id': 'device1', 'device_name': 'Bedroom'},
                {'device_id': 'device2', 'device_name': 'Guest Room'}
            ]
        }
        
        # Should not raise any exceptions
        self.plugin.discover_devices()
        
        mock_api.get_user.assert_called_once()
    
    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_discover_devices_error(self, mock_emfit_api):
        """
        Test that an exception is raised when an API error occurs during device discovery.
        """
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_user.side_effect = Exception("API error")
        
        with pytest.raises(Exception, match="API error"):
            self.plugin.discover_devices()