"""Blink Camera."""

# built-in imports
import asyncio
import json
import logging
import os
import pprint
import sys
import time
import traceback
from typing import Union
from aiohttp import ClientSession, TraceConfig

# third party imports

# local imports
from src import blink_config
from src import environment as env
from src import thermostat_api as api
from src import thermostat_common as tc
from src import utilities as util

# Blink library
BLINK_DEBUG = False  # debug uses local blink repo instead of pkg
BLINKPY_BLINKPY_MODULE = "blinkpy.blinkpy"  # module path constant
NO_ERROR_MSG = "(no message)"  # fallback when exception has no message text
if BLINK_DEBUG and not env.is_azure_environment():
    pkg = BLINKPY_BLINKPY_MODULE
    mod_path = "..\\blinkpy"
    if env.is_interactive_environment():
        mod_path = "..\\" + mod_path
    blinkpy = env.dynamic_module_import(BLINKPY_BLINKPY_MODULE, mod_path, pkg)
    auth = env.dynamic_module_import("blinkpy.auth", mod_path, pkg)
else:
    from blinkpy import auth  # noqa E402, from path / site packages
    from blinkpy import blinkpy  # noqa E402, from path / site packages

# Import blinkpy exceptions for proper error handling
try:
    from blinkpy.auth import (  # type: ignore
        LoginError,
        UnauthorizedError,
        BlinkTwoFARequiredError,
    )
    from aiohttp.client_exceptions import (  # type: ignore
        ClientConnectionError,
        ContentTypeError,
    )
except ImportError:
    # Fallback for older versions or missing exceptions
    class LoginError(Exception):
        """Login error fallback."""

        pass

    class UnauthorizedError(Exception):
        """Unauthorized error fallback."""

        pass

    class BlinkTwoFARequiredError(Exception):
        """Two-factor authentication required error fallback."""

        pass

    class ClientConnectionError(Exception):
        """Client connection error fallback."""

        pass

    class ContentTypeError(Exception):
        """Content type error fallback."""

        pass


# Path for token cache file used to persist refresh token across runs.
# Storing the refresh token allows blinkpy to skip the PKCE web flow on
# subsequent authentication attempts (auth.startup() tries refresh first).
TOKEN_CACHE_FILE = "./data/blink_auth_cache.json"


