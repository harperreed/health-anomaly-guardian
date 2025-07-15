"""
ABOUTME: Unit tests for the main SleepAnomalyDetector class
ABOUTME: Tests ML algorithms, API integration, and core detection functionality
"""

from unittest.mock import Mock, patch

import pytest

from anomaly_detector.detector import SleepAnomalyDetector


class TestSleepAnomalyDetector:
    """Test SleepAnomalyDetector class with plugin architecture."""

    def test_detector_init_with_valid_config(self, mock_console):
        """Test detector initialization with valid configuration."""
        with patch.dict(
            "os.environ",
            {
                "IFOREST_CONTAM": "0.1",
                "IFOREST_TRAIN_WINDOW": "30",
                "IFOREST_SHOW_N": "3",
                "EMFIT_TOKEN": "test_token",
            },
        ):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit"]

                detector = SleepAnomalyDetector(mock_console)
                assert detector.contam_env == 0.1
                assert detector.window_env == 30
                assert detector.n_out_env == 3

    def test_detector_init_with_invalid_contamination(self, mock_console):
        """Test detector initialization with invalid contamination value."""
        with patch.dict("os.environ", {"IFOREST_CONTAM": "1.5", "EMFIT_TOKEN": "test"}):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit"]

                with pytest.raises(SystemExit):
                    SleepAnomalyDetector(mock_console)

    def test_detector_init_with_invalid_window(self, mock_console):
        """Test detector initialization with invalid window size."""
        with patch.dict(
            "os.environ", {"IFOREST_TRAIN_WINDOW": "5", "EMFIT_TOKEN": "test"}
        ):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit"]

                with pytest.raises(SystemExit):
                    SleepAnomalyDetector(mock_console)

    def test_get_api_client_with_plugin(self, mock_console):
        """Test API client initialization via plugin."""
        with patch.dict("os.environ", {"EMFIT_TOKEN": "test_token"}):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_api_client = Mock()
                mock_plugin.get_api_client.return_value = mock_api_client
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit"]

                detector = SleepAnomalyDetector(mock_console)
                api_client = detector.get_api_client()

                assert api_client == mock_api_client
                mock_plugin.get_api_client.assert_called_once()

    def test_invalid_plugin_name(self, mock_console):
        """Test detector initialization with invalid plugin name."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_pm.return_value.get_plugin.return_value = None
                mock_pm.return_value.list_plugins.return_value = ["emfit", "oura"]

                with pytest.raises(SystemExit):
                    SleepAnomalyDetector(mock_console, "invalid_plugin")

    def test_plugin_selection_from_env(self, mock_console):
        """Test plugin selection from environment variable."""
        with patch.dict(
            "os.environ", {"SLEEP_TRACKER_PLUGIN": "oura", "OURA_TOKEN": "test"}
        ):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit", "oura"]

                detector = SleepAnomalyDetector(mock_console)
                assert detector.plugin_name == "oura"

    def test_plugin_selection_from_parameter(self, mock_console):
        """Test plugin selection from parameter override."""
        with patch.dict(
            "os.environ", {"SLEEP_TRACKER_PLUGIN": "emfit", "OURA_TOKEN": "test"}
        ):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit", "oura"]

                detector = SleepAnomalyDetector(mock_console, "oura")
                assert detector.plugin_name == "oura"

    def test_discover_devices_via_plugin(self, mock_console):
        """Test device discovery via plugin."""
        with patch.dict("os.environ", {"EMFIT_TOKEN": "test_token"}):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit"]

                detector = SleepAnomalyDetector(mock_console)
                detector.discover_devices()

                mock_plugin.discover_devices.assert_called_once()

    def test_clear_cache_functionality(self, mock_console):
        """Test cache clearing functionality."""
        with patch.dict("os.environ", {"EMFIT_TOKEN": "test_token"}):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit"]

                detector = SleepAnomalyDetector(mock_console)

                # Mock the glob functionality
                from pathlib import Path

                mock_files = [Mock(spec=Path), Mock(spec=Path)]
                with patch("pathlib.Path.glob", return_value=mock_files):
                    count = detector.clear_cache()

                    assert count == 2
                    # Check that unlink() was called on each file
                    for mock_file in mock_files:
                        mock_file.unlink.assert_called_once()

    def test_run_functionality(self, mock_console):
        """Test running detection via plugin."""
        with patch.dict("os.environ", {"EMFIT_TOKEN": "test_token"}):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_plugin.name = "emfit"
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit"]

                detector = SleepAnomalyDetector(mock_console)

                # Mock the methods that run() calls
                with patch.object(
                    detector,
                    "get_device_ids",
                    return_value=(["device1"], {"device1": "Device 1"}),
                ):
                    with patch.object(detector, "run_single_device", return_value=None):
                        with patch("anomaly_detector.detector.CacheManager") as mock_cm:
                            mock_cache = Mock()
                            mock_cache.clear_expired.return_value = 0
                            mock_cm.return_value = mock_cache

                            detector.run(30, 0.05, 5, False, False, True, None)

                            # Should call run_single_device with the device
                            detector.run_single_device.assert_called_once()

    def test_config_validation_contamination_range(self, mock_console):
        """Test contamination parameter validation."""
        with patch.dict("os.environ", {"IFOREST_CONTAM": "0.0", "EMFIT_TOKEN": "test"}):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit"]

                with pytest.raises(SystemExit):
                    SleepAnomalyDetector(mock_console)

    def test_config_validation_window_minimum(self, mock_console):
        """Test window size minimum validation."""
        with patch.dict(
            "os.environ", {"IFOREST_TRAIN_WINDOW": "6", "EMFIT_TOKEN": "test"}
        ):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit"]

                with pytest.raises(SystemExit):
                    SleepAnomalyDetector(mock_console)

    def test_cache_configuration(self, mock_console):
        """Test cache configuration loading."""
        with patch.dict(
            "os.environ",
            {
                "EMFIT_TOKEN": "test_token",
                "SLEEP_TRACKER_CACHE_DIR": "/custom/cache",
                "SLEEP_TRACKER_CACHE_ENABLED": "false",
                "SLEEP_TRACKER_CACHE_TTL_HOURS": "24",
            },
        ):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit"]

                detector = SleepAnomalyDetector(mock_console)
                assert str(detector.cache_dir) == "/custom/cache"
                assert not detector.cache_enabled
                assert detector.cache_ttl_hours == 24

    def test_openai_config_loading(self, mock_console):
        """Test OpenAI configuration loading."""
        with patch.dict(
            "os.environ",
            {
                "EMFIT_TOKEN": "test_token",
                "OPENAI_API_KEY": "test_openai_key",
            },
        ):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit"]

                detector = SleepAnomalyDetector(mock_console)
                assert detector.openai_api_key == "test_openai_key"

    def test_pushover_config_loading(self, mock_console):
        """Test Pushover notification configuration loading."""
        with patch.dict(
            "os.environ",
            {
                "EMFIT_TOKEN": "test_token",
                "PUSHOVER_APIKEY": "test_api_key",
                "PUSHOVER_USERKEY": "test_user_key",
            },
        ):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit"]

                detector = SleepAnomalyDetector(mock_console)
                assert detector.pushover_token == "test_api_key"
                assert detector.pushover_user == "test_user_key"
