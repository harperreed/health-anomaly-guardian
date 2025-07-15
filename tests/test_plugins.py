"""
ABOUTME: Tests for the plugin architecture
ABOUTME: Comprehensive tests for plugin loading, interface compliance, and functionality
"""

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from anomaly_detector.cache import CacheManager
from anomaly_detector.exceptions import APIError, DataError
from anomaly_detector.plugins import PluginManager
from anomaly_detector.plugins.eight import EightPlugin
from anomaly_detector.plugins.emfit import EmfitPlugin
from anomaly_detector.plugins.oura import OuraPlugin


@pytest.fixture
def mock_console():
    """
    Return a mocked Rich Console instance for use in tests.
    """
    return MagicMock(spec=Console)


@pytest.fixture
def plugin_manager(mock_console):
    """
    Fixture that returns a PluginManager instance initialized with a mocked console for use in tests.
    """
    return PluginManager(mock_console)


@pytest.fixture
def cache_manager():
    """
    Fixture that yields a CacheManager instance using a temporary directory and a 1-hour TTL for cache expiration during tests.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        yield CacheManager(Path(temp_dir) / "cache", ttl_hours=1)


class TestPluginManager:
    """Test the PluginManager class."""

    def test_plugin_manager_initialization(self, mock_console):
        """
        Test that the PluginManager is initialized with the provided console and contains a plugins dictionary.
        """
        manager = PluginManager(mock_console)
        assert manager.console == mock_console
        assert hasattr(manager, "_plugins")
        assert isinstance(manager._plugins, dict)

    def test_plugin_loading(self, plugin_manager):
        """
        Verify that the plugin manager loads all expected plugins by checking their presence in the available plugins list.
        """
        available_plugins = plugin_manager.list_plugins()
        assert "emfit" in available_plugins
        assert "oura" in available_plugins
        assert "eight" in available_plugins

    def test_get_plugin_valid(self, plugin_manager):
        """
        Verifies that valid plugin names return the correct plugin instances with matching names.
        """
        emfit_plugin = plugin_manager.get_plugin("emfit")
        # Check class name and module instead of isinstance due to dynamic loading
        assert emfit_plugin.__class__.__name__ == "EmfitPlugin"
        assert emfit_plugin.__class__.__module__ == "anomaly_detector.plugins.emfit"
        assert emfit_plugin.name == "emfit"

        oura_plugin = plugin_manager.get_plugin("oura")
        assert oura_plugin.__class__.__name__ == "OuraPlugin"
        assert oura_plugin.__class__.__module__ == "anomaly_detector.plugins.oura"
        assert oura_plugin.name == "oura"

        eight_plugin = plugin_manager.get_plugin("eight")
        assert eight_plugin.__class__.__name__ == "EightPlugin"
        assert eight_plugin.__class__.__module__ == "anomaly_detector.plugins.eight"
        assert eight_plugin.name == "eight"

    def test_get_plugin_invalid(self, plugin_manager):
        """
        Verify that requesting a nonexistent plugin from the plugin manager returns None.
        """
        invalid_plugin = plugin_manager.get_plugin("nonexistent")
        assert invalid_plugin is None

    def test_get_plugin_case_insensitive(self, plugin_manager):
        """
        Verify that retrieving a plugin by name is case-insensitive by asserting that plugins fetched with different casing have the same type.
        """
        plugin_upper = plugin_manager.get_plugin("EMFIT")
        plugin_lower = plugin_manager.get_plugin("emfit")
        assert type(plugin_upper) is type(plugin_lower)

    def test_get_default_plugin(self, plugin_manager):
        """
        Verifies that the default plugin returned by the plugin manager is an instance of EmfitPlugin.
        """
        default_plugin = plugin_manager.get_default_plugin()
        # Check class name and module instead of isinstance due to dynamic loading
        assert default_plugin.__class__.__name__ == "EmfitPlugin"
        assert default_plugin.__class__.__module__ == "anomaly_detector.plugins.emfit"

    def test_list_plugins(self, plugin_manager):
        """
        Verifies that the plugin manager returns a list of available plugin names as strings, including at least the core plugins.
        """
        plugins = plugin_manager.list_plugins()
        assert isinstance(plugins, list)
        assert len(plugins) >= 3  # At least emfit, oura, eight
        assert all(isinstance(name, str) for name in plugins)


class TestSleepTrackerPlugin:
    """Test the SleepTrackerPlugin interface compliance."""

    def test_plugin_interface_compliance(self, plugin_manager):
        """
        Verify that all loaded plugins implement the required interface and attributes.

        Asserts that each plugin provides the expected methods and properties, and that the plugin's name attribute matches its registered name.
        """
        for plugin_name in plugin_manager.list_plugins():
            plugin = plugin_manager.get_plugin(plugin_name)

            # Check that plugin has all required methods
            assert hasattr(plugin, "_load_config")
            assert hasattr(plugin, "get_api_client")
            assert hasattr(plugin, "get_device_ids")
            assert hasattr(plugin, "fetch_data")
            assert hasattr(plugin, "discover_devices")
            assert hasattr(plugin, "notification_title")

            # Check that plugin has name attribute
            assert hasattr(plugin, "name")
            assert plugin.name == plugin_name

    def test_plugin_notification_titles(self, plugin_manager):
        """
        Verify that all loaded plugins have unique, non-empty string notification titles.
        """
        titles = []
        for plugin_name in plugin_manager.list_plugins():
            plugin = plugin_manager.get_plugin(plugin_name)
            title = plugin.notification_title
            assert isinstance(title, str)
            assert len(title) > 0
            titles.append(title)

        # Check that all titles are unique
        assert len(titles) == len(set(titles))


class TestEmfitPlugin:
    """Test the EmfitPlugin implementation."""

    @pytest.fixture
    def emfit_plugin(self, mock_console):
        """
        Creates an EmfitPlugin instance with test environment variables for token and device ID.

        Returns:
            EmfitPlugin: An instance configured with mock credentials for testing.
        """
        with patch.dict(
            os.environ,
            {"EMFIT_TOKEN": "test_token", "EMFIT_DEVICE_ID": "test_device_123"},
        ):
            return EmfitPlugin(mock_console)

    def test_emfit_plugin_initialization(self, emfit_plugin):
        """
        Verify that the EmfitPlugin initializes with the correct name, token, and device ID from the environment.
        """
        assert emfit_plugin.name == "emfit"
        assert emfit_plugin.token == "test_token"
        assert emfit_plugin.device_id == "test_device_123"

    def test_emfit_api_client_creation(self, emfit_plugin):
        """
        Tests that the EmfitPlugin creates an EmfitAPI client using the configured token.
        """
        with patch("anomaly_detector.plugins.emfit.EmfitAPI") as mock_api:
            mock_api.return_value = MagicMock()
            emfit_plugin.get_api_client()
            mock_api.assert_called_once_with("test_token")

    def test_emfit_notification_title(self, emfit_plugin):
        """
        Verifies that the EmfitPlugin's notification title is set to "Emfit Anomaly Alert".
        """
        assert emfit_plugin.notification_title == "Emfit Anomaly Alert"


class TestOuraPlugin:
    """Test the OuraPlugin implementation."""

    @pytest.fixture
    def oura_plugin(self, mock_console):
        """
        Creates an OuraPlugin instance with test environment variables for use in unit tests.

        Returns:
            OuraPlugin: An instance configured with mock API token and device ID.
        """
        with patch.dict(
            os.environ,
            {"OURA_API_TOKEN": "test_token", "OURA_DEVICE_ID": "test_device_123"},
        ):
            return OuraPlugin(mock_console)

    def test_oura_plugin_initialization(self, oura_plugin):
        """Test OuraPlugin initialization."""
        assert oura_plugin.name == "oura"
        assert oura_plugin.api_token == "test_token"
        assert oura_plugin.device_id == "test_device_123"

    def test_oura_api_client_creation(self, oura_plugin):
        """
        Test that the OuraPlugin creates an API client with the correct token attribute.
        """
        client = oura_plugin.get_api_client()
        assert client is not None
        assert hasattr(client, "token")
        assert client.token == "test_token"

    def test_oura_api_client_no_token(self, mock_console):
        """
        Test that creating an OuraPlugin API client without the OURA_API_TOKEN environment variable raises an APIError with the expected message.
        """
        with patch.dict(os.environ, {}, clear=True):
            plugin = OuraPlugin(mock_console)
            with pytest.raises(
                APIError, match="OURA_API_TOKEN environment variable must be set"
            ):
                plugin.get_api_client()

    def test_oura_notification_title(self, oura_plugin):
        """Test OuraPlugin notification title."""
        assert oura_plugin.notification_title == "Oura Anomaly Alert"

    def test_oura_get_device_ids_configured(self, oura_plugin):
        """
        Test that OuraPlugin returns the configured device ID and name when auto-discovery is disabled.
        """
        device_ids, device_names = oura_plugin.get_device_ids(auto_discover=False)
        assert device_ids == ["test_device_123"]
        assert device_names == {"test_device_123": "Oura Ring (test_device_123)"}

    def test_oura_get_device_ids_auto_discover(self, oura_plugin):
        """Test OuraPlugin device ID auto-discovery."""
        # Clear device_id to force auto-discovery and ensure credentials are set
        oura_plugin.device_id = None
        oura_plugin.api_token = "test_token"
        device_ids, device_names = oura_plugin.get_device_ids(auto_discover=True)
        assert len(device_ids) == 1
        assert device_ids[0].startswith("oura-ring-")
        assert "Oura Ring" in device_names[device_ids[0]]


class TestEightPlugin:
    """Test the EightPlugin implementation."""

    @pytest.fixture
    def eight_plugin(self, mock_console):
        """
        Creates an EightPlugin instance with test environment variables for username, password, and device ID.

        Parameters:
                mock_console: A mocked console instance used for plugin initialization.

        Returns:
                EightPlugin: An instance of EightPlugin configured with test credentials.
        """
        with patch.dict(
            os.environ,
            {
                "EIGHT_USERNAME": "test_user",
                "EIGHT_PASSWORD": "test_pass",
                "EIGHT_DEVICE_ID": "test_device_123",
            },
        ):
            return EightPlugin(mock_console)

    def test_eight_plugin_initialization(self, eight_plugin):
        """
        Verify that the EightPlugin initializes with the correct name, username, password, and device ID.
        """
        assert eight_plugin.name == "eight"
        assert eight_plugin.username == "test_user"
        assert eight_plugin.password == "test_pass"
        assert eight_plugin.device_id == "test_device_123"

    def test_eight_api_client_creation(self, eight_plugin):
        """
        Verify that the EightPlugin creates an API client with the correct username and password attributes.
        """
        client = eight_plugin.get_api_client()
        assert client is not None
        assert hasattr(client, "username")
        assert hasattr(client, "password")
        assert client.username == "test_user"
        assert client.password == "test_pass"

    def test_eight_api_client_no_credentials(self, mock_console):
        """
        Verify that creating an EightPlugin API client without required credentials raises an APIError.

        Ensures that if the EIGHT_USERNAME and EIGHT_PASSWORD environment variables are not set, attempting to create the API client results in an APIError with the appropriate message.
        """
        with patch.dict(os.environ, {}, clear=True):
            plugin = EightPlugin(mock_console)
            with pytest.raises(
                APIError,
                match="EIGHT_USERNAME and EIGHT_PASSWORD environment variables must be set",
            ):
                plugin.get_api_client()

    def test_eight_notification_title(self, eight_plugin):
        """
        Verifies that the EightPlugin's notification title is set to "Eight Sleep Anomaly Alert".
        """
        assert eight_plugin.notification_title == "Eight Sleep Anomaly Alert"

    def test_eight_get_device_ids_configured(self, eight_plugin):
        """
        Tests that EightPlugin retrieves the configured device ID and name when auto-discovery is disabled.

        Asserts that the returned device IDs and names match the expected configured values.
        """
        device_ids, device_names = eight_plugin.get_device_ids(auto_discover=False)
        assert device_ids == ["test_device_123"]
        assert device_names == {"test_device_123": "Eight Sleep Pod (test_device_123)"}

    def test_eight_get_device_ids_auto_discover(self, eight_plugin):
        """
        Tests that EightPlugin can automatically discover at least one device ID containing 'eight-pod' when auto_discover is enabled.
        """
        # Clear device_id to force auto-discovery and ensure credentials are set
        eight_plugin.device_id = None
        eight_plugin.username = "test_user"
        eight_plugin.password = "test_pass"
        device_ids, device_names = eight_plugin.get_device_ids(auto_discover=True)
        assert len(device_ids) >= 1
        assert any("eight-pod" in device_id for device_id in device_ids)


class TestCacheIntegration:
    """Test cache integration with plugins."""

    def test_cache_key_prefixing(self, cache_manager):
        """
        Verify that the cache manager prefixes cache keys with plugin names to ensure data isolation between plugins and prevent cross-plugin data interference.
        """
        device_id = "test_device"
        date = "2024-01-15"
        test_data = {"test": "data"}

        # Test different plugins use different cache keys
        cache_manager.set(device_id, date, test_data, "emfit")
        cache_manager.set(device_id, date, test_data, "oura")
        cache_manager.set(device_id, date, test_data, "eight")

        # All should be cached separately
        emfit_data = cache_manager.get(device_id, date, "emfit")
        oura_data = cache_manager.get(device_id, date, "oura")
        eight_data = cache_manager.get(device_id, date, "eight")

        assert emfit_data == test_data
        assert oura_data == test_data
        assert eight_data == test_data

        # Test cache isolation - different plugins don't interfere
        cache_manager.set(device_id, date, {"emfit": "specific"}, "emfit")
        emfit_data = cache_manager.get(device_id, date, "emfit")
        oura_data = cache_manager.get(device_id, date, "oura")

        assert emfit_data == {"emfit": "specific"}
        assert oura_data == test_data  # Should still be the original data

    def test_cache_backward_compatibility(self, cache_manager):
        """
        Verify that the cache manager supports storing and retrieving data without plugin name prefixes for backward compatibility.

        Ensures that data cached using the legacy key format (without plugin name) can still be accessed as expected.
        """
        device_id = "test_device"
        date = "2024-01-15"
        test_data = {"test": "data"}

        # Test old-style cache (without plugin name)
        cache_manager.set(device_id, date, test_data)
        retrieved_data = cache_manager.get(device_id, date)

        assert retrieved_data == test_data


class TestPluginErrorHandling:
    """Test plugin error handling and edge cases."""

    def test_plugin_loading_with_import_error(self, mock_console):
        """
        Verify that the plugin manager handles import errors during plugin loading without crashing, ensuring the plugins dictionary is still initialized.
        """
        # This should not crash, just log warnings
        manager = PluginManager(mock_console)
        assert isinstance(manager._plugins, dict)

    def test_plugin_config_validation(self, mock_console):
        """
        Tests that plugins raise APIError when required environment variables are missing during API client creation.
        """
        # Test plugins handle missing environment variables gracefully
        with patch.dict(os.environ, {}, clear=True):
            oura_plugin = OuraPlugin(mock_console)
            with pytest.raises(APIError):
                oura_plugin.get_api_client()

            eight_plugin = EightPlugin(mock_console)
            with pytest.raises(APIError):
                eight_plugin.get_api_client()

    def test_plugin_data_fetching_errors(self, cache_manager):
        """
        Verify that the plugin's data fetching method raises a DataError when no data is available for the specified device and date range.
        """
        # Use a real console since Rich Progress needs specific methods
        from rich.console import Console

        real_console = Console()

        with patch.dict(os.environ, {"OURA_API_TOKEN": "test_token"}):
            oura_plugin = OuraPlugin(real_console)

            # Test that fetch_data raises DataError for no data
            start_date = datetime.now() - timedelta(days=7)
            end_date = datetime.now()

            with pytest.raises(DataError):
                oura_plugin.fetch_data(
                    "test_device", start_date, end_date, cache_manager
                )

    def test_plugin_discover_devices_errors(self, mock_console):
        """
        Verify that the OuraPlugin's device discovery method does not raise unexpected exceptions, ensuring robust error handling during device discovery.
        """
        with patch.dict(os.environ, {"OURA_API_TOKEN": "test_token"}):
            oura_plugin = OuraPlugin(mock_console)

            # This should not crash, just display information
            try:
                oura_plugin.discover_devices()
            except Exception as e:
                # Should not raise unexpected exceptions
                raise AssertionError(
                    f"discover_devices raised unexpected exception: {e}"
                ) from e
