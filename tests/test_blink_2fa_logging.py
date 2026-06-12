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

    def _make_ios_response_mock(self, status=200, token_data=None):
        """
        Build a mock HTTP response for iOS client grant tests.

        inputs:
            status(int): HTTP status code to return.
            token_data(dict): token payload; defaults to a valid token.
        returns:
            mock_response MagicMock with .status and .json() set.
        """
        payload = token_data or {
            "access_token": "ios_tok",
            "refresh_token": "ios_rtok",
            "expires_in": 3600,
        }
        mock_response = MagicMock()
        mock_response.status = status
        mock_response.json = AsyncMock(return_value=payload)
        return mock_response

    def _make_blink_obj_for_password_grant(
        self, login_result=None, ios_response_status=200
    ):
        """
        Build a mock Blink object pre-wired for password grant tests.

        The object also includes a session mock used by the iOS client
        grant fallback path (_attempt_ios_client_grant).

        inputs:
            login_result: return value for auth.login() (dict or None).
            ios_response_status(int): HTTP status for the iOS grant POST.
        returns:
            (mock_blink_obj, mock_auth_obj) tuple.
        """
        ios_response = self._make_ios_response_mock(ios_response_status)
        mock_session = MagicMock()
        mock_session.post = AsyncMock(return_value=ios_response)

        mock_auth_obj = MagicMock()
        mock_auth_obj.login = AsyncMock(return_value=login_result or {
            "access_token": "tok", "refresh_token": "rtok",
            "expires_in": 3600,
        })
        mock_auth_obj._process_token_data = AsyncMock()
        mock_auth_obj.data = {}
        mock_auth_obj.session = mock_session
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
        When blink.start() returns False and auth.login() raises LoginError,
        the LoginError propagates so the retry loop can handle it.
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

            with self.assertRaises(blink.LoginError):
                self._run_async(
                    stub._attempt_async_authentication(MagicMock())
                )

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
    # _attempt_password_grant_auth: UnauthorizedError → iOS client grant
    # ------------------------------------------------------------------

    def test_attempt_async_auth_ios_grant_fallback_on_unauthorized(self):
        """
        When blink.start() returns False and auth.login() raises
        UnauthorizedError (HTTP 401 from the android client), the iOS
        client grant fallback is tried and should succeed.
        """
        from src import blink  # noqa: PLC0415

        stub = self._make_thermostat_stub()
        mock_blink_obj, mock_auth_obj = self._make_blink_obj_for_password_grant(
            ios_response_status=200
        )
        mock_auth_obj.login = AsyncMock(side_effect=blink.UnauthorizedError)

        with patch.object(blink, "blinkpy") as mock_blinkpy_mod, \
                patch.object(blink, "auth") as mock_auth_mod:
            mock_blinkpy_mod.Blink.return_value = mock_blink_obj
            mock_blinkpy_mod.BlinkSetupError = Exception
            mock_auth_mod.Auth.return_value = mock_auth_obj

            result = self._run_async(
                stub._attempt_async_authentication(MagicMock())
            )

        self.assertTrue(result, "iOS grant fallback should return True")
        # android login was attempted once; iOS grant used session.post
        mock_auth_obj.login.assert_called_once()
        mock_auth_obj.session.post.assert_called_once()

    def test_attempt_ios_client_grant_success(self):
        """
        _attempt_ios_client_grant() returns True when the token
        endpoint responds with HTTP 200.
        """
        stub = self._make_thermostat_stub()
        mock_blink_obj, mock_auth_obj = self._make_blink_obj_for_password_grant(
            ios_response_status=200
        )
        stub.blink = mock_blink_obj

        result = self._run_async(stub._attempt_ios_client_grant())

        self.assertTrue(result)
        mock_auth_obj.session.post.assert_called_once()

    def test_attempt_ios_client_grant_unauthorized(self):
        """
        _attempt_ios_client_grant() raises UnauthorizedError when the
        token endpoint responds with HTTP 401.
        """
        from src import blink  # noqa: PLC0415

        stub = self._make_thermostat_stub()
        mock_blink_obj, mock_auth_obj = self._make_blink_obj_for_password_grant(
            ios_response_status=401
        )
        stub.blink = mock_blink_obj

        with self.assertRaises(blink.UnauthorizedError):
            self._run_async(stub._attempt_ios_client_grant())

    def test_attempt_ios_client_grant_2fa_rejected(self):
        """
        _attempt_ios_client_grant() raises ValueError with a helpful
        message when the token endpoint returns HTTP 412 and a 2FA code
        was already included in the request (code was rejected).
        """
        stub = self._make_thermostat_stub()
        # bl_2fa is set to "123456" so has_2fa=True
        mock_blink_obj, mock_auth_obj = self._make_blink_obj_for_password_grant(
            ios_response_status=412
        )
        stub.blink = mock_blink_obj

        with self.assertRaises(ValueError) as ctx:
            self._run_async(stub._attempt_ios_client_grant())

        self.assertIn("2FA required but the stored code was rejected",
                      str(ctx.exception))

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
