"""
ABOUTME: Integration tests for SleepAnomalyDetector with plugin system
ABOUTME: Tests detector initialization and plugin integration
"""

import pytest
from unittest.mock import Mock, patch
from rich.console import Console

from anomaly_detector.detector import SleepAnomalyDetector
from anomaly_detector.plugins import SleepTrackerPlugin
from anomaly_detector.exceptions import ConfigError


class TestDetectorPluginIntegration:
    """Test the integration between detector and plugin system."""
    
    def setup_method(self):
        """
        Initializes the test environment by setting up a console and mocking environment variables required for detector and plugin configuration.
        """
        self.console = Console()
        
        # Mock environment variables
        self.env_vars = {
            'IFOREST_CONTAM': '0.05',
            'IFOREST_TRAIN_WINDOW': '90',
            'IFOREST_SHOW_N': '5',
            'SLEEP_TRACKER_CACHE_DIR': './cache',
            'SLEEP_TRACKER_CACHE_ENABLED': 'true',
            'SLEEP_TRACKER_CACHE_TTL_HOURS': '24',
            'SLEEP_TRACKER_PLUGIN': 'emfit',
            'EMFIT_TOKEN': 'test_token',
            'EMFIT_DEVICE_ID': 'test_device'
        }
    
    def test_detector_loads_default_plugin(self):
        """
        Verify that SleepAnomalyDetector loads the default plugin ("emfit") when no plugin name is specified.
        """
        with patch('anomaly_detector.detector.get_env_var', side_effect=lambda key, default=None: self.env_vars.get(key, default)):
            with patch('anomaly_detector.detector.get_env_float', side_effect=lambda key, default=None: float(self.env_vars.get(key, default))):
                with patch('anomaly_detector.detector.get_env_int', side_effect=lambda key, default=None: int(self.env_vars.get(key, default))):
                    detector = SleepAnomalyDetector(self.console)
                    
                    assert detector.plugin is not None
                    assert detector.plugin.name == "emfitplugin"
                    assert detector.plugin_name == "emfit"
    
    def test_detector_loads_specified_plugin(self):
        """
        Verifies that SleepAnomalyDetector loads the specified plugin when a plugin name is provided.
        
        This test patches environment variable accessors to use mocked values, instantiates the detector with the plugin name "oura", and asserts that the correct plugin is loaded and identified.
        """
        with patch('anomaly_detector.detector.get_env_var', side_effect=lambda key, default=None: self.env_vars.get(key, default)):
            with patch('anomaly_detector.detector.get_env_float', side_effect=lambda key, default=None: float(self.env_vars.get(key, default))):
                with patch('anomaly_detector.detector.get_env_int', side_effect=lambda key, default=None: int(self.env_vars.get(key, default))):
                    detector = SleepAnomalyDetector(self.console, plugin_name="oura")
                    
                    assert detector.plugin is not None
                    assert detector.plugin.name == "ouraplugin"
                    assert detector.plugin_name == "oura"
    
    def test_detector_invalid_plugin_raises_error(self):
        """
        Verify that initializing SleepAnomalyDetector with an invalid plugin name raises a SystemExit due to configuration error.
        """
        with patch('anomaly_detector.detector.get_env_var', side_effect=lambda key, default=None: self.env_vars.get(key, default)):
            with patch('anomaly_detector.detector.get_env_float', side_effect=lambda key, default=None: float(self.env_vars.get(key, default))):
                with patch('anomaly_detector.detector.get_env_int', side_effect=lambda key, default=None: int(self.env_vars.get(key, default))):
                    with pytest.raises(SystemExit):  # ConfigError causes sys.exit(1)
                        SleepAnomalyDetector(self.console, plugin_name="nonexistent")
    
    def test_detector_delegates_to_plugin_methods(self):
        """
        Verify that SleepAnomalyDetector delegates method calls to its plugin's implementations.
        
        This test ensures that the detector's methods for obtaining the API client, device IDs, and fetching sleep data correctly invoke the corresponding plugin methods and return their results.
        """
        with patch('anomaly_detector.detector.get_env_var', side_effect=lambda key, default=None: self.env_vars.get(key, default)):
            with patch('anomaly_detector.detector.get_env_float', side_effect=lambda key, default=None: float(self.env_vars.get(key, default))):
                with patch('anomaly_detector.detector.get_env_int', side_effect=lambda key, default=None: int(self.env_vars.get(key, default))):
                    detector = SleepAnomalyDetector(self.console)
                    
                    # Mock plugin methods
                    detector.plugin.get_api_client = Mock(return_value="mock_api")
                    detector.plugin.get_device_ids = Mock(return_value=(["device1"], {"device1": "Device 1"}))
                    detector.plugin.fetch_data = Mock()
                    
                    # Test delegation
                    api_client = detector.get_api_client()
                    assert api_client == "mock_api"
                    detector.plugin.get_api_client.assert_called_once()
                    
                    device_ids, device_names = detector.get_device_ids()
                    assert device_ids == ["device1"]
                    assert device_names == {"device1": "Device 1"}
                    detector.plugin.get_device_ids.assert_called_once_with(True)
                    
                    from datetime import datetime
                    mock_cache = Mock()
                    detector.fetch_sleep_data("device1", datetime.now(), datetime.now(), mock_cache)
                    detector.plugin.fetch_data.assert_called_once()
    
    def test_detector_config_validation(self):
        """
        Verifies that the detector raises a SystemExit when initialized with invalid configuration values.
        
        This test specifically checks that setting an out-of-range contamination value in the environment triggers configuration validation failure and causes the detector to exit.
        """
        # Test invalid contamination value
        invalid_env = self.env_vars.copy()
        invalid_env['IFOREST_CONTAM'] = '1.5'  # Invalid: > 1.0
        
        with patch('anomaly_detector.detector.get_env_var', side_effect=lambda key, default=None: invalid_env.get(key, default)):
            with patch('anomaly_detector.detector.get_env_float', side_effect=lambda key, default=None: float(invalid_env.get(key, default))):
                with patch('anomaly_detector.detector.get_env_int', side_effect=lambda key, default=None: int(invalid_env.get(key, default))):
                    with pytest.raises(SystemExit):  # ConfigError causes sys.exit(1)
                        SleepAnomalyDetector(self.console)
    
    def test_detector_cache_config(self):
        """
        Verify that the SleepAnomalyDetector correctly parses and assigns cache-related configuration parameters from environment variables.
        """
        with patch('anomaly_detector.detector.get_env_var', side_effect=lambda key, default=None: self.env_vars.get(key, default)):
            with patch('anomaly_detector.detector.get_env_float', side_effect=lambda key, default=None: float(self.env_vars.get(key, default))):
                with patch('anomaly_detector.detector.get_env_int', side_effect=lambda key, default=None: int(self.env_vars.get(key, default))):
                    detector = SleepAnomalyDetector(self.console)
                    
                    assert str(detector.cache_dir) == "./cache"
                    assert detector.cache_enabled == True
                    assert detector.cache_ttl_hours == 24
    
    def test_detector_plugin_manager_integration(self):
        """
        Verify that SleepAnomalyDetector initializes its plugin manager, assigns the console, and loads available plugins including "emfit".
        """
        with patch('anomaly_detector.detector.get_env_var', side_effect=lambda key, default=None: self.env_vars.get(key, default)):
            with patch('anomaly_detector.detector.get_env_float', side_effect=lambda key, default=None: float(self.env_vars.get(key, default))):
                with patch('anomaly_detector.detector.get_env_int', side_effect=lambda key, default=None: int(self.env_vars.get(key, default))):
                    detector = SleepAnomalyDetector(self.console)
                    
                    # Test plugin manager is initialized
                    assert detector.plugin_manager is not None
                    assert detector.plugin_manager.console == self.console
                    
                    # Test plugin manager has loaded plugins
                    available_plugins = detector.plugin_manager.list_plugins()
                    assert len(available_plugins) > 0
                    assert "emfit" in available_plugins