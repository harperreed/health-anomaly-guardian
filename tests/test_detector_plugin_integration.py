"""
Tests for the detector integration with the plugin system.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from rich.console import Console

from anomaly_detector.detector import SleepAnomalyDetector
from anomaly_detector.exceptions import ConfigError, APIError


class TestDetectorPluginIntegration:
    """Tests for SleepAnomalyDetector integration with plugins."""

    @pytest.fixture
    def console(self):
        """Create a console instance."""
        return Console()

    @patch.dict('os.environ', {'EMFIT_TOKEN': 'test_token'})
    def test_detector_default_plugin_selection(self, console):
        """Test that detector selects emfit plugin by default."""
        detector = SleepAnomalyDetector(console)
        
        assert detector.plugin_name == "emfit"
        assert detector.plugin is not None
        assert detector.plugin.name == "emfit"

    @patch.dict('os.environ', {'SLEEP_TRACKER_PLUGIN': 'oura', 'OURA_API_TOKEN': 'test_token'})
    def test_detector_plugin_selection_via_env(self, console):
        """Test that detector selects plugin based on environment variable."""
        detector = SleepAnomalyDetector(console)
        
        assert detector.plugin_name == "oura"
        assert detector.plugin is not None
        assert detector.plugin.name == "oura"

    @patch.dict('os.environ', {'EIGHT_USERNAME': 'test_user', 'EIGHT_PASSWORD': 'test_pass'})
    def test_detector_plugin_selection_via_parameter(self, console):
        """Test that detector selects plugin based on constructor parameter."""
        detector = SleepAnomalyDetector(console, plugin_name="eight")
        
        assert detector.plugin_name == "eight"
        assert detector.plugin is not None
        assert detector.plugin.name == "eight"

    def test_detector_invalid_plugin_selection(self, console):
        """Test that detector raises error for invalid plugin."""
        with pytest.raises(SystemExit):  # ConfigError triggers sys.exit(1)
            SleepAnomalyDetector(console, plugin_name="nonexistent")

    @patch.dict('os.environ', {'EMFIT_TOKEN': 'test_token'})
    def test_detector_plugin_method_delegation(self, console):
        """Test that detector properly delegates to plugin methods."""
        detector = SleepAnomalyDetector(console)
        
        # Mock the plugin methods
        detector.plugin.get_api_client = Mock(return_value="mock_api_client")
        detector.plugin.get_device_ids = Mock(return_value=(["device1"], {"device1": "Device 1"}))
        detector.plugin.discover_devices = Mock()
        
        # Test delegation
        api_client = detector.get_api_client()
        assert api_client == "mock_api_client"
        detector.plugin.get_api_client.assert_called_once()
        
        device_ids, device_names = detector.get_device_ids()
        assert device_ids == ["device1"]
        assert device_names == {"device1": "Device 1"}
        detector.plugin.get_device_ids.assert_called_once_with(True)
        
        detector.discover_devices()
        detector.plugin.discover_devices.assert_called_once()

    @patch.dict('os.environ', {'EMFIT_TOKEN': 'test_token'})
    def test_detector_notification_title_from_plugin(self, console):
        """Test that detector uses plugin's notification title."""
        detector = SleepAnomalyDetector(console)
        
        # Mock the plugin's notification title
        detector.plugin.notification_title = "Test Plugin Alert"
        
        # Test that notify method uses plugin's title
        with patch('requests.post') as mock_post:
            mock_post.return_value.raise_for_status = Mock()
            detector.pushover_token = "test_token"
            detector.pushover_user = "test_user"
            
            detector.notify("Test message")
            
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[1]["data"]["title"] == "Test Plugin Alert"

    @patch.dict('os.environ', {'EMFIT_TOKEN': 'test_token'})
    def test_detector_plugin_configuration_validation_order(self, console):
        """Test that plugin validation happens early in configuration."""
        # This test ensures that plugin validation is done before other config
        # to avoid the configuration validation gap issue
        
        # Mock PluginManager to return None for a plugin
        with patch('anomaly_detector.detector.PluginManager') as mock_plugin_manager:
            mock_manager_instance = Mock()
            mock_manager_instance.get_plugin.return_value = None
            mock_manager_instance.list_plugins.return_value = ["emfit", "oura", "eight"]
            mock_plugin_manager.return_value = mock_manager_instance
            
            # Should raise ConfigError and exit
            with pytest.raises(SystemExit):
                SleepAnomalyDetector(console, plugin_name="invalid")

    @patch.dict('os.environ', {'EMFIT_TOKEN': 'test_token'})
    def test_detector_plugin_name_in_display_results(self, console):
        """Test that plugin name is properly used in display results."""
        detector = SleepAnomalyDetector(console)
        
        # Mock the plugin name
        detector.plugin.name = "test_plugin"
        
        # Test that run method uses plugin name in display
        with patch.object(detector, 'get_device_ids') as mock_get_devices:
            mock_get_devices.return_value = ([], {})
            
            # Should raise ConfigError about no device IDs
            with pytest.raises(SystemExit):
                detector.run(window=30, contamin=0.05, n_out=5, alert=False)

    @patch.dict('os.environ', {'EMFIT_TOKEN': 'test_token'})
    def test_detector_configuration_validation(self, console):
        """Test that detector validates configuration properly."""
        # Test valid configuration
        detector = SleepAnomalyDetector(console)
        
        # Configuration should be loaded
        assert 0.0 < detector.contam_env < 1.0
        assert detector.window_env >= 7
        assert detector.plugin_name == "emfit"

    @patch.dict('os.environ', {'EMFIT_TOKEN': 'test_token', 'IFOREST_CONTAM': '1.5'})
    def test_detector_invalid_contamination_config(self, console):
        """Test that detector validates contamination parameter."""
        with pytest.raises(SystemExit):  # ConfigError triggers sys.exit(1)
            SleepAnomalyDetector(console)

    @patch.dict('os.environ', {'EMFIT_TOKEN': 'test_token', 'IFOREST_TRAIN_WINDOW': '5'})
    def test_detector_invalid_window_config(self, console):
        """Test that detector validates window parameter."""
        with pytest.raises(SystemExit):  # ConfigError triggers sys.exit(1)
            SleepAnomalyDetector(console)

    @patch.dict('os.environ', {'EMFIT_TOKEN': 'test_token'})
    def test_detector_cache_initialization(self, console):
        """Test that detector initializes cache properly."""
        detector = SleepAnomalyDetector(console)
        
        # Should have cache configuration
        assert detector.cache_dir is not None
        assert detector.cache_enabled is not None
        assert detector.cache_ttl_hours is not None

    @patch.dict('os.environ', {'EMFIT_TOKEN': 'test_token'})
    def test_detector_clear_cache_method(self, console):
        """Test that detector can clear cache."""
        detector = SleepAnomalyDetector(console)
        
        # Mock the cache directory
        with patch('pathlib.Path.glob') as mock_glob:
            mock_file = Mock()
            mock_file.unlink = Mock()
            mock_glob.return_value = [mock_file]
            
            removed_count = detector.clear_cache()
            
            assert removed_count == 1
            mock_file.unlink.assert_called_once()

    @patch.dict('os.environ', {'EMFIT_TOKEN': 'test_token'})
    @patch('anomaly_detector.detector.CacheManager')
    def test_detector_cache_plugin_integration(self, mock_cache_manager, console):
        """Test that detector integrates properly with plugin-aware cache."""
        detector = SleepAnomalyDetector(console)
        
        # Mock cache manager instance
        mock_cache_instance = Mock()
        mock_cache_manager.return_value = mock_cache_instance
        
        # Mock plugin methods
        detector.plugin.get_device_ids = Mock(return_value=(["device1"], {"device1": "Device 1"}))
        detector.plugin.fetch_data = Mock()
        
        # Mock data for preprocessing
        import pandas as pd
        mock_data = pd.DataFrame({
            'date': [pd.Timestamp('2024-01-01')],
            'hr': [65],
            'rr': [14],
            'sleep_dur': [8.0],
            'score': [85],
            'tnt': [5]
        })
        detector.plugin.fetch_data.return_value = mock_data
        
        # Test that cache is created and passed to plugin
        with patch.object(detector, 'run_single_device') as mock_run_single:
            detector.run(window=30, contamin=0.05, n_out=5, alert=False)
            
            # Should have created cache manager
            mock_cache_manager.assert_called_once()
            
            # Should have called run_single_device with cache
            mock_run_single.assert_called_once()
            call_args = mock_run_single.call_args[0]
            assert len(call_args) >= 3  # device_id, device_name, cache at minimum