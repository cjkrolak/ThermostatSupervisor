"""KumoCloud integration"""

# built-in imports
import logging
import os
import pprint
import time
import traceback
from typing import TYPE_CHECKING, Union

# third party imports

# local imports
from src import environment as env
from src import kumocloud_config
from src import thermostat_api as api
from src import thermostat_common as tc
from src import utilities as util

# pykumo import
PYKUMO_DEBUG = False  # debug uses local pykumo repo instead of pkg
if PYKUMO_DEBUG and not env.is_azure_environment():
    mod_path = "..\\pykumo\\pykumo"
    if env.is_interactive_environment():
        mod_path = "..\\" + mod_path
    pykumo = env.dynamic_module_import("pykumo", mod_path)  # type: ignore
elif TYPE_CHECKING:
    # Allow type checking to proceed without runtime import
    from typing import Any
    pykumo: Any = None  # type: ignore
else:
    import pykumo  # noqa: E402


class SupervisorLogHandler(logging.Handler):
    """Custom logging handler to redirect pykumo logs to supervisor logging."""

    def emit(self, record):
        """
        Emit a log record through the supervisor's log_msg function.

        inputs:
            record(LogRecord): The logging record to emit
        """
        try:
            # Format the message
            msg = self.format(record)

            # Map logging levels to supervisor log modes
            level_mapping = {
                logging.DEBUG: util.DEBUG_LOG + util.DATA_LOG,
                logging.INFO: util.DATA_LOG,
                logging.WARNING: util.DATA_LOG,
                logging.ERROR: util.DATA_LOG + util.STDERR_LOG,
                logging.CRITICAL: util.DATA_LOG + util.STDERR_LOG,
            }

            # Get the appropriate log mode, default to DATA_LOG for unknown levels
            log_mode = level_mapping.get(record.levelno, util.DATA_LOG)

            # Log through supervisor's logging system
            util.log_msg(f"[pykumo] {msg}", mode=log_mode, file_name="kumo_log.txt")
        except Exception:
            # Fallback to avoid breaking logging completely
            self.handleError(record)


