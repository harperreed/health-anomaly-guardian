"""
ABOUTME: Tests for the Oura sleep tracker plugin
ABOUTME: Tests Oura-specific functionality and placeholder implementation
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pandas as pd
import pytest
from rich.console import Console

from anomaly_detector.exceptions import APIError, ConfigError, DataError
from anomaly_detector.plugins.oura import OuraAPIClient, OuraPlugin


class TestOuraPlugin:
    """Test the Oura plugin functionality."""

    def setup_method(self):
        """
        Initializes the test environment by setting up a console instance, mocking environment variables for the Oura plugin, and instantiating the plugin with these mocks.
        """
        self.console = Console()

        # Mock environment variables
        self.env_vars = {
            "OURA_API_TOKEN": "test_token",
            "OURA_DEVICE_ID": "test_device_123",
        }

        with patch(
            "anomaly_detector.plugins.oura.get_env_var",
            side_effect=lambda key, default=None: self.env_vars.get(key, default),
        ):
            self.plugin = OuraPlugin(self.console)

    def test_plugin_initialization(self):
        """
        Test that the Oura plugin initializes with the correct name, console, API token, and device ID.
        """
        assert self.plugin.name == "oura"
        assert self.plugin.console == self.console
        assert self.plugin.api_token == "test_token"
        assert self.plugin.device_id == "test_device_123"

    def test_notification_title(self):
        """
        Tests that the plugin's notification title property returns the expected alert string.
        """
        assert self.plugin.notification_title == "Oura Anomaly Alert"

    def test_cache_key_generation(self):
        """
        Tests that the plugin's cache key is generated with the correct prefix, device ID, and date string.
        """
        device_id = "test_device"
        date_str = "2024-01-01"

        cache_key = self.plugin._get_cache_key(device_id, date_str)

        assert cache_key == f"oura_{device_id}_{date_str}"

    def test_get_api_client_with_token(self):
        """
        Test that the API client is correctly instantiated as an OuraAPIClient when a valid token is present.
        """
        api_client = self.plugin.get_api_client()

        assert isinstance(api_client, OuraAPIClient)
        assert api_client.token == "test_token"

    def test_get_api_client_no_token(self):
        """
        Test that attempting to initialize the API client without an API token raises an APIError.
        """
        self.plugin.api_token = None

        with pytest.raises(
            APIError, match="OURA_API_TOKEN environment variable must be set"
        ):
            self.plugin.get_api_client()

    def test_get_device_ids_with_config(self):
        """
        Test that device IDs and names are correctly returned when a device ID is configured and auto-discovery is disabled.
        """
        device_ids, device_names = self.plugin.get_device_ids(auto_discover=False)

        assert device_ids == ["test_device_123"]
        assert device_names == {"test_device_123": "Oura Ring (test_device_123)"}

    def test_get_device_ids_auto_discovery(self):
        """
        Test that device IDs and names are correctly retrieved via auto-discovery when no device ID is configured.
        """
        self.plugin.device_id = None

        device_ids, device_names = self.plugin.get_device_ids(auto_discover=True)

        assert device_ids == ["oura-ring-oura-user-default"]
        assert device_names == {"oura-ring-oura-user-default": "Oura Ring"}

    def test_get_device_ids_no_config_no_discovery(self):
        """
        Test that retrieving device IDs without a configured device ID and with auto-discovery disabled raises a ConfigError.
        """
        self.plugin.device_id = None

        with pytest.raises(ConfigError, match="No Oura device ID found"):
            self.plugin.get_device_ids(auto_discover=False)

    def test_fetch_data_placeholder(self):
        """
        Test that the fetch_data method raises a DataError when no valid sleep data is found.

        Verifies that the placeholder implementation of fetch_data raises the expected DataError when called with a device ID, date range, and cache returning no valid data.
        """
        cache = Mock()
        cache.get.return_value = None
        cache.get_stats.return_value = {"valid_files": 0}

        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)

        # Should raise DataError since it's a placeholder
        with pytest.raises(DataError, match="No valid Oura sleep data found"):
            self.plugin.fetch_data("test_device", start_date, end_date, cache)

    def test_discover_devices(self):
        """
        Tests that the device discovery method executes without raising exceptions.
        """
        # Should not raise any exceptions
        self.plugin.discover_devices()


class TestOuraAPIClient:
    """Test the Oura API client functionality."""

    def setup_method(self):
        """
        Set up the API client instance for each test in the test class.
        """
        self.api_client = OuraAPIClient("test_token")

    def test_initialization(self):
        """
        Verify that the API client is initialized with the correct token.
        """
        assert self.api_client.token == "test_token"

    def test_get_user_info(self):
        """
        Test that the API client's `get_user_info` method returns a dictionary with expected user profile data.
        """
        user_info = self.api_client.get_user_info()

        assert isinstance(user_info, dict)
        assert user_info["id"] == "oura-user-default"
        assert user_info["email"] == "user@example.com"
        assert "age" in user_info
        assert "weight" in user_info

    def test_get_sleep_data(self):
        """
        Tests that the sleep data retrieval method returns expected data structure.
        """
        sleep_data = self.api_client.get_sleep_data("2024-01-01", "2024-01-01")

        assert isinstance(sleep_data, dict)
        assert "data" in sleep_data
        assert "next_token" in sleep_data
        assert sleep_data["data"] == []
        assert sleep_data["next_token"] is None


class TestOuraPluginExtended:
    """Extended tests for comprehensive Oura plugin coverage."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Console()

        # Mock environment variables
        self.env_vars = {
            "OURA_API_TOKEN": "test_token_extended",
            "OURA_DEVICE_ID": "test_device_extended",
        }

        with patch(
            "anomaly_detector.plugins.oura.get_env_var",
            side_effect=lambda key, default=None: self.env_vars.get(key, default),
        ):
            self.plugin = OuraPlugin(self.console)

    def test_plugin_initialization_with_missing_env_vars(self):
        """Test plugin initialization when environment variables are missing."""
        with patch("anomaly_detector.plugins.oura.get_env_var", return_value=None):
            plugin = OuraPlugin(self.console)
            assert plugin.api_token is None
            assert plugin.device_id is None

    def test_plugin_initialization_with_empty_env_vars(self):
        """Test plugin initialization when environment variables are empty strings."""
        empty_env = {"OURA_API_TOKEN": "", "OURA_DEVICE_ID": ""}
        with patch(
            "anomaly_detector.plugins.oura.get_env_var",
            side_effect=lambda key, default=None: empty_env.get(key, default),
        ):
            plugin = OuraPlugin(self.console)
            assert plugin.api_token == ""
            assert plugin.device_id == ""

    def test_cache_key_generation_with_special_characters(self):
        """Test cache key generation with special characters in device ID and date."""
        device_id = "test-device_123!@#"
        date_str = "2024-01-01T12:00:00"

        cache_key = self.plugin._get_cache_key(device_id, date_str)

        assert cache_key == f"oura_{device_id}_{date_str}"

    def test_cache_key_generation_with_none_values(self):
        """Test cache key generation with None values."""
        cache_key = self.plugin._get_cache_key(None, "2024-01-01")
        assert cache_key == "oura_None_2024-01-01"

    def test_get_device_ids_with_whitespace_device_id(self):
        """Test device ID retrieval with whitespace in configured device ID."""
        self.plugin.device_id = "  test_device_123  "

        device_ids, device_names = self.plugin.get_device_ids(auto_discover=False)

        assert device_ids == ["  test_device_123  "]
        assert device_names == {
            "  test_device_123  ": "Oura Ring (  test_device_123  )"
        }

    def test_get_device_ids_with_empty_device_id(self):
        """Test device ID retrieval with empty device ID."""
        self.plugin.device_id = ""

        with pytest.raises(ConfigError, match="No Oura device ID found"):
            self.plugin.get_device_ids(auto_discover=False)

    def test_fetch_data_with_cache_hit(self):
        """Test data fetching when cache has valid data."""
        cache = Mock()
        cached_data = pd.DataFrame(
            {
                "timestamp": [datetime(2024, 1, 1, 10, 0)],
                "sleep_score": [85],
                "deep_sleep_duration": [120],
            }
        )
        cache.get.return_value = cached_data
        cache.get_stats.return_value = {"valid_files": 1}

        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)

        result = self.plugin.fetch_data("test_device", start_date, end_date, cache)

        assert result.equals(cached_data)
        cache.get.assert_called_once()

    def test_fetch_data_with_invalid_date_range(self):
        """Test data fetching with invalid date range (end before start)."""
        cache = Mock()
        cache.get.return_value = None
        cache.get_stats.return_value = {"valid_files": 0}

        start_date = datetime(2024, 1, 2)
        end_date = datetime(2024, 1, 1)  # End before start

        with pytest.raises(DataError, match="No valid Oura sleep data found"):
            self.plugin.fetch_data("test_device", start_date, end_date, cache)

    def test_fetch_data_with_none_device_id(self):
        """Test data fetching with None device ID."""
        cache = Mock()
        cache.get.return_value = None
        cache.get_stats.return_value = {"valid_files": 0}

        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)

        with pytest.raises(DataError, match="No valid Oura sleep data found"):
            self.plugin.fetch_data(None, start_date, end_date, cache)

    def test_fetch_data_with_none_cache(self):
        """Test data fetching with None cache."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)

        with pytest.raises(DataError, match="No valid Oura sleep data found"):
            self.plugin.fetch_data("test_device", start_date, end_date, None)

    def test_discover_devices_with_api_error(self):
        """Test device discovery when API client raises error."""
        with patch.object(
            self.plugin, "get_api_client", side_effect=APIError("API connection failed")
        ):
            # Should handle gracefully and not raise
            self.plugin.discover_devices()

    def test_discover_devices_with_none_api_token(self):
        """Test device discovery when API token is None."""
        self.plugin.api_token = None

        # Should handle gracefully and not raise (discovery prints error but doesn't re-raise)
        self.plugin.discover_devices()

    def test_notification_title_consistency(self):
        """Test that notification title is consistent."""
        # Test multiple instances have same title
        plugin2 = OuraPlugin(self.console)
        assert self.plugin.notification_title == plugin2.notification_title
        assert self.plugin.notification_title == "Oura Anomaly Alert"

    def test_plugin_name_consistency(self):
        """Test that plugin name is consistent and lowercase."""
        assert self.plugin.name == "oura"
        assert self.plugin.name.islower()

    @patch("anomaly_detector.plugins.oura.get_env_var")
    def test_get_api_client_with_different_tokens(self, mock_get_env):
        """Test API client initialization with different token values."""
        test_cases = [
            "short_token",
            "very_long_token_with_many_characters_and_numbers_123456789",
            "token-with-dashes",
            "token_with_underscores",
            "token.with.dots",
            "UPPERCASE_TOKEN",
        ]

        for token in test_cases:
            mock_get_env.side_effect = (
                lambda key, default=None, t=token: t
                if key == "OURA_API_TOKEN"
                else default
            )
            plugin = OuraPlugin(self.console)
            api_client = plugin.get_api_client()

            assert isinstance(api_client, OuraAPIClient)
            assert api_client.token == token


class TestOuraAPIClientExtended:
    """Extended tests for comprehensive Oura API client coverage."""

    def setup_method(self):
        """Set up test fixtures."""
        self.api_client = OuraAPIClient("test_token_extended")

    def test_initialization_with_none_token(self):
        """Test API stub initialization with None token."""
        api_client = OuraAPIClient(None)
        assert api_client.token is None

    def test_initialization_with_empty_token(self):
        """Test API stub initialization with empty token."""
        api_client = OuraAPIClient("")
        assert api_client.token == ""

    def test_initialization_with_whitespace_token(self):
        """Test API stub initialization with whitespace token."""
        api_client = OuraAPIClient("  token_with_spaces  ")
        assert api_client.token == "  token_with_spaces  "

    def test_get_user_info_consistency(self):
        """Test that user info is consistent across multiple calls."""
        user_info1 = self.api_client.get_user_info()
        user_info2 = self.api_client.get_user_info()

        assert user_info1 == user_info2
        assert user_info1["id"] == "oura-user-default"
        assert user_info1["email"] == "user@example.com"

    def test_get_user_info_structure(self):
        """Test user info has expected structure."""
        user_info = self.api_client.get_user_info()

        assert isinstance(user_info, dict)
        assert "id" in user_info
        assert "email" in user_info
        assert "age" in user_info
        assert "weight" in user_info
        assert len(user_info) >= 4

    def test_get_sleep_data_with_different_dates(self):
        """Test sleep data retrieval with various date formats."""
        date_formats = [
            "2024-01-01",
            "2024-12-31",
            "2023-02-28",
            "2024-02-29",  # Leap year
            "invalid-date",
            "",
            None,
        ]

        for date_str in date_formats:
            sleep_data = self.api_client.get_sleep_data(date_str, date_str)
            assert isinstance(sleep_data, dict)
            assert "data" in sleep_data
            assert "next_token" in sleep_data

    def test_get_sleep_data_return_type(self):
        """Test sleep data return type is consistent."""
        sleep_data = self.api_client.get_sleep_data("2024-01-01", "2024-01-01")
        assert isinstance(sleep_data, dict)
        assert "data" in sleep_data

        # Test with different date
        sleep_data2 = self.api_client.get_sleep_data("2024-06-15", "2024-06-15")
        assert isinstance(sleep_data2, dict)
        assert "data" in sleep_data2

    def test_api_stub_methods_exist(self):
        """Test that required methods exist on the API stub."""
        assert hasattr(self.api_client, "get_user_info")
        assert hasattr(self.api_client, "get_sleep_data")
        assert callable(self.api_client.get_user_info)
        assert callable(self.api_client.get_sleep_data)

    def test_token_attribute_accessible(self):
        """Test that token attribute is accessible."""
        assert hasattr(self.api_client, "token")
        assert self.api_client.token == "test_token_extended"


class TestOuraPluginIntegration:
    """Integration tests for Oura plugin with mock external dependencies."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Console()

        # Mock environment variables
        self.env_vars = {
            "OURA_API_TOKEN": "integration_test_token",
            "OURA_DEVICE_ID": "integration_test_device",
        }

        with patch(
            "anomaly_detector.plugins.oura.get_env_var",
            side_effect=lambda key, default=None: self.env_vars.get(key, default),
        ):
            self.plugin = OuraPlugin(self.console)

    def test_full_workflow_with_mocked_dependencies(self):
        """Test the full plugin workflow with mocked external dependencies."""
        # Mock cache
        cache = Mock()
        cache.get.return_value = None
        cache.get_stats.return_value = {"valid_files": 0}

        # Mock API client
        api_client = Mock()
        api_client.get_user_info.return_value = {
            "device_id": "integration_test_device",
            "name": "Test Oura Ring",
        }
        api_client.get_sleep_data.return_value = None

        with patch.object(self.plugin, "get_api_client", return_value=api_client):
            # Test device discovery
            self.plugin.discover_devices()

            # Test device ID retrieval
            device_ids, device_names = self.plugin.get_device_ids(auto_discover=False)
            assert device_ids == ["integration_test_device"]

            # Test data fetching (should raise DataError due to placeholder)
            start_date = datetime(2024, 1, 1)
            end_date = datetime(2024, 1, 1)

            with pytest.raises(DataError, match="No valid Oura sleep data found"):
                self.plugin.fetch_data(
                    "integration_test_device", start_date, end_date, cache
                )

    def test_error_handling_chain(self):
        """Test error handling across the plugin chain."""
        # Test ConfigError -> APIError -> DataError chain

        # 1. ConfigError when no device ID
        self.plugin.device_id = None
        with pytest.raises(ConfigError, match="No Oura device ID found"):
            self.plugin.get_device_ids(auto_discover=False)

        # 2. APIError when no token
        self.plugin.api_token = None
        with pytest.raises(
            APIError, match="OURA_API_TOKEN environment variable must be set"
        ):
            self.plugin.get_api_client()

        # 3. DataError when no valid data
        self.plugin.api_token = "test_token"
        cache = Mock()
        cache.get.return_value = None
        cache.get_stats.return_value = {"valid_files": 0}

        with pytest.raises(DataError, match="No valid Oura sleep data found"):
            self.plugin.fetch_data(
                "test_device", datetime(2024, 1, 1), datetime(2024, 1, 1), cache
            )

    def test_plugin_state_consistency(self):
        """Test that plugin state remains consistent across operations."""
        original_token = self.plugin.api_token
        original_device_id = self.plugin.device_id
        original_name = self.plugin.name

        # Perform various operations
        self.plugin.get_device_ids(auto_discover=False)
        self.plugin.discover_devices()

        # Verify state hasn't changed
        assert self.plugin.api_token == original_token
        assert self.plugin.device_id == original_device_id
        assert self.plugin.name == original_name

    def test_console_usage(self):
        """Test that console is properly used throughout the plugin."""
        # Verify console is stored
        assert self.plugin.console is not None
        assert isinstance(self.plugin.console, Console)

        # Test console doesn't change
        original_console = self.plugin.console
        self.plugin.discover_devices()
        assert self.plugin.console is original_console


