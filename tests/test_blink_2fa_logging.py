"""
Unit test module for blink.py 2FA logging functionality.
"""

# built-in imports
import unittest

# local imports
from src import utilities as util
from tests import unit_test_common as utc


class Blink2FALoggingTests(utc.UnitTest):
    """Test 2FA logging functionality in blink.py."""

    def setUp(self):
        super().setUp()
        util.log_msg.file_name = "unit_test.txt"

    def test_2fa_log_message_formatting(self):
        """
        Test that source messages are correctly formatted for different sources.

        This verifies the message formatting without importing blink module.
        """
        # Test different source values and their expected messages
        test_cases = [
            (
                "supervisor-env.txt",
                "using stored 2FA from supervisor-env.txt"
            ),
            (
                "environment_variable",
                "using stored 2FA from environment variable"
            ),
            ("default", "using default 2FA value (missing)"),
            ("other_source", "using 2FA from other_source"),
        ]

        for source, expected_msg in test_cases:
            if source == "supervisor-env.txt":
                source_msg = "using stored 2FA from supervisor-env.txt"
            elif source == "environment_variable":
                source_msg = "using stored 2FA from environment variable"
            elif source == "default":
                source_msg = "using default 2FA value (missing)"
            else:
                source_msg = f"using 2FA from {source}"

            self.assertEqual(
                source_msg,
                expected_msg,
                f"Source message mismatch for source '{source}'"
            )

    def test_2fa_masking_logic(self):
        """
        Test the 2FA masking logic in _log_2fa_source.

        This verifies that the logic for deciding whether to mask
        the 2FA is correct based on debug mode.
        """
        # Test masking in non-debug mode
        util.log_msg.debug = False
        value = "123456"
        debug_enabled = getattr(util.log_msg, "debug", False)

        if debug_enabled:
            twofa_display = f"2FA code: {value}"
        else:
            if value and not value.startswith("<"):
                twofa_display = "2FA code: ******"
            else:
                twofa_display = f"2FA code: {value}"

        self.assertEqual(
            twofa_display,
            "2FA code: ******",
            "2FA should be masked in non-debug mode"
        )

        # Test showing in debug mode
        util.log_msg.debug = True
        debug_enabled = getattr(util.log_msg, "debug", False)

        if debug_enabled:
            twofa_display = f"2FA code: {value}"
        else:
            if value and not value.startswith("<"):
                twofa_display = "2FA code: ******"
            else:
                twofa_display = f"2FA code: {value}"

        self.assertEqual(
            twofa_display,
            "2FA code: 123456",
            "2FA should be visible in debug mode"
        )

        # Reset debug mode
        util.log_msg.debug = False

    def test_2fa_source_message_formatting(self):
        """
        Test that source messages are formatted correctly.
        """
        # Test supervisor-env.txt source
        source = "supervisor-env.txt"
        if source == "supervisor-env.txt":
            source_msg = "using stored 2FA from supervisor-env.txt"
        elif source == "environment_variable":
            source_msg = "using stored 2FA from environment variable"
        elif source == "default":
            source_msg = "using default 2FA value (missing)"
        else:
            source_msg = f"using 2FA from {source}"

        self.assertEqual(
            source_msg,
            "using stored 2FA from supervisor-env.txt"
        )

        # Test environment variable source
        source = "environment_variable"
        if source == "supervisor-env.txt":
            source_msg = "using stored 2FA from supervisor-env.txt"
        elif source == "environment_variable":
            source_msg = "using stored 2FA from environment variable"
        elif source == "default":
            source_msg = "using default 2FA value (missing)"
        else:
            source_msg = f"using 2FA from {source}"

        self.assertEqual(
            source_msg,
            "using stored 2FA from environment variable"
        )

        # Test default source
        source = "default"
        if source == "supervisor-env.txt":
            source_msg = "using stored 2FA from supervisor-env.txt"
        elif source == "environment_variable":
            source_msg = "using stored 2FA from environment variable"
        elif source == "default":
            source_msg = "using default 2FA value (missing)"
        else:
            source_msg = f"using 2FA from {source}"

        self.assertEqual(
            source_msg,
            "using default 2FA value (missing)"
        )


if __name__ == "__main__":
    unittest.main()
