"""
ABOUTME: End-to-end tests for the complete anomaly detection workflow
ABOUTME: Tests full system integration from CLI to API to output
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from anomaly_detector.cli import main


class TestEndToEnd:
    """End-to-end integration tests."""

    @pytest.mark.skipif(
        not all(
            [
                os.getenv("EMFIT_USERNAME"),
                os.getenv("EMFIT_PASSWORD"),
                os.getenv("EMFIT_DEVICE_ID"),
            ]
        ),
        reason="E2E tests require real Emfit API credentials",
    )
    def test_real_api_integration(self):
        """Test with real Emfit API (requires credentials)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up environment for test
            test_env = {
                "EMFIT_CACHE_DIR": temp_dir,
                "EMFIT_CACHE_ENABLED": "true",
                "EMFIT_CACHE_TTL_HOURS": "1",
                "IFOREST_TRAIN_WINDOW": "30",  # Shorter window for faster testing
                "IFOREST_CONTAM": "0.1",
                "IFOREST_SHOW_N": "3",
            }

            with patch.dict(os.environ, test_env):
                with patch("sys.argv", ["anomaly-detector", "--train-days", "30"]):
                    # Should not raise an exception
                    try:
                        main()
                    except SystemExit as e:
                        # Exit code 0 is success
                        assert e.code == 0

    def test_cli_with_mock_api(self):
        """Test CLI with mocked API for reproducible testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_env = {
                "EMFIT_TOKEN": "fake_token",
                "EMFIT_DEVICE_ID": "test_device",
                "EMFIT_CACHE_DIR": temp_dir,
                "EMFIT_CACHE_ENABLED": "false",  # Disable cache for cleaner test
                "IFOREST_TRAIN_WINDOW": "30",
                "IFOREST_CONTAM": "0.1",
                "IFOREST_SHOW_N": "3",
            }

            # Mock the EmfitAPI
            with patch("anomaly_detector.detector.EmfitAPI") as mock_api_class:
                mock_api = Mock()
                mock_api_class.return_value = mock_api

                # Mock API responses
                mock_api.get_user.return_value = {
                    "device_settings": [
                        {"device_id": "test_device", "device_name": "Test Device"}
                    ]
                }

                # Generate mock sleep data for 30 days
                import datetime
                from datetime import timedelta

                base_date = datetime.datetime.now() - timedelta(days=30)
                mock_trends_responses = []

                for i in range(31):  # 31 days of data
                    current_date = base_date + timedelta(days=i)
                    mock_trends_responses.append(
                        {
                            "data": [
                                {
                                    "date": current_date.strftime("%Y-%m-%d"),
                                    "meas_hr_avg": 60
                                    + (i % 10),  # Vary heart rate 60-70
                                    "meas_rr_avg": 15
                                    + (i % 3),  # Vary respiratory rate 15-18
                                    "sleep_duration": 7.5
                                    + (i % 2) * 0.5,  # Vary duration 7.5-8
                                    "sleep_score": 80 + (i % 20),  # Vary score 80-100
                                    "tossnturn_count": 5
                                    + (i % 5),  # Vary toss & turn 5-10
                                }
                            ]
                        }
                    )

                # Make the last day an obvious outlier
                mock_trends_responses[-1]["data"][0].update(
                    {
                        "meas_hr_avg": 100,  # Very high heart rate
                        "meas_rr_avg": 25,  # High respiratory rate
                        "sleep_duration": 4,  # Short sleep
                        "sleep_score": 30,  # Low score
                        "tossnturn_count": 50,  # High movement
                    }
                )

                mock_api.get_trends.side_effect = mock_trends_responses

                with patch.dict(os.environ, test_env):
                    with patch("sys.argv", ["anomaly-detector", "--train-days", "30"]):
                        try:
                            main()
                        except SystemExit as e:
                            # Should exit successfully
                            assert e.code == 0

    def test_cli_help(self):
        """Test CLI help output."""
        with patch("sys.argv", ["anomaly-detector", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # Help should exit with code 0
            assert exc_info.value.code == 0

    def test_cli_discover_devices(self):
        """Test device discovery command."""
        test_env = {
            "EMFIT_TOKEN": "fake_token",
        }

        with patch("anomaly_detector.detector.EmfitAPI") as mock_api_class:
            mock_api = Mock()
            mock_api_class.return_value = mock_api
            mock_api.get_user.return_value = {
                "device_settings": [
                    {"device_id": "123", "device_name": "Device 1"},
                    {"device_id": "456", "device_name": "Device 2"},
                ]
            }

            with patch.dict(os.environ, test_env):
                with patch("sys.argv", ["anomaly-detector", "--discover-devices"]):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    # Should exit successfully after showing devices
                    assert exc_info.value.code == 0

    def test_cli_clear_cache(self):
        """Test cache clearing command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_env = {
                "EMFIT_CACHE_DIR": temp_dir,
                "EMFIT_TOKEN": "fake_token",
            }

            # Create some dummy cache files
            cache_files = [
                Path(temp_dir) / "cache1.json",
                Path(temp_dir) / "cache2.json",
            ]

            for cache_file in cache_files:
                cache_file.write_text('{"test": "data"}')

            with patch.dict(os.environ, test_env):
                with patch("sys.argv", ["anomaly-detector", "--clear-cache"]):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    # Should exit successfully after clearing cache
                    assert exc_info.value.code == 0

                    # Cache files should be gone
                    assert not any(cache_file.exists() for cache_file in cache_files)

    def test_cli_invalid_arguments(self):
        """Test CLI with invalid arguments."""
        test_env = {
            "EMFIT_TOKEN": "fake_token",
            "EMFIT_DEVICE_ID": "test_device",
            "IFOREST_CONTAM": "2.0",  # Invalid contamination > 1
        }

        with patch.dict(os.environ, test_env):
            with patch("sys.argv", ["anomaly-detector"]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                # Should exit with error code
                assert exc_info.value.code == 1

    def test_cli_no_credentials(self):
        """Test CLI without any credentials."""
        # Clear any existing credentials
        test_env = {
            "EMFIT_TOKEN": "",
            "EMFIT_USERNAME": "",
            "EMFIT_PASSWORD": "",
        }

        with patch.dict(os.environ, test_env, clear=True):
            with patch("sys.argv", ["anomaly-detector"]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                # Should exit with error code
                assert exc_info.value.code == 1

    def test_cli_gpt_analysis_flag(self):
        """Test CLI with GPT analysis enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_env = {
                "EMFIT_TOKEN": "fake_token",
                "EMFIT_DEVICE_ID": "test_device",
                "EMFIT_CACHE_DIR": temp_dir,
                "OPENAI_API_KEY": "fake_openai_key",
                "IFOREST_TRAIN_WINDOW": "30",
            }

            with patch("anomaly_detector.detector.EmfitAPI") as mock_api_class:
                mock_api = Mock()
                mock_api_class.return_value = mock_api

                # Mock minimal successful responses
                mock_api.get_user.return_value = {
                    "device_settings": [
                        {"device_id": "test_device", "device_name": "Test"}
                    ]
                }

                # Mock sufficient data for ML
                import datetime
                from datetime import timedelta

                base_date = datetime.datetime.now() - timedelta(days=30)
                mock_trends_responses = []

                for i in range(31):
                    current_date = base_date + timedelta(days=i)
                    mock_trends_responses.append(
                        {
                            "data": [
                                {
                                    "date": current_date.strftime("%Y-%m-%d"),
                                    "meas_hr_avg": 65,
                                    "meas_rr_avg": 16,
                                    "sleep_duration": 8,
                                    "sleep_score": 85,
                                    "tossnturn_count": 5,
                                }
                            ]
                        }
                    )

                mock_api.get_trends.side_effect = mock_trends_responses

                with patch("anomaly_detector.detector.OpenAI") as mock_openai:
                    mock_client = Mock()
                    mock_openai.return_value = mock_client
                    mock_response = Mock()
                    mock_response.choices = [Mock()]
                    mock_response.choices[0].message.content = "Test GPT analysis"
                    mock_client.chat.completions.create.return_value = mock_response

                    with patch.dict(os.environ, test_env):
                        with patch("sys.argv", ["anomaly-detector", "--gpt-analysis"]):
                            try:
                                main()
                            except SystemExit as e:
                                assert e.code == 0
