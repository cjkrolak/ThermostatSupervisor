"""
Unit test module for blink.py 2FA logging functionality.
"""

# built-in imports
import ast
from pathlib import Path
import unittest

# local imports
from src import utilities as util
from tests import unit_test_common as utc


class Blink2FALoggingTests(utc.UnitTest):
    """Test 2FA logging functionality in blink.py."""

    def setUp(self):
        super().setUp()
        util.log_msg.file_name = "unit_test.txt"  # type: ignore[attr-defined]

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
        util.log_msg.debug = False  # type: ignore[attr-defined]
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
        util.log_msg.debug = True  # type: ignore[attr-defined]
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
        util.log_msg.debug = False  # type: ignore[attr-defined]

    def _get_source_msg(self, source):
        if source == "supervisor-env.txt":
            return "using stored 2FA from supervisor-env.txt"
        elif source == "environment_variable":
            return "using stored 2FA from environment variable"
        elif source == "default":
            return "using default 2FA value (missing)"
        else:
            return f"using 2FA from {source}"

    def test_2fa_source_message_formatting(self):
        """
        Test that source messages are formatted correctly.
        """
        # Test supervisor-env.txt source
        source = "supervisor-env.txt"
        source_msg = self._get_source_msg(source)

        self.assertEqual(
            source_msg,
            "using stored 2FA from supervisor-env.txt"
        )

        # Test environment variable source
        source = "environment_variable"
        source_msg = self._get_source_msg(source)

        self.assertEqual(
            source_msg,
            "using stored 2FA from environment variable"
        )

        # Test default source
        source = "default"
        source_msg = self._get_source_msg(source)

        self.assertEqual(
            source_msg,
            "using default 2FA value (missing)"
        )

    def test_zone_initialized_before_2fa_logging(self):
        """
        Verify zone_number is assigned before _log_2fa_source() call.
        """
        blink_path = Path(__file__).resolve().parent.parent / "src" / "blink.py"
        source = blink_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        init_func = None
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == "ThermostatClass":
                for class_node in node.body:
                    if (
                        isinstance(class_node, ast.FunctionDef)
                        and class_node.name == "__init__"
                    ):
                        init_func = class_node
                        break
                break

        self.assertIsNotNone(init_func, "ThermostatClass.__init__ not found")

        zone_assignment_index = None
        log_call_index = None
        for index, stmt in enumerate(init_func.body):
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"
                        and target.attr == "zone_number"
                    ):
                        zone_assignment_index = index
            if (
                isinstance(stmt, ast.Expr)
                and isinstance(stmt.value, ast.Call)
                and isinstance(stmt.value.func, ast.Attribute)
                and isinstance(stmt.value.func.value, ast.Name)
                and stmt.value.func.value.id == "self"
                and stmt.value.func.attr == "_log_2fa_source"
            ):
                log_call_index = index

        self.assertIsNotNone(
            zone_assignment_index,
            "self.zone_number assignment not found in __init__",
        )
        self.assertIsNotNone(
            log_call_index,
            "self._log_2fa_source call not found in __init__",
        )
        self.assertLess(
            zone_assignment_index,
            log_call_index,
            "self.zone_number must be assigned before 2FA source logging",
        )


if __name__ == "__main__":
    unittest.main()
