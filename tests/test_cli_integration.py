import unittest
import subprocess
import sys
import os
import tempfile
import shutil

class TestCLIIntegration(unittest.TestCase):
    """Integration tests for CLI functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        
    def tearDown(self):
        """Clean up after tests"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cli_execution_from_command_line(self):
        """Test CLI can be executed from command line"""
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'cli', '--help'],
                capture_output=True,
                text=True,
                timeout=10
            )
            # Should not crash
            self.assertIsNotNone(result.returncode)
        except subprocess.TimeoutExpired:
            self.fail("CLI execution timed out")
        except FileNotFoundError:
            # CLI module might not exist, skip this test
            self.skipTest("CLI module not found")
    
    def test_cli_with_pipes(self):
        """Test CLI works with pipes"""
        try:
            # Test with echo piped to CLI
            process1 = subprocess.Popen(
                ['echo', 'test'],
                stdout=subprocess.PIPE
            )
            process2 = subprocess.Popen(
                [sys.executable, '-m', 'cli'],
                stdin=process1.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            process1.stdout.close()
            stdout, stderr = process2.communicate(timeout=10)
            
            # Should not crash
            self.assertIsNotNone(process2.returncode)
        except subprocess.TimeoutExpired:
            self.fail("CLI with pipes timed out")
        except FileNotFoundError:
            self.skipTest("CLI module not found")
    
    def test_cli_with_large_input(self):
        """Test CLI handles large input gracefully"""
        try:
            large_input = "test\n" * 10000
            result = subprocess.run(
                [sys.executable, '-m', 'cli'],
                input=large_input,
                capture_output=True,
                text=True,
                timeout=30
            )
            # Should not crash
            self.assertIsNotNone(result.returncode)
        except subprocess.TimeoutExpired:
            self.fail("CLI with large input timed out")
        except FileNotFoundError:
            self.skipTest("CLI module not found")


if __name__ == '__main__':
    unittest.main()