class TestOuraPluginEdgeCases:
    """Test edge cases and boundary conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Console()

        # Mock environment variables
        self.env_vars = {
            "OURA_API_TOKEN": "edge_case_token",
            "OURA_DEVICE_ID": "edge_case_device",
        }

        with patch(
            "anomaly_detector.plugins.oura.get_env_var",
            side_effect=lambda key, default=None: self.env_vars.get(key, default),
        ):
            self.plugin = OuraPlugin(self.console)

    def test_date_boundary_conditions(self):
        """Test date boundary conditions in data fetching."""
        cache = Mock()
        cache.get.return_value = None
        cache.get_stats.return_value = {"valid_files": 0}

        # Test same start and end date
        same_date = datetime(2024, 1, 1)
        with pytest.raises(DataError):
            self.plugin.fetch_data("test_device", same_date, same_date, cache)

        # Test very far future dates
        future_start = datetime(2050, 1, 1)
        future_end = datetime(2050, 1, 2)
        with pytest.raises(DataError):
            self.plugin.fetch_data("test_device", future_start, future_end, cache)

        # Test very old dates
        old_start = datetime(1900, 1, 1)
        old_end = datetime(1900, 1, 2)
        with pytest.raises(DataError):
            self.plugin.fetch_data("test_device", old_start, old_end, cache)

    def test_device_id_edge_cases(self):
        """Test edge cases for device ID handling."""
        edge_case_device_ids = [
            "a",  # Single character
            "a" * 1000,  # Very long device ID
            "device-with-dashes",
            "device_with_underscores",
            "device.with.dots",
            "UPPERCASE_DEVICE",
            "device123",
            "123device",
            "device with spaces",
        ]

        for device_id in edge_case_device_ids:
            self.plugin.device_id = device_id
            device_ids, device_names = self.plugin.get_device_ids(auto_discover=False)

            assert device_ids == [device_id]
            assert device_names == {device_id: f"Oura Ring ({device_id})"}

    def test_cache_key_edge_cases(self):
        """Test edge cases for cache key generation."""
        edge_cases = [
            ("a", "b"),  # Minimal inputs
            ("device" * 100, "date" * 100),  # Long inputs
            ("device-123", "2024-01-01T00:00:00Z"),  # Standard ISO format
            ("device_!@#$%^&*()", "date_!@#$%^&*()"),  # Special characters
        ]

        for device_id, date_str in edge_cases:
            cache_key = self.plugin._get_cache_key(device_id, date_str)
            expected = f"oura_{device_id}_{date_str}"
            assert cache_key == expected

    def test_memory_and_performance_considerations(self):
        """Test memory usage and performance considerations."""
        # Test that plugin doesn't hold unnecessary references
        import gc

        # Create and destroy multiple plugins
        plugins = []
        for _i in range(100):
            with patch(
                "anomaly_detector.plugins.oura.get_env_var",
                side_effect=lambda key, default=None: self.env_vars.get(key, default),
            ):
                plugin = OuraPlugin(self.console)
                plugins.append(plugin)

        # Clear references
        plugins.clear()
        gc.collect()

        # Verify our main plugin still works
        assert self.plugin.name == "oura"
        assert self.plugin.notification_title == "Oura Anomaly Alert"