class ThermostatClass(
    pykumo.KumoCloudAccount, tc.ThermostatCommon  # type: ignore[name-defined]
):
    """KumoCloud thermostat functions."""

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
            self.KC_UNAME_KEY, "<" + self.KC_UNAME_KEY + api.KEY_MISSING_SUFFIX
        )
        self.kc_pwd = os.environ.get(
            self.KC_PASSWORD_KEY, "<" + self.KC_PASSWORD_KEY + api.KEY_MISSING_SUFFIX
        )

        # construct the superclass
        # call both parent class __init__
        self._need_fetch = True  # force data fetch
        self.args = [self.kc_uname, self.kc_pwd]
        # kumocloud account init sets the self._url
        pykumo.KumoCloudAccount.__init__(  # type: ignore[attr-defined]
            self, *self.args
        )
        tc.ThermostatCommon.__init__(self)

        # integrate pykumo logger with supervisor logging system
        self._setup_pykumo_logging()

        # set tstat type and debug flag
        self.thermostat_type = kumocloud_config.ALIAS
        self.verbose = verbose

        # configure zone info
        self.zone_number = int(zone)
        self.zone_name = kumocloud_config.metadata[self.zone_number]["zone_name"]
        self.device_id = self.get_target_zone_id(self.zone_name)
        self.serial_number = None  # will be populated when unit is queried.
        self.zone_info = {}

    def _setup_pykumo_logging(self):
        """
        Configure pykumo loggers to use supervisor logging system.

        This method sets up a custom handler that redirects pykumo log messages
        to the supervisor's log_msg function, ensuring all logging goes to the
        same destination.
        """
        # List of pykumo modules that have loggers
        pykumo_modules = [
            "pykumo.py_kumo_cloud_account",
            "pykumo.py_kumo",
            "pykumo.py_kumo_base",
            "pykumo.py_kumo_station",
        ]

        for module_name in pykumo_modules:
            try:
                # Get the logger for each pykumo module
                pykumo_logger = logging.getLogger(module_name)

                # Remove any existing handlers to avoid duplicate logging
                for handler in pykumo_logger.handlers[:]:
                    pykumo_logger.removeHandler(handler)

                # Add our custom handler
                supervisor_handler = SupervisorLogHandler()
                supervisor_handler.setLevel(logging.DEBUG)

                # Set a simple formatter
                formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
                supervisor_handler.setFormatter(formatter)

                pykumo_logger.addHandler(supervisor_handler)
                pykumo_logger.setLevel(logging.INFO)

                # Prevent propagation to avoid duplicate messages
                pykumo_logger.propagate = False

            except Exception as exc:
                # Log setup failure but don't break initialization
                util.log_msg(
                    f"Failed to setup logging for {module_name}: {exc}",
                    mode=util.DATA_LOG + util.STDERR_LOG,
                    func_name=1,
                )

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
            # Create a helpful error message with valid zone names
            valid_zone_names = [
                kumocloud_config.metadata[i]["zone_name"]
                for i in kumocloud_config.metadata
            ]
            error_msg = (
                f"zone_name='{self.zone_name}' not found in kumocloud metadata. "
                f"Valid zone names are: {valid_zone_names}. "
                f"Available zone indices are: {list(kumocloud_config.metadata.keys())}"
            )
            raise ValueError(error_msg) from None
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

    def _get_serial_number_list(self):
        """Get indoor unit serial numbers with retry logic."""
        try:
            serial_num_lst = list(self.get_indoor_units())  # will query unit
        except UnboundLocalError:  # patch for issue #205
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

        return serial_num_lst

    def _validate_and_populate_metadata(self, serial_num_lst):
        """Validate serial number list and populate metadata."""
        if not serial_num_lst:
            raise tc.AuthenticationError(
                "pykumo meta data is blank, probably"
                " due to an Authentication Error,"
                " check your credentials."
            )

        for idx, serial_number in enumerate(serial_num_lst):
            # populate meta data dict
            if self.verbose:
                print(f"zone index={idx}, serial_number={serial_number}")
            kumocloud_config.metadata[idx]["serial_number"] = serial_number

    def _get_zone_data(self, zone, serial_num_lst):
        """Get zone data based on zone parameter."""
        # raw_json list:
        # [0]: token, username, device fields
        # [1]: lastupdate date
        # [2]: zone meta data
        # [3]: device token
        if zone is None:
            # returned cached raw data for all zones
            return self.get_raw_json()[2]  # does not fetch results,
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
            return self.get_raw_json()[2]["children"][0]["zoneTable"][
                serial_num_lst[zone_index]
            ]

    def get_metadata(self, zone=None, trait=None, parameter=None, retry=False):
        """Get all thermostat meta data for zone from kumocloud.

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
            serial_num_lst = self._get_serial_number_list()
            self._validate_and_populate_metadata(serial_num_lst)
            raw_json = self._get_zone_data(zone, serial_num_lst)

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
                    UnboundLocalError,
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
        return int(self._is_mode(tc.ThermostatCommonZone.HEAT_MODE))

    def is_cool_mode(self) -> int:
        """
        Refresh the cached zone information and return the cool mode.

        inputs:
            None
        returns:
            (int): cool mode, 1=enabled, 0=disabled.
        """
        return int(self._is_mode(tc.ThermostatCommonZone.COOL_MODE))

    def is_dry_mode(self) -> int:
        """
        Refresh the cached zone information and return the dry mode.

        inputs:
            None
        returns:
            (int): dry mode, 1=enabled, 0=disabled.
        """
        return int(self._is_mode(tc.ThermostatCommonZone.DRY_MODE))

    def is_fan_mode(self) -> int:
        """
        Refresh the cached zone information and return the fan mode.

        inputs:
            None
        returns:
            (int): fan mode, 1=enabled, 0=disabled.
        """
        return int(self._is_mode(tc.ThermostatCommonZone.FAN_MODE))

    def is_auto_mode(self) -> int:
        """
        Refresh the cached zone information and return the auto mode.

        inputs:
            None
        returns:
            (int): auto mode, 1=enabled, 0=disabled.
        """
        return int(self._is_mode(tc.ThermostatCommonZone.AUTO_MODE))

    def is_eco_mode(self) -> int:
        """
        Refresh the cached zone information and return the eco mode.

        inputs:
            None
        returns:
            (int): eco mode, 1=enabled, 0=disabled.
        """
        eco_value = self.get_parameter(
            "energy_save", "reportedInitialSettings", default_val=0
        )
        return int(eco_value if eco_value is not None else 0)

    def is_off_mode(self) -> int:
        """
        Refresh the cached zone information and return the off mode.

        inputs:
            None
        returns:
            (int): off mode, 1=enabled, 0=disabled.
        """
        return int(self._is_mode(tc.ThermostatCommonZone.OFF_MODE))

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

    def is_fanning(self) -> int:
        """Return 1 if fan relay is active, else 0."""
        return int(self.is_fan_on() and self.is_power_on())

    def is_power_on(self) -> int:
        """Return 1 if power relay is active, else 0."""
        self.refresh_zone_info()
        power_value = self.get_parameter("power", "reportedCondition", default_val=0)
        return int(power_value if power_value is not None else 0)

    def is_fan_on(self) -> int:
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

    def is_defrosting(self) -> int:
        """Return 1 if defrosting is active, else 0."""
        self.refresh_zone_info()
        defrost_value = self.get_parameter(
            "defrost", "status_display", "reportedCondition"
        )
        return int(defrost_value if defrost_value is not None else 0)

    def is_standby(self) -> int:
        """Return 1 if standby is active, else 0."""
        self.refresh_zone_info()
        standby_value = self.get_parameter(
            "standby", "status_display", "reportedCondition", default_val=0
        )
        return int(standby_value if standby_value is not None else 0)

    def get_wifi_strength(self) -> float:  # noqa R0201
        """Return the wifi signal strength in dBm.

        rssi is sometimes reported in the reportedCondition dict,
        rssi is always reported in the rssi dict.
        rssi dict can be empty if unit is off.
        """
        self.refresh_zone_info()
        rssi_value = self.get_parameter("rssi", "rssi", None, util.BOGUS_INT)
        return float(rssi_value if rssi_value is not None else util.BOGUS_INT)

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

    def get_system_switch_position(self) -> Union[int, str]:  # used
        """
        Return the system switch position.

        inputs:
            None
        returns:
            (int or str) current mode for unit, should match value
                  in self.system_switch_position
        """
        self.refresh_zone_info()
        # first check if power is on
        # if power is off then operation_mode key may be missing.
        if not self.is_power_on():
            off_mode_value = self.system_switch_position[
                tc.ThermostatCommonZone.OFF_MODE
            ]
            # If the value is a list, return the first element
            if isinstance(off_mode_value, list):
                return off_mode_value[0]
            return off_mode_value
        else:
            op_mode = self.get_parameter("operation_mode", "reportedCondition")
            return op_mode if op_mode is not None else 0

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
        Refresh zone info from KumoCloud.

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
            except UnboundLocalError:  # patch for issue #205
                util.log_msg(
                    "WARNING: Kumocloud refresh failed due to timeout",
                    mode=util.BOTH_LOG,
                    func_name=1,
                )
            self.last_fetch_time = now_time
            # refresh device object
            self.zone_info = self.Thermostat.get_all_metadata(self.zone_number)


if __name__ == "__main__":
    # verify environment
    env.get_python_version()
    env.show_package_version(pykumo)

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
            func=Zone.pyhtcc.get_zones_info,
            measure_response_time=True,
        )
        ppp = pprint.PrettyPrinter(indent=4)
        ppp.pprint(meas_data)
