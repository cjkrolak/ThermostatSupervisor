"""
Unit test to verify sys.modules truncation functionality.

This test validates that the helper methods truncate sys.modules
output when assertions fail, preventing log overflow.
"""

import unittest

from tests import unit_test_common as utc


class TestSysModulesTruncation(utc.UnitTest):
    """Test that sys.modules output is properly truncated."""

    def test_truncate_sys_modules_short(self):
        """Test that short sys.modules representation is not truncated."""
        # Use a very large max_chars to ensure no truncation
        result = self._truncate_sys_modules(max_chars=1000000)
        # Should not contain truncation message
        self.assertNotIn("[OUTPUT TRUNCATED:", result)

    def test_truncate_sys_modules_long(self):
        """Test that long sys.modules representation is truncated."""
        # Force truncation with small max_chars
        result = self._truncate_sys_modules(max_chars=100)
        # Should be exactly 100 chars plus the truncation message
        self.assertIn("[OUTPUT TRUNCATED:", result)
        # Should report character counts
        self.assertIn("showing 100 of", result)
        self.assertIn("characters]", result)

    def test_assert_module_not_in_success(self):
        """Test that assertModuleNotIn passes when module is not present."""
        # This should pass without error
        self.assertModuleNotIn('definitely_not_a_real_module_name_12345')

    def test_assert_module_in_success(self):
        """Test that assertModuleIn passes when module is present."""
        # 'sys' should always be present
        self.assertModuleIn('sys')

    def test_assert_module_not_in_failure_truncates(self):
        """Test that assertModuleNotIn failure message is truncated."""
        # 'sys' is always loaded, so this should fail
        try:
            self.assertModuleNotIn('sys', "Custom failure message")
            self.fail("Expected assertion to fail")
        except AssertionError as e:
            error_msg = str(e)
            # Verify custom message is included
            self.assertIn("Custom failure message", error_msg)
            # Verify truncation message is present
            self.assertIn("[OUTPUT TRUNCATED:", error_msg)
            # Verify it mentions sys
            self.assertIn("'sys' unexpectedly found", error_msg)

    def test_assert_module_in_failure_truncates(self):
        """Test that assertModuleIn failure message is truncated."""
        # This module definitely doesn't exist
        fake_module = 'definitely_not_a_real_module_name_12345'
        try:
            self.assertModuleIn(fake_module, "Custom failure message")
            self.fail("Expected assertion to fail")
        except AssertionError as e:
            error_msg = str(e)
            # Verify custom message is included
            self.assertIn("Custom failure message", error_msg)
            # Verify truncation message is present
            self.assertIn("[OUTPUT TRUNCATED:", error_msg)
            # Verify it mentions the missing module
            self.assertIn(f"'{fake_module}' not found", error_msg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
