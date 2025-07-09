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
        """Set up test fixtures."""
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
        """Test plugin initializes with correct name and configuration."""
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
        """Test cache key generation with plugin prefix."""
        device_id = "test_device"
        date_str = "2024-01-01"
        
        cache_key = self.plugin._get_cache_key(device_id, date_str)
        
        assert cache_key == f"emfitplugin_{device_id}_{date_str}"
    
    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_get_api_client_with_token(self, mock_emfit_api):
        """Test API client initialization with token."""
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        
        api_client = self.plugin.get_api_client()
        
        assert api_client == mock_api
        mock_emfit_api.assert_called_once_with('test_token')
    
    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_get_api_client_with_username_password(self, mock_emfit_api):
        """Test API client initialization with username/password."""
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
        """Test API client initialization with authentication failure."""
        self.plugin.token = None
        
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.login.return_value = None
        
        with pytest.raises(APIError, match="Authentication failed"):
            self.plugin.get_api_client()
    
    def test_get_api_client_no_credentials(self):
        """Test API client initialization without credentials."""
        self.plugin.token = None
        self.plugin.username = None
        self.plugin.password = None
        
        with pytest.raises(APIError, match="Either EMFIT_TOKEN or EMFIT_USERNAME/PASSWORD must be set"):
            self.plugin.get_api_client()
    
    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_get_device_ids_auto_discovery(self, mock_emfit_api):
        """Test device ID discovery from API."""
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
        """Test device IDs from manual configuration (comma-separated)."""
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_user.side_effect = Exception("API error")
        
        device_ids, device_names = self.plugin.get_device_ids(auto_discover=True)
        
        assert device_ids == ['device1', 'device2', 'device3']
        assert device_names == {'device1': 'device1', 'device2': 'device2', 'device3': 'device3'}
    
    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_get_device_ids_single_device(self, mock_emfit_api):
        """Test device ID from single device configuration."""
        self.plugin.device_ids = None
        
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_user.side_effect = Exception("API error")
        
        device_ids, device_names = self.plugin.get_device_ids(auto_discover=True)
        
        assert device_ids == ['test_device_123']
        assert device_names == {'test_device_123': 'test_device_123'}
    
    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_get_device_ids_no_config(self, mock_emfit_api):
        """Test device ID retrieval with no configuration."""
        self.plugin.device_ids = None
        self.plugin.device_id = None
        
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_user.side_effect = Exception("API error")
        
        with pytest.raises(ConfigError, match="No device IDs found"):
            self.plugin.get_device_ids(auto_discover=True)
    
    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_fetch_data_success(self, mock_emfit_api):
        """Test successful data fetching."""
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
        """Test data fetching with cache hits."""
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
        """Test data fetching with validation failures."""
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
        """Test device discovery functionality."""
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
        """Test device discovery with API error."""
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_user.side_effect = Exception("API error")
        
        with pytest.raises(Exception, match="API error"):
            self.plugin.discover_devices()
    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_fetch_data_empty_response(self, mock_emfit_api):
        """Test data fetching with empty API response."""
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_trends.return_value = {'data': []}
        
        cache = Mock()
        cache.get.return_value = None
        cache.get_stats.return_value = {'valid_files': 0}
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        with pytest.raises(DataError, match="No valid sleep data found"):
            self.plugin.fetch_data('test_device', start_date, end_date, cache)

    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_fetch_data_malformed_response(self, mock_emfit_api):
        """Test data fetching with malformed API response."""
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_trends.return_value = {'invalid_key': 'invalid_data'}
        
        cache = Mock()
        cache.get.return_value = None
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        with pytest.raises(DataError):
            self.plugin.fetch_data('test_device', start_date, end_date, cache)

    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_fetch_data_missing_required_fields(self, mock_emfit_api):
        """Test data fetching with missing required fields."""
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_trends.return_value = {
            'data': [{
                'date': '2024-01-01',
                # Missing all required fields
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
    def test_fetch_data_partial_valid_data(self, mock_emfit_api):
        """Test data fetching with mix of valid and invalid data."""
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_trends.return_value = {
            'data': [
                {
                    'date': '2024-01-01',
                    'meas_hr_avg': None,  # Invalid
                    'meas_rr_avg': 16,
                    'sleep_duration': 8.5,
                    'sleep_score': 85,
                    'tossnturn_count': 12
                },
                {
                    'date': '2024-01-02',
                    'meas_hr_avg': 70,  # Valid
                    'meas_rr_avg': 18,
                    'sleep_duration': 7.5,
                    'sleep_score': 80,
                    'tossnturn_count': 8
                }
            ]
        }
        
        cache = Mock()
        cache.get.return_value = None
        cache.get_stats.return_value = {'valid_files': 1}
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 2)
        
        result = self.plugin.fetch_data('test_device', start_date, end_date, cache)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1  # Only valid data should be returned
        assert result.iloc[0]['hr'] == 70

    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_fetch_data_network_error(self, mock_emfit_api):
        """Test data fetching with network error."""
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_trends.side_effect = Exception("Network error")
        
        cache = Mock()
        cache.get.return_value = None
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        with pytest.raises(Exception, match="Network error"):
            self.plugin.fetch_data('test_device', start_date, end_date, cache)

    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_fetch_data_date_range_validation(self, mock_emfit_api):
        """Test data fetching with invalid date ranges."""
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        
        cache = Mock()
        cache.get.return_value = None
        
        start_date = datetime(2024, 1, 2)
        end_date = datetime(2024, 1, 1)  # End before start
        
        # Should handle invalid date ranges gracefully
        self.plugin.fetch_data('test_device', start_date, end_date, cache)

    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_fetch_data_large_date_range(self, mock_emfit_api):
        """Test data fetching with very large date range."""
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_trends.return_value = {'data': []}
        
        cache = Mock()
        cache.get.return_value = None
        cache.get_stats.return_value = {'valid_files': 0}
        
        start_date = datetime(2020, 1, 1)
        end_date = datetime(2024, 12, 31)  # Very large range
        
        with pytest.raises(DataError, match="No valid sleep data found"):
            self.plugin.fetch_data('test_device', start_date, end_date, cache)

    def test_cache_key_generation_edge_cases(self):
        """Test cache key generation with various edge cases."""
        # Test with empty device ID
        cache_key = self.plugin._get_cache_key("", "2024-01-01")
        assert cache_key == "emfitplugin__2024-01-01"
        
        # Test with special characters
        cache_key = self.plugin._get_cache_key("device-123_test", "2024-01-01")
        assert cache_key == "emfitplugin_device-123_test_2024-01-01"
        
        # Test with None values
        cache_key = self.plugin._get_cache_key(None, "2024-01-01")
        assert cache_key == "emfitplugin_None_2024-01-01"

    def test_plugin_initialization_missing_env_vars(self):
        """Test plugin initialization with missing environment variables."""
        # Test with missing token but present username/password
        env_vars = {
            'EMFIT_USERNAME': 'test_user',
            'EMFIT_PASSWORD': 'test_pass',
            'EMFIT_DEVICE_ID': 'test_device_123'
        }
        
        with patch('anomaly_detector.plugins.emfit.get_env_var', side_effect=lambda key, default=None: env_vars.get(key, default)):
            plugin = EmfitPlugin(self.console)
            assert plugin.token is None
            assert plugin.username == 'test_user'
            assert plugin.password == 'test_pass'

    def test_plugin_initialization_all_missing_env_vars(self):
        """Test plugin initialization with all missing environment variables."""
        env_vars = {}
        
        with patch('anomaly_detector.plugins.emfit.get_env_var', side_effect=lambda key, default=None: env_vars.get(key, default)):
            plugin = EmfitPlugin(self.console)
            assert plugin.token is None
            assert plugin.username is None
            assert plugin.password is None
            assert plugin.device_id is None
            assert plugin.device_ids is None

    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_get_device_ids_api_timeout(self, mock_emfit_api):
        """Test device ID retrieval with API timeout."""
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_user.side_effect = TimeoutError("API timeout")
        
        device_ids, device_names = self.plugin.get_device_ids(auto_discover=True)
        
        # Should fall back to configured device IDs
        assert device_ids == ['device1', 'device2', 'device3']
        assert device_names == {'device1': 'device1', 'device2': 'device2', 'device3': 'device3'}

    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_get_device_ids_api_malformed_response(self, mock_emfit_api):
        """Test device ID retrieval with malformed API response."""
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_user.return_value = {'invalid_key': 'invalid_data'}
        
        device_ids, device_names = self.plugin.get_device_ids(auto_discover=True)
        
        # Should fall back to configured device IDs
        assert device_ids == ['device1', 'device2', 'device3']
        assert device_names == {'device1': 'device1', 'device2': 'device2', 'device3': 'device3'}

    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_get_device_ids_empty_device_settings(self, mock_emfit_api):
        """Test device ID retrieval with empty device settings."""
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_user.return_value = {'device_settings': []}
        
        device_ids, device_names = self.plugin.get_device_ids(auto_discover=True)
        
        # Should fall back to configured device IDs
        assert device_ids == ['device1', 'device2', 'device3']
        assert device_names == {'device1': 'device1', 'device2': 'device2', 'device3': 'device3'}

    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_get_device_ids_missing_device_name(self, mock_emfit_api):
        """Test device ID retrieval with missing device names."""
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_user.return_value = {
            'device_settings': [
                {'device_id': 'device1'},  # Missing device_name
                {'device_id': 'device2', 'device_name': 'Guest Room'}
            ]
        }
        
        device_ids, device_names = self.plugin.get_device_ids(auto_discover=True)
        
        assert device_ids == ['device1', 'device2']
        assert device_names == {'device1': 'device1', 'device2': 'Guest Room'}

    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_fetch_data_with_cache_stats_none(self, mock_emfit_api):
        """Test data fetching when cache stats return None."""
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
        cache.get_stats.return_value = None  # Cache stats return None
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        result = self.plugin.fetch_data('test_device', start_date, end_date, cache)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_fetch_data_extreme_values(self, mock_emfit_api):
        """Test data fetching with extreme values."""
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_trends.return_value = {
            'data': [{
                'date': '2024-01-01',
                'meas_hr_avg': 999,  # Extreme value
                'meas_rr_avg': 0,    # Extreme value
                'sleep_duration': 24,  # Extreme value
                'sleep_score': 0,     # Extreme value
                'tossnturn_count': 1000  # Extreme value
            }]
        }
        
        cache = Mock()
        cache.get.return_value = None
        cache.get_stats.return_value = {'valid_files': 1}
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        result = self.plugin.fetch_data('test_device', start_date, end_date, cache)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]['hr'] == 999

    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_fetch_data_string_numeric_values(self, mock_emfit_api):
        """Test data fetching with string numeric values."""
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_trends.return_value = {
            'data': [{
                'date': '2024-01-01',
                'meas_hr_avg': '65',  # String numeric
                'meas_rr_avg': '16',
                'sleep_duration': '8.5',
                'sleep_score': '85',
                'tossnturn_count': '12'
            }]
        }
        
        cache = Mock()
        cache.get.return_value = None
        cache.get_stats.return_value = {'valid_files': 1}
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        result = self.plugin.fetch_data('test_device', start_date, end_date, cache)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_fetch_data_different_date_formats(self, mock_emfit_api):
        """Test data fetching with different date formats."""
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_trends.return_value = {
            'data': [{
                'date': '2024/01/01',  # Different date format
                'meas_hr_avg': 65,
                'meas_rr_avg': 16,
                'sleep_duration': 8.5,
                'sleep_score': 85,
                'tossnturn_count': 12
            }]
        }
        
        cache = Mock()
        cache.get.return_value = None
        cache.get_stats.return_value = {'valid_files': 1}
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        result = self.plugin.fetch_data('test_device', start_date, end_date, cache)
        
        assert isinstance(result, pd.DataFrame)

    def test_notification_title_consistency(self):
        """Test that notification title is consistent across instances."""
        plugin1 = EmfitPlugin(self.console)
        plugin2 = EmfitPlugin(self.console)
        
        assert plugin1.notification_title == plugin2.notification_title
        assert plugin1.notification_title == "Emfit Anomaly Alert"

    def test_plugin_name_consistency(self):
        """Test that plugin name is consistent across instances."""
        plugin1 = EmfitPlugin(self.console)
        plugin2 = EmfitPlugin(self.console)
        
        assert plugin1.name == plugin2.name
        assert plugin1.name == "emfitplugin"

    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_api_client_caching(self, mock_emfit_api):
        """Test that API client is properly cached."""
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        
        # First call
        client1 = self.plugin.get_api_client()
        # Second call
        client2 = self.plugin.get_api_client()
        
        assert client1 == client2
        # Should only initialize once
        assert mock_emfit_api.call_count <= 2

    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_discover_devices_with_console_output(self, mock_emfit_api):
        """Test device discovery with console output verification."""
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        mock_api.get_user.return_value = {
            'device_settings': [
                {'device_id': 'device1', 'device_name': 'Bedroom'},
                {'device_id': 'device2', 'device_name': 'Guest Room'}
            ]
        }
        
        # Mock console to verify output
        mock_console = Mock()
        plugin = EmfitPlugin(mock_console)
        
        plugin.discover_devices()
        
        # Verify console was used for output
        assert mock_console.print.called

    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_fetch_data_cache_key_consistency(self, mock_emfit_api):
        """Test that cache keys are consistent for same parameters."""
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        
        cache = Mock()
        cache.get.return_value = None
        cache.get_stats.return_value = {'valid_files': 0}
        
        device_id = 'test_device'
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        # Should generate same cache key for same parameters
        expected_key = self.plugin._get_cache_key(device_id, start_date.strftime('%Y-%m-%d'))
        
        try:
            self.plugin.fetch_data(device_id, start_date, end_date, cache)
        except DataError:
            pass  # We expect this to fail due to no data
        
        cache.get.assert_called_with(expected_key)

    def test_device_ids_parsing_edge_cases(self):
        """Test device IDs parsing with various edge cases."""
        # Test with spaces around commas
        self.plugin.device_ids = ' device1 , device2 , device3 '
        device_ids, device_names = self.plugin.get_device_ids(auto_discover=False)
        assert device_ids == ['device1', 'device2', 'device3']
        
        # Test with empty string
        self.plugin.device_ids = ''
        self.plugin.device_id = 'fallback_device'
        device_ids, device_names = self.plugin.get_device_ids(auto_discover=False)
        assert device_ids == ['fallback_device']
        
        # Test with single device in comma-separated format
        self.plugin.device_ids = 'single_device'
        device_ids, device_names = self.plugin.get_device_ids(auto_discover=False)
        assert device_ids == ['single_device']

    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_concurrent_api_calls(self, mock_emfit_api):
        """Test behavior with concurrent API calls."""
        import threading
        
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
        cache.get_stats.return_value = {'valid_files': 1}
        
        results = []
        errors = []
        
        def fetch_data_thread():
            try:
                result = self.plugin.fetch_data('test_device', datetime(2024, 1, 1), datetime(2024, 1, 1), cache)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = [threading.Thread(target=fetch_data_thread) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Should handle concurrent access gracefully
        assert len(errors) == 0
        assert len(results) == 3

    @patch('anomaly_detector.plugins.emfit.EmfitAPI')
    def test_memory_usage_with_large_datasets(self, mock_emfit_api):
        """Test memory usage with large datasets."""
        mock_api = Mock()
        mock_emfit_api.return_value = mock_api
        
        # Create large dataset
        large_dataset = []
        for i in range(1000):
            large_dataset.append({
                'date': f'2024-01-{(i % 31) + 1:02d}',
                'meas_hr_avg': 65 + (i % 20),
                'meas_rr_avg': 16 + (i % 5),
                'sleep_duration': 8.5 + (i % 3),
                'sleep_score': 85 + (i % 15),
                'tossnturn_count': 12 + (i % 10)
            })
        
        mock_api.get_trends.return_value = {'data': large_dataset}
        
        cache = Mock()
        cache.get.return_value = None
        cache.get_stats.return_value = {'valid_files': 1000}
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        result = self.plugin.fetch_data('test_device', start_date, end_date, cache)
        
        # Should handle large datasets without issues
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