def _write_cache_file_sync(cache_data: dict) -> None:
    """Write cache data to TOKEN_CACHE_FILE with restricted permissions.

    This sync helper is called via asyncio.to_thread() to avoid blocking the
    event loop.  Using os.open() with mode 0o600 ensures the cache file
    (which may contain a refresh token) is owner-readable only on POSIX.

    Args:
        cache_data (dict): Token data to serialise as JSON.
    """
    fd = os.open(TOKEN_CACHE_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        f = os.fdopen(fd, "w", encoding="utf-8")
    except Exception:
        os.close(fd)
        raise
    with f:
        json.dump(cache_data, f, indent=2)


class ThermostatClass(blinkpy.Blink, tc.ThermostatCommon):  # type: ignore[misc]
    """Blink Camera thermostat functions."""

    def __init__(self, zone, verbose=True):
        """
        Constructor, connect to thermostat.

        inputs:
            zone(str):  zone of thermostat.
            verbose(bool): debug flag.
        """
        # Initialize parent classes
        tc.ThermostatCommon.__init__(self)

        # Blink server auth credentials from env vars
        self.BL_UNAME_KEY = "BLINK_USERNAME"
        self.BL_PASSWORD_KEY = "BLINK_PASSWORD"
        self.BL_2FA_KEY = "BLINK_2FA"
        self.zone_number = int(zone)

        # Get username
        uname_result = env.get_env_variable(
            self.BL_UNAME_KEY,
            default="<" + self.BL_UNAME_KEY + api.KEY_MISSING_SUFFIX
        )
        self.bl_uname = uname_result["value"]

        # Get password
        pwd_result = env.get_env_variable(
            self.BL_PASSWORD_KEY,
            default="<" + self.BL_PASSWORD_KEY + api.KEY_MISSING_SUFFIX
        )
        self.bl_pwd = pwd_result["value"]

        # Get 2FA with detailed logging
        twofa_result = env.get_env_variable(
            self.BL_2FA_KEY,
            default="<" + self.BL_2FA_KEY + api.KEY_MISSING_SUFFIX
        )
        self.bl_2fa = twofa_result["value"]
        self._log_2fa_source(twofa_result)

        self.auth_dict = {"username": self.bl_uname, "password": self.bl_pwd}
        self.verbose = verbose

        # Validate credentials early: catch blank/missing values before
        # attempting network auth so the error message pinpoints the cause.
        self._validate_credentials()

        # connect to Blink server and authenticate
        self.args = None
        self.thermostat_type = None
        self.blink = None
        if env.get_package_version(blinkpy) >= (0, 22, 0):  # type: ignore[operator]
            asyncio.run(self.async_auth_start())
        else:
            self.auth_start()

        # get cameras
        self.camera_metadata = {}
        self.get_cameras()

        # configure zone info
        self.zone_name = self.get_zone_name()
        self.device_id = None  # initialize
        self.device_id = self.get_target_zone_id(self.zone_number)
        self.serial_number = None  # will be populated when unit is queried.

    def _validate_credentials(self):
        """
        Validate that required credentials are present and non-empty.

        Checks the username and password loaded from the environment.
        If any required field is blank, empty, or is still the placeholder
        sentinel value produced when the env key is missing, a descriptive
        ``ValueError`` is raised immediately so the caller sees a targeted
        error message instead of a cryptic Blink server rejection.

        Note: BLINK_2FA is optional and is not validated here; it is
        consumed directly by the async auth flow when present.

        Common causes of a missing/blank value on Windows:
        - The ``supervisor-env.txt`` file was saved with a UTF-8 BOM by
          Notepad or another editor; the BOM prefix corrupts the first key
          name so the lookup silently returns the sentinel default.
        - The environment variable is not set in the shell or the file.

        raises:
            ValueError: with a specific message identifying which credential
                is missing or blank and where to set it.
        """
        # Build the exact sentinel strings used when an env key is missing.
        uname_sentinel = "<" + self.BL_UNAME_KEY + api.KEY_MISSING_SUFFIX
        pwd_sentinel = "<" + self.BL_PASSWORD_KEY + api.KEY_MISSING_SUFFIX
        issues = []

        # Validate username
        if not self.bl_uname or not self.bl_uname.strip():
            issues.append(
                f"BLINK_USERNAME is blank or empty. "
                f"Check that {self.BL_UNAME_KEY} is set in "
                f"supervisor-env.txt or as an environment variable."
            )
        elif self.bl_uname == uname_sentinel:
            issues.append(
                f"BLINK_USERNAME is missing. "
                f"Set {self.BL_UNAME_KEY} in supervisor-env.txt "
                f"or as an environment variable."
            )

        # Validate password
        if not self.bl_pwd or not self.bl_pwd.strip():
            issues.append(
                f"BLINK_PASSWORD is blank or empty. "
                f"Check that {self.BL_PASSWORD_KEY} is set in "
                f"supervisor-env.txt or as an environment variable."
            )
        elif self.bl_pwd == pwd_sentinel:
            issues.append(
                f"BLINK_PASSWORD is missing. "
                f"Set {self.BL_PASSWORD_KEY} in supervisor-env.txt "
                f"or as an environment variable."
            )

        if issues:
            details = "; ".join(issues)
            raise ValueError(
                f"[Blink zone {self.zone_number}] Credential validation "
                f"failed — authentication cannot proceed. {details} "
                f"Tip: if supervisor-env.txt was saved on Windows, "
                f"ensure the file is encoded as UTF-8 WITHOUT BOM "
                f"(in Notepad, choose 'Save As' and select 'UTF-8' "
                f"instead of 'UTF-8 with BOM')."
            )

    def _log_2fa_source(self, twofa_result):
        """
        Log the source of the 2FA code with appropriate masking.

        inputs:
            twofa_result(dict): result from get_env_variable with source info
        returns:
            None
        """
        source = twofa_result.get("source", "unknown")
        value = twofa_result.get("value", "")

        # Create source message
        if source == "supervisor-env.txt":
            source_msg = "using stored 2FA from supervisor-env.txt"
        elif source == "environment_variable":
            source_msg = "using stored 2FA from environment variable"
        elif source == "default":
            source_msg = "using default 2FA value (missing)"
        else:
            source_msg = f"using 2FA from {source}"

        # Mask or show 2FA based on debug mode
        debug_enabled = getattr(util.log_msg, "debug", False)
        if debug_enabled:
            # Show actual 2FA in debug mode
            twofa_display = f"2FA code: {value}"
        else:
            # Mask 2FA in non-debug mode
            if value and not value.startswith("<"):
                twofa_display = "2FA code: ******"
            else:
                twofa_display = f"2FA code: {value}"

        # Log the information
        util.log_msg(
            f"Blink zone {self.zone_number}: {source_msg}, {twofa_display}",
            mode=util.STDOUT_LOG + util.DATA_LOG,
        )

    def _handle_auth_retry(self, attempt, max_retries, retry_delay, error):
        """Handle authentication retry logic."""
        error_type = type(error).__name__
        error_detail = str(error) if str(error) else NO_ERROR_MSG
        if attempt < max_retries - 1:
            if self.verbose:
                print(
                    f"Authentication attempt {attempt + 1} failed: "
                    f"[{error_type}] {error_detail}. "
                    f"Retrying in {retry_delay} seconds..."
                )
                print(traceback.format_exc())
            time.sleep(retry_delay)
            return retry_delay * 2  # exponential backoff
        else:
            # Final attempt failed
            error_msg = self._format_auth_error(error, "sync")
            banner = "*" * len(error_msg)
            print(banner)
            print(error_msg)
            print(banner)
            sys.exit(1)

    def _handle_setup_retry(self, attempt, max_retries, retry_delay):
        """Handle setup post-verification retry logic."""
        if attempt < max_retries - 1:
            if self.verbose:
                print(
                    f"Post-verification setup failed, retrying in "
                    f"{retry_delay} seconds... "
                    f"(attempt {attempt + 1})"
                )
            time.sleep(retry_delay)
            return True  # Continue retry loop
        else:
            raise RuntimeError(
                "Blink post-verification setup failed after retries. "
                "Camera list may not be available."
            )

    def _attempt_authentication(self):
        """Attempt single authentication process."""
        self.blink = blinkpy.Blink()  # type: ignore[misc]
        if self.blink is None:
            raise RuntimeError(
                "ERROR: Blink object failed to instantiate "
                f"for zone {self.zone_number}"
            )

        self.blink.auth = auth.Auth(  # type: ignore[misc]
            self.auth_dict, no_prompt=True
        )
        self.blink.start()

        # Send 2FA key with proper error checking
        auth_success = self.blink.auth.send_auth_key(  # type: ignore[attr-defined]
            self.blink, self.bl_2fa
        )
        if not auth_success:
            raise ValueError(
                "2FA verification failed. Please check your verification code."
            )

        # Check if setup_post_verify succeeds with retry
        setup_success = self.blink.setup_post_verify()
        return setup_success

    def auth_start(self):
        """
        blinkpy < 0.22.0-compatible start with improved error handling
        """
        self._setup_auth_parameters()
        self._execute_auth_with_retry()

    def _setup_auth_parameters(self):
        """Setup authentication parameters."""
        self.args = [self.bl_uname, self.bl_pwd]
        self.thermostat_type = blink_config.ALIAS

    def _execute_auth_with_retry(self):
        """Execute authentication with retry logic."""
        max_retries = 3
        retry_delay = 5  # seconds
        expected_exceptions = (
            AttributeError,
            ValueError,
            KeyError,
            LoginError,
            UnauthorizedError,
            ClientConnectionError,
            ContentTypeError,
        )

        for attempt in range(max_retries):
            try:
                setup_success = self._attempt_authentication()
                if not setup_success:
                    if self._handle_setup_retry(attempt, max_retries, retry_delay):
                        continue
                break

            except expected_exceptions as e:
                retry_delay = self._handle_auth_retry(
                    attempt, max_retries, retry_delay, e
                )
                continue
            except Exception as e:
                self._handle_unexpected_error(e)

    async def _execute_async_auth_with_retry(self, session):
        """Execute async authentication with retry logic."""
        max_retries = 3
        retry_delay = 5  # seconds
        expected_exceptions = (
            AttributeError,
            ValueError,
            KeyError,
            LoginError,
            UnauthorizedError,
            ClientConnectionError,
            ContentTypeError,
        )

        for attempt in range(max_retries):
            try:
                setup_success = await self._attempt_async_authentication(session)
                if not setup_success:
                    if await self._handle_async_setup_retry(
                        attempt, max_retries, retry_delay
                    ):
                        continue
                break

            except expected_exceptions as e:
                retry_delay = await self._handle_async_auth_retry(
                    attempt, max_retries, retry_delay, e
                )
                continue
            except Exception as e:
                self._handle_unexpected_error(e)

    def _handle_unexpected_error(self, error):
        """Handle unexpected errors during authentication."""
        print(traceback.format_exc())

        # Check for specific error patterns
        error_str = str(error)
        if (
            "homescreen" in error_str.lower()
            or "token refresh" in error_str.lower()
        ):
            error_msg = (
                f"ERROR: Blink authentication failed for zone "
                f"{self.zone_number}. The server rejected the request after "
                f"token refresh, likely due to an invalid or expired 2FA code. "
                f"2FA codes from authenticator apps expire after 30-60 seconds. "
                f"Please update your {self.BL_2FA_KEY} environment variable or "
                f"supervisor-env.txt file with a fresh code from your "
                f"authenticator app and restart the application. "
                f"Error: {error_str}"
            )
        else:
            error_msg = (
                f"ERROR: Unexpected error during Blink authentication for zone "
                f"{self.zone_number}: {error_str}"
            )

        banner = "*" * len(error_msg)
        print(banner)
        print(error_msg)
        print(banner)
        sys.exit(1)

    async def _handle_async_auth_retry(self, attempt, max_retries, retry_delay, error):
        """Handle async authentication retry logic."""
        error_type = type(error).__name__
        error_detail = str(error) if str(error) else NO_ERROR_MSG
        if attempt < max_retries - 1:
            if self.verbose:
                print(
                    f"Authentication attempt {attempt + 1} failed: "
                    f"[{error_type}] {error_detail}. "
                    f"Retrying in {retry_delay} seconds..."
                )
                print(traceback.format_exc())
            await asyncio.sleep(retry_delay)
            return retry_delay * 2  # exponential backoff
        else:
            # Final attempt failed
            error_msg = self._format_auth_error(error, "async")
            banner = "*" * len(error_msg)
            print(banner)
            print(error_msg)
            print(banner)
            sys.exit(1)

    async def _handle_async_setup_retry(self, attempt, max_retries, retry_delay):
        """Handle async setup post-verification retry logic."""
        if attempt < max_retries - 1:
            if self.verbose:
                print(
                    f"Post-verification setup failed, retrying in "
                    f"{retry_delay} seconds... (attempt {attempt + 1})"
                )
            await asyncio.sleep(retry_delay)
            return True  # Continue retry loop
        else:
            raise RuntimeError(
                "Blink post-verification setup failed after "
                "retries. Camera list may not be available."
            )

    def _load_token_cache(self) -> dict:
        """
        Load cached auth tokens from the token cache file.

        If the file exists and contains a valid ``refresh_token`` and
        ``hardware_id``, the cached data is returned so it can be merged
        into the ``Auth`` initialisation dict.  When ``auth.startup()``
        receives a non-empty ``refresh_token`` + ``hardware_id`` it tries
        the OAuth v2 token-refresh path first, skipping the PKCE web flow
        entirely.  The PKCE web flow is only attempted when the refresh
        token is absent or has expired.

        The cache file intentionally does **not** store username or
        password — those are already held in ``supervisor-env.txt``.

        returns:
            (dict): Cached token data (may be empty if no valid cache).
        """
        if not os.path.exists(TOKEN_CACHE_FILE):
            return {}
        try:
            with open(TOKEN_CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
            if cache.get("refresh_token") and cache.get("hardware_id"):
                if self.verbose:
                    hw_suffix = cache["hardware_id"][-8:]
                    print(
                        f"[Blink zone {self.zone_number}] Loaded token "
                        f"cache (hardware_id: ...{hw_suffix}). "
                        f"Refresh token will be tried first."
                    )
                return cache
        except (json.JSONDecodeError, OSError, KeyError) as exc:
            if self.verbose:
                print(
                    f"[Blink zone {self.zone_number}] Could not load "
                    f"token cache: {exc}"
                )
        return {}

    async def _save_token_cache(self) -> None:
        """
        Save auth tokens to the token cache file after a successful login.

        The cache stores the OAuth access token, refresh token,
        ``hardware_id``, and related metadata produced by blinkpy after
        successful authentication.  On the next run ``_load_token_cache``
        returns this data so ``auth.startup()`` can use the refresh token
        path instead of re-running the full PKCE web flow.

        Username and password are **not** saved — they are already stored
        in ``supervisor-env.txt`` and are merged back when creating
        ``Auth`` for each run.

        Silently skips saving if ``self.blink`` or ``self.blink.auth`` is
        not yet initialised.
        """
        if self.blink is None or not hasattr(self.blink, "auth"):
            return
        if self.blink.auth is None:
            return
        try:
            os.makedirs(os.path.dirname(TOKEN_CACHE_FILE) or ".", exist_ok=True)
            # Guard: login_attributes may be absent or not dict-like in some
            # blinkpy versions; convert defensively to avoid AttributeError.
            try:
                cache_data = dict(self.blink.auth.login_attributes)
            except (AttributeError, TypeError, ValueError):
                if self.verbose:
                    print(
                        f"[Blink zone {self.zone_number}] Warning: "
                        f"login_attributes unavailable; skipping token cache."
                    )
                return
            cache_data.pop("username", None)
            cache_data.pop("password", None)
            # Offload blocking file I/O to a thread to avoid blocking the
            # event loop.  _write_cache_file_sync uses os.open() with mode
            # 0o600 to restrict read/write access to the owner only.
            await asyncio.to_thread(_write_cache_file_sync, cache_data)
            if self.verbose:
                print(
                    f"[Blink zone {self.zone_number}] Token cache saved "
                    f"to {TOKEN_CACHE_FILE}. "
                    f"Future logins will use the refresh token."
                )
        except OSError as exc:
            if self.verbose:
                print(
                    f"[Blink zone {self.zone_number}] Warning: could not "
                    f"save token cache: {exc}"
                )

    async def _attempt_async_authentication(self, session):
        """
        Attempt single async authentication process.

        Tries two authentication paths in order:

        1. **Token refresh** (if a cached ``refresh_token`` and
           ``hardware_id`` exist from a previous run): blinkpy's
           ``auth.startup()`` tries an OAuth v2 token refresh first.
           On success the full PKCE web flow is bypassed entirely.
           If the cached token has expired, ``startup()`` automatically
           falls through to the PKCE web flow.
        2. **OAuth v2 PKCE web flow** (blinkpy 0.25.x+, preferred fresh
           login): ``blink.start()`` orchestrates a full PKCE
           authorization-code flow.  If ``BlinkTwoFARequiredError`` is
           raised, 2FA is completed via ``send_2fa_code()`` or the legacy
           ``send_auth_key()`` API.
        3. **Password grant fallback** (``auth.login()``): used when the
           PKCE web flow returns ``False`` (e.g. Blink's web signin page
           returns an unexpected HTTP status such as 406).  This is the
           legacy OAuth password-grant path (``client_id=android``) that
           blinkpy uses for token refresh internally.

        After any successful authentication the tokens are saved to the
        cache file so the next run can use the refresh token path.
        """
        # Merge cached tokens into the auth-init dict so that
        # auth.startup() will attempt token refresh before PKCE.
        cached = self._load_token_cache()
        auth_init_data = dict(self.auth_dict)
        if cached:
            auth_init_data.update(cached)

        self.blink = blinkpy.Blink(session=session)  # type: ignore[misc]
        self.blink.auth = auth.Auth(  # type: ignore[misc]
            auth_init_data, no_prompt=True, session=session
        )

        if self.verbose:
            if cached:
                print(
                    f"[Blink zone {self.zone_number}] Attempting auth "
                    f"(cached token present — refresh tried first)..."
                )
            else:
                print(
                    f"[Blink zone {self.zone_number}] Attempting OAuth v2 "
                    f"PKCE web flow via blink.start()..."
                )

        # Path 1 + 2: token refresh (if cached) then PKCE web flow.
        # BlinkTwoFARequiredError is only raised by the PKCE path.
        try:
            result = await self.blink.start()
        except BlinkTwoFARequiredError:
            if self.verbose:
                print(
                    f"[Blink zone {self.zone_number}] 2FA required. "
                    f"Completing via send_2fa_code()..."
                )
            result = await self._complete_2fa_auth()
            if not result:
                raise ValueError(
                    "2FA verification failed. Please check your "
                    "verification code."
                )
            await self._save_token_cache()
            return result

        if result:
            if self.verbose:
                print(
                    f"[Blink zone {self.zone_number}] Authentication "
                    f"succeeded."
                )
            await self._save_token_cache()
            return result

        # Path 3: Password grant fallback via auth.login().
        # Used when the PKCE web flow returns False — e.g. Blink's
        # OAuth web signin returns HTTP 406 (rate limiting / account
        # lockout), which causes oauth_signin() to return None and
        # blinkpy to log "Login failed".
        #
        # However, if the PKCE failure was caused by a 2FA rate limit
        # (HTTP 429 "2fa_rate_limit_exceeded") the password grant will
        # not help either — stop retrying immediately and inform the
        # user of the lockout period.
        if getattr(self, "_rate_limit_detected", False):
            self._handle_rate_limit_error()  # never returns
        if self.verbose:
            print(
                f"[Blink zone {self.zone_number}] OAuth v2 web flow "
                f"returned False. Trying password grant fallback via "
                f"auth.login()..."
            )
        result = await self._attempt_password_grant_auth()
        if result:
            await self._save_token_cache()
        return result

    def _handle_rate_limit_error(self) -> None:
        """
        Display a clear 2FA rate-limit error message and exit.

        Called when the HTTP trace detects a 429
        ``2fa_rate_limit_exceeded`` response during the OAuth v2 PKCE
        sign-in step.  Blink enforces this limit when too many 2FA
        verification requests are made in a short period — for example
        when repeated login runs each trigger a new 2FA code delivery
        to the user's phone or email.

        The account is locked for the period reported in the server
        response ``next_time_in_secs`` (typically 86400 s = 24 hours).

        This method **never returns** — it calls ``sys.exit(1)`` after
        printing the error banner so the retry loop cannot continue and
        worsen the rate-limit situation.
        """
        wait_secs = self._rate_limit_next_time_secs or 86400
        wait_hours = wait_secs // 3600
        wait_mins = (wait_secs % 3600) // 60
        error_lines = [
            f"ERROR: Blink 2FA rate limit exceeded for zone "
            f"{self.zone_number}.",
            f"Blink has locked your account's 2FA for approximately "
            f"{wait_hours} hour(s) {wait_mins} minute(s) "
            f"({wait_secs} seconds).",
            "This happens when too many 2FA-login requests are made "
            "in a short period (e.g. repeated runs with a stale code).",
            "Recommended actions:",
            f"  1. Wait {wait_hours} hour(s) before retrying.",
            "  2. Sign into the official Blink mobile app to verify "
            "your account is accessible.",
            f"  3. When the lockout expires, update {self.BL_2FA_KEY} "
            f"in supervisor-env.txt with a fresh 2FA code sent by Blink.",
            f"  4. Delete {TOKEN_CACHE_FILE} (if present) to force a "
            f"clean login on the next run.",
        ]
        banner_len = max(len(line) for line in error_lines)
        banner = "*" * banner_len
        print(banner)
        for line in error_lines:
            print(line)
        print(banner)
        sys.exit(1)

    async def _attempt_password_grant_auth(self):
        """
        Fallback: authenticate via the legacy OAuth password grant.

        Calls ``auth.login()`` which POSTs to the Blink OAuth token
        endpoint (``/oauth/token``) with ``client_id=android`` and
        ``grant_type=password``.  This is the pre-PKCE authentication
        path still present in blinkpy for internal token-refresh use.
        It is tried when the OAuth v2 PKCE web flow (``blink.start()``)
        returns ``False`` — for example when Blink's PKCE signin page
        returns an unexpected HTTP status such as 406.

        Note: Blink's server may return HTTP 401 with
        ``"error": "unsupported_grant_type"`` indicating that the
        password grant flow has been permanently disabled on their
        end.  When this occurs ``UnauthorizedError`` is raised and a
        ``ValueError`` is propagated with targeted guidance.

        If ``auth.login()`` raises ``BlinkTwoFARequiredError`` (HTTP 412)
        the stored 2FA code is added to the next request and login is
        retried via ``_complete_password_grant_2fa``.

        returns:
            (bool): True if authentication succeeded.
        raises:
            ValueError: if the server rejects the password grant or all
                auth paths have failed (includes rate-limiting guidance).
        """
        try:
            login_data = await self.blink.auth.login()
        except BlinkTwoFARequiredError:
            # Blink requires 2FA for this login attempt (HTTP 412).
            if self.verbose:
                print(
                    f"[Blink zone {self.zone_number}] Password grant: "
                    f"2FA required. Retrying with stored 2FA code..."
                )
            return await self._complete_password_grant_2fa()
        except (UnauthorizedError, LoginError) as e:
            # 4xx/5xx rejection from the password grant endpoint.
            # HTTP 401 with "unsupported_grant_type" is a common response
            # when Blink has disabled password grant, but other errors are
            # also possible (invalid credentials, account locked, etc.).
            error_type = type(e).__name__
            error_detail = str(e) if str(e) else NO_ERROR_MSG
            if self.verbose:
                print(
                    f"[Blink zone {self.zone_number}] Password grant "
                    f"failed: [{error_type}] {error_detail}"
                )
                print(traceback.format_exc())
            extra_hint = ""
            if "unsupported_grant_type" in error_detail:
                extra_hint = (
                    " The 'unsupported_grant_type' error indicates the "
                    "password grant path has been permanently disabled by "
                    "Blink; the only supported login path is the OAuth v2 "
                    "PKCE web flow (blink.start()). "
                )
            raise ValueError(
                f"Blink password grant rejected for zone "
                f"{self.zone_number}. [{error_type}] {error_detail}."
                f"{extra_hint}"
                f"Recommended actions: "
                f"(1) Ensure your credentials in supervisor-env.txt "
                f"are correct (username, password). "
                f"(2) Update {self.BL_2FA_KEY} with a fresh 2FA code "
                f"received from Blink. "
                f"(3) Sign into the official Blink app to verify your "
                f"account is accessible before retrying."
            ) from e

        if not login_data:
            raise ValueError(
                f"Blink password grant returned no token data for zone "
                f"{self.zone_number}. Please verify your credentials."
            )

        return await self._setup_blink_after_login(login_data)

    async def _complete_password_grant_2fa(self):
        """
        Complete 2FA for the password grant authentication path.

        After auth.login() raises BlinkTwoFARequiredError (HTTP 412), Blink
        sends a new code to the user.  This method adds the stored 2FA code
        to the auth data and retries the password grant so that the code is
        sent in the '2fa-code' request header.

        returns:
            (bool): True if authentication completed, False otherwise.
        raises:
            ValueError: if the 2FA code is rejected or login returns no data.
        """
        # Include the stored 2FA code in the next login request headers.
        self.blink.auth.data["2fa_code"] = self.bl_2fa
        try:
            login_data = await self.blink.auth.login()
        except BlinkTwoFARequiredError:
            raise ValueError(
                "2FA verification failed for password grant. "
                "The stored 2FA code may be expired or incorrect. "
                f"Please update {self.BL_2FA_KEY} in supervisor-env.txt "
                "with a fresh code and restart the application."
            )
        finally:
            # Always remove the 2FA code to avoid leaking it into future
            # requests or retries.
            self.blink.auth.data.pop("2fa_code", None)

        if not login_data:
            raise ValueError(
                "2FA completion returned no token data for zone "
                f"{self.zone_number}."
            )

        return await self._setup_blink_after_login(login_data)

    async def _setup_blink_after_login(self, login_data):
        """
        Complete Blink setup after a successful password grant login.

        Processes the token response and runs the same setup steps that
        blink.start() would normally execute after auth.startup():
        token processing, URL setup, homescreen fetch, and post-verify.

        inputs:
            login_data (dict): token response from auth.login().
        returns:
            (bool): True if setup completed successfully, False otherwise.
        """
        await self.blink.auth._process_token_data(login_data)

        try:
            self.blink.setup_urls()
            await self.blink.get_homescreen()
        except blinkpy.BlinkSetupError:
            self.blink.available = False
            return False

        if not self.blink.last_refresh:
            self.blink.last_refresh = int(
                time.time() - self.blink.refresh_rate * 1.05
            )

        return await self.blink.setup_post_verify()

    async def _complete_2fa_auth(self):
        """
        Complete 2FA for the OAuth v2 web flow (blink.start() path).

        Uses send_2fa_code (blinkpy 0.25.x OAuth v2) when available,
        falling back to the legacy send_auth_key API for 0.22.x.

        returns:
            (bool): True if 2FA completed successfully, False otherwise.
        """
        if hasattr(self.blink, "send_2fa_code"):
            # New blinkpy 0.25.x API (OAuth v2)
            return await self.blink.send_2fa_code(self.bl_2fa)

        if hasattr(self.blink.auth, "send_auth_key"):
            # Legacy blinkpy 0.22.x API
            auth_success = await self.blink.auth.send_auth_key(  # type: ignore
                self.blink, self.bl_2fa
            )
            if not auth_success:
                return False
            return await self.blink.setup_post_verify()

        raise ValueError(
            "Unsupported blinkpy version: no 2FA completion method found. "
            "Please update blinkpy to a supported version."
        )

    def _configure_blink_logging(self) -> None:
        """
        Enable DEBUG-level Python logging for blinkpy when verbose mode
        is active.

        This surfaces every internal blinkpy log message (HTTP step
        outcomes, PKCE flow progress, token refresh attempts, etc.) on
        stdout so the caller can see exactly where authentication stalls.
        The handler is idempotent — calling this method multiple times
        will not duplicate handlers.

        The StreamHandler is added only to the root ``blinkpy`` logger.
        Child loggers (``blinkpy.auth``, ``blinkpy.blinkpy``, etc.)
        propagate to the parent by default in Python's logging hierarchy,
        so attaching the handler only to the parent ensures each message
        is emitted exactly once rather than once per ancestor.
        """
        if not self.verbose:
            return

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("[blinkpy] %(name)s %(levelname)s: %(message)s")
        )

        # Add handler to the root blinkpy logger only; child loggers
        # propagate to it naturally, preventing duplicate log entries.
        root_logger = logging.getLogger("blinkpy")
        if not any(
            isinstance(h, logging.StreamHandler) and h.stream is sys.stdout
            for h in root_logger.handlers
        ):
            root_logger.addHandler(handler)
        root_logger.setLevel(logging.DEBUG)

        # Set child loggers to DEBUG so their messages are not filtered
        # before reaching the parent handler, but do not add separate
        # handlers to avoid double-logging via propagation.
        for name in ("blinkpy.auth", BLINKPY_BLINKPY_MODULE, "blinkpy.api"):
            logging.getLogger(name).setLevel(logging.DEBUG)

    def _create_http_trace_config(self) -> TraceConfig:
        """
        Build an aiohttp TraceConfig for HTTP monitoring during auth.

        Always runs (regardless of ``self.verbose``) to enable server-side
        rate-limit detection.  When a HTTP 429 response body contains
        ``"error_cause": "2fa_rate_limit_exceeded"``, the instance
        attributes ``_rate_limit_detected`` (True) and
        ``_rate_limit_next_time_secs`` are set so that
        ``_attempt_async_authentication`` can abort retrying immediately
        and show a clear wait-time message.

        When ``self.verbose`` is True, each request URL and response
        status code are also printed to stdout so the caller can trace
        exactly which authentication step fails.  Network exceptions
        are printed as well.

        returns:
            (TraceConfig): configured trace config object ready to attach
                to a ClientSession.
        """
        zone = self.zone_number

        async def _on_request_start(_session, _ctx, params) -> None:
            if self.verbose:
                host = params.url.host or ""
                path = params.url.path or ""
                print(
                    f"[Blink zone {zone}][HTTP→] "
                    f"{params.method} {host}{path}"
                )
            # Yield to the event loop; aiohttp trace callbacks must be async.
            await asyncio.sleep(0)

        async def _on_request_end(_session, _ctx, params) -> None:
            status = params.response.status
            if self.verbose:
                host = params.url.host or ""
                path = params.url.path or ""
                print(
                    f"[Blink zone {zone}][HTTP←] "
                    f"{status} {host}{path}"
                )
            if status >= 400:
                # Read and cache the response body. aiohttp caches the
                # body after the first read() so blinkpy can still
                # consume it afterwards.
                body_bytes = b""
                try:
                    body_bytes = await params.response.read()
                except Exception as exc:
                    if self.verbose:
                        print(
                            f"[Blink zone {zone}][HTTP {status} body] "
                            f"(could not read: {exc})"
                        )

                if body_bytes:
                    if self.verbose:
                        snippet = (
                            body_bytes.decode("utf-8", errors="replace")[
                                :500
                            ].replace("\n", " ")
                        )
                        print(
                            f"[Blink zone {zone}]"
                            f"[HTTP {status} body] {snippet}"
                        )

                    # Detect 2FA rate limit (HTTP 429) unconditionally
                    # so we can stop retrying even when verbose=False.
                    if status == 429:
                        try:
                            body_json = json.loads(body_bytes)
                            if (
                                body_json.get("error_cause")
                                == "2fa_rate_limit_exceeded"
                            ):
                                self._rate_limit_detected = True
                                self._rate_limit_next_time_secs = (
                                    body_json.get("next_time_in_secs")
                                )
                        except Exception:
                            pass

                if self.verbose and status == 406:
                    print(
                        f"[Blink zone {zone}] NOTE: HTTP 406 may "
                        f"indicate temporary account lockout or IP "
                        f"rate-limiting by Blink's server. "
                        f"If all auth paths fail, try waiting 15-30 "
                        f"minutes and signing into the official Blink "
                        f"mobile app before retrying."
                    )

        async def _on_request_exception(_session, _ctx, params) -> None:
            if self.verbose:
                exc = params.exception
                host = params.url.host or ""
                path = params.url.path or ""
                print(
                    f"[Blink zone {zone}][HTTP✗] "
                    f"{type(exc).__name__}: {exc} {host}{path}"
                )
            # Yield to the event loop; aiohttp trace callbacks must be async.
            await asyncio.sleep(0)

        tc = TraceConfig()
        tc.on_request_start.append(_on_request_start)
        tc.on_request_end.append(_on_request_end)
        tc.on_request_exception.append(_on_request_exception)
        return tc

    async def async_auth_start(self):
        """
        Async auth start, compatible with blinkpy 0.22.0+.

        blinkpy 0.22.0 introduced the async start flow. blinkpy 0.25.x+
        uses OAuth v2 (BlinkTwoFARequiredError / send_2fa_code). Older
        0.22.x used send_auth_key for 2FA completion. Both are handled by
        _attempt_async_authentication via _complete_2fa_auth.

        An aiohttp TraceConfig is **always** attached (regardless of
        ``self.verbose``) so that HTTP 429 ``2fa_rate_limit_exceeded``
        responses are detected and the retry loop is aborted immediately.
        When ``self.verbose`` is True, DEBUG-level blinkpy logging is
        also enabled and per-request log lines are printed to stdout.
        """
        self._configure_blink_logging()
        # Initialise rate-limit detection state; set by the TraceConfig
        # callback when a HTTP 429 2fa_rate_limit_exceeded is received.
        self._rate_limit_detected = False
        self._rate_limit_next_time_secs = None
        # Always attach trace config — needed for rate-limit detection
        # even when verbose=False.  Verbose output is gated inside the
        # trace callbacks on self.verbose.
        async with ClientSession(
            trace_configs=[self._create_http_trace_config()]
        ) as session:
            self._setup_auth_parameters()
            await self._execute_async_auth_with_retry(session)

    def _format_auth_error(self, error, auth_type="sync"):
        """
        Format authentication error messages with specific guidance.

        inputs:
            error: The exception that occurred
            auth_type: "sync" or "async" to indicate which auth method failed
        returns:
            (str): Formatted error message with troubleshooting guidance
        """
        error_type = type(error).__name__
        error_str = str(error)

        error_handlers = {
            LoginError: self._format_login_error,
            UnauthorizedError: self._format_unauthorized_error,
            ClientConnectionError: self._format_connection_error,
            ContentTypeError: self._format_content_error,
            BlinkTwoFARequiredError: self._format_2fa_required_error,
            ValueError: self._format_value_error,
            AttributeError: self._format_attribute_error,
        }

        handler = error_handlers.get(type(error))
        if handler:
            return handler(error_str, auth_type)

        return self._format_generic_error(error_type, error_str, auth_type)

    def _format_login_error(self, error_str, auth_type):
        """Format login error message."""
        return (
            f"ERROR: Blink login failed for zone {self.zone_number} "
            f"({auth_type} mode). Please check your username and password. "
            f"The Blink server may also be down or experiencing issues. "
            f"Error: {error_str}"
        )

    def _format_unauthorized_error(self, error_str, auth_type):
        """Format unauthorized error message."""
        detail = error_str if error_str else "UnauthorizedError (no detail)"
        return (
            f"ERROR: Blink authorization failed for zone {self.zone_number} "
            f"({auth_type} mode). Your account may be locked or credentials "
            f"may be invalid. Error: {detail}"
        )

    def _format_connection_error(self, error_str, auth_type):
        """Format connection error message."""
        return (
            f"ERROR: Network connection to Blink servers failed for zone "
            f"{self.zone_number} ({auth_type} mode). Please check your "
            f"internet connection and try again. Error: {error_str}"
        )

    def _format_content_error(self, error_str, auth_type):
        """Format content type error message."""
        return (
            f"ERROR: Received invalid response from Blink servers for zone "
            f"{self.zone_number} ({auth_type} mode). The server may be "
            f"experiencing issues. Error: {error_str}"
        )

    def _format_value_error(self, error_str, auth_type):
        """Format value error message."""
        if (
            "2FA verification failed" in error_str
            or "Invalid Verification Code" in error_str
        ):
            return (
                f"ERROR: Invalid 2FA verification code for zone "
                f"{self.zone_number} ({auth_type} mode). The 2FA code may "
                f"be expired or incorrect. 2FA codes from authenticator apps "
                f"expire after 30-60 seconds. Please update your "
                f"{self.BL_2FA_KEY} environment variable or "
                f"supervisor-env.txt file with a fresh code from your "
                f"authenticator app and restart the application. "
                f"Error: {error_str}"
            )
        return self._format_generic_error("ValueError", error_str, auth_type)

    def _format_attribute_error(self, error_str, auth_type):
        """Format attribute error message."""
        return (
            f"ERROR: Blink authentication state error for zone "
            f"{self.zone_number} ({auth_type} mode). This may occur if the "
            f"initial login failed. Please verify your credentials and try "
            f"again. Error: {error_str}"
        )

    def _format_2fa_required_error(self, error_str, auth_type):
        """Format two-factor authentication required error message."""
        return (
            f"ERROR: Blink 2FA required but could not be completed for zone "
            f"{self.zone_number} ({auth_type} mode). Please ensure "
            f"{self.BL_2FA_KEY} is set in your environment or "
            f"supervisor-env.txt with a valid, current 2FA code. "
            f"Error: {error_str}"
        )

    def _format_generic_error(self, error_type, error_str, auth_type):
        """Format generic error message."""
        return (
            f"ERROR: Blink authentication failed for zone "
            f"{self.zone_number} ({auth_type} mode). Error type: "
            f"{error_type}. Error details: {error_str}"
        )

    def get_zone_name(self):
        """
        Return the name associated with the zone number from metadata dict.

        inputs:
            None
        returns:
            (str) zone name
        """
        return blink_config.metadata[self.zone_number]["zone_name"]

    def get_target_zone_id(self, zone=0):
        """
        Return the target zone ID.

        inputs:
            zone(int): zone number.
        returns:
            (obj): Blink object
        """
        # return the target zone object
        return zone

    def get_cameras(self):
        """
        Get the blink cameras
        """
        table_length = 20
        if self.verbose:
            print("blink camera inventory:")
            print("-" * table_length)

        if not self.blink.cameras:  # type: ignore[attr-defined]
            if self.verbose:
                print("WARNING: No cameras found in blink.cameras")
                print("This may indicate authentication or setup issues")
            return

        for name, camera in self.blink.cameras.items():  # type: ignore[attr-defined]
            if self.verbose:
                print(name)
                print(camera.attributes)
            self.camera_metadata[name] = camera.attributes
        if self.verbose:
            # type: ignore on next line for dynamic blink attributes
            total = len(self.blink.cameras)  # type: ignore[attr-defined]
            print(f"Total cameras found: {total}")
            print("-" * table_length)

    def get_all_metadata(self, zone=None, retry=False):
        """Get all thermostat meta data for device_id from local API.

        inputs:
            zone(): specified zone
            retry(bool): if True will retry with extended retry mechanism
        returns:
            (dict): dictionary of meta data.
        """
        return self.get_metadata(zone, retry=retry)

    def _handle_empty_camera_list_async(self, zone_name):
        """Handle empty camera list for async version of blinkpy."""
        available_cameras = (
            list(self.blink.cameras.keys())  # type: ignore[attr-defined]
            if self.blink.cameras  # type: ignore[attr-defined]
            else []
        )
        error_msg = (
            f"Camera list is empty when searching for camera "
            f"'{zone_name}'. Available cameras: "
            f"{available_cameras}. This may indicate "
            f"authentication tokens have expired. Please restart "
            f"the application to re-authenticate."
        )
        raise ValueError(error_msg)

    def _handle_token_refresh_failure(self, zone_name, refresh_error):
        """Handle token refresh failure with helpful error message."""
        if self.verbose:
            print(f"Token refresh failed: {str(refresh_error)}")

        available_cameras = (
            # type: ignore on next lines for dynamic blink attributes
            list(self.blink.cameras.keys())  # type: ignore[attr-defined]
            if self.blink.cameras  # type: ignore[attr-defined]
            else []
        )
        error_msg = (
            f"Camera list is empty when searching for "
            f"camera '{zone_name}'. Available cameras: "
            f"{available_cameras}. Authentication token "
            f"refresh failed: {str(refresh_error)}. Please "
            f"restart the application to re-authenticate."
        )
        raise ValueError(error_msg)

    def _attempt_sync_token_refresh(self, zone_name):
        """Attempt to refresh authentication token for sync version."""
        try:
            self._perform_token_refresh()
            self._refresh_camera_data()
        except Exception as refresh_error:
            self._handle_token_refresh_failure(zone_name, refresh_error)

    def _perform_token_refresh(self):
        """Perform the actual token refresh."""
        if self.verbose:
            print("Attempting to refresh authentication token...")
        self.blink.auth.refresh_token()  # type: ignore[attr-defined, operator]

    def _refresh_camera_data(self):
        """Refresh camera data after token refresh."""
        if hasattr(self.blink, "refresh"):
            self.blink.refresh()  # type: ignore[attr-defined]
        elif hasattr(self.blink, "setup_camera_list"):
            self.blink.setup_camera_list()  # type: ignore[attr-defined]

        # Update our local camera metadata cache
        self.get_cameras()

    def _refresh_camera_list_if_empty(self, zone_name):
        """Refresh camera list if it's empty."""
        if self.blink.cameras != {}:  # type: ignore[attr-defined]
            return

        self._log_camera_refresh_attempt(zone_name)

        if not hasattr(self.blink.auth, "refresh_token"):  # type: ignore[attr-defined]
            return

        try:
            self._attempt_camera_refresh(zone_name)
            self._validate_camera_refresh_success(zone_name)
        except Exception as e:
            self._handle_camera_refresh_error(e, zone_name)

    def _log_camera_refresh_attempt(self, zone_name):
        """Log camera refresh attempt."""
        if self.verbose:
            print(
                f"Camera list is empty, attempting to refresh authentication "
                f"and camera list for zone {zone_name}"
            )

    def _attempt_camera_refresh(self, zone_name):
        """Attempt to refresh camera list based on blinkpy version."""
        if env.get_package_version(blinkpy) >= (0, 22, 0):  # type: ignore[operator]
            self._handle_empty_camera_list_async(zone_name)
        else:
            self._attempt_sync_token_refresh(zone_name)

    def _validate_camera_refresh_success(self, zone_name):
        """Validate that camera refresh was successful."""
        if self.blink.cameras == {}:  # type: ignore[attr-defined]
            error_msg = (
                f"Camera list is still empty after refresh attempt "
                f"for camera '{zone_name}'. This may indicate "
                f"authentication failed or no cameras are available. "
                f"Please check your Blink credentials, 2FA code, and "
                f"ensure cameras are online in the Blink app."
            )
            raise ValueError(error_msg)

    def _handle_camera_refresh_error(self, error, zone_name):
        """Handle camera refresh errors."""
        if "Camera list is empty when searching" in str(error):
            raise
        else:
            raise ValueError(
                f"Camera list is empty when searching for camera "
                f"'{zone_name}'. Failed to refresh camera list: {str(error)}"
            )

    def _find_camera_by_name(self, zone_name, parameter):
        """Find camera by name and return its attributes or specific parameter."""
        for name, camera in self.blink.cameras.items():  # type: ignore[attr-defined]
            if name == zone_name:
                if self.verbose:
                    print(f"found camera {name}: {camera.attributes}")
                if parameter is None:
                    return camera.attributes
                else:
                    return camera.attributes[parameter]

        # Camera not found - provide helpful error
        # type: ignore on next line for dynamic blink attributes
        available_cameras = list(
            self.blink.cameras.keys()  # type: ignore[attr-defined]
        )
        error_msg = (
            f"Camera zone '{zone_name}' was not found. "
            f"Available cameras: {available_cameras}. "
            f"Please check the zone name in blink_config.py matches "
            f"your Blink app."
        )
        raise ValueError(error_msg)

    def get_metadata(self, zone=None, trait=None, parameter=None, retry=False):
        """Get thermostat meta data for device_id from local API.

        inputs:
            zone(): specified zone
            trait(str): trait or parent key, if None will assume a non-nested
            dict
            parameter(str): target parameter, if None will return all.
            retry(bool): if True will retry with extended retry mechanism
        returns:
            (dict): dictionary of meta data.
        """
        del trait  # unused on blink

        def _get_metadata_internal():
            zone_name = blink_config.metadata[self.zone_number]["zone_name"]
            self._refresh_camera_list_if_empty(zone_name)
            return self._find_camera_by_name(zone_name, parameter)

        if retry:
            # Use standardized extended retry mechanism
            return util.execute_with_extended_retries(
                func=_get_metadata_internal,
                thermostat_type=getattr(self, "thermostat_type", "Blink"),
                zone_name=str(getattr(self, "zone_name", zone)),
                number_of_retries=5,
                initial_retry_delay_sec=60,
                exception_types=(
                    ValueError,
                    KeyError,
                    AttributeError,
                    ConnectionError,
                    TimeoutError,
                ),
                email_notification=None,  # Blink doesn't import email_notification
            )
        else:
            # Single attempt without retry
            return _get_metadata_internal()

    def print_all_thermostat_metadata(self, zone):
        """Print all metadata for zone to the screen.

        inputs:
            zone(int): specified zone, if None will print all zones.
        returns:
            None, prints result to screen
        """
        self.exec_print_all_thermostat_metadata(self.get_all_metadata, [zone])


class ThermostatZone(tc.ThermostatCommonZone):
    """
    KumoCloud single zone on local network.

    Class needs to be updated for multi-zone support.
    """

    def __init__(self, Thermostat_obj, verbose=True):
        """
        Zone constructor.

        inputs:
            Thermostat(obj): Thermostat class instance.
            verbose(bool): debug flag.
        """
        # construct the superclass, requires auth setup first
        super().__init__()

        # runtime parameter defaults
        self.poll_time_sec = 10 * 60  # default to 10 minutes
        self.connection_time_sec = 8 * 60 * 60  # default to 8 hours

        # server data cache expiration parameters to mitigate spam detection
        self.fetch_interval_sec = 60  # age of server data before refresh (seconds)
        self.last_fetch_time = time.time() - 2 * self.fetch_interval_sec
        self.last_printed_refresh_time = None  # track last printed cache message time

        # switch config for this thermostat
        self.system_switch_position[  # type: ignore[assignment]
            tc.ThermostatCommonZone.COOL_MODE
        ] = "cool"
        self.system_switch_position[  # type: ignore[assignment]
            tc.ThermostatCommonZone.HEAT_MODE
        ] = "heat"
        self.system_switch_position[  # type: ignore[assignment]
            tc.ThermostatCommonZone.OFF_MODE
        ] = "off"
        self.system_switch_position[  # type: ignore[assignment]
            tc.ThermostatCommonZone.DRY_MODE
        ] = "dry"
        self.system_switch_position[  # type: ignore[assignment]
            tc.ThermostatCommonZone.AUTO_MODE
        ] = "auto"
        self.system_switch_position[  # type: ignore[assignment]
            tc.ThermostatCommonZone.FAN_MODE
        ] = "vent"

        # zone info
        self.verbose = verbose
        self.thermostat_type = blink_config.ALIAS
        self.device_id = Thermostat_obj.device_id
        self.Thermostat = Thermostat_obj
        self.zone_number = Thermostat_obj.zone_number
        self.zone_name = self.get_zone_name()
        self.zone_metadata = Thermostat_obj.get_metadata(zone=self.zone_number)

    def get_display_temp(self) -> float:  # used
        """
        Refresh the cached zone information and return Indoor Temp in °F.

        inputs:
            None
        returns:
            (float): indoor temp in °F.
        """
        # Refresh zone metadata if needed (respects cache timeout)
        self.refresh_zone_info()

        raw_temp = self.zone_metadata.get(blink_config.API_TEMPF_MEAN)
        if isinstance(raw_temp, (str, float, int)):
            raw_temp = float(raw_temp)
        elif isinstance(raw_temp, type(None)):
            raw_temp = float(util.BOGUS_INT)
        return raw_temp

    def get_zone_name(self) -> str:
        """
        Return the name associated with the zone number from metadata dict.

        inputs:
            None
        returns:
            (str) zone name
        """
        return blink_config.metadata[self.zone_number]["zone_name"]

    def get_display_humidity(self) -> Union[float, None]:
        """
        Refresh the cached zone information and return IndoorHumidity.

        inputs:
            None
        returns:
            (float, None): indoor humidity in %RH, None if not supported.
        """
        return None  # not available

    def get_is_humidity_supported(self) -> bool:
        """Return humidity sensor status."""
        return self.get_display_humidity() is not None

    def is_heat_mode(self) -> int:
        """Return the heat mode."""
        return 0  # not applicable

    def is_cool_mode(self) -> int:
        """Return the cool mode."""
        return 0  # not applicable

    def is_dry_mode(self) -> int:
        """Return the dry mode."""
        return 0  # not applicable

    def is_auto_mode(self) -> int:
        """Return the auto mode."""
        return 0  # not applicable

    def is_eco_mode(self) -> int:
        """Return the auto mode."""
        return 0  # not applicable

    def is_fan_mode(self) -> int:
        """Return the fan mode."""
        return 0  # not applicable

    def is_off_mode(self) -> int:
        """Return the off mode."""
        return 1  # always off

    def is_heating(self) -> int:
        """Return 1 if actively heating, else 0."""
        return 0  # not applicable

    def is_cooling(self) -> int:
        """Return 1 if actively cooling, else 0."""
        return 0  # not applicable

    def is_drying(self) -> int:
        """Return 1 if drying relay is active, else 0."""
        return 0  # not applicable

    def is_auto(self) -> int:
        """Return 1 if auto relay is active, else 0."""
        return 0  # not applicable

    def is_eco(self) -> int:
        """Return 1 if eco relay is active, else 0."""
        return 0  # not applicable

    def is_fanning(self) -> int:
        """Return 1 if fan relay is active, else 0."""
        return 0  # not applicable

    def is_power_on(self) -> int:
        """Return 1 if power relay is active, else 0."""
        return 1  # always on

    def is_fan_on(self) -> int:
        """Return 1 if fan relay is active, else 0."""
        return 0  # not applicable

    def is_defrosting(self) -> int:
        """Return 1 if defrosting is active, else 0."""
        return 0  # not applicable

    def is_standby(self) -> int:
        """Return 1 if standby is active, else 0."""
        return 0  # not applicable

    def get_system_switch_position(self) -> int:
        """Return the thermostat mode.

        inputs:
            None
        returns:
            (int): thermostat mode, see tc.system_switch_position for details.
        """
        off_mode_value = self.system_switch_position[  # type: ignore[index]
            self.OFF_MODE
        ]
        # If the value is a list, return the first element
        if isinstance(off_mode_value, list):
            return off_mode_value[0]  # type: ignore[index]
        return off_mode_value

    def get_wifi_strength(self) -> float:  # noqa R0201
        """Return the wifi signal strength in dBm."""
        # Refresh zone metadata if needed (respects cache timeout)
        self.refresh_zone_info()

        raw_wifi = self.zone_metadata.get(blink_config.API_WIFI_STRENGTH)
        if isinstance(raw_wifi, (str, float, int)):
            return float(raw_wifi)
        else:
            return float(util.BOGUS_INT)

    def get_wifi_status(self) -> bool:  # noqa R0201
        """Return the wifi connection status."""
        raw_wifi = self.get_wifi_strength()
        if isinstance(raw_wifi, (float, int)):
            return raw_wifi >= util.MIN_WIFI_DBM
        else:
            return False

    def get_battery_voltage(self) -> float:  # noqa R0201
        """Return the battery voltage in volts."""
        # Refresh zone metadata if needed (respects cache timeout)
        self.refresh_zone_info()

        raw_voltage = self.zone_metadata.get(blink_config.API_BATTERY_VOLTAGE)
        if isinstance(raw_voltage, (str, float, int)):
            return float(raw_voltage) / 100.0
        else:
            return float(util.BOGUS_INT)

    def get_battery_status(self) -> bool:  # noqa R0201
        """Return the battery status."""
        # Refresh zone metadata if needed (respects cache timeout)
        self.refresh_zone_info()

        raw_status = self.zone_metadata.get(blink_config.API_BATTERY_STATUS)
        if isinstance(raw_status, str):
            raw_status = raw_status == "ok"
        return raw_status

    def refresh_zone_info(self, force_refresh=False) -> None:
        """
        Refresh zone metadata from blink server with spam mitigation.

        This method overrides the base class to properly refresh blink camera
        data while respecting cache intervals to prevent server spam detection.

        inputs:
            force_refresh(bool): if True, ignore expiration timer and refresh
        returns:
            None, updates self.zone_metadata with fresh data from server
        """
        now_time = time.time()
        # refresh if past expiration date or force_refresh option
        if force_refresh or (
            now_time >= (self.last_fetch_time + self.fetch_interval_sec)
        ):
            if self.verbose:
                util.log_msg(
                    f"Refreshing zone metadata for {self.zone_name} "
                    f"(last refresh: {now_time - self.last_fetch_time:.1f}s ago)",
                    mode=util.STDOUT_LOG,
                    func_name=1,
                )

            # Get fresh metadata from blink server
            try:
                self.zone_metadata = self.Thermostat.get_metadata(zone=self.zone_number)
                self.last_fetch_time = now_time
                if self.verbose:
                    util.log_msg(
                        f"Zone metadata refreshed successfully for {self.zone_name}",
                        mode=util.STDOUT_LOG,
                        func_name=1,
                    )
            except Exception as e:
                if self.verbose:
                    util.log_msg(
                        f"Failed to refresh zone metadata for {self.zone_name}: {e}",
                        mode=util.STDOUT_LOG,
                        func_name=1,
                    )
                # Don't update last_fetch_time on failure to retry sooner
                raise
        else:
            if self.verbose:
                time_until_refresh = (
                    self.last_fetch_time + self.fetch_interval_sec - now_time
                )
                # Only log if refresh time has changed significantly from last print
                rounded_refresh_time = round(time_until_refresh)
                if (self.last_printed_refresh_time is None or
                        abs(rounded_refresh_time -
                            self.last_printed_refresh_time) >= 1):
                    util.log_msg(
                        f"Using cached data for {self.zone_name} "
                        f"(refresh in {time_until_refresh:.1f}s)",
                        mode=util.STDOUT_LOG,
                        func_name=1,
                    )
                    self.last_printed_refresh_time = rounded_refresh_time


if __name__ == "__main__":
    # verify environment
    env.get_python_version()
    env.show_package_version(blinkpy)

    # get zone override
    api.uip = api.UserInputs(argv_list=None, thermostat_type=blink_config.ALIAS)
    zone_number = api.uip.get_user_inputs(api.uip.zone_name, api.input_flds.zone)

    _, Zone = tc.thermostat_basic_checkout(
        blink_config.ALIAS, zone_number, ThermostatClass, ThermostatZone
    )

    # this code is rem'd out because it will trigger blink server spam detectors.
    # tc.print_select_data_from_all_zones(
    #     blink_config.ALIAS,
    #     blink_config.get_available_zones(),
    #     ThermostatClass,
    #     ThermostatZone,
    #     display_wifi=True,
    #     display_battery=True,
    # )

    # measure thermostat response time
    if blink_config.check_response_time:
        MEASUREMENTS = 30
        meas_data = Zone.measure_thermostat_repeatability(
            MEASUREMENTS,
            func=Zone.pyhtcc.get_zones_info,
            measure_response_time=True,
        )
        ppp = pprint.PrettyPrinter(indent=4)
        ppp.pprint(meas_data)
