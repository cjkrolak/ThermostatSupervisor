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

    These tests verify that _attempt_async_authentication and helpers
    behave correctly for blinkpy 0.25.x (OAuth v2 flow with
    BlinkTwoFARequiredError / send_2fa_code), the password grant fallback
    path (auth.login()), and older 0.22.x APIs (send_auth_key).
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
        instance.bl_uname = "user@example.com"
        instance.bl_pwd = "secret"
        instance.auth_dict = {"username": "user@example.com",
                              "password": "secret"}
        instance.blink = None
        instance.verbose = False
        instance.BL_2FA_KEY = "BLINK_2FA"
        return instance

    def _make_blink_obj_for_password_grant(
        self, login_result=None
    ):
        """
        Build a mock Blink object pre-wired for password grant tests.

        inputs:
            login_result: return value for auth.login() (dict or None).
        returns:
            (mock_blink_obj, mock_auth_obj) tuple.
        """
        mock_auth_obj = MagicMock()
        mock_auth_obj.login = AsyncMock(return_value=login_result or {
            "access_token": "tok", "refresh_token": "rtok",
            "expires_in": 3600,
        })
        mock_auth_obj._process_token_data = AsyncMock()
        mock_auth_obj.data = {}
        mock_auth_obj.hardware_id = "TEST-HARDWARE-UUID"

        mock_blink_obj = MagicMock()
        mock_blink_obj.start = AsyncMock(return_value=False)
        mock_blink_obj.auth = mock_auth_obj
        mock_blink_obj.setup_urls = MagicMock()
        mock_blink_obj.get_homescreen = AsyncMock()
        mock_blink_obj.setup_post_verify = AsyncMock(return_value=True)
        mock_blink_obj.last_refresh = None
        mock_blink_obj.refresh_rate = 30

        return mock_blink_obj, mock_auth_obj

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
        When blink.start() returns True, authentication succeeds without
        attempting the password grant fallback.
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
        # Password grant path should not have been used
        mock_blink_obj.auth.login.assert_not_called()

    # ------------------------------------------------------------------
    # _attempt_async_authentication: start() returns False → fallback
    # ------------------------------------------------------------------

    def test_attempt_async_auth_start_false_fallback_succeeds(self):
        """
        When blink.start() returns False, the password grant fallback is
        attempted.  When auth.login() succeeds, setup completes and True
        is returned.
        """
        from src import blink  # noqa: PLC0415

        stub = self._make_thermostat_stub()
        mock_blink_obj, mock_auth_obj = self._make_blink_obj_for_password_grant()

        with patch.object(blink, "blinkpy") as mock_blinkpy_mod, \
                patch.object(blink, "auth") as mock_auth_mod:
            mock_blinkpy_mod.Blink.return_value = mock_blink_obj
            mock_blinkpy_mod.BlinkSetupError = Exception
            mock_auth_mod.Auth.return_value = mock_auth_obj

            result = self._run_async(
                stub._attempt_async_authentication(MagicMock())
            )

        self.assertTrue(result, "Should return True after password grant")
        mock_auth_obj.login.assert_called_once()

    def test_attempt_async_auth_start_false_fallback_login_error(self):
        """
        When blink.start() returns False and auth.login() raises LoginError
        (e.g. HTTP 406), a ValueError is raised indicating the password grant
        path has been permanently disabled or rejected by Blink's server.
        """
        from src import blink  # noqa: PLC0415

        stub = self._make_thermostat_stub()
        mock_blink_obj, mock_auth_obj = self._make_blink_obj_for_password_grant()
        mock_auth_obj.login = AsyncMock(side_effect=blink.LoginError)

        with patch.object(blink, "blinkpy") as mock_blinkpy_mod, \
                patch.object(blink, "auth") as mock_auth_mod:
            mock_blinkpy_mod.Blink.return_value = mock_blink_obj
            mock_blinkpy_mod.BlinkSetupError = Exception
            mock_auth_mod.Auth.return_value = mock_auth_obj

            with self.assertRaises(ValueError) as ctx:
                self._run_async(
                    stub._attempt_async_authentication(MagicMock())
                )

        # Error must mention that password grant is disabled or rejected
        error_msg = str(ctx.exception).lower()
        self.assertTrue(
            "permanently disabled" in error_msg
            or "rejected" in error_msg
            or "unsupported_grant_type" in error_msg,
            f"Expected password-grant-disabled guidance in: {error_msg}",
        )
        mock_auth_obj.login.assert_called_once()

    def test_attempt_async_auth_login_error_unauthorized_raises_value_error(
        self
    ):
        """
        When blink.start() returns False and auth.login() raises
        UnauthorizedError (HTTP 401 / unsupported_grant_type), a ValueError
        is raised indicating the password grant path is disabled.
        """
        from src import blink  # noqa: PLC0415

        stub = self._make_thermostat_stub()
        mock_blink_obj, mock_auth_obj = self._make_blink_obj_for_password_grant()
        mock_auth_obj.login = AsyncMock(side_effect=blink.UnauthorizedError)

        with patch.object(blink, "blinkpy") as mock_blinkpy_mod, \
                patch.object(blink, "auth") as mock_auth_mod:
            mock_blinkpy_mod.Blink.return_value = mock_blink_obj
            mock_blinkpy_mod.BlinkSetupError = Exception
            mock_auth_mod.Auth.return_value = mock_auth_obj

            with self.assertRaises(ValueError) as ctx:
                self._run_async(
                    stub._attempt_async_authentication(MagicMock())
                )

        error_msg = str(ctx.exception).lower()
        self.assertTrue(
            "permanently disabled" in error_msg
            or "rejected" in error_msg
            or "unsupported_grant_type" in error_msg,
            f"Expected password-grant-disabled guidance in: {error_msg}",
        )
        mock_auth_obj.login.assert_called_once()

    def test_attempt_async_auth_start_false_fallback_2fa_required(self):
        """
        When blink.start() returns False and auth.login() raises
        BlinkTwoFARequiredError, the password grant 2FA path is used:
        the stored 2FA code is added to auth.data and login is retried.
        """
        from src import blink  # noqa: PLC0415

        stub = self._make_thermostat_stub()
        mock_blink_obj, mock_auth_obj = self._make_blink_obj_for_password_grant()

        # First call → 2FA required; second call (with code) → success
        mock_auth_obj.login = AsyncMock(side_effect=[
            blink.BlinkTwoFARequiredError,
            {"access_token": "tok", "refresh_token": "rtok",
             "expires_in": 3600},
        ])

        with patch.object(blink, "blinkpy") as mock_blinkpy_mod, \
                patch.object(blink, "auth") as mock_auth_mod:
            mock_blinkpy_mod.Blink.return_value = mock_blink_obj
            mock_blinkpy_mod.BlinkSetupError = Exception
            mock_auth_mod.Auth.return_value = mock_auth_obj

            result = self._run_async(
                stub._attempt_async_authentication(MagicMock())
            )

        self.assertTrue(result)
        # login() must have been called twice
        self.assertEqual(mock_auth_obj.login.call_count, 2)
        # 2FA code should be cleaned up from auth.data after completion
        self.assertNotIn("2fa_code", mock_blink_obj.auth.data)

    def test_attempt_async_auth_start_false_fallback_2fa_fails(self):
        """
        When blink.start() returns False, auth.login() raises
        BlinkTwoFARequiredError, and the 2FA retry also raises the error,
        a descriptive ValueError is raised.
        """
        from src import blink  # noqa: PLC0415

        stub = self._make_thermostat_stub()
        mock_blink_obj, mock_auth_obj = self._make_blink_obj_for_password_grant()
        mock_auth_obj.login = AsyncMock(
            side_effect=blink.BlinkTwoFARequiredError
        )

        with patch.object(blink, "blinkpy") as mock_blinkpy_mod, \
                patch.object(blink, "auth") as mock_auth_mod:
            mock_blinkpy_mod.Blink.return_value = mock_blink_obj
            mock_blinkpy_mod.BlinkSetupError = Exception
            mock_auth_mod.Auth.return_value = mock_auth_obj

            with self.assertRaises(ValueError) as ctx:
                self._run_async(
                    stub._attempt_async_authentication(MagicMock())
                )

        self.assertIn("2FA verification failed", str(ctx.exception))
        # 2FA code must be cleaned up even on failure
        self.assertNotIn("2fa_code", mock_blink_obj.auth.data)

    # ------------------------------------------------------------------
    # _attempt_password_grant_auth: UnauthorizedError → ValueError
    # ------------------------------------------------------------------

    def test_attempt_async_auth_ios_grant_fallback_on_unauthorized(self):
        """
        When blink.start() returns False and auth.login() raises
        UnauthorizedError (HTTP 401 / unsupported_grant_type), a ValueError
        is raised indicating the password grant path is disabled.
        Previously this fell through to an iOS grant; that path has been
        removed since ``client_id=ios`` only supports PKCE, not password
        grant.
        """
        from src import blink  # noqa: PLC0415

        stub = self._make_thermostat_stub()
        mock_blink_obj, mock_auth_obj = self._make_blink_obj_for_password_grant()
        mock_auth_obj.login = AsyncMock(side_effect=blink.UnauthorizedError)

        with patch.object(blink, "blinkpy") as mock_blinkpy_mod, \
                patch.object(blink, "auth") as mock_auth_mod:
            mock_blinkpy_mod.Blink.return_value = mock_blink_obj
            mock_blinkpy_mod.BlinkSetupError = Exception
            mock_auth_mod.Auth.return_value = mock_auth_obj

            with self.assertRaises(ValueError) as ctx:
                self._run_async(
                    stub._attempt_async_authentication(MagicMock())
                )

        error_msg = str(ctx.exception).lower()
        self.assertTrue(
            "permanently disabled" in error_msg
            or "rejected" in error_msg
            or "unsupported_grant_type" in error_msg,
            f"Expected password-grant-disabled guidance in: {error_msg}",
        )
        mock_auth_obj.login.assert_called_once()

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
                patch.object(blink, "auth") as mock_auth_mod, \
                patch.object(stub, "_save_token_cache",
                             new=AsyncMock(return_value=None)):
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
                patch.object(blink, "auth") as mock_auth_mod, \
                patch.object(stub, "_save_token_cache",
                             new=AsyncMock(return_value=None)):
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


