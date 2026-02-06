"""Test module to verify duplicate STDOUT message fixes."""

import os
import sys
import shutil
import unittest
from io import StringIO

# Add the project to path if needed  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import utilities as util  # noqa: E402


class DuplicateStdoutFixTest(unittest.TestCase):
    """Test that duplicate STDOUT messages have been fixed."""

    def setUp(self):
        """Set up test environment."""
        # Clean up data folder to test directory creation
        if os.path.exists('./data'):
            shutil.rmtree('./data')

        # Reset flask server mode
        util.log_stdout_to_stderr = False

    def tearDown(self):
        """Clean up after tests."""
        # Reset flask server mode
        util.log_stdout_to_stderr = False

    def capture_stdout_stderr(self, func):
        """Capture both stdout and stderr output."""
        old_stdout = sys.stdout
        old_stderr = sys.stderr

        stdout_capture = StringIO()
        stderr_capture = StringIO()

        try:
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture
            func()
            return stdout_capture.getvalue(), stderr_capture.getvalue()
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def test_data_log_directory_creation_not_in_stdout(self):
        """Test that DATA_LOG directory creation message doesn't go to STDOUT."""
        stdout, stderr = self.capture_stdout_stderr(
            lambda: util.log_msg('Test message', util.DATA_LOG)
        )

        # Message should be in STDOUT but directory creation should be in STDERR
        self.assertIn('Test message', stdout)
        self.assertNotIn('data folder', stdout)
        self.assertIn('data folder', stderr)

    def test_dual_stream_log_directory_creation_not_in_stdout(self):
        """Test that DUAL_STREAM_LOG directory creation message doesn't go to STDOUT."""  # noqa: E501
        stdout, stderr = self.capture_stdout_stderr(
            lambda: util.log_msg('Test message', util.DUAL_STREAM_LOG)
        )

        # Message should be in STDOUT but directory creation should be in STDERR
        self.assertIn('Test message', stdout)
        self.assertNotIn('data folder', stdout)
        self.assertIn('data folder', stderr)

    def test_flask_server_mode_no_duplicate_with_stderr_log(self):
        """Test that flask server mode doesn't duplicate when STDERR_LOG is explicit."""  # noqa: E501
        util.log_stdout_to_stderr = True

        stdout, stderr = self.capture_stdout_stderr(
            lambda: util.log_msg('Test message', util.STDOUT_LOG | util.STDERR_LOG)
        )

        # Should only appear in STDERR once, not in STDOUT
        self.assertEqual('', stdout)
        self.assertEqual('Test message\n', stderr)

    def test_explicit_stdout_stderr_combination_still_works(self):
        """Test that explicit STDOUT_LOG | STDERR_LOG combination still works when not in flask mode."""  # noqa: E501
        util.log_stdout_to_stderr = False

        stdout, stderr = self.capture_stdout_stderr(
            lambda: util.log_msg('Test message', util.STDOUT_LOG | util.STDERR_LOG)
        )

        # Should appear in both streams when explicitly requested
        self.assertEqual('Test message\n', stdout)
        self.assertEqual('Test message\n', stderr)

    def test_flask_server_mode_stdout_to_stderr_conversion(self):
        """Test that flask server mode correctly converts STDOUT to STDERR."""
        util.log_stdout_to_stderr = True

        stdout, stderr = self.capture_stdout_stderr(
            lambda: util.log_msg('Test message', util.STDOUT_LOG)
        )

        # Should only appear in STDERR, not STDOUT
        self.assertEqual('', stdout)
        self.assertEqual('Test message\n', stderr)

    def test_both_log_mode_works_correctly(self):
        """Test that BOTH_LOG mode works correctly without duplicates."""
        stdout, stderr = self.capture_stdout_stderr(
            lambda: util.log_msg('Test message', util.BOTH_LOG)
        )

        # Should appear in STDOUT only (file logging tested separately)
        # Directory creation message should be in STDERR
        self.assertEqual('Test message\n', stdout)
        self.assertIn('data folder', stderr)

    def test_quiet_log_mode_no_duplicates(self):
        """Test that QUIET_LOG mode doesn't produce duplicates."""
        stdout, stderr = self.capture_stdout_stderr(
            lambda: util.log_msg('Test message', util.QUIET_LOG)
        )

        # Should appear in STDOUT only once
        self.assertEqual('Test message\n', stdout)
        self.assertEqual('', stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
