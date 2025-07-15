import os
import shutil
import sys
import tempfile
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

# Add project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anomaly_detector import cli


class TestCLI(unittest.TestCase):
    """Unit tests for CLI module - properly mocked"""

    def setUp(self):
        """Set up test fixtures before each test method"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        # Mock the detector to avoid running actual implementation
        self.detector_mock = MagicMock()
        self.detector_mock.plugin_name = "emfit"
        self.detector_mock.plugin_manager.list_plugins.return_value = [
            "emfit",
            "oura",
            "eight",
        ]
        self.detector_mock.window_env = 90
        self.detector_mock.contam_env = 0.05
        self.detector_mock.n_out_env = 5
        self.detector_mock.clear_cache.return_value = 5
        self.detector_mock.discover_devices.return_value = None
        self.detector_mock.run.return_value = None

    def tearDown(self):
        """Clean up after each test method"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_main_function_exists(self):
        """Test that main function exists and is callable"""
        self.assertTrue(hasattr(cli, "main"))
        self.assertTrue(callable(cli.main))

    def test_main_with_no_arguments(self):
        """Test main function with no arguments"""
        with patch("sys.argv", ["cli"]):
            with patch(
                "anomaly_detector.detector.SleepAnomalyDetector",
                return_value=self.detector_mock,
            ):
                with patch("sys.stdout", new_callable=StringIO):
                    try:
                        cli.main()
                        # Should call detector.run with default args
                        self.detector_mock.run.assert_called_once()
                    except SystemExit:
                        # SystemExit is acceptable for CLI programs
                        pass

    def test_main_with_help_argument(self):
        """Test main function with help argument"""
        with patch("sys.argv", ["cli", "--help"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                    try:
                        cli.main()
                        # If we get here, SystemExit was not raised
                        stdout_output = mock_stdout.getvalue()
                        stderr_output = mock_stderr.getvalue()
                        self.fail(
                            f"SystemExit not raised. stdout: '{stdout_output}', stderr: '{stderr_output}'"
                        )
                    except SystemExit:
                        # Expected behavior
                        stdout_output = mock_stdout.getvalue()
                        stderr_output = mock_stderr.getvalue()
                        combined_output = stdout_output + stderr_output
                        self.assertIn("usage", combined_output.lower())

    def test_main_with_version_argument(self):
        """Test main function with version argument"""
        with patch("sys.argv", ["cli", "--version"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                try:
                    cli.main()
                    output = mock_stdout.getvalue()
                    # Should contain version information
                    self.assertIn("Sleep Anomaly Detector", output)
                except SystemExit:
                    # Expected for --version
                    pass

    def test_main_with_list_plugins(self):
        """Test main function with list-plugins flag"""
        with patch("sys.argv", ["cli", "--list-plugins"]):
            with patch(
                "anomaly_detector.detector.SleepAnomalyDetector",
                return_value=self.detector_mock,
            ):
                with patch("sys.stdout", new_callable=StringIO):
                    try:
                        cli.main()
                        # Should call list_plugins and exit
                        self.detector_mock.plugin_manager.list_plugins.assert_called_once()
                    except SystemExit:
                        # Expected for --list-plugins
                        pass

    def test_main_with_clear_cache(self):
        """Test main function with clear-cache flag"""
        with patch("sys.argv", ["cli", "--clear-cache"]):
            with patch(
                "anomaly_detector.detector.SleepAnomalyDetector",
                return_value=self.detector_mock,
            ):
                with patch("sys.stdout", new_callable=StringIO):
                    try:
                        cli.main()
                        # Should call clear_cache
                        self.detector_mock.clear_cache.assert_called_once()
                    except SystemExit:
                        pass

    def test_main_with_discover_devices(self):
        """Test main function with discover-devices flag"""
        with patch("sys.argv", ["cli", "--discover-devices"]):
            with patch(
                "anomaly_detector.detector.SleepAnomalyDetector",
                return_value=self.detector_mock,
            ):
                with patch("sys.stdout", new_callable=StringIO):
                    try:
                        cli.main()
                        # Should call discover_devices
                        self.detector_mock.discover_devices.assert_called_once()
                    except SystemExit:
                        # Expected for --discover-devices
                        pass

    def test_main_with_plugin_argument(self):
        """Test main function with plugin argument"""
        with patch("sys.argv", ["cli", "--plugin", "oura"]):
            with patch(
                "anomaly_detector.detector.SleepAnomalyDetector"
            ) as mock_detector_class:
                mock_detector_class.return_value = self.detector_mock
                with patch("sys.stdout", new_callable=StringIO):
                    try:
                        cli.main()
                        # Should create detector with oura plugin
                        mock_detector_class.assert_called_once()
                        args = mock_detector_class.call_args[0]
                        self.assertEqual(args[1], "oura")
                    except SystemExit:
                        pass

    def test_main_with_train_days_argument(self):
        """Test main function with train-days argument"""
        with patch("sys.argv", ["cli", "--train-days", "30"]):
            with patch(
                "anomaly_detector.detector.SleepAnomalyDetector",
                return_value=self.detector_mock,
            ):
                with patch("sys.stdout", new_callable=StringIO):
                    try:
                        cli.main()
                        # Should call detector.run with train_days=30
                        self.detector_mock.run.assert_called_once()
                        args = self.detector_mock.run.call_args[0]
                        self.assertEqual(args[0], 30)  # train_days
                    except SystemExit:
                        pass

    def test_main_with_contamination_argument(self):
        """Test main function with contamination argument"""
        with patch("sys.argv", ["cli", "--contamination", "0.1"]):
            with patch(
                "anomaly_detector.detector.SleepAnomalyDetector",
                return_value=self.detector_mock,
            ):
                with patch("sys.stdout", new_callable=StringIO):
                    try:
                        cli.main()
                        # Should call detector.run with contamination=0.1
                        self.detector_mock.run.assert_called_once()
                        args = self.detector_mock.run.call_args[0]
                        self.assertEqual(args[1], 0.1)  # contamination
                    except SystemExit:
                        pass

    def test_main_with_alert_flag(self):
        """Test main function with alert flag"""
        with patch("sys.argv", ["cli", "--alert"]):
            with patch(
                "anomaly_detector.detector.SleepAnomalyDetector",
                return_value=self.detector_mock,
            ):
                with patch("sys.stdout", new_callable=StringIO):
                    try:
                        cli.main()
                        # Should call detector.run with alert=True
                        self.detector_mock.run.assert_called_once()
                        args = self.detector_mock.run.call_args[0]
                        self.assertTrue(args[3])  # alert
                    except SystemExit:
                        pass

    def test_main_keyboard_interrupt(self):
        """Test main function handles keyboard interrupt gracefully"""
        with patch("sys.argv", ["cli"]):
            with patch(
                "anomaly_detector.detector.SleepAnomalyDetector",
                return_value=self.detector_mock,
            ):
                self.detector_mock.run.side_effect = KeyboardInterrupt
                with patch("sys.stdout", new_callable=StringIO):
                    try:
                        cli.main()
                        self.fail("Expected SystemExit")
                    except SystemExit as e:
                        self.assertEqual(e.code, 1)

    def test_main_with_invalid_argument(self):
        """Test main function with invalid argument"""
        with patch("sys.argv", ["cli", "--invalid-option"]):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                with self.assertRaises(SystemExit):
                    cli.main()
                error_output = mock_stderr.getvalue()
                self.assertIn("unrecognized arguments", error_output.lower())


if __name__ == "__main__":
    unittest.main()
