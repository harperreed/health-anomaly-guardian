"""
ABOUTME: Unit tests for the main SleepAnomalyDetector class
ABOUTME: Tests ML algorithms, API integration, and core detection functionality
"""

from unittest.mock import Mock, patch

import numpy as np
import pytest

from anomaly_detector.detector import SleepAnomalyDetector
from anomaly_detector.exceptions import APIError, ConfigError, DataError


class TestSleepAnomalyDetector:
    """Test SleepAnomalyDetector class."""

    def test_detector_init_with_valid_config(self, mock_console):
        """Test detector initialization with valid configuration."""
        with patch.dict(
            "os.environ",
            {
                "IFOREST_CONTAM": "0.1",
                "IFOREST_TRAIN_WINDOW": "30",
                "IFOREST_SHOW_N": "3",
            },
        ):
            detector = SleepAnomalyDetector(mock_console)
            assert detector.contam_env == 0.1
            assert detector.window_env == 30
            assert detector.n_out_env == 3

    def test_detector_init_with_invalid_contamination(self, mock_console):
        """Test detector initialization with invalid contamination value."""
        with patch.dict("os.environ", {"IFOREST_CONTAM": "1.5"}):
            with pytest.raises(SystemExit):
                SleepAnomalyDetector(mock_console)

    def test_detector_init_with_invalid_window(self, mock_console):
        """Test detector initialization with invalid window size."""
        with patch.dict("os.environ", {"IFOREST_TRAIN_WINDOW": "5"}):
            with pytest.raises(SystemExit):
                SleepAnomalyDetector(mock_console)

    def test_get_emfit_api_with_token(self, mock_console):
        """Test EmfitAPI initialization with token."""
        with patch.dict("os.environ", {"EMFIT_TOKEN": "test_token"}):
            detector = SleepAnomalyDetector(mock_console)

            with patch("anomaly_detector.detector.EmfitAPI") as mock_api:
                _ = detector.get_emfit_api()
                mock_api.assert_called_once_with("test_token")

    def test_get_emfit_api_with_credentials(self, mock_console):
        """Test EmfitAPI initialization with username/password."""
        with patch.dict(
            "os.environ", {"EMFIT_USERNAME": "test_user", "EMFIT_PASSWORD": "test_pass"}
        ):
            detector = SleepAnomalyDetector(mock_console)

            with patch("anomaly_detector.detector.EmfitAPI") as mock_api:
                mock_api_instance = Mock()
                mock_api.return_value = mock_api_instance
                mock_api_instance.login.return_value = {"token": "login_token"}

                _ = detector.get_emfit_api()
                mock_api_instance.login.assert_called_once_with(
                    "test_user", "test_pass"
                )

    def test_get_emfit_api_no_credentials(self, mock_console):
        """Test EmfitAPI initialization without credentials."""
        with patch.dict("os.environ", {}, clear=True):
            detector = SleepAnomalyDetector(mock_console)

            with pytest.raises(
                APIError,
                match="Either EMFIT_TOKEN or EMFIT_USERNAME/PASSWORD must be set",
            ):
                detector.get_emfit_api()

    def test_get_device_ids_auto_discovery(self, mock_console):
        """Test device ID auto-discovery."""
        detector = SleepAnomalyDetector(mock_console)

        mock_api = Mock()
        mock_api.get_user.return_value = {
            "device_settings": [
                {"device_id": "123", "device_name": "Device 1"},
                {"device_id": "456", "device_name": "Device 2"},
            ]
        }

        device_ids, device_names = detector.get_device_ids(mock_api)

        assert device_ids == ["123", "456"]
        assert device_names == {"123": "Device 1", "456": "Device 2"}

    def test_get_device_ids_manual_config(self, mock_console):
        """Test device ID manual configuration."""
        with patch.dict("os.environ", {"EMFIT_DEVICE_IDS": "111,222,333"}):
            detector = SleepAnomalyDetector(mock_console)

            mock_api = Mock()
            mock_api.get_user.side_effect = Exception("Auto-discovery failed")

            device_ids, device_names = detector.get_device_ids(mock_api)

            assert device_ids == ["111", "222", "333"]
            assert device_names == {"111": "111", "222": "222", "333": "333"}

    def test_get_device_ids_single_device(self, mock_console):
        """Test single device ID configuration."""
        with patch.dict("os.environ", {"EMFIT_DEVICE_ID": "single_device"}):
            detector = SleepAnomalyDetector(mock_console)

            mock_api = Mock()
            mock_api.get_user.side_effect = Exception("Auto-discovery failed")

            device_ids, device_names = detector.get_device_ids(mock_api)

            assert device_ids == ["single_device"]
            assert device_names == {"single_device": "single_device"}

    def test_get_device_ids_no_config(self, mock_console):
        """Test device ID with no configuration."""
        with patch.dict("os.environ", {}, clear=True):
            detector = SleepAnomalyDetector(mock_console)

            mock_api = Mock()
            mock_api.get_user.side_effect = Exception("Auto-discovery failed")

            with pytest.raises(ConfigError, match="No device IDs found"):
                detector.get_device_ids(mock_api)

    def test_preprocess_data(self, mock_console, sample_sleep_data):
        """Test data preprocessing."""
        detector = SleepAnomalyDetector(mock_console)

        # Add some missing values
        df = sample_sleep_data.copy()
        df.loc[0, "hr"] = np.nan
        original_hr_0 = df.loc[0, "hr"]

        processed_df = detector.preprocess(df)

        # Check that missing values are filled
        assert not processed_df.isnull().any().any()
        # The NaN should be replaced with median
        assert processed_df.loc[0, "hr"] != original_hr_0  # Should not be NaN anymore
        assert processed_df.loc[0, "hr"] == df["hr"].median()  # Should be median

    def test_preprocess_data_error(self, mock_console):
        """Test data preprocessing with error."""
        detector = SleepAnomalyDetector(mock_console)

        # Pass invalid data
        with pytest.raises(DataError):
            detector.preprocess("invalid_data")

    def test_fit_iforest_success(self, mock_console, sample_features):
        """Test IsolationForest fitting with valid data."""
        detector = SleepAnomalyDetector(mock_console)

        model = detector.fit_iforest(sample_features, 0.1)

        assert model is not None
        assert hasattr(model, "predict")
        assert hasattr(model, "decision_function")

    def test_fit_iforest_insufficient_data(self, mock_console):
        """Test IsolationForest fitting with insufficient data."""
        detector = SleepAnomalyDetector(mock_console)

        # Only 5 samples - should fail
        X = np.random.rand(5, 4)

        with pytest.raises(DataError, match="Insufficient data for anomaly detection"):
            detector.fit_iforest(X, 0.1)

    def test_notify_with_credentials(self, mock_console):
        """Test push notification with valid credentials."""
        with patch.dict(
            "os.environ",
            {"PUSHOVER_APIKEY": "test_token", "PUSHOVER_USERKEY": "test_user"},
        ):
            detector = SleepAnomalyDetector(mock_console)

            with patch("requests.post") as mock_post:
                mock_post.return_value.raise_for_status.return_value = None

                detector.notify("Test message")

                mock_post.assert_called_once()
                args, kwargs = mock_post.call_args
                assert "https://api.pushover.net/1/messages.json" in args
                assert kwargs["data"]["message"] == "Test message"

    def test_notify_without_credentials(self, mock_console):
        """Test push notification without credentials."""
        detector = SleepAnomalyDetector(mock_console)

        # Should not raise an exception, just log a warning
        detector.notify("Test message")

    def test_analyze_outlier_with_gpt(self, mock_console, sample_sleep_data):
        """Test GPT analysis of outlier."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
            detector = SleepAnomalyDetector(mock_console)

            with patch("anomaly_detector.detector.OpenAI") as mock_openai:
                mock_client = Mock()
                mock_openai.return_value = mock_client

                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message.content = "Test analysis"
                mock_client.chat.completions.create.return_value = mock_response

                # Add required if_score attribute to the sample data
                outlier_row = sample_sleep_data.iloc[0].copy()
                outlier_row["if_score"] = -0.5

                result = detector.analyze_outlier_with_gpt(
                    outlier_row, sample_sleep_data
                )

                assert result == "Test analysis"

    def test_analyze_outlier_without_api_key(self, mock_console, sample_sleep_data):
        """Test GPT analysis without API key."""
        detector = SleepAnomalyDetector(mock_console)

        outlier_row = sample_sleep_data.iloc[0]
        result = detector.analyze_outlier_with_gpt(outlier_row, sample_sleep_data)

        assert result is None

    def test_clear_cache(self, mock_console, temp_dir):
        """Test cache clearing functionality."""
        with patch.dict("os.environ", {"EMFIT_CACHE_DIR": str(temp_dir)}):
            detector = SleepAnomalyDetector(mock_console)

            # Create some dummy cache files
            cache_files = [
                temp_dir / "cache1.json",
                temp_dir / "cache2.json",
                temp_dir / "cache3.json",
            ]

            for cache_file in cache_files:
                cache_file.write_text('{"test": "data"}')

            cleared_count = detector.clear_cache()

            assert cleared_count == 3
            assert not any(cache_file.exists() for cache_file in cache_files)

    def test_discover_devices(self, mock_console):
        """Test device discovery functionality."""
        detector = SleepAnomalyDetector(mock_console)

        with patch.object(detector, "get_emfit_api") as mock_get_api:
            mock_api = Mock()
            mock_api.get_user.return_value = {"device_settings": []}
            mock_get_api.return_value = mock_api

            detector.discover_devices()

            mock_api.get_user.assert_called_once()
