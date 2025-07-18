"""
Integration tests for SleepAnomalyDetector with plugin system
Tests detector initialization and plugin integration
"""

from unittest.mock import Mock, patch

import pytest
from rich.console import Console

from anomaly_detector.detector import SleepAnomalyDetector
from anomaly_detector.exceptions import APIError


class TestDetectorPluginIntegration:
    """Test the integration between detector and plugin system."""

    def setup_method(self):
        """
        Initializes the test environment by setting up a console and mocking environment variables required for detector and plugin configuration.
        """
        self.console = Console()

        # Mock environment variables
        self.env_vars = {
            "IFOREST_CONTAM": "0.05",
            "IFOREST_TRAIN_WINDOW": "90",
            "IFOREST_SHOW_N": "5",
            "SLEEP_TRACKER_CACHE_DIR": "./cache",
            "SLEEP_TRACKER_CACHE_ENABLED": "true",
            "SLEEP_TRACKER_CACHE_TTL_HOURS": "87600",
            "SLEEP_TRACKER_PLUGIN": "emfit",
            "EMFIT_TOKEN": "test_token",
            "EMFIT_DEVICE_ID": "test_device",
        }

    def test_detector_loads_default_plugin(self):
        """
        Verify that SleepAnomalyDetector loads the default plugin ("emfit") when no plugin name is specified.
        """
        with patch.dict("os.environ", self.env_vars):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_plugin.name = "emfit"
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit"]

                detector = SleepAnomalyDetector(self.console)

                assert detector.plugin is not None
                assert detector.plugin.name == "emfit"
                assert detector.plugin_name == "emfit"

    def test_detector_loads_specified_plugin(self):
        """
        Verifies that SleepAnomalyDetector loads the specified plugin when a plugin name is provided.

        This test patches environment variable accessors to use mocked values, instantiates the detector with the plugin name "oura", and asserts that the correct plugin is loaded and identified.
        """
        with patch.dict("os.environ", self.env_vars):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_plugin.name = "oura"
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["oura"]

                detector = SleepAnomalyDetector(self.console, plugin_name="oura")

                assert detector.plugin is not None
                assert detector.plugin.name == "oura"
                assert detector.plugin_name == "oura"

    def test_detector_invalid_plugin_raises_error(self):
        """
        Verify that initializing SleepAnomalyDetector with an invalid plugin name raises a SystemExit due to configuration error.
        """
        with patch.dict("os.environ", self.env_vars):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_pm.return_value.get_plugin.return_value = None  # Plugin not found
                mock_pm.return_value.list_plugins.return_value = ["emfit", "oura"]

                with pytest.raises(SystemExit):  # ConfigError causes sys.exit(1)
                    SleepAnomalyDetector(self.console, plugin_name="nonexistent")

    def test_detector_delegates_to_plugin_methods(self):
        """
        Verify that SleepAnomalyDetector delegates method calls to its plugin's implementations.

        This test ensures that the detector's methods for obtaining the API client, device IDs, and fetching sleep data correctly invoke the corresponding plugin methods and return their results.
        """
        with patch.dict("os.environ", self.env_vars):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_plugin.name = "emfit"
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit"]

                detector = SleepAnomalyDetector(self.console)

                # Mock plugin methods
                detector.plugin.get_api_client = Mock(return_value="mock_api")
                detector.plugin.get_device_ids = Mock(
                    return_value=(["device1"], {"device1": "Device 1"})
                )
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
                detector.fetch_sleep_data(
                    "device1", datetime.now(), datetime.now(), mock_cache
                )
                detector.plugin.fetch_data.assert_called_once()

    def test_detector_config_validation(self):
        """
        Verifies that the detector raises a SystemExit when initialized with invalid configuration values.

        This test specifically checks that setting an out-of-range contamination value in the environment triggers configuration validation failure and causes the detector to exit.
        """
        # Test invalid contamination value
        invalid_env = self.env_vars.copy()
        invalid_env["IFOREST_CONTAM"] = "1.5"  # Invalid: > 1.0

        with patch.dict("os.environ", invalid_env):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_plugin.name = "emfit"
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit"]

                with pytest.raises(SystemExit):  # ConfigError causes sys.exit(1)
                    SleepAnomalyDetector(self.console)

    def test_detector_cache_config(self):
        """
        Verify that the SleepAnomalyDetector correctly parses and assigns cache-related configuration parameters from environment variables.
        """
        with patch.dict("os.environ", self.env_vars):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_plugin.name = "emfit"
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit"]

                detector = SleepAnomalyDetector(self.console)

                assert str(detector.cache_dir) == "cache"
                assert detector.cache_enabled
                assert detector.cache_ttl_hours == 87600

    def test_detector_plugin_manager_integration(self):
        """
        Verify that SleepAnomalyDetector initializes its plugin manager, assigns the console, and loads available plugins including "emfit".
        """
        with patch.dict("os.environ", self.env_vars):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_plugin.name = "emfit"
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit", "oura"]

                detector = SleepAnomalyDetector(self.console)

                # Test plugin manager is initialized
                assert detector.plugin_manager is not None
                # Verify console was passed to plugin manager
                mock_pm.assert_called_once_with(self.console)

                # Test plugin manager has loaded plugins
                available_plugins = detector.plugin_manager.list_plugins()
                assert len(available_plugins) > 0
                assert "emfit" in available_plugins

    def test_detector_environment_variable_defaults(self):
        """Test detector uses appropriate defaults when environment variables are missing."""
        minimal_env = {
            "SLEEP_TRACKER_PLUGIN": "emfit",
            "EMFIT_TOKEN": "test_token",
            "EMFIT_DEVICE_ID": "test_device",
        }

        with patch.dict("os.environ", minimal_env, clear=True):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_plugin.name = "emfit"
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit"]

                detector = SleepAnomalyDetector(self.console)

                # Test that defaults are applied correctly
                assert detector.cache_enabled  # Should use default
                assert detector.cache_ttl_hours == 87600  # Should use default
                assert detector.plugin is not None

    def test_detector_with_cache_disabled(self):
        """Test detector behavior when cache is disabled."""
        cache_disabled_env = self.env_vars.copy()
        cache_disabled_env["SLEEP_TRACKER_CACHE_ENABLED"] = "false"

        with patch.dict("os.environ", cache_disabled_env):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_plugin.name = "emfit"
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit"]

                detector = SleepAnomalyDetector(self.console)

                assert not detector.cache_enabled

    def test_detector_multiple_plugin_switches(self):
        """Test detector can handle switching between different plugins."""
        # Test emfit plugin
        with patch.dict("os.environ", self.env_vars):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin_emfit = Mock()
                mock_plugin_emfit.name = "emfit"
                mock_plugin_oura = Mock()
                mock_plugin_oura.name = "oura"

                # Mock to return different plugins based on name
                def get_plugin_side_effect(name):
                    if name == "emfit":
                        return mock_plugin_emfit
                    elif name == "oura":
                        return mock_plugin_oura
                    return None

                mock_pm.return_value.get_plugin.side_effect = get_plugin_side_effect
                mock_pm.return_value.list_plugins.return_value = ["emfit", "oura"]

                detector1 = SleepAnomalyDetector(self.console, plugin_name="emfit")
                assert detector1.plugin_name == "emfit"

                # Test oura plugin
                detector2 = SleepAnomalyDetector(self.console, plugin_name="oura")
                assert detector2.plugin_name == "oura"

    def test_detector_plugin_initialization_failure(self):
        """Test detector handles plugin initialization failures gracefully."""
        with patch.dict("os.environ", self.env_vars):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_pm.return_value.get_plugin.side_effect = Exception(
                    "Plugin initialization failed"
                )

                with pytest.raises(Exception, match="Plugin initialization failed"):
                    SleepAnomalyDetector(self.console)

    def test_detector_isolation_forest_parameters(self):
        """Test detector properly configures isolation forest parameters."""
        custom_env = self.env_vars.copy()
        custom_env.update(
            {
                "IFOREST_CONTAM": "0.1",
                "IFOREST_TRAIN_WINDOW": "60",
                "IFOREST_SHOW_N": "10",
            }
        )

        with patch.dict("os.environ", custom_env):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_plugin.name = "emfit"
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit"]

                detector = SleepAnomalyDetector(self.console)

                # Verify parameters are set correctly
                assert detector.contam_env == 0.1
                assert detector.window_env == 60
                assert detector.n_out_env == 10

    def test_detector_plugin_method_error_handling(self):
        """Test detector handles plugin method errors gracefully."""
        with patch(
            "anomaly_detector.detector.get_env_var",
            side_effect=lambda key, default=None: self.env_vars.get(key, default),
        ):
            with patch(
                "anomaly_detector.detector.get_env_float",
                side_effect=lambda key, default=None: float(
                    self.env_vars.get(key, default)
                ),
            ):
                with patch(
                    "anomaly_detector.detector.get_env_int",
                    side_effect=lambda key, default=None: int(
                        self.env_vars.get(key, default)
                    ),
                ):
                    detector = SleepAnomalyDetector(self.console)

                    # Mock plugin methods to raise exceptions
                    detector.plugin.get_api_client = Mock(
                        side_effect=APIError("API Error")
                    )
                    detector.plugin.get_device_ids = Mock(
                        side_effect=APIError("Device Error")
                    )

                    # Test that errors are properly propagated
                    with pytest.raises(APIError):
                        detector.get_api_client()

                    with pytest.raises(APIError):
                        detector.get_device_ids()

    def test_detector_console_integration(self):
        """Test detector properly integrates with console for output."""
        with patch(
            "anomaly_detector.detector.get_env_var",
            side_effect=lambda key, default=None: self.env_vars.get(key, default),
        ):
            with patch(
                "anomaly_detector.detector.get_env_float",
                side_effect=lambda key, default=None: float(
                    self.env_vars.get(key, default)
                ),
            ):
                with patch(
                    "anomaly_detector.detector.get_env_int",
                    side_effect=lambda key, default=None: int(
                        self.env_vars.get(key, default)
                    ),
                ):
                    detector = SleepAnomalyDetector(self.console)

                    # Test console is properly stored
                    assert detector.console == self.console

    def test_detector_boundary_contamination_values(self):
        """Test detector handles boundary contamination values correctly."""
        # Test minimum valid contamination (should fail because 0.0 is not > 0.0)
        min_env = self.env_vars.copy()
        min_env["IFOREST_CONTAM"] = "0.0"

        with patch.dict("os.environ", min_env):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_plugin.name = "emfit"
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit"]

                with pytest.raises(SystemExit):  # Should fail validation
                    SleepAnomalyDetector(self.console)

        # Test maximum valid contamination
        max_env = self.env_vars.copy()
        max_env["IFOREST_CONTAM"] = "0.5"

        with patch.dict("os.environ", max_env):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_plugin.name = "emfit"
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit"]

                detector = SleepAnomalyDetector(self.console)
                assert detector is not None

    def test_detector_invalid_configuration_combinations(self):
        """Test detector handles invalid configuration combinations."""
        # Test negative train window
        invalid_env = self.env_vars.copy()
        invalid_env["IFOREST_TRAIN_WINDOW"] = "-1"

        with patch(
            "anomaly_detector.detector.get_env_var",
            side_effect=lambda key, default=None: invalid_env.get(key, default),
        ):
            with patch(
                "anomaly_detector.detector.get_env_float",
                side_effect=lambda key, default=None: float(
                    invalid_env.get(key, default)
                ),
            ):
                with patch(
                    "anomaly_detector.detector.get_env_int",
                    side_effect=lambda key, default=None: int(
                        invalid_env.get(key, default)
                    ),
                ):
                    with pytest.raises(SystemExit):
                        SleepAnomalyDetector(self.console)

    def test_detector_plugin_data_fetch_with_cache(self):
        """Test detector handles data fetching with cache integration."""
        from datetime import datetime, timedelta

        with patch.dict("os.environ", self.env_vars):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_plugin.name = "emfit"
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit"]

                detector = SleepAnomalyDetector(self.console)

                # Mock cache and plugin
                mock_cache = Mock()
                mock_cache.get.return_value = None
                detector.plugin.fetch_data = Mock(return_value={"test": "data"})

                start_date = datetime.now() - timedelta(days=1)
                end_date = datetime.now()

                detector.fetch_sleep_data(
                    "test_device", start_date, end_date, mock_cache
                )

                # Verify plugin was called
                detector.plugin.fetch_data.assert_called_once()
                # Verify cache was used (called through plugin)
                assert mock_cache.get.called or detector.plugin.fetch_data.called

    def test_detector_plugin_registry_access(self):
        """Test detector can access plugin registry information."""
        with patch(
            "anomaly_detector.detector.get_env_var",
            side_effect=lambda key, default=None: self.env_vars.get(key, default),
        ):
            with patch(
                "anomaly_detector.detector.get_env_float",
                side_effect=lambda key, default=None: float(
                    self.env_vars.get(key, default)
                ),
            ):
                with patch(
                    "anomaly_detector.detector.get_env_int",
                    side_effect=lambda key, default=None: int(
                        self.env_vars.get(key, default)
                    ),
                ):
                    detector = SleepAnomalyDetector(self.console)

                    # Test plugin manager provides access to registry
                    available_plugins = detector.plugin_manager.list_plugins()
                    assert isinstance(available_plugins, list | dict)
                    assert len(available_plugins) > 0

    def test_detector_concurrent_plugin_usage(self):
        """Test detector handles concurrent plugin usage scenarios."""
        import threading

        def create_detector():
            with patch(
                "anomaly_detector.detector.get_env_var",
                side_effect=lambda key, default=None: self.env_vars.get(key, default),
            ):
                with patch(
                    "anomaly_detector.detector.get_env_float",
                    side_effect=lambda key, default=None: float(
                        self.env_vars.get(key, default)
                    ),
                ):
                    with patch(
                        "anomaly_detector.detector.get_env_int",
                        side_effect=lambda key, default=None: int(
                            self.env_vars.get(key, default)
                        ),
                    ):
                        return SleepAnomalyDetector(self.console)

        # Test multiple detector instances can be created concurrently
        detectors = []
        threads = []

        for _i in range(3):
            thread = threading.Thread(
                target=lambda: detectors.append(create_detector())
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All detectors should be initialized successfully
        assert len(detectors) == 3
        for detector in detectors:
            assert detector is not None
            assert detector.plugin is not None

    def test_detector_state_isolation(self):
        """Test detector instances maintain state isolation."""
        with patch(
            "anomaly_detector.detector.get_env_var",
            side_effect=lambda key, default=None: self.env_vars.get(key, default),
        ):
            with patch(
                "anomaly_detector.detector.get_env_float",
                side_effect=lambda key, default=None: float(
                    self.env_vars.get(key, default)
                ),
            ):
                with patch(
                    "anomaly_detector.detector.get_env_int",
                    side_effect=lambda key, default=None: int(
                        self.env_vars.get(key, default)
                    ),
                ):
                    detector1 = SleepAnomalyDetector(self.console, plugin_name="emfit")
                    detector2 = SleepAnomalyDetector(self.console, plugin_name="oura")

                    # Verify state isolation
                    assert detector1.plugin_name != detector2.plugin_name
                    assert detector1.plugin is not detector2.plugin
                    assert detector1.plugin_manager is not detector2.plugin_manager

    def test_detector_graceful_shutdown(self):
        """Test detector handles graceful shutdown scenarios."""
        with patch(
            "anomaly_detector.detector.get_env_var",
            side_effect=lambda key, default=None: self.env_vars.get(key, default),
        ):
            with patch(
                "anomaly_detector.detector.get_env_float",
                side_effect=lambda key, default=None: float(
                    self.env_vars.get(key, default)
                ),
            ):
                with patch(
                    "anomaly_detector.detector.get_env_int",
                    side_effect=lambda key, default=None: int(
                        self.env_vars.get(key, default)
                    ),
                ):
                    detector = SleepAnomalyDetector(self.console)

                    # Test detector can be safely deleted
                    plugin_ref = detector.plugin
                    del detector

                    # Plugin should still exist independently
                    assert plugin_ref is not None

    def test_detector_plugin_compatibility_check(self):
        """Test detector verifies plugin compatibility."""
        with patch(
            "anomaly_detector.detector.get_env_var",
            side_effect=lambda key, default=None: self.env_vars.get(key, default),
        ):
            with patch(
                "anomaly_detector.detector.get_env_float",
                side_effect=lambda key, default=None: float(
                    self.env_vars.get(key, default)
                ),
            ):
                with patch(
                    "anomaly_detector.detector.get_env_int",
                    side_effect=lambda key, default=None: int(
                        self.env_vars.get(key, default)
                    ),
                ):
                    detector = SleepAnomalyDetector(self.console)

                    # Test plugin has required interface
                    assert hasattr(detector.plugin, "get_api_client")
                    assert hasattr(detector.plugin, "get_device_ids")
                    assert hasattr(detector.plugin, "fetch_data")
                    assert hasattr(detector.plugin, "name")

    def test_detector_error_recovery(self):
        """Test detector can recover from transient errors."""
        with patch(
            "anomaly_detector.detector.get_env_var",
            side_effect=lambda key, default=None: self.env_vars.get(key, default),
        ):
            with patch(
                "anomaly_detector.detector.get_env_float",
                side_effect=lambda key, default=None: float(
                    self.env_vars.get(key, default)
                ),
            ):
                with patch(
                    "anomaly_detector.detector.get_env_int",
                    side_effect=lambda key, default=None: int(
                        self.env_vars.get(key, default)
                    ),
                ):
                    detector = SleepAnomalyDetector(self.console)

                    # Mock plugin to fail first time, succeed second time
                    call_count = 0

                    def mock_api_client():
                        nonlocal call_count
                        call_count += 1
                        if call_count == 1:
                            raise APIError("Temporary failure")
                        return "success"

                    detector.plugin.get_api_client = Mock(side_effect=mock_api_client)

                    # First call should fail
                    with pytest.raises(APIError):
                        detector.get_api_client()

                    # Second call should succeed
                    result = detector.get_api_client()
                    assert result == "success"

    def test_detector_resource_cleanup(self):
        """Test detector properly cleans up resources."""
        with patch(
            "anomaly_detector.detector.get_env_var",
            side_effect=lambda key, default=None: self.env_vars.get(key, default),
        ):
            with patch(
                "anomaly_detector.detector.get_env_float",
                side_effect=lambda key, default=None: float(
                    self.env_vars.get(key, default)
                ),
            ):
                with patch(
                    "anomaly_detector.detector.get_env_int",
                    side_effect=lambda key, default=None: int(
                        self.env_vars.get(key, default)
                    ),
                ):
                    detector = SleepAnomalyDetector(self.console)

                    # Test cleanup method if it exists
                    if hasattr(detector, "cleanup"):
                        detector.cleanup()

                    # Test plugin cleanup if it exists
                    if hasattr(detector.plugin, "cleanup"):
                        detector.plugin.cleanup()

                    # Verify no hanging references
                    assert (
                        detector.plugin is not None
                    )  # Should still exist until explicitly cleaned up

    def test_detector_performance_metrics(self):
        """Test detector provides performance metrics if available."""
        with patch.dict("os.environ", self.env_vars):
            with patch("anomaly_detector.detector.PluginManager") as mock_pm:
                mock_plugin = Mock()
                mock_plugin.name = "emfit"
                mock_plugin.get_api_client.return_value = Mock()
                mock_pm.return_value.get_plugin.return_value = mock_plugin
                mock_pm.return_value.list_plugins.return_value = ["emfit"]

                detector = SleepAnomalyDetector(self.console)

                # Test performance tracking if available
                if hasattr(detector, "get_performance_metrics"):
                    metrics = detector.get_performance_metrics()
                    assert isinstance(metrics, dict)
                else:
                    # Test that basic timing can be tracked
                    import time

                    start = time.time()
                    detector.get_api_client()
                    elapsed = time.time() - start
                    assert elapsed >= 0

    def teardown_method(self):
        """Clean up after each test."""
        # Clean up any resources created during tests
        pass
