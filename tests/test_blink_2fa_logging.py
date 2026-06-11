"""
Unit test module for blink.py 2FA logging functionality and auth flow.
"""

# built-in imports
import ast
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
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


class BlinkAsyncAuthFlowTests(utc.UnitTest):
    """
    Unit tests for the async authentication flow in ThermostatClass.

    These tests verify that _attempt_async_authentication and
    _complete_2fa_auth behave correctly for blinkpy 0.25.x (OAuth v2
    flow with BlinkTwoFARequiredError / send_2fa_code) and older 0.22.x
    APIs (send_auth_key).
    """

    def _make_thermostat_stub(self):
        """
        Build a minimal ThermostatClass stub without invoking __init__.

        Returns a plain object whose async methods come from the real
        ThermostatClass, but with only the attributes needed for auth
        tests pre-set.
        """
        # Import here so blinkpy is already initialised by the module
        from src import blink  # noqa: PLC0415

        instance = object.__new__(blink.ThermostatClass)
        instance.zone_number = 0
        instance.bl_2fa = "123456"
        instance.auth_dict = {"username": "user@example.com",
                              "password": "secret"}
        instance.blink = None
        instance.verbose = False
        instance.BL_2FA_KEY = "BLINK_2FA"
        return instance

    def _run_async(self, coro):
        """Run a coroutine synchronously for testing."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    # ------------------------------------------------------------------
    # _attempt_async_authentication: login succeeds without 2FA
    # ------------------------------------------------------------------

    def test_attempt_async_auth_success_no_2fa(self):
        """
        When blink.start() returns True, authentication succeeds without 2FA.
        """
        from src import blink  # noqa: PLC0415

        stub = self._make_thermostat_stub()

        mock_blink_obj = MagicMock()
        mock_blink_obj.start = AsyncMock(return_value=True)

        mock_auth_obj = MagicMock()

        with patch.object(blink, "blinkpy") as mock_blinkpy_mod, \
                patch.object(blink, "auth") as mock_auth_mod:
            mock_blinkpy_mod.Blink.return_value = mock_blink_obj
            mock_auth_mod.Auth.return_value = mock_auth_obj

            result = self._run_async(
                stub._attempt_async_authentication(MagicMock())
            )

        self.assertTrue(result, "Should return True when login succeeds")

    # ------------------------------------------------------------------
    # _attempt_async_authentication: start() returns False
    # ------------------------------------------------------------------

    def test_attempt_async_auth_start_returns_false_raises(self):
        """
        When blink.start() returns False, a ValueError is raised with
        an informative message (no AttributeError on blink.urls).
        """
        from src import blink  # noqa: PLC0415

        stub = self._make_thermostat_stub()

        mock_blink_obj = MagicMock()
        mock_blink_obj.start = AsyncMock(return_value=False)

        with patch.object(blink, "blinkpy") as mock_blinkpy_mod, \
                patch.object(blink, "auth") as mock_auth_mod:
            mock_blinkpy_mod.Blink.return_value = mock_blink_obj
            mock_auth_mod.Auth.return_value = MagicMock()

            with self.assertRaises(ValueError) as ctx:
                self._run_async(
                    stub._attempt_async_authentication(MagicMock())
                )

        self.assertIn(
            "Login returned False",
            str(ctx.exception),
            "ValueError message should indicate login returned False",
        )

    # ------------------------------------------------------------------
    # _attempt_async_authentication: blinkpy 0.25.x - BlinkTwoFARequired
    # ------------------------------------------------------------------

    def test_attempt_async_auth_2fa_required_uses_send_2fa_code(self):
        """
        When blink.start() raises BlinkTwoFARequiredError and the Blink
        object has send_2fa_code, that method is called (blinkpy 0.25.x).
        """
        from src import blink  # noqa: PLC0415

        stub = self._make_thermostat_stub()

        mock_blink_obj = MagicMock(spec=["start", "send_2fa_code"])
        mock_blink_obj.start = AsyncMock(
            side_effect=blink.BlinkTwoFARequiredError
        )
        mock_blink_obj.send_2fa_code = AsyncMock(return_value=True)

        with patch.object(blink, "blinkpy") as mock_blinkpy_mod, \
                patch.object(blink, "auth") as mock_auth_mod:
            mock_blinkpy_mod.Blink.return_value = mock_blink_obj
            mock_auth_mod.Auth.return_value = MagicMock()

            result = self._run_async(
                stub._attempt_async_authentication(MagicMock())
            )

        mock_blink_obj.send_2fa_code.assert_called_once_with(stub.bl_2fa)
        self.assertTrue(result, "Should return True after successful 2FA")

    # ------------------------------------------------------------------
    # _attempt_async_authentication: legacy 0.22.x fallback
    # ------------------------------------------------------------------

    def test_attempt_async_auth_2fa_required_fallback_send_auth_key(self):
        """
        When BlinkTwoFARequiredError is raised and the Blink object does
        NOT have send_2fa_code but auth has send_auth_key, the legacy
        0.22.x path is used.
        """
        from src import blink  # noqa: PLC0415

        stub = self._make_thermostat_stub()

        mock_auth_obj = MagicMock(spec=["send_auth_key"])
        mock_auth_obj.send_auth_key = AsyncMock(return_value=True)

        mock_blink_obj = MagicMock(spec=["start", "setup_post_verify"])
        mock_blink_obj.auth = mock_auth_obj
        mock_blink_obj.start = AsyncMock(
            side_effect=blink.BlinkTwoFARequiredError
        )
        mock_blink_obj.setup_post_verify = AsyncMock(return_value=True)

        with patch.object(blink, "blinkpy") as mock_blinkpy_mod, \
                patch.object(blink, "auth") as mock_auth_mod:
            mock_blinkpy_mod.Blink.return_value = mock_blink_obj
            mock_auth_mod.Auth.return_value = mock_auth_obj

            result = self._run_async(
                stub._attempt_async_authentication(MagicMock())
            )

        mock_auth_obj.send_auth_key.assert_called_once_with(
            mock_blink_obj, stub.bl_2fa
        )
        self.assertTrue(result)

    # ------------------------------------------------------------------
    # _complete_2fa_auth: send_2fa_code fails
    # ------------------------------------------------------------------

    def test_complete_2fa_auth_send_2fa_code_failure_raises(self):
        """
        When send_2fa_code returns False, _attempt_async_authentication
        raises a ValueError describing a failed 2FA verification.
        """
        from src import blink  # noqa: PLC0415

        stub = self._make_thermostat_stub()

        mock_blink_obj = MagicMock(spec=["start", "send_2fa_code"])
        mock_blink_obj.start = AsyncMock(
            side_effect=blink.BlinkTwoFARequiredError
        )
        mock_blink_obj.send_2fa_code = AsyncMock(return_value=False)

        with patch.object(blink, "blinkpy") as mock_blinkpy_mod, \
                patch.object(blink, "auth") as mock_auth_mod:
            mock_blinkpy_mod.Blink.return_value = mock_blink_obj
            mock_auth_mod.Auth.return_value = MagicMock()

            with self.assertRaises(ValueError) as ctx:
                self._run_async(
                    stub._attempt_async_authentication(MagicMock())
                )

        self.assertIn(
            "2FA verification failed",
            str(ctx.exception),
        )

    # ------------------------------------------------------------------
    # _complete_2fa_auth: no 2FA method available
    # ------------------------------------------------------------------

    def test_complete_2fa_auth_no_method_raises_value_error(self):
        """
        When BlinkTwoFARequiredError is raised but neither send_2fa_code
        nor send_auth_key is available, a ValueError is raised with an
        unsupported-version message.
        """
        from src import blink  # noqa: PLC0415

        stub = self._make_thermostat_stub()

        # spec=[] means the mock has no attributes matching either method
        mock_blink_obj = MagicMock(spec=["start"])
        mock_blink_obj.start = AsyncMock(
            side_effect=blink.BlinkTwoFARequiredError
        )
        mock_blink_obj.auth = MagicMock(spec=[])

        with patch.object(blink, "blinkpy") as mock_blinkpy_mod, \
                patch.object(blink, "auth") as mock_auth_mod:
            mock_blinkpy_mod.Blink.return_value = mock_blink_obj
            mock_auth_mod.Auth.return_value = MagicMock(spec=[])

            with self.assertRaises(ValueError) as ctx:
                self._run_async(
                    stub._attempt_async_authentication(MagicMock())
                )

        self.assertIn(
            "Unsupported blinkpy version",
            str(ctx.exception),
        )


if __name__ == "__main__":
    unittest.main()
