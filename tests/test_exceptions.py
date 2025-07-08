"""
ABOUTME: Unit tests for custom exception classes
ABOUTME: Tests that custom exceptions work correctly and inherit from Exception
"""

import pytest

from anomaly_detector.exceptions import APIError, ConfigError, DataError


class TestConfigError:
    """Test ConfigError exception."""

    def test_config_error_inherits_from_exception(self):
        """Test that ConfigError inherits from Exception."""
        assert issubclass(ConfigError, Exception)

    def test_config_error_can_be_raised(self):
        """Test that ConfigError can be raised."""
        with pytest.raises(ConfigError):
            raise ConfigError("Test configuration error")

    def test_config_error_message(self):
        """Test that ConfigError preserves error message."""
        message = "Invalid configuration value"
        with pytest.raises(ConfigError, match=message):
            raise ConfigError(message)

    def test_config_error_empty_message(self):
        """Test that ConfigError works with empty message."""
        with pytest.raises(ConfigError):
            raise ConfigError()


class TestAPIError:
    """Test APIError exception."""

    def test_api_error_inherits_from_exception(self):
        """Test that APIError inherits from Exception."""
        assert issubclass(APIError, Exception)

    def test_api_error_can_be_raised(self):
        """Test that APIError can be raised."""
        with pytest.raises(APIError):
            raise APIError("Test API error")

    def test_api_error_message(self):
        """Test that APIError preserves error message."""
        message = "API authentication failed"
        with pytest.raises(APIError, match=message):
            raise APIError(message)

    def test_api_error_with_details(self):
        """Test that APIError works with detailed messages."""
        message = "Failed to connect to Emfit API: Connection timeout after 30 seconds"
        with pytest.raises(APIError, match="Failed to connect to Emfit API"):
            raise APIError(message)


class TestDataError:
    """Test DataError exception."""

    def test_data_error_inherits_from_exception(self):
        """Test that DataError inherits from Exception."""
        assert issubclass(DataError, Exception)

    def test_data_error_can_be_raised(self):
        """Test that DataError can be raised."""
        with pytest.raises(DataError):
            raise DataError("Test data error")

    def test_data_error_message(self):
        """Test that DataError preserves error message."""
        message = "Insufficient data for processing"
        with pytest.raises(DataError, match=message):
            raise DataError(message)

    def test_data_error_multiline_message(self):
        """Test that DataError works with multiline messages."""
        message = (
            "Data validation failed:\n- Missing required columns\n- Invalid date format"
        )
        with pytest.raises(DataError, match="Data validation failed"):
            raise DataError(message)


class TestExceptionChaining:
    """Test exception chaining and inheritance."""

    def test_all_exceptions_are_distinct(self):
        """Test that all custom exceptions are distinct types."""
        assert ConfigError != APIError
        assert ConfigError != DataError
        assert APIError != DataError

    def test_exception_instances_have_correct_types(self):
        """Test that exception instances have correct types."""
        config_err = ConfigError("config")
        api_err = APIError("api")
        data_err = DataError("data")

        assert isinstance(config_err, ConfigError)
        assert isinstance(api_err, APIError)
        assert isinstance(data_err, DataError)

        assert not isinstance(config_err, APIError)
        assert not isinstance(api_err, DataError)
        assert not isinstance(data_err, ConfigError)

    def test_exceptions_can_be_caught_as_base_exception(self):
        """Test that custom exceptions can be caught as base Exception."""
        try:
            raise ConfigError("test")
        except Exception as e:
            assert isinstance(e, ConfigError)

        try:
            raise APIError("test")
        except Exception as e:
            assert isinstance(e, APIError)

        try:
            raise DataError("test")
        except Exception as e:
            assert isinstance(e, DataError)
