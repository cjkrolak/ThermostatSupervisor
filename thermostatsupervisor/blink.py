"""Blink Camera."""

# built-in imports
import asyncio
import os
import pprint
import sys
import time
import traceback
from typing import Union
from aiohttp import ClientSession

# third party imports

# local imports
from thermostatsupervisor import blink_config
from thermostatsupervisor import environment as env
from thermostatsupervisor import thermostat_api as api
from thermostatsupervisor import thermostat_common as tc
from thermostatsupervisor import utilities as util

# Blink library
BLINK_DEBUG = True  # debug uses local blink repo instead of pkg
if BLINK_DEBUG and not env.is_azure_environment():
    pkg = "blinkpy.blinkpy"
    mod_path = "..\\blinkpy"
    if env.is_interactive_environment():
        mod_path = "..\\" + mod_path
    blinkpy = env.dynamic_module_import("blinkpy.blinkpy", mod_path, pkg)
    auth = env.dynamic_module_import("blinkpy.auth", mod_path, pkg)
else:
    from blinkpy import auth  # noqa E402, from path / site packages
    from blinkpy import blinkpy  # noqa E402, from path / site packages

# Import blinkpy exceptions for proper error handling
try:
    from blinkpy.auth import LoginError, UnauthorizedError
    from aiohttp.client_exceptions import ClientConnectionError, ContentTypeError
except ImportError:
    # Fallback for older versions or missing exceptions
    class LoginError(Exception):
        """Login error fallback."""

        pass

    class UnauthorizedError(Exception):
        """Unauthorized error fallback."""

        pass

    class ClientConnectionError(Exception):
        """Client connection error fallback."""

        pass

    class ContentTypeError(Exception):
        """Content type error fallback."""

        pass


