"""KumoCloud integration"""
# built-in imports
import os
import pprint
import time
import traceback
from typing import Union

# third party imports
import requests

# local imports
from thermostatsupervisor import environment as env
from thermostatsupervisor import kumocloud_config
from thermostatsupervisor import thermostat_api as api
from thermostatsupervisor import thermostat_common as tc
from thermostatsupervisor import utilities as util

# pykumo import - removed for v3 API implementation
# v3 API uses direct REST calls instead of pykumo library


class ThermostatClass(tc.ThermostatCommon):
    """KumoCloud thermostat functions using v3 API."""

    def __init__(self, zone, verbose=True):
        """
        Constructor, connect to thermostat.

        inputs:
            zone(str):  zone of thermostat.
            verbose(bool): debug flag.
        """
        # Kumocloud server auth credentials from env vars
        self.KC_UNAME_KEY = "KUMO_USERNAME"
        self.KC_PASSWORD_KEY = "KUMO_PASSWORD"
        self.kc_uname = os.environ.get(
            self.KC_UNAME_KEY, "<" + self.KC_UNAME_KEY + "_KEY_MISSING>"
        )
        self.kc_pwd = os.environ.get(
            self.KC_PASSWORD_KEY, "<" + self.KC_PASSWORD_KEY + "_KEY_MISSING>"
        )

        # construct the superclass
        tc.ThermostatCommon.__init__(self)

        # v3 API configuration
        self.base_url = "https://app-prod.kumocloud.com"
        self.app_version = "3.0.3"
        self.access_token = None
        self.refresh_token = None
        self._need_fetch = True  # force data fetch

        # cached data storage
        self._sites_data = None
        self._zones_data = None
        self._device_data = {}
        self._last_fetch_time = 0
        self.fetch_interval_sec = 60

        # set tstat type and debug flag
        self.thermostat_type = kumocloud_config.ALIAS
        self.verbose = verbose

        # configure zone info
        self.zone_number = int(zone)
        self.zone_name = kumocloud_config.metadata[self.zone_number]["zone_name"]
        self.device_id = self.get_target_zone_id(self.zone_name)
        self.serial_number = None  # will be populated when unit is queried.
        self.zone_info = {}

        # authenticate on initialization
        self._authenticate()

    def _get_base_headers(self):
        """Get base headers required for v3 API."""
        return {
            "Accept": "application/json text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US, en",
            "x-app-version": self.app_version,
            "Content-Type": "application/json"
        }

    def _authenticate(self):
        """Authenticate with KumoCloud v3 API and store tokens."""
        login_url = f"{self.base_url}/v3/login"
        login_data = {
            "username": self.kc_uname,
            "password": self.kc_pwd,
            "appVersion": self.app_version
        }

        try:
            response = requests.post(
                login_url,
                json=login_data,
                headers=self._get_base_headers(),
                timeout=util.HTTP_TIMEOUT
            )
            response.raise_for_status()

            auth_data = response.json()
            self.access_token = auth_data["token"]["access"]
            self.refresh_token = auth_data["token"]["refresh"]

            if self.verbose:
                util.log_msg(
                    "Successfully authenticated with KumoCloud v3 API",
                    mode=util.DEBUG_LOG + util.STDOUT_LOG,
                    func_name=1,
                )

        except requests.exceptions.RequestException as e:
            raise tc.AuthenticationError(
                f"Failed to authenticate with KumoCloud v3 API: {e}"
            ) from e
        except KeyError as e:
            raise tc.AuthenticationError(
                f"Invalid response format from KumoCloud v3 API: {e}"
            ) from e

    def _refresh_access_token(self):
        """Refresh the access token using the refresh token."""
        refresh_url = f"{self.base_url}/v3/refresh"
        headers = self._get_base_headers()
        headers["Authorization"] = f"Bearer {self.refresh_token}"

        refresh_data = {"refresh": self.refresh_token}

        try:
            response = requests.post(
                refresh_url,
                json=refresh_data,
                headers=headers,
                timeout=util.HTTP_TIMEOUT
            )
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data["access"]
            self.refresh_token = token_data["refresh"]

            if self.verbose:
                util.log_msg(
                    "Successfully refreshed KumoCloud v3 API tokens",
                    mode=util.DEBUG_LOG + util.STDOUT_LOG,
                    func_name=1,
                )

        except requests.exceptions.RequestException as e:
            # If refresh fails, try full re-authentication
            if self.verbose:
                util.log_msg(
                    f"Token refresh failed, attempting re-authentication: {e}",
                    mode=util.DEBUG_LOG + util.STDOUT_LOG,
                    func_name=1,
                )
            self._authenticate()

    def _get_auth_headers(self):
        """Get headers with authentication token."""
        headers = self._get_base_headers()
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def _make_authenticated_request(self, url, method="GET", data=None,
                                    retry_auth=True):
        """Make authenticated request to v3 API with automatic token refresh."""
        headers = self._get_auth_headers()

        try:
            if method.upper() == "POST":
                response = requests.post(
                    url, json=data, headers=headers, timeout=util.HTTP_TIMEOUT
                )
            else:
                response = requests.get(
                    url, headers=headers, timeout=util.HTTP_TIMEOUT
                )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401 and retry_auth:
                # Token expired, try to refresh and retry
                self._refresh_access_token()
                return self._make_authenticated_request(
                    url, method, data, retry_auth=False
                )
            else:
                raise

    def _fetch_if_needed(self):
        """Fetch data from v3 API if needed (cache expiration)."""
        current_time = time.time()
        if (self._need_fetch or
                current_time >= (self._last_fetch_time +
                                 self.fetch_interval_sec)):
            self._fetch_sites_data()
            self._need_fetch = False
            self._last_fetch_time = current_time

    def _fetch_sites_data(self):
        """Fetch sites data from v3 API."""
        sites_url = f"{self.base_url}/v3/sites/"
        self._sites_data = self._make_authenticated_request(sites_url)

        if self._sites_data and len(self._sites_data) > 0:
            # Get the first site (most users have only one)
            site_id = self._sites_data[0]["id"]
            self._fetch_zones_data(site_id)

    def _fetch_zones_data(self, site_id):
        """Fetch zones data for a specific site."""
        zones_url = f"{self.base_url}/v3/sites/{site_id}/zones"
        self._zones_data = self._make_authenticated_request(zones_url)

        # Fetch device data for each zone
        if self._zones_data:
            for zone in self._zones_data:
                if "adapter" in zone and "deviceSerial" in zone["adapter"]:
                    device_serial = zone["adapter"]["deviceSerial"]
                    self._fetch_device_data(device_serial)

    def _fetch_device_data(self, device_serial):
        """Fetch device data for a specific device serial."""
        device_status_url = f"{self.base_url}/v3/devices/{device_serial}/status"
        device_settings_url = (
            f"{self.base_url}/v3/devices/{device_serial}/initial-settings"
        )

        try:
            status_data = self._make_authenticated_request(device_status_url)
            settings_data = self._make_authenticated_request(device_settings_url)

            # Combine status and settings data
            self._device_data[device_serial] = {
                "status": status_data,
                "settings": settings_data,
                "serial": device_serial
            }
        except Exception as e:
            util.log_msg(
                f"Failed to fetch device data for {device_serial}: {e}",
                mode=util.BOTH_LOG,
                func_name=1,
            )

    def get_indoor_units(self):
        """Get list of indoor unit serial numbers (compatibility method)."""
        self._fetch_if_needed()
        serial_numbers = []

        if self._zones_data:
            for zone in self._zones_data:
                if "adapter" in zone and "deviceSerial" in zone["adapter"]:
                    serial_numbers.append(zone["adapter"]["deviceSerial"])

        return serial_numbers

    def get_raw_json(self):
        """Get raw JSON data compatible with old API (compatibility method)."""
        self._fetch_if_needed()

        # Create a structure similar to the old API format
        # [0]: token, username, device fields (not used in new implementation)
        # [1]: last update date
        # [2]: zone meta data
        # [3]: device token (not used in new implementation)

        zone_table = {}
        if self._zones_data and self._device_data:
            for zone in self._zones_data:
                if "adapter" in zone and "deviceSerial" in zone["adapter"]:
                    device_serial = zone["adapter"]["deviceSerial"]
                    if device_serial in self._device_data:
                        # Create zone entry compatible with old format
                        device_data = self._device_data[device_serial]
                        zone_entry = self._convert_v3_to_legacy_format(
                            device_data, zone
                        )
                        zone_table[device_serial] = zone_entry

        return [
            {},  # token/username data (not used)
            time.time(),  # last update timestamp
            {"children": [{"zoneTable": zone_table}]},  # zone metadata
            {}  # device token (not used)
        ]

    def _convert_v3_to_legacy_format(self, device_data, zone_data):
        """Convert v3 API data format to legacy format for compatibility."""
        legacy_format = {
            "label": zone_data.get("label", "Unknown Zone"),
            "reportedCondition": {},
            "reportedInitialSettings": {},
            "rssi": {}
        }

        if "status" in device_data:
            status = device_data["status"]
            # Map v3 status fields to legacy format
            if "roomTemp" in status:
                legacy_format["reportedCondition"]["room_temp"] = status["roomTemp"]
            if "spHeat" in status:
                legacy_format["reportedCondition"]["sp_heat"] = status["spHeat"]
            if "spCool" in status:
                legacy_format["reportedCondition"]["sp_cool"] = status["spCool"]
            if "power" in status:
                legacy_format["reportedCondition"]["power"] = status["power"]
            if "mode" in status:
                legacy_format["reportedCondition"]["operation_mode"] = (
                    status["mode"]
                )
            if "fanSpeed" in status:
                legacy_format["reportedCondition"]["fan_speed"] = (
                    status["fanSpeed"]
                )
            if "defrost" in status:
                legacy_format["reportedCondition"]["defrost"] = {
                    "status_display": status["defrost"]
                }
            if "standby" in status:
                legacy_format["reportedCondition"]["standby"] = {
                    "status_display": status["standby"]
                }
            if "wifiSignal" in status:
                legacy_format["rssi"]["rssi"] = status["wifiSignal"]

        if "settings" in device_data:
            settings = device_data["settings"]
            # Map v3 settings fields to legacy format
            if "energySave" in settings:
                legacy_format["reportedInitialSettings"]["energy_save"] = (
                    settings["energySave"]
                )

        return legacy_format

    def get_target_zone_id(self, zone=0):
        """
        Return the target zone ID.

        inputs:
            zone(int):  zone number.
        returns:
            (int): device_id
        """
        return zone

    def get_zone_index_from_name(self):
        """
        Return zone index for specified zone_name.

        inputs:
            None
        returns:
            (int): zone index.
        """
        if self.verbose:
            print(f"getting index for zone_name={self.zone_name}...")
            print(f"metadata dict={kumocloud_config.metadata}")
        try:
            zone_index = [
                i
                for i in kumocloud_config.metadata
                if kumocloud_config.metadata[i]["zone_name"] == self.zone_name
            ][0]
        except IndexError:
            print(
                f"ERROR: zone_name={self.zone_name} not present in meta data"
                f" dict, valid values are {kumocloud_config.metadata.keys()}"
            )
            raise
        return zone_index

    def get_all_metadata(self, zone=None, retry=False):
        """Get all thermostat meta data for zone from kumocloud.

        inputs:
            zone(int): specified zone, if None will print all zones.
            retry(bool): if True will retry with extended retry mechanism.
        returns:
            (dict): JSON dict
        """
        return self.get_metadata(zone, retry=retry)

    def get_metadata(self, zone=None, trait=None, parameter=None, retry=False):
        """Get all thermostat meta data for zone from kumocloud v3 API.

        inputs:
            zone(int): specified zone, if None will print all zones.
            trait(str): trait or parent key, if None will assume a non-nested
                        dict
            parameter(str): target parameter, if None will return all.
            retry(bool): if True will retry with extended retry mechanism
        returns:
            (int, float, str, dict): depends on parameter
        """
        del trait  # not needed on Kumocloud

        def _get_metadata_internal():
            try:
                serial_num_lst = list(self.get_indoor_units())  # will query unit
            except Exception:  # catch any exception during fetch
                util.log_msg(
                    "WARNING: Kumocloud refresh failed due to timeout",
                    mode=util.BOTH_LOG,
                    func_name=1,
                )
                time.sleep(30)
                serial_num_lst = list(self.get_indoor_units())  # retry
            if self.verbose:
                util.log_msg(
                    f"indoor unit serial numbers: {str(serial_num_lst)}",
                    mode=util.DEBUG_LOG + util.STDOUT_LOG,
                    func_name=1,
                )

            # validate serial number list
            if not serial_num_lst:
                raise tc.AuthenticationError(
                    "KumoCloud v3 API meta data is blank, probably"
                    " due to an Authentication Error,"
                    " check your credentials."
                )

            for idx, serial_number in enumerate(serial_num_lst):
                # populate meta data dict
                if self.verbose:
                    print(f"zone index={idx}, serial_number={serial_number}")
                kumocloud_config.metadata[idx]["serial_number"] = serial_number

            # Get data using the compatibility method
            raw_json_data = self.get_raw_json()

            if zone is None:
                # returned cached raw data for all zones
                raw_json = raw_json_data[2]  # zone meta data
            else:
                # if zone name input, find zone index
                if not isinstance(zone, int):
                    self.zone_name = zone
                    zone_index = self.get_zone_index_from_name()
                else:
                    zone_index = zone
                # return cached raw data for specified zone, will be a dict
                try:
                    self.serial_number = serial_num_lst[zone_index]
                except IndexError as exc:
                    raise IndexError(
                        f"ERROR: Invalid Zone, index ({zone_index}) does "
                        "not exist in serial number list "
                        f"({serial_num_lst})"
                    ) from exc
                raw_json = raw_json_data[2]["children"][0]["zoneTable"][
                    serial_num_lst[zone_index]
                ]

            if parameter is None:
                return raw_json
            else:
                return raw_json[parameter]

        if retry:
            # Use standardized extended retry mechanism
            return util.execute_with_extended_retries(
                func=_get_metadata_internal,
                thermostat_type=getattr(self, "thermostat_type", "KumoCloud"),
                zone_name=str(getattr(self, "zone_name", str(zone))),
                number_of_retries=5,
                initial_retry_delay_sec=60,
                exception_types=(
                    Exception,  # Catch broader exceptions for v3 API
                    tc.AuthenticationError,
                    IndexError,
                    KeyError,
                    ConnectionError,
                    TimeoutError,
                ),
                email_notification=None,  # KumoCloud doesn't import email_notification
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
    KumoCloud single zone from kumocloud.

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

        # server data cache expiration parameters
        self.fetch_interval_sec = 60  # age of server data before refresh
        self.last_fetch_time = time.time() - 2 * self.fetch_interval_sec

        # switch config for this thermostat
        self.system_switch_position[
            tc.ThermostatCommonZone.HEAT_MODE
        ] = 1  # "Heat" 0 0001
        self.system_switch_position[
            tc.ThermostatCommonZone.OFF_MODE
        ] = 16  # "Off"  1 0000
        self.system_switch_position[
            tc.ThermostatCommonZone.FAN_MODE
        ] = 7  # "Fan"   0 0111
        self.system_switch_position[
            tc.ThermostatCommonZone.DRY_MODE
        ] = 2  # dry     0 0010
        self.system_switch_position[
            tc.ThermostatCommonZone.COOL_MODE
        ] = 3  # cool   0 0011
        self.system_switch_position[
            tc.ThermostatCommonZone.AUTO_MODE
        ] = 33  # auto   0 0101

        # zone info
        self.verbose = verbose
        self.thermostat_type = kumocloud_config.ALIAS
        self.device_id = Thermostat_obj.device_id
        self.Thermostat = Thermostat_obj
        self.zone_info = Thermostat_obj.get_all_metadata(Thermostat_obj.zone_number)
        self.zone_number = Thermostat_obj.zone_number
        self.zone_name = self.get_zone_name()  # get real zone name from device

    def get_parameter(
        self, key, parent_key=None, grandparent_key=None, default_val=None
    ):
        """
        Get parameter from zone dictionary.

        inputs:
            key(str): target dict key
            parent_key(str): first level dict key
            grandparent_key(str): second level dict key
            default_val(str, int, float): default value on key errors
        """
        return_val = default_val
        try:
            if grandparent_key is not None:
                grandparent_dict = self.zone_info[grandparent_key]
                parent_dict = grandparent_dict[parent_key]
                return_val = parent_dict[key]
            elif parent_key is not None:
                parent_dict = self.zone_info[parent_key]
                return_val = parent_dict[key]
            else:
                return_val = self.zone_info[key]
        except (KeyError, TypeError):
            if default_val is None:
                # if no default val, then display detailed key error
                util.log_msg(traceback.format_exc(), mode=util.BOTH_LOG, func_name=1)
                util.log_msg(
                    f"target key={key}, raw zone_info dict:",
                    mode=util.BOTH_LOG,
                    func_name=1,
                )
                raise
        return return_val

    def get_zone_name(self):
        """
        Return the name associated with the zone number.

        inputs:
            None
        returns:
            (str) zone name
        """
        self.refresh_zone_info()
        zone_name = self.get_parameter("label")
        # update metadata dict.
        kumocloud_config.metadata[self.zone_number]["zone_name"] = zone_name
        return zone_name

    def get_display_temp(self) -> float:  # used
        """
        Refresh the cached zone information and return Indoor Temp in °F.

        inputs:
            None
        returns:
            (float): indoor temp in °F.
        """
        self.refresh_zone_info()
        return util.c_to_f(
            self.get_parameter(
                "room_temp", "reportedCondition", default_val=util.BOGUS_INT
            )
        )

    def get_display_humidity(self) -> Union[float, None]:
        """
        Refresh the cached zone information and return IndoorHumidity.

        inputs:
            None
        returns:
            (float, None): indoor humidity in %RH, None if not supported.
        """
        if not self.get_is_humidity_supported():
            return None
        else:
            # untested, don't have humidity support
            # zone refreshed during if clause above
            return util.c_to_f(
                self.get_parameter(
                    "humidity", "reportedCondition", default_val=util.BOGUS_INT
                )
            )

    def get_is_humidity_supported(self) -> bool:  # used
        """
        Refresh the cached zone information and return the
          True if humidity sensor data is trustworthy.

        inputs:
            None
        returns:
            (booL): True if is in humidity sensor is available and not faulted.
        """
        self.refresh_zone_info()
        return bool(self.get_parameter("humidistat", "inputs", "acoilSettings"))

    def is_heat_mode(self) -> int:
        """
        Refresh the cached zone information and return the heat mode.

        inputs:
            None
        returns:
            (int) heat mode, 1=enabled, 0=disabled.
        """
        return int(
            self.get_system_switch_position()
            == self.system_switch_position[tc.ThermostatCommonZone.HEAT_MODE]
        )

    def is_cool_mode(self) -> int:
        """
        Refresh the cached zone information and return the cool mode.

        inputs:
            None
        returns:
            (int): cool mode, 1=enabled, 0=disabled.
        """
        return int(
            self.get_system_switch_position()
            == self.system_switch_position[tc.ThermostatCommonZone.COOL_MODE]
        )

    def is_dry_mode(self) -> int:
        """
        Refresh the cached zone information and return the dry mode.

        inputs:
            None
        returns:
            (int): dry mode, 1=enabled, 0=disabled.
        """
        return int(
            self.get_system_switch_position()
            == self.system_switch_position[tc.ThermostatCommonZone.DRY_MODE]
        )

    def is_fan_mode(self) -> int:
        """
        Refresh the cached zone information and return the fan mode.

        inputs:
            None
        returns:
            (int): fan mode, 1=enabled, 0=disabled.
        """
        return int(
            self.get_system_switch_position()
            == self.system_switch_position[tc.ThermostatCommonZone.FAN_MODE]
        )

    def is_auto_mode(self) -> int:
        """
        Refresh the cached zone information and return the auto mode.

        inputs:
            None
        returns:
            (int): auto mode, 1=enabled, 0=disabled.
        """
        return int(
            self.get_system_switch_position()
            == self.system_switch_position[tc.ThermostatCommonZone.AUTO_MODE]
        )

    def is_eco_mode(self) -> int:
        """
        Refresh the cached zone information and return the eco mode.

        inputs:
            None
        returns:
            (int): eco mode, 1=enabled, 0=disabled.
        """
        return int(self.get_parameter("energy_save", "reportedInitialSettings"))

    def is_off_mode(self) -> int:
        """
        Refresh the cached zone information and return the off mode.

        inputs:
            None
        returns:
            (int): off mode, 1=enabled, 0=disabled.
        """
        return int(
            self.get_system_switch_position()
            == self.system_switch_position[tc.ThermostatCommonZone.OFF_MODE]
        )

    def is_heating(self):
        """Return 1 if heating relay is active, else 0."""
        return int(
            self.is_heat_mode()
            and self.is_power_on()
            and self.get_heat_setpoint_raw() > self.get_display_temp()
        )

    def is_cooling(self):
        """Return 1 if cooling relay is active, else 0."""
        return int(
            self.is_cool_mode()
            and self.is_power_on()
            and self.get_cool_setpoint_raw() < self.get_display_temp()
        )

    def is_drying(self):
        """Return 1 if drying relay is active, else 0."""
        return int(
            self.is_dry_mode()
            and self.is_power_on()
            and self.get_cool_setpoint_raw() < self.get_display_temp()
        )

    def is_auto(self):
        """Return 1 if auto relay is active, else 0."""
        return int(
            self.is_auto_mode()
            and self.is_power_on()
            and (
                self.get_cool_setpoint_raw() < self.get_display_temp()
                or self.get_heat_setpoint_raw() > self.get_display_temp()
            )
        )

    def is_eco(self):
        """Return 1 if eco relay is active, else 0."""
        return int(
            self.is_eco_mode()
            and self.is_power_on()
            and (
                self.get_cool_setpoint_raw() < self.get_display_temp()
                or self.get_heat_setpoint_raw() > self.get_display_temp()
            )
        )

    def is_fanning(self):
        """Return 1 if fan relay is active, else 0."""
        return int(self.is_fan_on() and self.is_power_on())

    def is_power_on(self):
        """Return 1 if power relay is active, else 0."""
        self.refresh_zone_info()
        return self.get_parameter("power", "reportedCondition", default_val=0)

    def is_fan_on(self):
        """Return 1 if fan relay is active, else 0."""
        if self.is_power_on():
            fan_speed = self.get_parameter("fan_speed", "reportedCondition")
            if fan_speed is None:
                return 0  # no fan_speed key, return 0
            else:
                return int(
                    fan_speed > 0
                    or self.get_parameter("fan_speed_text", "more", "reportedCondition")
                    != "off"
                )
        else:
            return 0

    def is_defrosting(self):
        """Return 1 if defrosting is active, else 0."""
        self.refresh_zone_info()
        return int(self.get_parameter("defrost", "status_display", "reportedCondition"))

    def is_standby(self):
        """Return 1 if standby is active, else 0."""
        self.refresh_zone_info()
        return int(self.get_parameter("standby", "status_display", "reportedCondition"))

    def get_wifi_strength(self) -> float:  # noqa R0201
        """Return the wifi signal strength in dBm.

        rssi is sometimes reported in the reportedCondition dict,
        rssi is always reported in the rssi dict.
        rssi dict can be empty if unit is off.
        """
        self.refresh_zone_info()
        return float(self.get_parameter("rssi", "rssi", None, util.BOGUS_INT))

    def get_wifi_status(self) -> bool:  # noqa R0201
        """Return the wifi connection status."""
        raw_wifi = self.get_wifi_strength()
        if isinstance(raw_wifi, (float, int)):
            return raw_wifi >= util.MIN_WIFI_DBM
        else:
            return False

    def get_battery_voltage(self) -> float:  # noqa R0201
        """Return the battery voltage in volts.

        This tstat is on line power so any valid response
        from tstat returns line power value.
        """
        return 120.0 if self.get_wifi_status() else 0.0

    def get_battery_status(self) -> bool:  # noqa R0201
        """Return the battery status.

        For this tstat any positive number returns True.
        """
        return self.get_battery_voltage() > 0.0

    def get_heat_setpoint_raw(self) -> float:  # used
        """
        Refresh the cached zone information and return the heat setpoint.

        inputs:
            None
        returns:
            (float): heating set point in °F.
        """
        self.refresh_zone_info()
        # if power is off then sp_heat may be missing
        return util.c_to_f(
            self.get_parameter("sp_heat", "reportedCondition", default_val=-1)
        )

    def get_heat_setpoint(self) -> str:
        """Return heat setpoint with units as a string."""
        return util.temp_value_with_units(self.get_heat_setpoint_raw())

    def get_schedule_heat_sp(self) -> float:  # used
        """
        Return the schedule heat setpoint.

        inputs:
            None
        returns:
            (float): scheduled heating set point in °F.
        """
        return float(kumocloud_config.MAX_HEAT_SETPOINT)  # max heat set point allowed

    def get_schedule_cool_sp(self) -> float:
        """
        Return the schedule cool setpoint.

        inputs:
            None
        returns:
            (float): scheduled cooling set point in °F.
        """
        return kumocloud_config.MIN_COOL_SETPOINT  # min cool set point allowed

    def get_cool_setpoint_raw(self) -> float:
        """
        Return the cool setpoint.

        inputs:
            None
        returns:
            (float): cooling set point in °F.
        """
        self.refresh_zone_info()
        # if power is off then sp_heat may be missing
        return util.c_to_f(
            self.get_parameter("sp_cool", "reportedCondition", default_val=-1)
        )

    def get_cool_setpoint(self) -> str:
        """Return cool setpoint with units as a string."""
        return util.temp_value_with_units(self.get_cool_setpoint_raw())

    def get_is_invacation_hold_mode(self) -> bool:  # used
        """
        Return the
          'IsInVacationHoldMode' setting.

        inputs:
            None
        returns:
            (booL): True if is in vacation hold mode.
        """
        return False  # no schedule, hold not implemented

    def get_vacation_hold(self) -> bool:
        """
        Return the
        VacationHold setting.

        inputs:
            None
        returns:
            (bool): True if vacation hold is set.
        """
        return False  # no schedule, hold not implemented

    def get_system_switch_position(self) -> int:  # used
        """
        Return the system switch position.

        inputs:
            None
        returns:
            (int) current mode for unit, should match value
                  in self.system_switch_position
        """
        self.refresh_zone_info()
        # first check if power is on
        # if power is off then operation_mode key may be missing.
        if not self.is_power_on():
            return self.system_switch_position[tc.ThermostatCommonZone.OFF_MODE]
        else:
            return self.get_parameter("operation_mode", "reportedCondition")

    def set_heat_setpoint(self, temp: int) -> None:
        """
        Set a new heat setpoint.

        This will also attempt to turn the thermostat to 'Heat'
        inputs:
            temp(int): desired temperature in F
        returns:
            None
        """
        # self.device_id.set_heat_setpoint(self._f_to_c(temp))
        # TODO needs implementation
        del temp
        util.log_msg(
            "WARNING: this method not implemented yet for this thermostat type",
            mode=util.BOTH_LOG,
            func_name=1,
        )

    def set_cool_setpoint(self, temp: int) -> None:
        """
        Set a new cool setpoint.

        This will also attempt to turn the thermostat to 'Cool'
        inputs:
            temp(int): desired temperature in °F.
        returns:
            None
        """
        # self.device_id.set_cool_setpoint(self._f_to_c(temp))
        # TODO needs implementation
        del temp
        util.log_msg(
            "WARNING: this method not implemented yet for this thermostat type",
            mode=util.BOTH_LOG,
            func_name=1,
        )

    def refresh_zone_info(self, force_refresh=False):
        """
        Refresh zone info from KumoCloud v3 API.

        inputs:
            force_refresh(bool): if True, ignore expiration timer.
        returns:
            None, zone_data is refreshed.
        """
        now_time = time.time()
        # refresh if past expiration date or force_refresh option
        if force_refresh or (
            now_time >= (self.last_fetch_time + self.fetch_interval_sec)
        ):
            self.Thermostat._need_fetch = True  # pylint: disable=protected-access
            try:
                self.Thermostat._fetch_if_needed()  # pylint: disable=protected-access
            except Exception:  # catch any exception from v3 API
                util.log_msg(
                    "WARNING: Kumocloud v3 API refresh failed",
                    mode=util.BOTH_LOG,
                    func_name=1,
                )
            self.last_fetch_time = now_time
            # refresh device object
            self.zone_info = self.Thermostat.get_all_metadata(self.zone_number)


if __name__ == "__main__":
    # verify environment
    env.get_python_version()
    # Note: pykumo version check removed since we now use v3 API directly

    # get zone override
    api.uip = api.UserInputs(argv_list=None, thermostat_type=kumocloud_config.ALIAS)
    zone_number = api.uip.get_user_inputs(api.uip.zone_name, api.input_flds.zone)

    _, Zone = tc.thermostat_basic_checkout(
        kumocloud_config.ALIAS, zone_number, ThermostatClass, ThermostatZone
    )

    tc.print_select_data_from_all_zones(
        kumocloud_config.ALIAS,
        kumocloud_config.get_available_zones(),
        ThermostatClass,
        ThermostatZone,
        display_wifi=True,
        display_battery=True,
    )

    # measure thermostat response time
    if kumocloud_config.check_response_time:
        MEASUREMENTS = 30
        meas_data = Zone.measure_thermostat_repeatability(
            MEASUREMENTS,
            func=Zone.Thermostat.get_all_metadata,  # Updated to use correct method
            measure_response_time=True,
        )
        ppp = pprint.PrettyPrinter(indent=4)
        ppp.pprint(meas_data)
