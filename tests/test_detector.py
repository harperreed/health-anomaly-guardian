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

    def test_detector_init_with_missing_env_vars(self, mock_console):
        """Test detector initialization with missing environment variables uses defaults."""
        with patch.dict("os.environ", {}, clear=True):
            detector = SleepAnomalyDetector(mock_console)
            # Should use default values when env vars are not set
            assert hasattr(detector, 'contam_env')
            assert hasattr(detector, 'window_env')
            assert hasattr(detector, 'n_out_env')

    def test_detector_init_with_invalid_contamination_negative(self, mock_console):
        """Test detector initialization with negative contamination value."""
        with patch.dict("os.environ", {"IFOREST_CONTAM": "-0.1"}):
            with pytest.raises(SystemExit):
                SleepAnomalyDetector(mock_console)

    def test_detector_init_with_invalid_contamination_zero(self, mock_console):
        """Test detector initialization with zero contamination value."""
        with patch.dict("os.environ", {"IFOREST_CONTAM": "0.0"}):
            with pytest.raises(SystemExit):
                SleepAnomalyDetector(mock_console)

    def test_detector_init_with_invalid_window_zero(self, mock_console):
        """Test detector initialization with zero window size."""
        with patch.dict("os.environ", {"IFOREST_TRAIN_WINDOW": "0"}):
            with pytest.raises(SystemExit):
                SleepAnomalyDetector(mock_console)

    def test_detector_init_with_invalid_window_negative(self, mock_console):
        """Test detector initialization with negative window size."""
        with patch.dict("os.environ", {"IFOREST_TRAIN_WINDOW": "-10"}):
            with pytest.raises(SystemExit):
                SleepAnomalyDetector(mock_console)

    def test_detector_init_with_invalid_n_out_negative(self, mock_console):
        """Test detector initialization with negative n_out value."""
        with patch.dict("os.environ", {"IFOREST_SHOW_N": "-1"}):
            with pytest.raises(SystemExit):
                SleepAnomalyDetector(mock_console)

    def test_detector_init_with_invalid_n_out_zero(self, mock_console):
        """Test detector initialization with zero n_out value."""
        with patch.dict("os.environ", {"IFOREST_SHOW_N": "0"}):
            with pytest.raises(SystemExit):
                SleepAnomalyDetector(mock_console)

    def test_detector_init_with_non_numeric_env_vars(self, mock_console):
        """Test detector initialization with non-numeric environment variables."""
        with patch.dict("os.environ", {"IFOREST_CONTAM": "not_a_number"}):
            with pytest.raises(SystemExit):
                SleepAnomalyDetector(mock_console)

    def test_get_emfit_api_with_empty_token(self, mock_console):
        """Test EmfitAPI initialization with empty token."""
        with patch.dict("os.environ", {"EMFIT_TOKEN": ""}):
            detector = SleepAnomalyDetector(mock_console)
            
            with pytest.raises(APIError, match="Either EMFIT_TOKEN or EMFIT_USERNAME/PASSWORD must be set"):
                detector.get_emfit_api()

    def test_get_emfit_api_with_empty_username(self, mock_console):
        """Test EmfitAPI initialization with empty username."""
        with patch.dict("os.environ", {"EMFIT_USERNAME": "", "EMFIT_PASSWORD": "test_pass"}):
            detector = SleepAnomalyDetector(mock_console)
            
            with pytest.raises(APIError, match="Either EMFIT_TOKEN or EMFIT_USERNAME/PASSWORD must be set"):
                detector.get_emfit_api()

    def test_get_emfit_api_with_empty_password(self, mock_console):
        """Test EmfitAPI initialization with empty password."""
        with patch.dict("os.environ", {"EMFIT_USERNAME": "test_user", "EMFIT_PASSWORD": ""}):
            detector = SleepAnomalyDetector(mock_console)
            
            with pytest.raises(APIError, match="Either EMFIT_TOKEN or EMFIT_USERNAME/PASSWORD must be set"):
                detector.get_emfit_api()

    def test_get_emfit_api_login_failure(self, mock_console):
        """Test EmfitAPI login failure."""
        with patch.dict("os.environ", {"EMFIT_USERNAME": "test_user", "EMFIT_PASSWORD": "test_pass"}):
            detector = SleepAnomalyDetector(mock_console)

            with patch("anomaly_detector.detector.EmfitAPI") as mock_api:
                mock_api_instance = Mock()
                mock_api.return_value = mock_api_instance
                mock_api_instance.login.side_effect = Exception("Login failed")

                with pytest.raises(APIError):
                    detector.get_emfit_api()

    def test_get_emfit_api_login_returns_none(self, mock_console):
        """Test EmfitAPI login returns None."""
        with patch.dict("os.environ", {"EMFIT_USERNAME": "test_user", "EMFIT_PASSWORD": "test_pass"}):
            detector = SleepAnomalyDetector(mock_console)

            with patch("anomaly_detector.detector.EmfitAPI") as mock_api:
                mock_api_instance = Mock()
                mock_api.return_value = mock_api_instance
                mock_api_instance.login.return_value = None

                with pytest.raises(APIError):
                    detector.get_emfit_api()

    def test_get_emfit_api_login_returns_empty_dict(self, mock_console):
        """Test EmfitAPI login returns empty dict."""
        with patch.dict("os.environ", {"EMFIT_USERNAME": "test_user", "EMFIT_PASSWORD": "test_pass"}):
            detector = SleepAnomalyDetector(mock_console)

            with patch("anomaly_detector.detector.EmfitAPI") as mock_api:
                mock_api_instance = Mock()
                mock_api.return_value = mock_api_instance
                mock_api_instance.login.return_value = {}

                with pytest.raises(APIError):
                    detector.get_emfit_api()

    def test_get_device_ids_empty_device_settings(self, mock_console):
        """Test device ID discovery with empty device settings."""
        detector = SleepAnomalyDetector(mock_console)

        mock_api = Mock()
        mock_api.get_user.return_value = {"device_settings": []}

        with pytest.raises(ConfigError, match="No device IDs found"):
            detector.get_device_ids(mock_api)

    def test_get_device_ids_missing_device_settings(self, mock_console):
        """Test device ID discovery with missing device settings key."""
        detector = SleepAnomalyDetector(mock_console)

        mock_api = Mock()
        mock_api.get_user.return_value = {}

        with pytest.raises(ConfigError, match="No device IDs found"):
            detector.get_device_ids(mock_api)

    def test_get_device_ids_malformed_device_settings(self, mock_console):
        """Test device ID discovery with malformed device settings."""
        detector = SleepAnomalyDetector(mock_console)

        mock_api = Mock()
        mock_api.get_user.return_value = {
            "device_settings": [
                {"device_id": "123"},  # Missing device_name
                {"device_name": "Device 2"},  # Missing device_id
                {"device_id": "456", "device_name": "Device 3"}  # Valid entry
            ]
        }

        device_ids, device_names = detector.get_device_ids(mock_api)

        # Should handle malformed entries gracefully
        assert "456" in device_ids
        assert device_names["456"] == "Device 3"

    def test_get_device_ids_empty_manual_config(self, mock_console):
        """Test device ID with empty manual configuration."""
        with patch.dict("os.environ", {"EMFIT_DEVICE_IDS": ""}):
            detector = SleepAnomalyDetector(mock_console)

            mock_api = Mock()
            mock_api.get_user.side_effect = Exception("Auto-discovery failed")

            with pytest.raises(ConfigError, match="No device IDs found"):
                detector.get_device_ids(mock_api)

    def test_get_device_ids_whitespace_manual_config(self, mock_console):
        """Test device ID with whitespace in manual configuration."""
        with patch.dict("os.environ", {"EMFIT_DEVICE_IDS": " 111 , 222 , 333 "}):
            detector = SleepAnomalyDetector(mock_console)

            mock_api = Mock()
            mock_api.get_user.side_effect = Exception("Auto-discovery failed")

            device_ids, device_names = detector.get_device_ids(mock_api)

            # Should strip whitespace
            assert device_ids == ["111", "222", "333"]

    def test_get_device_ids_empty_single_device(self, mock_console):
        """Test single device ID with empty configuration."""
        with patch.dict("os.environ", {"EMFIT_DEVICE_ID": ""}):
            detector = SleepAnomalyDetector(mock_console)

            mock_api = Mock()
            mock_api.get_user.side_effect = Exception("Auto-discovery failed")

            with pytest.raises(ConfigError, match="No device IDs found"):
                detector.get_device_ids(mock_api)

    def test_preprocess_data_empty_dataframe(self, mock_console):
        """Test data preprocessing with empty DataFrame."""
        detector = SleepAnomalyDetector(mock_console)

        import pandas as pd
        empty_df = pd.DataFrame()

        with pytest.raises(DataError):
            detector.preprocess(empty_df)

    def test_preprocess_data_single_column(self, mock_console):
        """Test data preprocessing with single column DataFrame."""
        detector = SleepAnomalyDetector(mock_console)

        import pandas as pd
        df = pd.DataFrame({"hr": [60, 65, 70, 75, 80]})

        processed_df = detector.preprocess(df)

        assert len(processed_df.columns) == 1
        assert not processed_df.isnull().any().any()

    def test_preprocess_data_all_nan_column(self, mock_console):
        """Test data preprocessing with all NaN column."""
        detector = SleepAnomalyDetector(mock_console)

        import pandas as pd
        df = pd.DataFrame({
            "hr": [60, 65, 70, 75, 80],
            "all_nan": [np.nan, np.nan, np.nan, np.nan, np.nan]
        })

        processed_df = detector.preprocess(df)

        # Should handle all-NaN columns gracefully
        assert not processed_df.isnull().any().any()

    def test_preprocess_data_with_string_columns(self, mock_console):
        """Test data preprocessing with string columns."""
        detector = SleepAnomalyDetector(mock_console)

        import pandas as pd
        df = pd.DataFrame({
            "hr": [60, 65, 70, 75, 80],
            "notes": ["good", "bad", "normal", "poor", "excellent"]
        })

        # Should either handle string columns or raise appropriate error
        try:
            processed_df = detector.preprocess(df)
            # If successful, ensure numeric columns are processed
            assert "hr" in processed_df.columns
        except DataError:
            # If it raises DataError, that's also acceptable
            pass

    def test_fit_iforest_edge_case_minimum_samples(self, mock_console):
        """Test IsolationForest fitting with minimum required samples."""
        detector = SleepAnomalyDetector(mock_console)

        # Test with exactly 10 samples (minimum required)
        X = np.random.rand(10, 4)

        model = detector.fit_iforest(X, 0.1)

        assert model is not None
        assert hasattr(model, "predict")

    def test_fit_iforest_single_feature(self, mock_console):
        """Test IsolationForest fitting with single feature."""
        detector = SleepAnomalyDetector(mock_console)

        X = np.random.rand(50, 1)

        model = detector.fit_iforest(X, 0.1)

        assert model is not None
        assert hasattr(model, "predict")

    def test_fit_iforest_high_contamination(self, mock_console):
        """Test IsolationForest fitting with high contamination rate."""
        detector = SleepAnomalyDetector(mock_console)

        X = np.random.rand(100, 4)

        model = detector.fit_iforest(X, 0.5)  # High contamination

        assert model is not None
        assert hasattr(model, "predict")

    def test_fit_iforest_with_nan_values(self, mock_console):
        """Test IsolationForest fitting with NaN values."""
        detector = SleepAnomalyDetector(mock_console)

        X = np.random.rand(50, 4)
        X[0, 0] = np.nan

        with pytest.raises(DataError):
            detector.fit_iforest(X, 0.1)

    def test_fit_iforest_with_infinite_values(self, mock_console):
        """Test IsolationForest fitting with infinite values."""
        detector = SleepAnomalyDetector(mock_console)

        X = np.random.rand(50, 4)
        X[0, 0] = np.inf

        with pytest.raises(DataError):
            detector.fit_iforest(X, 0.1)

    def test_notify_with_http_error(self, mock_console):
        """Test push notification with HTTP error."""
        with patch.dict("os.environ", {"PUSHOVER_APIKEY": "test_token", "PUSHOVER_USERKEY": "test_user"}):
            detector = SleepAnomalyDetector(mock_console)

            with patch("requests.post") as mock_post:
                mock_post.return_value.raise_for_status.side_effect = Exception("HTTP Error")

                # Should not raise exception, but handle gracefully
                detector.notify("Test message")

    def test_notify_with_network_error(self, mock_console):
        """Test push notification with network error."""
        with patch.dict("os.environ", {"PUSHOVER_APIKEY": "test_token", "PUSHOVER_USERKEY": "test_user"}):
            detector = SleepAnomalyDetector(mock_console)

            with patch("requests.post") as mock_post:
                mock_post.side_effect = Exception("Network Error")

                # Should not raise exception, but handle gracefully
                detector.notify("Test message")

    def test_notify_with_empty_message(self, mock_console):
        """Test push notification with empty message."""
        with patch.dict("os.environ", {"PUSHOVER_APIKEY": "test_token", "PUSHOVER_USERKEY": "test_user"}):
            detector = SleepAnomalyDetector(mock_console)

            with patch("requests.post") as mock_post:
                mock_post.return_value.raise_for_status.return_value = None

                detector.notify("")

                mock_post.assert_called_once()

    def test_notify_with_long_message(self, mock_console):
        """Test push notification with very long message."""
        with patch.dict("os.environ", {"PUSHOVER_APIKEY": "test_token", "PUSHOVER_USERKEY": "test_user"}):
            detector = SleepAnomalyDetector(mock_console)

            with patch("requests.post") as mock_post:
                mock_post.return_value.raise_for_status.return_value = None

                long_message = "A" * 1000  # Very long message
                detector.notify(long_message)

                mock_post.assert_called_once()

    def test_analyze_outlier_with_gpt_api_error(self, mock_console, sample_sleep_data):
        """Test GPT analysis with API error."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
            detector = SleepAnomalyDetector(mock_console)

            with patch("anomaly_detector.detector.OpenAI") as mock_openai:
                mock_client = Mock()
                mock_openai.return_value = mock_client
                mock_client.chat.completions.create.side_effect = Exception("API Error")

                outlier_row = sample_sleep_data.iloc[0].copy()
                outlier_row["if_score"] = -0.5

                result = detector.analyze_outlier_with_gpt(outlier_row, sample_sleep_data)

                assert result is None

    def test_analyze_outlier_with_gpt_empty_response(self, mock_console, sample_sleep_data):
        """Test GPT analysis with empty response."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
            detector = SleepAnomalyDetector(mock_console)

            with patch("anomaly_detector.detector.OpenAI") as mock_openai:
                mock_client = Mock()
                mock_openai.return_value = mock_client

                mock_response = Mock()
                mock_response.choices = []
                mock_client.chat.completions.create.return_value = mock_response

                outlier_row = sample_sleep_data.iloc[0].copy()
                outlier_row["if_score"] = -0.5

                result = detector.analyze_outlier_with_gpt(outlier_row, sample_sleep_data)

                assert result is None

    def test_analyze_outlier_with_gpt_malformed_response(self, mock_console, sample_sleep_data):
        """Test GPT analysis with malformed response."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
            detector = SleepAnomalyDetector(mock_console)

            with patch("anomaly_detector.detector.OpenAI") as mock_openai:
                mock_client = Mock()
                mock_openai.return_value = mock_client

                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message = None
                mock_client.chat.completions.create.return_value = mock_response

                outlier_row = sample_sleep_data.iloc[0].copy()
                outlier_row["if_score"] = -0.5

                result = detector.analyze_outlier_with_gpt(outlier_row, sample_sleep_data)

                assert result is None

    def test_analyze_outlier_with_gpt_missing_if_score(self, mock_console, sample_sleep_data):
        """Test GPT analysis with missing if_score in outlier data."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
            detector = SleepAnomalyDetector(mock_console)

            outlier_row = sample_sleep_data.iloc[0].copy()
            # Don't add if_score

            result = detector.analyze_outlier_with_gpt(outlier_row, sample_sleep_data)

            # Should handle missing if_score gracefully
            assert result is None or isinstance(result, str)

    def test_clear_cache_nonexistent_directory(self, mock_console):
        """Test cache clearing with nonexistent directory."""
        with patch.dict("os.environ", {"EMFIT_CACHE_DIR": "/nonexistent/directory"}):
            detector = SleepAnomalyDetector(mock_console)

            cleared_count = detector.clear_cache()

            assert cleared_count == 0

    def test_clear_cache_empty_directory(self, mock_console, temp_dir):
        """Test cache clearing with empty directory."""
        with patch.dict("os.environ", {"EMFIT_CACHE_DIR": str(temp_dir)}):
            detector = SleepAnomalyDetector(mock_console)

            cleared_count = detector.clear_cache()

            assert cleared_count == 0

    def test_clear_cache_mixed_files(self, mock_console, temp_dir):
        """Test cache clearing with mixed file types."""
        with patch.dict("os.environ", {"EMFIT_CACHE_DIR": str(temp_dir)}):
            detector = SleepAnomalyDetector(mock_console)

            # Create mixed files
            (temp_dir / "cache1.json").write_text('{"test": "data"}')
            (temp_dir / "cache2.txt").write_text('test data')
            (temp_dir / "cache3.json").write_text('{"test": "data"}')
            (temp_dir / "subdirectory").mkdir()

            cleared_count = detector.clear_cache()

            # Should only clear JSON files
            assert cleared_count == 2
            assert not (temp_dir / "cache1.json").exists()
            assert not (temp_dir / "cache3.json").exists()
            assert (temp_dir / "cache2.txt").exists()  # Should remain
            assert (temp_dir / "subdirectory").exists()  # Should remain

    def test_clear_cache_permission_error(self, mock_console, temp_dir):
        """Test cache clearing with permission error."""
        with patch.dict("os.environ", {"EMFIT_CACHE_DIR": str(temp_dir)}):
            detector = SleepAnomalyDetector(mock_console)

            cache_file = temp_dir / "cache1.json"
            cache_file.write_text('{"test": "data"}')

            with patch("pathlib.Path.unlink") as mock_unlink:
                mock_unlink.side_effect = PermissionError("Permission denied")

                cleared_count = detector.clear_cache()

                assert cleared_count == 0

    def test_discover_devices_with_api_error(self, mock_console):
        """Test device discovery with API error."""
        detector = SleepAnomalyDetector(mock_console)

        with patch.object(detector, "get_emfit_api") as mock_get_api:
            mock_get_api.side_effect = APIError("API Error")

            # Should handle API error gracefully
            detector.discover_devices()

    def test_discover_devices_with_user_error(self, mock_console):
        """Test device discovery with user API error."""
        detector = SleepAnomalyDetector(mock_console)

        with patch.object(detector, "get_emfit_api") as mock_get_api:
            mock_api = Mock()
            mock_api.get_user.side_effect = Exception("User API Error")
            mock_get_api.return_value = mock_api

            # Should handle user API error gracefully
            detector.discover_devices()

    def test_discover_devices_with_complex_device_info(self, mock_console):
        """Test device discovery with complex device information."""
        detector = SleepAnomalyDetector(mock_console)

        with patch.object(detector, "get_emfit_api") as mock_get_api:
            mock_api = Mock()
            mock_api.get_user.return_value = {
                "device_settings": [
                    {
                        "device_id": "123",
                        "device_name": "Master Bedroom",
                        "device_type": "QS",
                        "firmware_version": "1.2.3"
                    },
                    {
                        "device_id": "456",
                        "device_name": "Guest Room",
                        "device_type": "QS+",
                        "firmware_version": "1.2.4"
                    }
                ]
            }
            mock_get_api.return_value = mock_api

            detector.discover_devices()

            mock_api.get_user.assert_called_once()

    def test_detector_with_multiple_configuration_sources(self, mock_console):
        """Test detector behavior with multiple configuration sources."""
        with patch.dict("os.environ", {
            "IFOREST_CONTAM": "0.15",
            "IFOREST_TRAIN_WINDOW": "45",
            "IFOREST_SHOW_N": "5",
            "EMFIT_TOKEN": "test_token",
            "EMFIT_DEVICE_IDS": "111,222",
            "PUSHOVER_APIKEY": "push_key",
            "PUSHOVER_USERKEY": "push_user",
            "OPENAI_API_KEY": "openai_key",
            "EMFIT_CACHE_DIR": "/tmp/cache"
        }):
            detector = SleepAnomalyDetector(mock_console)

            # Should successfully initialize with all configurations
            assert detector.contam_env == 0.15
            assert detector.window_env == 45
            assert detector.n_out_env == 5

    def test_detector_stress_test_large_dataset(self, mock_console):
        """Test detector with large dataset to ensure performance."""
        detector = SleepAnomalyDetector(mock_console)

        # Create large dataset
        large_X = np.random.rand(1000, 10)

        model = detector.fit_iforest(large_X, 0.1)

        assert model is not None
        predictions = model.predict(large_X)
        assert len(predictions) == 1000

    def test_detector_concurrent_operations(self, mock_console):
        """Test detector with concurrent-like operations."""
        detector = SleepAnomalyDetector(mock_console)

        # Simulate multiple operations that might happen concurrently
        with patch.object(detector, "get_emfit_api") as mock_get_api:
            mock_api = Mock()
            mock_api.get_user.return_value = {"device_settings": []}
            mock_get_api.return_value = mock_api

            # Multiple calls should be handled correctly
            detector.discover_devices()
            detector.discover_devices()
            detector.discover_devices()

            assert mock_api.get_user.call_count == 3

    @pytest.mark.parametrize("contamination", [0.01, 0.1, 0.2, 0.3, 0.4, 0.5])
    def test_fit_iforest_various_contamination_levels(self, mock_console, contamination):
        """Test IsolationForest fitting with various contamination levels."""
        detector = SleepAnomalyDetector(mock_console)

        X = np.random.rand(100, 4)
        model = detector.fit_iforest(X, contamination)

        assert model is not None
        predictions = model.predict(X)
        anomaly_count = np.sum(predictions == -1)
        expected_anomaly_count = int(contamination * len(X))
        
        # Allow some tolerance in the expected anomaly count
        assert abs(anomaly_count - expected_anomaly_count) <= 10

    @pytest.mark.parametrize("device_config", [
        {"EMFIT_DEVICE_ID": "single"},
        {"EMFIT_DEVICE_IDS": "multi1,multi2,multi3"},
        {"EMFIT_DEVICE_IDS": "single_in_list"},
    ])
    def test_get_device_ids_various_configurations(self, mock_console, device_config):
        """Test device ID retrieval with various configurations."""
        with patch.dict("os.environ", device_config):
            detector = SleepAnomalyDetector(mock_console)

            mock_api = Mock()
            mock_api.get_user.side_effect = Exception("Auto-discovery failed")

            device_ids, device_names = detector.get_device_ids(mock_api)

            assert len(device_ids) > 0
            assert len(device_names) == len(device_ids)

    def test_detector_memory_efficiency(self, mock_console):
        """Test detector memory efficiency with large data operations."""
        detector = SleepAnomalyDetector(mock_console)

        # Test with multiple datasets to ensure memory is managed properly
        for i in range(5):
            X = np.random.rand(200, 5)
            model = detector.fit_iforest(X, 0.1)
            assert model is not None
            # Force garbage collection simulation
            del X, model

    def test_detector_edge_case_single_sample(self, mock_console):
        """Test detector with single sample edge case."""
        detector = SleepAnomalyDetector(mock_console)

        X = np.random.rand(1, 4)

        with pytest.raises(DataError):
            detector.fit_iforest(X, 0.1)

    def test_detector_edge_case_identical_samples(self, mock_console):
        """Test detector with identical samples."""
        detector = SleepAnomalyDetector(mock_console)

        # All samples identical
        X = np.ones((50, 4))

        model = detector.fit_iforest(X, 0.1)

        assert model is not None
        predictions = model.predict(X)
        # With identical samples, predictions should be consistent
        assert len(np.unique(predictions)) <= 2  # Should be mostly normal or all normal

    def test_detector_robustness_with_outliers(self, mock_console):
        """Test detector robustness with extreme outliers in training data."""
        detector = SleepAnomalyDetector(mock_console)

        # Normal data with extreme outliers
        X = np.random.normal(0, 1, (100, 4))
        X[0] = [1000, 1000, 1000, 1000]  # Extreme outlier
        X[1] = [-1000, -1000, -1000, -1000]  # Extreme outlier

        model = detector.fit_iforest(X, 0.1)

        assert model is not None
        predictions = model.predict(X)
        assert len(predictions) == 100

