"""Test configuration and utilities"""

import os
import shutil
import tempfile
from unittest.mock import patch


class TestEnvironment:
    """Test environment setup and teardown"""

    def __init__(self):
        self.temp_dir = None
        self.original_cwd = None

    def __enter__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)


def create_test_file(filepath, content):
    """Create a test file with given content"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        f.write(content)
    return filepath


def mock_cli_args(*args):
    """Mock CLI arguments"""
    return patch("sys.argv", ["cli"] + list(args))