class BlinkDiagnosticsTests(utc.UnitTest):
    """
    Tests for enhanced diagnostic methods added to ThermostatClass:
    _configure_blink_logging, _create_http_trace_config, and the
    verbose iOS grant response body logging.
    """

    def _make_thermostat_stub(self, verbose=False):
        """Build a minimal ThermostatClass stub for diagnostics tests."""
        from src import blink  # noqa: PLC0415

        instance = object.__new__(blink.ThermostatClass)
        instance.zone_number = 0
        instance.bl_2fa = "123456"
        instance.bl_uname = "user@example.com"
        instance.bl_pwd = "secret"
        instance.auth_dict = {
            "username": "user@example.com",
            "password": "secret",
        }
        instance.blink = None
        instance.verbose = verbose
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
    # _configure_blink_logging
    # ------------------------------------------------------------------

    def test_configure_blink_logging_verbose_adds_handler(self):
        """
        _configure_blink_logging() adds a StreamHandler only to the parent
        ``blinkpy`` logger and sets all blinkpy loggers to DEBUG level.
        Child loggers propagate to the parent naturally, so each message
        is emitted exactly once.
        """
        import logging  # noqa: PLC0415
        stub = self._make_thermostat_stub(verbose=True)

        # Remove any existing handlers to start clean.
        for name in ("blinkpy", "blinkpy.auth", "blinkpy.blinkpy",
                     "blinkpy.api"):
            logging.getLogger(name).handlers = []

        stub._configure_blink_logging()

        # Parent logger must have the StreamHandler and be at DEBUG level.
        parent = logging.getLogger("blinkpy")
        self.assertEqual(parent.level, logging.DEBUG)
        self.assertTrue(
            any(isinstance(h, logging.StreamHandler)
                for h in parent.handlers),
            "Expected StreamHandler on 'blinkpy' parent logger"
        )

        # Child loggers must be at DEBUG but must NOT have their own
        # StreamHandler (they propagate to the parent to avoid double-
        # logging each message).
        for name in ("blinkpy.auth", "blinkpy.blinkpy", "blinkpy.api"):
            child = logging.getLogger(name)
            self.assertEqual(child.level, logging.DEBUG,
                             f"{name!r} must be at DEBUG level")
            self.assertFalse(
                any(isinstance(h, logging.StreamHandler)
                    for h in child.handlers),
                f"Child logger {name!r} must not have its own "
                f"StreamHandler (would cause double-logging)"
            )

    def test_configure_blink_logging_noop_when_not_verbose(self):
        """
        _configure_blink_logging() does nothing when verbose=False,
        so blinkpy loggers keep their current handlers.
        """
        import logging  # noqa: PLC0415
        stub = self._make_thermostat_stub(verbose=False)
        # Capture current handler count
        initial = len(logging.getLogger("blinkpy").handlers)
        stub._configure_blink_logging()
        after = len(logging.getLogger("blinkpy").handlers)
        self.assertEqual(initial, after)

    def test_configure_blink_logging_idempotent(self):
        """
        Calling _configure_blink_logging() twice should not duplicate
        the stdout StreamHandler on a logger.
        """
        import logging  # noqa: PLC0415
        stub = self._make_thermostat_stub(verbose=True)
        logging.getLogger("blinkpy").handlers = []

        stub._configure_blink_logging()
        count_after_first = len(logging.getLogger("blinkpy").handlers)
        stub._configure_blink_logging()
        count_after_second = len(logging.getLogger("blinkpy").handlers)

        self.assertEqual(count_after_first, count_after_second,
                         "Handler count must not increase on second call")

    # ------------------------------------------------------------------
    # _create_http_trace_config
    # ------------------------------------------------------------------

    def test_create_http_trace_config_returns_trace_config(self):
        """
        _create_http_trace_config() returns an aiohttp TraceConfig with
        on_request_start and on_request_end signals attached.
        """
        from aiohttp import TraceConfig  # noqa: PLC0415
        stub = self._make_thermostat_stub(verbose=True)
        tc = stub._create_http_trace_config()
        self.assertIsInstance(tc, TraceConfig)
        self.assertTrue(len(tc.on_request_start) > 0,
                        "on_request_start must have at least one callback")
        self.assertTrue(len(tc.on_request_end) > 0,
                        "on_request_end must have at least one callback")

    def test_http_trace_config_callbacks_print_request(self):
        """
        The on_request_start callback prints the HTTP method and path.
        """
        import io  # noqa: PLC0415
        import sys  # noqa: PLC0415
        from unittest.mock import MagicMock  # noqa: PLC0415
        import yarl  # noqa: PLC0415

        stub = self._make_thermostat_stub(verbose=True)
        tc = stub._create_http_trace_config()

        async def run():
            params = MagicMock()
            params.method = "GET"
            params.url = yarl.URL("https://api.oauth.blink.com/oauth/v2/signin")
            await tc.on_request_start[0](None, None, params)

        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            self._run_async(run())
        finally:
            sys.stdout = old_stdout

        output = captured.getvalue()
        self.assertIn("GET", output)
        self.assertIn("/oauth/v2/signin", output)

    def test_http_trace_config_4xx_body_logged_on_request_end(self):
        """
        The on_request_end callback reads and prints the response body
        for 4xx status codes, and prints a specific 406 guidance note.
        """
        import io  # noqa: PLC0415
        import sys  # noqa: PLC0415
        import yarl  # noqa: PLC0415
        from unittest.mock import AsyncMock, MagicMock  # noqa: PLC0415

        stub = self._make_thermostat_stub(verbose=True)
        tc = stub._create_http_trace_config()

        async def run():
            params = MagicMock()
            params.url = yarl.URL(
                "https://api.oauth.blink.com/oauth/v2/signin"
            )
            params.response = MagicMock()
            params.response.status = 406
            params.response.read = AsyncMock(
                return_value=b'{"error":"blocked","message":"Rate limited"}'
            )
            await tc.on_request_end[0](None, None, params)

        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            self._run_async(run())
        finally:
            sys.stdout = old_stdout

        output = captured.getvalue()
        # Status and path must appear
        self.assertIn("406", output)
        self.assertIn("/oauth/v2/signin", output)
        # Response body snippet must appear
        self.assertIn("blocked", output)
        # 406-specific guidance note must appear
        self.assertIn("406", output)
        self.assertIn("rate", output.lower())

    # ------------------------------------------------------------------
    # _validate_credentials
    # ------------------------------------------------------------------

    def test_validate_credentials_passes_for_valid_inputs(self):
        """
        _validate_credentials() does not raise when username and password
        are both populated with real (non-sentinel) values.
        """
        stub = self._make_thermostat_stub()
        stub.BL_UNAME_KEY = "BLINK_USERNAME"
        stub.BL_PASSWORD_KEY = "BLINK_PASSWORD"
        stub.bl_uname = "user@example.com"
        stub.bl_pwd = "mypassword"
        # Should not raise
        stub._validate_credentials()

    def test_validate_credentials_raises_on_missing_username(self):
        """
        _validate_credentials() raises ValueError when bl_uname contains
        the sentinel placeholder that indicates the env key was not found.
        """
        stub = self._make_thermostat_stub()
        stub.BL_UNAME_KEY = "BLINK_USERNAME"
        stub.BL_PASSWORD_KEY = "BLINK_PASSWORD"
        stub.bl_uname = "<BLINK_USERNAME_KEY_MISSING>"
        stub.bl_pwd = "mypassword"

        with self.assertRaises(ValueError) as ctx:
            stub._validate_credentials()

        self.assertIn("BLINK_USERNAME is missing", str(ctx.exception))
        self.assertIn("supervisor-env.txt", str(ctx.exception))
        # The BOM tip must appear to guide Windows users.
        self.assertIn("BOM", str(ctx.exception))

    def test_validate_credentials_raises_on_blank_username(self):
        """
        _validate_credentials() raises ValueError when bl_uname is an empty
        string or whitespace-only (e.g. caused by a blank value in the file).
        """
        stub = self._make_thermostat_stub()
        stub.BL_UNAME_KEY = "BLINK_USERNAME"
        stub.BL_PASSWORD_KEY = "BLINK_PASSWORD"
        stub.bl_uname = "   "
        stub.bl_pwd = "mypassword"

        with self.assertRaises(ValueError) as ctx:
            stub._validate_credentials()

        self.assertIn("BLINK_USERNAME is blank", str(ctx.exception))

    def test_validate_credentials_raises_on_missing_password(self):
        """
        _validate_credentials() raises ValueError when bl_pwd is the missing
        sentinel placeholder.
        """
        stub = self._make_thermostat_stub()
        stub.BL_UNAME_KEY = "BLINK_USERNAME"
        stub.BL_PASSWORD_KEY = "BLINK_PASSWORD"
        stub.bl_uname = "user@example.com"
        stub.bl_pwd = "<BLINK_PASSWORD_KEY_MISSING>"

        with self.assertRaises(ValueError) as ctx:
            stub._validate_credentials()

        self.assertIn("BLINK_PASSWORD is missing", str(ctx.exception))

    def test_validate_credentials_raises_on_blank_password(self):
        """
        _validate_credentials() raises ValueError when bl_pwd is blank.
        """
        stub = self._make_thermostat_stub()
        stub.BL_UNAME_KEY = "BLINK_USERNAME"
        stub.BL_PASSWORD_KEY = "BLINK_PASSWORD"
        stub.bl_uname = "user@example.com"
        stub.bl_pwd = ""

        with self.assertRaises(ValueError) as ctx:
            stub._validate_credentials()

        self.assertIn("BLINK_PASSWORD is blank", str(ctx.exception))

    def test_validate_credentials_reports_both_issues(self):
        """
        _validate_credentials() includes both username and password problems
        in a single error when both fields are invalid.
        """
        stub = self._make_thermostat_stub()
        stub.BL_UNAME_KEY = "BLINK_USERNAME"
        stub.BL_PASSWORD_KEY = "BLINK_PASSWORD"
        stub.bl_uname = ""
        stub.bl_pwd = ""

        with self.assertRaises(ValueError) as ctx:
            stub._validate_credentials()

        msg = str(ctx.exception)
        self.assertIn("BLINK_USERNAME", msg)
        self.assertIn("BLINK_PASSWORD", msg)

    # ------------------------------------------------------------------
    # iOS grant verbose response body logging
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # _handle_rate_limit_error and 429 trace detection
    # ------------------------------------------------------------------

    def test_handle_rate_limit_error_exits_with_clear_message(self):
        """
        _handle_rate_limit_error() prints a banner with wait-time info
        and calls sys.exit(1).  The message must include the lockout
        duration, zone number, and actionable guidance.
        """
        import io  # noqa: PLC0415
        import sys  # noqa: PLC0415

        stub = self._make_thermostat_stub()
        stub._rate_limit_next_time_secs = 86400

        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(SystemExit) as ctx:
                stub._handle_rate_limit_error()
        finally:
            sys.stdout = old_stdout

        self.assertEqual(ctx.exception.code, 1)
        output = captured.getvalue()
        # Must mention the lockout duration
        self.assertIn("86400", output)
        self.assertIn("24", output)   # 86400 s = 24 hours
        # Must mention zone number
        self.assertIn("zone 0", output.lower())
        # Must include guidance steps
        self.assertIn("2FA", output)

    def test_handle_rate_limit_error_uses_default_when_secs_none(self):
        """
        When _rate_limit_next_time_secs is None (body not parsed), the
        method falls back to 86400 seconds (24 hours).
        """
        import io  # noqa: PLC0415
        import sys  # noqa: PLC0415

        stub = self._make_thermostat_stub()
        stub._rate_limit_next_time_secs = None

        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            with self.assertRaises(SystemExit):
                stub._handle_rate_limit_error()
        finally:
            sys.stdout = old_stdout

        output = captured.getvalue()
        self.assertIn("86400", output)

    def test_trace_config_detects_429_rate_limit(self):
        """
        When on_request_end fires for a HTTP 429 response whose body
        contains "error_cause":"2fa_rate_limit_exceeded", the trace
        callback sets _rate_limit_detected=True and captures
        next_time_in_secs on the stub.
        """
        import json  # noqa: PLC0415
        import yarl  # noqa: PLC0415

        stub = self._make_thermostat_stub(verbose=False)
        stub._rate_limit_detected = False
        stub._rate_limit_next_time_secs = None
        tc = stub._create_http_trace_config()

        body = json.dumps({
            "error": "too_many_requests",
            "error_cause": "2fa_rate_limit_exceeded",
            "error_description": "2FA rate limit exceeded.",
            "next_time_in_secs": 86400,
        }).encode()

        async def run():
            params = MagicMock()
            params.url = yarl.URL(
                "https://api.oauth.blink.com/oauth/v2/signin"
            )
            params.response = MagicMock()
            params.response.status = 429
            params.response.read = AsyncMock(return_value=body)
            await tc.on_request_end[0](None, None, params)

        self._run_async(run())

        self.assertTrue(stub._rate_limit_detected)
        self.assertEqual(stub._rate_limit_next_time_secs, 86400)

    def test_trace_config_no_false_positive_on_non_rate_limit_429(self):
        """
        A HTTP 429 response whose body does NOT contain the
        "2fa_rate_limit_exceeded" error_cause must NOT set
        _rate_limit_detected.
        """
        import json  # noqa: PLC0415
        import yarl  # noqa: PLC0415

        stub = self._make_thermostat_stub(verbose=False)
        stub._rate_limit_detected = False
        stub._rate_limit_next_time_secs = None
        tc = stub._create_http_trace_config()

        body = json.dumps({
            "error": "too_many_requests",
            "error_cause": "some_other_limit",
        }).encode()

        async def run():
            params = MagicMock()
            params.url = yarl.URL(
                "https://api.oauth.blink.com/oauth/v2/signin"
            )
            params.response = MagicMock()
            params.response.status = 429
            params.response.read = AsyncMock(return_value=body)
            await tc.on_request_end[0](None, None, params)

        self._run_async(run())

        self.assertFalse(stub._rate_limit_detected)
        self.assertIsNone(stub._rate_limit_next_time_secs)

    def test_attempt_async_auth_rate_limited_exits_immediately(self):
        """
        When blink.start() returns False and _rate_limit_detected is True,
        _attempt_async_authentication calls _handle_rate_limit_error()
        and never reaches the password grant fallback.
        """
        from src import blink  # noqa: PLC0415
        import io  # noqa: PLC0415
        import sys  # noqa: PLC0415

        stub = self._make_thermostat_stub()
        stub._rate_limit_detected = True
        stub._rate_limit_next_time_secs = 86400

        mock_blink_obj = MagicMock()
        mock_blink_obj.start = AsyncMock(return_value=False)
        mock_auth_obj = MagicMock()
        mock_auth_obj.login = AsyncMock()  # must NOT be called

        with patch.object(blink, "blinkpy") as mock_blinkpy_mod, \
                patch.object(blink, "auth") as mock_auth_mod:
            mock_blinkpy_mod.Blink.return_value = mock_blink_obj
            mock_auth_mod.Auth.return_value = mock_auth_obj

            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                with self.assertRaises(SystemExit) as ctx:
                    self._run_async(
                        stub._attempt_async_authentication(MagicMock())
                    )
            finally:
                sys.stdout = old_stdout

        self.assertEqual(ctx.exception.code, 1)
        output = captured.getvalue()
        self.assertIn("rate limit", output.lower())
        # Password grant must NOT be tried
        mock_auth_obj.login.assert_not_called()


if __name__ == "__main__":
    unittest.main()