class ThermostatClass(blinkpy.Blink, tc.ThermostatCommon):
    """Blink Camera thermostat functions."""

    def __init__(self, zone, verbose=True):
        """
        Constructor, connect to thermostat.

        inputs:
            zone(str):  zone of thermostat.
            verbose(bool): debug flag.
        """
        # Blink server auth credentials from env vars
        self.BL_UNAME_KEY = "BLINK_USERNAME"
        self.BL_PASSWORD_KEY = "BLINK_PASSWORD"
        self.bl_uname = os.environ.get(
            self.BL_UNAME_KEY, "<" + self.BL_UNAME_KEY + api.KEY_MISSING_SUFFIX
        )
        self.bl_pwd = os.environ.get(
            self.BL_PASSWORD_KEY, "<" + self.BL_PASSWORD_KEY + api.KEY_MISSING_SUFFIX
        )
        self.auth_dict = {"username": self.bl_uname, "password": self.bl_pwd}
        self.BL_2FA_KEY = "BLINK_2FA"
        self.bl_2fa = os.environ.get(
            self.BL_2FA_KEY, "<" + self.BL_2FA_KEY + api.KEY_MISSING_SUFFIX
        )
        self.verbose = verbose
        self.zone_number = int(zone)

        # connect to Blink server and authenticate
        self.args = None
        self.thermostat_type = None
        self.blink = None
        if env.get_package_version(blinkpy) >= (0, 22, 0):
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

    def _handle_auth_retry(self, attempt, max_retries, retry_delay, error):
        """Handle authentication retry logic."""
        if attempt < max_retries - 1:
            if self.verbose:
                print(
                    f"Authentication attempt {attempt + 1} failed: {str(error)}. "
                    f"Retrying in {retry_delay} seconds..."
                )
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
        self.blink = blinkpy.Blink()
        if self.blink is None:
            raise RuntimeError(
                "ERROR: Blink object failed to instantiate "
                f"for zone {self.zone_number}"
            )

        self.blink.auth = auth.Auth(self.auth_dict, no_prompt=True)
        self.blink.start()

        # Send 2FA key with proper error checking
        auth_success = self.blink.auth.send_auth_key(self.blink, self.bl_2fa)
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
        error_msg = (
            f"ERROR: Unexpected error during Blink authentication for zone "
            f"{self.zone_number}: {str(error)}"
        )
        banner = "*" * len(error_msg)
        print(banner)
        print(error_msg)
        print(banner)
        sys.exit(1)

    async def _handle_async_auth_retry(self, attempt, max_retries, retry_delay, error):
        """Handle async authentication retry logic."""
        if attempt < max_retries - 1:
            if self.verbose:
                print(
                    f"Authentication attempt {attempt + 1} failed: "
                    f"{str(error)}. Retrying in {retry_delay} seconds..."
                )
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

    async def _attempt_async_authentication(self, session):
        """Attempt single async authentication process."""
        self.blink = blinkpy.Blink(session=session)
        if self.blink is None:
            raise RuntimeError(
                "ERROR: Blink object failed to instantiate "
                f"for zone {self.zone_number}"
            )

        self.blink.auth = auth.Auth(self.auth_dict, no_prompt=True, session=session)
        await self.blink.start()

        # Send 2FA key with proper error checking
        auth_success = await self.blink.auth.send_auth_key(self.blink, self.bl_2fa)
        if not auth_success:
            raise ValueError(
                "2FA verification failed. " "Please check your verification code."
            )

        # Check if setup_post_verify succeeds with retry
        setup_success = await self.blink.setup_post_verify()
        return setup_success

    async def async_auth_start(self):
        """
        blinkpy 0.22.0 introducted async start, this is the compatible
        auth_start function with improved error handling and retry logic.
        """
        async with ClientSession() as session:
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
        return (
            f"ERROR: Blink authorization failed for zone {self.zone_number} "
            f"({auth_type} mode). Your account may be locked or credentials "
            f"may be invalid. Error: {error_str}"
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
        if "2FA verification failed" in error_str:
            return (
                f"ERROR: Invalid 2FA verification code for zone "
                f"{self.zone_number} ({auth_type} mode). Please check that "
                f"you're using a fresh code from your authenticator app. "
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

        if not self.blink.cameras:
            if self.verbose:
                print("WARNING: No cameras found in blink.cameras")
                print("This may indicate authentication or setup issues")
            return

        for name, camera in self.blink.cameras.items():
            if self.verbose:
                print(name)
                print(camera.attributes)
            self.camera_metadata[name] = camera.attributes
        if self.verbose:
            print(f"Total cameras found: {len(self.blink.cameras)}")
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
            list(self.blink.cameras.keys()) if self.blink.cameras else []
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
            list(self.blink.cameras.keys()) if self.blink.cameras else []
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
        self.blink.auth.refresh_token()

    def _refresh_camera_data(self):
        """Refresh camera data after token refresh."""
        if hasattr(self.blink, "refresh"):
            self.blink.refresh()
        elif hasattr(self.blink, "setup_camera_list"):
            self.blink.setup_camera_list()

        # Update our local camera metadata cache
        self.get_cameras()

    def _refresh_camera_list_if_empty(self, zone_name):
        """Refresh camera list if it's empty."""
        if self.blink.cameras != {}:
            return

        self._log_camera_refresh_attempt(zone_name)

        if not hasattr(self.blink.auth, "refresh_token"):
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
        if env.get_package_version(blinkpy) >= (0, 22, 0):
            self._handle_empty_camera_list_async(zone_name)
        else:
            self._attempt_sync_token_refresh(zone_name)

    def _validate_camera_refresh_success(self, zone_name):
        """Validate that camera refresh was successful."""
        if self.blink.cameras == {}:
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
        for name, camera in self.blink.cameras.items():
            if name == zone_name:
                if self.verbose:
                    print(f"found camera {name}: {camera.attributes}")
                if parameter is None:
                    return camera.attributes
                else:
                    return camera.attributes[parameter]

        # Camera not found - provide helpful error
        available_cameras = list(self.blink.cameras.keys())
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
        self.system_switch_position[tc.ThermostatCommonZone.COOL_MODE] = "cool"
        self.system_switch_position[tc.ThermostatCommonZone.HEAT_MODE] = "heat"
        self.system_switch_position[tc.ThermostatCommonZone.OFF_MODE] = "off"
        self.system_switch_position[tc.ThermostatCommonZone.DRY_MODE] = "dry"
        self.system_switch_position[tc.ThermostatCommonZone.AUTO_MODE] = "auto"
        self.system_switch_position[tc.ThermostatCommonZone.FAN_MODE] = "vent"

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
        return self.system_switch_position[self.OFF_MODE]

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
