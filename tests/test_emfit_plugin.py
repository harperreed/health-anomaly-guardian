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