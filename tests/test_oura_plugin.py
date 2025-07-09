"""
ABOUTME: Tests for the Oura sleep tracker plugin
ABOUTME: Tests Oura-specific functionality and placeholder implementation
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import pandas as pd
from rich.console import Console

from anomaly_detector.plugins.oura import OuraPlugin, _OuraAPIStub
from anomaly_detector.exceptions import APIError, ConfigError, DataError
from anomaly_detector.cache import CacheManager


class TestOuraPlugin:
    """Test the Oura plugin functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.console = Console()
        
        # Mock environment variables
        self.env_vars = {
            'OURA_API_TOKEN': 'test_token',
            'OURA_DEVICE_ID': 'test_device_123'
        }
        
        with patch('anomaly_detector.plugins.oura.get_env_var', side_effect=lambda key, default=None: self.env_vars.get(key, default)):
            self.plugin = OuraPlugin(self.console)
    
    def test_plugin_initialization(self):
        """Test plugin initializes with correct name and configuration."""
        assert self.plugin.name == "ouraplugin"
        assert self.plugin.console == self.console
        assert self.plugin.api_token == 'test_token'
        assert self.plugin.device_id == 'test_device_123'
    
    def test_notification_title(self):
        """Test notification title property."""
        assert self.plugin.notification_title == "Oura Anomaly Alert"
    
    def test_cache_key_generation(self):
        """Test cache key generation with plugin prefix."""
        device_id = "test_device"
        date_str = "2024-01-01"
        
        cache_key = self.plugin._get_cache_key(device_id, date_str)
        
        assert cache_key == f"ouraplugin_{device_id}_{date_str}"
    
    def test_get_api_client_with_token(self):
        """Test API client initialization with token."""
        api_client = self.plugin.get_api_client()
        
        assert isinstance(api_client, _OuraAPIStub)
        assert api_client.token == 'test_token'
    
    def test_get_api_client_no_token(self):
        """Test API client initialization without token."""
        self.plugin.api_token = None
        
        with pytest.raises(APIError, match="OURA_API_TOKEN environment variable must be set"):
            self.plugin.get_api_client()
    
    def test_get_device_ids_with_config(self):
        """Test device ID retrieval with configured device."""
        device_ids, device_names = self.plugin.get_device_ids(auto_discover=False)
        
        assert device_ids == ['test_device_123']
        assert device_names == {'test_device_123': 'Oura Ring (test_device_123)'}
    
    def test_get_device_ids_auto_discovery(self):
        """Test device ID retrieval with auto-discovery."""
        self.plugin.device_id = None
        
        device_ids, device_names = self.plugin.get_device_ids(auto_discover=True)
        
        assert device_ids == ['oura-ring-default']
        assert device_names == {'oura-ring-default': 'Oura Ring'}
    
    def test_get_device_ids_no_config_no_discovery(self):
        """Test device ID retrieval without configuration or auto-discovery."""
        self.plugin.device_id = None
        
        with pytest.raises(ConfigError, match="No Oura device ID found"):
            self.plugin.get_device_ids(auto_discover=False)
    
    def test_fetch_data_placeholder(self):
        """Test data fetching (placeholder implementation)."""
        cache = Mock()
        cache.get.return_value = None
        cache.get_stats.return_value = {'valid_files': 0}
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        # Should raise DataError since it's a placeholder
        with pytest.raises(DataError, match="No valid Oura sleep data found"):
            self.plugin.fetch_data('test_device', start_date, end_date, cache)
    
    def test_discover_devices(self):
        """Test device discovery functionality."""
        # Should not raise any exceptions
        self.plugin.discover_devices()


class TestOuraAPIStub:
    """Test the Oura API stub functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.api_stub = _OuraAPIStub("test_token")
    
    def test_initialization(self):
        """Test API stub initialization."""
        assert self.api_stub.token == "test_token"
    
    def test_get_user_info(self):
        """Test user info retrieval."""
        user_info = self.api_stub.get_user_info()
        
        assert isinstance(user_info, dict)
        assert user_info["device_id"] == "oura-ring-default"
        assert user_info["name"] == "Oura Ring"
    
    def test_get_sleep_data(self):
        """Test sleep data retrieval."""
        sleep_data = self.api_stub.get_sleep_data("2024-01-01")
        
        assert sleep_data is None  # Placeholder implementation