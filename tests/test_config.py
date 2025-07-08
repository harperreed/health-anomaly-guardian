"""
ABOUTME: Unit tests for configuration utilities
ABOUTME: Tests environment variable loading and validation functions
"""

import os
from unittest.mock import patch

import pytest

from anomaly_detector.config import get_env_float, get_env_int, get_env_var
from anomaly_detector.exceptions import ConfigError


class TestGetEnvVar:
    """Test get_env_var function."""

    def test_get_existing_env_var(self):
        """Test getting an existing environment variable."""
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            result = get_env_var("TEST_VAR")
            assert result == "test_value"

    def test_get_missing_env_var_with_default(self):
        """Test getting a missing environment variable with default."""
        result = get_env_var("MISSING_VAR", default="default_value")
        assert result == "default_value"

    def test_get_missing_env_var_without_default(self):
        """Test getting a missing environment variable without default."""
        result = get_env_var("MISSING_VAR")
        assert result is None

    def test_get_required_env_var_missing(self):
        """Test getting a required environment variable that is missing."""
        with pytest.raises(
            ConfigError, match="Required environment variable 'REQUIRED_VAR' not set"
        ):
            get_env_var("REQUIRED_VAR", required=True)

    def test_get_required_env_var_empty(self):
        """Test getting a required environment variable that is empty."""
        with patch.dict(os.environ, {"EMPTY_VAR": ""}):
            with pytest.raises(
                ConfigError, match="Required environment variable 'EMPTY_VAR' not set"
            ):
                get_env_var("EMPTY_VAR", required=True)

    def test_get_required_env_var_exists(self):
        """Test getting a required environment variable that exists."""
        with patch.dict(os.environ, {"REQUIRED_VAR": "required_value"}):
            result = get_env_var("REQUIRED_VAR", required=True)
            assert result == "required_value"


class TestGetEnvInt:
    """Test get_env_int function."""

    def test_get_valid_int_env_var(self):
        """Test getting a valid integer environment variable."""
        with patch.dict(os.environ, {"INT_VAR": "42"}):
            result = get_env_int("INT_VAR", default=10)
            assert result == 42

    def test_get_missing_int_env_var_uses_default(self):
        """Test getting a missing integer environment variable uses default."""
        result = get_env_int("MISSING_INT_VAR", default=100)
        assert result == 100

    def test_get_invalid_int_env_var_raises_error(self):
        """Test getting an invalid integer environment variable raises error."""
        with patch.dict(os.environ, {"INVALID_INT": "not_a_number"}):
            with pytest.raises(
                ConfigError, match="Invalid integer value for 'INVALID_INT'"
            ):
                get_env_int("INVALID_INT", default=10)

    def test_get_float_int_env_var_raises_error(self):
        """Test getting a float value for integer environment variable raises error."""
        with patch.dict(os.environ, {"FLOAT_INT": "42.5"}):
            with pytest.raises(
                ConfigError, match="Invalid integer value for 'FLOAT_INT'"
            ):
                get_env_int("FLOAT_INT", default=10)

    def test_get_negative_int_env_var(self):
        """Test getting a negative integer environment variable."""
        with patch.dict(os.environ, {"NEG_INT": "-15"}):
            result = get_env_int("NEG_INT", default=10)
            assert result == -15


class TestGetEnvFloat:
    """Test get_env_float function."""

    def test_get_valid_float_env_var(self):
        """Test getting a valid float environment variable."""
        with patch.dict(os.environ, {"FLOAT_VAR": "3.14"}):
            result = get_env_float("FLOAT_VAR", default=1.0)
            assert result == 3.14

    def test_get_valid_int_as_float_env_var(self):
        """Test getting a valid integer as float environment variable."""
        with patch.dict(os.environ, {"INT_FLOAT_VAR": "42"}):
            result = get_env_float("INT_FLOAT_VAR", default=1.0)
            assert result == 42.0

    def test_get_missing_float_env_var_uses_default(self):
        """Test getting a missing float environment variable uses default."""
        result = get_env_float("MISSING_FLOAT_VAR", default=2.5)
        assert result == 2.5

    def test_get_invalid_float_env_var_raises_error(self):
        """Test getting an invalid float environment variable raises error."""
        with patch.dict(os.environ, {"INVALID_FLOAT": "not_a_number"}):
            with pytest.raises(
                ConfigError, match="Invalid float value for 'INVALID_FLOAT'"
            ):
                get_env_float("INVALID_FLOAT", default=1.0)

    def test_get_negative_float_env_var(self):
        """Test getting a negative float environment variable."""
        with patch.dict(os.environ, {"NEG_FLOAT": "-2.5"}):
            result = get_env_float("NEG_FLOAT", default=1.0)
            assert result == -2.5

    def test_get_scientific_notation_float_env_var(self):
        """Test getting a scientific notation float environment variable."""
        with patch.dict(os.environ, {"SCI_FLOAT": "1.5e-3"}):
            result = get_env_float("SCI_FLOAT", default=1.0)
            assert result == 0.0015
