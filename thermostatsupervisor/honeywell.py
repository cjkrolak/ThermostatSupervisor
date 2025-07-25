"""
Connection to Honeywell thermoststat via TotalConnectComfort web site
using pyhtcc library.

https://pypi.org/project/pyhtcc/
"""
# built-in imports
import http.client
import logging
import os
import pprint
import time
from typing import Union

# third-party imports
import urllib3.exceptions

# local imports
from thermostatsupervisor import email_notification
from thermostatsupervisor import environment as env
from thermostatsupervisor import honeywell_config
from thermostatsupervisor import thermostat_api as api
from thermostatsupervisor import thermostat_common as tc
from thermostatsupervisor import utilities as util

# honeywell import
HONEYWELL_DEBUG = False  # debug uses local pyhtcc repo instead of pkg
if HONEYWELL_DEBUG and not env.is_azure_environment():
    mod_path = "..\\pyhtcc\\pyhtcc"
    if env.is_interactive_environment():
        mod_path = "..\\" + mod_path
    pyhtcc = env.dynamic_module_import("pyhtcc", mod_path)
else:
    import pyhtcc  # noqa E402, from path / site packages


class SupervisorLogHandler(logging.Handler):
    """Custom logging handler to redirect pyhtcc logs to supervisor logging."""

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
            util.log_msg(
                f"[pyhtcc] {msg}", mode=log_mode, file_name="honeywell_log.txt"
            )
        except Exception:
            # Fallback to avoid breaking logging completely
            self.handleError(record)


class ThermostatClass(pyhtcc.PyHTCC, tc.ThermostatCommon):
    """Extend the PyHTCC class with additional methods."""

    def __init__(self, zone, verbose=True):
        """
        inputs:
            zone(str):  zone number.
            verbose(bool): debug flag.
        """
        # TCC server auth credentials from env vars
        self.TCC_UNAME_KEY = "TCC_USERNAME"
        self.TCC_PASSWORD_KEY = "TCC_PASSWORD"
        self.tcc_uname = os.environ.get(
            self.TCC_UNAME_KEY, "<" + self.TCC_UNAME_KEY + api.KEY_MISSING_SUFFIX
        )
        self.tcc_pwd = os.environ.get(
            self.TCC_PASSWORD_KEY, "<" + self.TCC_PASSWORD_KEY + api.KEY_MISSING_SUFFIX
        )

        # construct the superclass
        # call both parent class __init__
        self.args = [self.tcc_uname, self.tcc_pwd]
        pyhtcc.PyHTCC.__init__(self, *self.args)
        tc.ThermostatCommon.__init__(self)

        # integrate pyhtcc logger with supervisor logging system
        self._setup_pyhtcc_logging()

        # set tstat type and debug flag
        self.thermostat_type = honeywell_config.ALIAS
        self.verbose = verbose

        # configure zone info
        self.zone_name = int(zone)
        self.device_id = self.get_target_zone_id(self.zone_name)

    def close(self):
        """Explicitly close the session created in pyhtcc."""
        if hasattr(self, "session") and self.session is not None:
            self.session.close()
            self.session = None

    def __del__(self):
        """Clean-up session created in pyhtcc (fallback)."""
        try:
            self.close()
        except (AttributeError, TypeError):
            # Handle cases where session doesn't exist or other cleanup issues
            pass

    def _setup_pyhtcc_logging(self):
        """
        Configure pyhtcc logger to use supervisor logging system.

        This method sets up a custom handler that redirects pyhtcc log messages
        to the supervisor's log_msg function, ensuring all logging goes to the
        same destination.
        """
        # Get the pyhtcc logger
        pyhtcc_logger = pyhtcc.logger

        # Remove any existing handlers to avoid duplicate logging
        for handler in pyhtcc_logger.handlers[:]:
            pyhtcc_logger.removeHandler(handler)

        # Add our custom handler
        supervisor_handler = SupervisorLogHandler()
        supervisor_handler.setLevel(logging.DEBUG)

        # Set a simple formatter
        formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
        supervisor_handler.setFormatter(formatter)

        pyhtcc_logger.addHandler(supervisor_handler)
        pyhtcc_logger.setLevel(logging.DEBUG)

        # Prevent propagation to avoid duplicate messages
        pyhtcc_logger.propagate = False

    def _get_zone_device_ids(self) -> list:
        """
        Return a list of zone Device IDs.

        inputs:
            None
        returns:
            (list): all zone device ids supported.
        """
        zone_id_lst = []
        for _, zone in enumerate(self.get_zones_info()):
            zone_id_lst.append(zone["DeviceID"])
        return zone_id_lst

    def get_target_zone_id(self, zone=honeywell_config.default_zone) -> int:
        """
        Return the target zone ID.

        inputs:
            zone(int):  zone number.
        returns:
            (int): zone device id number
        """
        try:
            zone_id = self._get_zone_device_ids()[zone]
        except IndexError as ex:
            raise ValueError(
                f"zone '{zone}' type{type(zone)} is not a valid "
                "choice for this Honeywell thermostat, valid "
                "choices are: "
                f"{self._get_zone_device_ids()}"
            ) from ex
        return zone_id

    def print_all_thermostat_metadata(self, zone):
        """
        Return initial meta data queried from thermostat.

        inputs:
            zone(int): zone number
        returns:
            None, prints data to the stdout.
        """
        # dump all meta data
        self.get_all_metadata(zone)

        # dump uiData in a readable format
        self.exec_print_all_thermostat_metadata(self.get_latestdata, [zone])

    def get_all_metadata(self, zone=honeywell_config.default_zone, retry=False) -> dict:
        """
        Return all the current thermostat metadata.

        inputs:
          zone(int): zone number, default=honeywell_config.default_zone
          retry(bool): if True will retry with extended retry mechanism.
        returns:
          (dict) thermostat meta data.
        """
        return_data = self.get_metadata(zone, retry=retry)
        util.log_msg(
            f"all meta data: {return_data}",
            mode=util.DEBUG_LOG + util.STDOUT_LOG,
            func_name=1,
        )
        return return_data

    def get_metadata(
        self,
        zone=honeywell_config.default_zone,
        trait=None,
        parameter=None,
        retry=False
    ) -> Union[dict, str]:
        """
        Return the current thermostat metadata settings.

        inputs:
          zone(int): zone number, default=honeywell_config.default_zone
          trait(str): trait or parent key, if None will assume a non-nested
                      dict
          parameter(str): target parameter, None = all settings
          retry(bool): if True will retry with extended retry mechanism
        returns:
          (dict) if parameter=None
          (str) if parameter != None
        """
        del trait  # not used on Honeywell

        def _get_metadata_internal():
            zone_info_list = self.get_zones_info()
            if parameter is None:
                try:
                    return_data = zone_info_list[zone]
                except IndexError:
                    print(
                        f"ERROR: zone {zone} does not exist in zone_info_list: "
                        f"{zone_info_list}"
                    )
                    raise
                util.log_msg(
                    f"zone {zone} info: {return_data}",
                    mode=util.DEBUG_LOG + util.STDOUT_LOG,
                    func_name=1,
                )
                return return_data
            else:
                try:
                    return_data = zone_info_list[zone].get(parameter)
                except IndexError:
                    print(
                        f"ERROR: zone {zone} does not exist in zone_info_list: "
                        f"{zone_info_list}"
                    )
                    raise
                util.log_msg(
                    f"zone {zone} parameter '{parameter}': {return_data}",
                    mode=util.DEBUG_LOG + util.STDOUT_LOG,
                    func_name=1,
                )
                return return_data

        if retry:
            # Use standardized extended retry mechanism
            return util.execute_with_extended_retries(
                func=_get_metadata_internal,
                thermostat_type=self.thermostat_type,
                zone_name=str(zone),
                number_of_retries=5,
                initial_retry_delay_sec=30,
                exception_types=(
                    http.client.HTTPException,
                    urllib3.exceptions.HTTPError,
                    urllib3.exceptions.ConnectionError,
                    urllib3.exceptions.TimeoutError,
                    ConnectionError,
                    TimeoutError,
                    IndexError,
                    KeyError,
                ),
                email_notification=email_notification,
            )
        else:
            # Single attempt without retry
            return _get_metadata_internal()

    def get_latestdata(self, zone=honeywell_config.default_zone, debug=False) -> dict:
        """
        Return the current thermostat latest data.

        inputs:
          zone(int): zone number, default=honeywell_config.default_zone
          debug(bool): debug flag
        returns:
          (dict) latest data from thermostat.
        """
        latest_data_dict = self.get_metadata(zone).get("latestData")
        if debug:
            util.log_msg(
                f"zone{zone} latestData: {latest_data_dict}",
                mode=util.BOTH_LOG,
                func_name=1,
            )
        return latest_data_dict

    def get_ui_data(self, zone=honeywell_config.default_zone) -> dict:
        """
        Return the latest thermostat ui data.

        inputs:
          zone(int): zone, default=honeywell_config.default_zone
        returns:
          (dict) ui data from thermostat.
        """
        ui_data_dict = self.get_latestdata(zone).get("uiData")
        util.log_msg(
            f"zone{zone} latestData: {ui_data_dict}",
            mode=util.DEBUG_LOG + util.STDOUT_LOG,
            func_name=1,
        )
        return ui_data_dict

    def get_ui_data_param(
        self, zone=honeywell_config.default_zone, parameter=None
    ) -> dict:
        """
        Return the latest thermostat ui data for one specific parameter.

        inputs:
          zone(int): zone, default=honeywell_config.default_zone
          parameter(str): paramenter name
        returns:
          (dict)  # need to verify return data type.
        """
        parameter_data = self.get_ui_data(zone=honeywell_config.default_zone).get(
            parameter
        )
        util.log_msg(
            f"zone{zone} uiData parameter {parameter}: {parameter_data}",
            mode=util.DEBUG_LOG + util.STDOUT_LOG,
            func_name=1,
        )
        return parameter_data

    def get_zones_info(self) -> list:
        """
        Return a list of dicts corresponding with each one corresponding to a
        particular zone.

        Method overridden from base class to add exception handling.
        inputs:
            None.
        returns:
            list of zone info.
        """
        return get_zones_info_with_retries(
            super().get_zones_info, self.thermostat_type, self.zone_name
        )


def get_zones_info_with_retries(func, thermostat_type, zone_name) -> list:
    """
    Return a list of dicts corresponding with each one corresponding to a
    particular zone.

    inputs:
        func(callable): function to override.
        thermostat_type(str): thermostat_type
        zone_name(str): zone name
    returns:
        list of zone info.
    """

    # Define Honeywell-specific exception types
    honeywell_exceptions = (
        pyhtcc.requests.exceptions.ConnectionError,
        pyhtcc.pyhtcc.UnexpectedError,
        pyhtcc.pyhtcc.NoZonesFoundError,
        pyhtcc.pyhtcc.UnauthorizedError,
        pyhtcc.pyhtcc.TooManyAttemptsError,
        pyhtcc.requests.exceptions.HTTPError,
        urllib3.exceptions.ProtocolError,
        http.client.RemoteDisconnected,
    )

    # Use the common retry utility
    return util.execute_with_extended_retries(
        func=func,
        thermostat_type=thermostat_type,
        zone_name=zone_name,
        number_of_retries=5,
        initial_retry_delay_sec=60,
        exception_types=honeywell_exceptions,
        email_notification=email_notification,
    )


class ThermostatZone(pyhtcc.Zone, tc.ThermostatCommonZone):
    """Extend the Zone class with additional methods to get and set
    uiData parameters."""

    def __init__(self, Thermostat_obj, verbose=True):
        """
        Zone constructor.

        inputs:
            Thermostat_obj(obj): Thermostat class object instance.
            verbose(bool): debug flag.
        returns:
            None
        """
        if not isinstance(Thermostat_obj.device_id, int):
            raise TypeError(
                f"device_id is type {type(Thermostat_obj.device_id)}, "
                f"expected type 'int'"
            )

        # preset zone_name for pyhtcc.Zone constructor
        self.zone_name = Thermostat_obj.zone_name

        # thermostat type, needs to be defined prior to pyhtcc.Zone.__init__
        self.thermostat_type = honeywell_config.ALIAS

        # server data cache expiration parameters
        # needs to be defined before pyhtcc.Zone.__init__
        self.fetch_interval_sec = 60  # age of server data before refresh
        self.last_fetch_time = time.time() - 2 * self.fetch_interval_sec

        # call both parent class __init__
        self.args = [Thermostat_obj.device_id, Thermostat_obj]
        pyhtcc.Zone.__init__(self, *self.args)
        tc.ThermostatCommonZone.__init__(self)

        # switch config for this thermostat
        self.system_switch_position[tc.ThermostatCommonZone.COOL_MODE] = 3
        self.system_switch_position[tc.ThermostatCommonZone.HEAT_MODE] = 1
        self.system_switch_position[tc.ThermostatCommonZone.OFF_MODE] = 2
        # TODO: what mode is 0 on Honeywell?

        # zone info
        self.verbose = verbose
        self.device_id = Thermostat_obj.device_id
        self.zone_name = self.get_zone_name()

        # runtime parameter defaults
        self.poll_time_sec = 10 * 60  # default to 10 minutes
        # min practical value is 2 minutes based on empirical test
        # max value was 3, higher settings will cause HTTP errors, why?
        # not showing error on Pi at 10 minutes, so changed default to 10 min.
        self.connection_time_sec = 8 * 60 * 60  # default to 8 hours

    def get_zone_name(self) -> str:  # used
        """
        Refresh the cached zone information then return Name.

        inputs:
            None
        returns:
            (str): zone name
        """
        self.refresh_zone_info()
        return self.zone_info["Name"]

    def get_display_temp(self) -> float:  # used
        """
        Refresh the cached zone information then return DispTemperature.

        inputs:
            None
        returns:
            (float): display temperature in °F.
        """
        return float(self.get_indoor_temperature_raw())

    def get_display_humidity(self) -> Union[float, None]:
        """
        Refresh the cached zone information then return IndoorHumidity.

        inputs:
            None
        returns:
            (float, None): indoor humidity in %RH, None if not supported.
        """
        raw_humidity = self.get_indoor_humidity_raw()
        if raw_humidity is not None:
            return float(raw_humidity)
        else:
            return raw_humidity

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
        available = bool(
            self.zone_info["latestData"]["uiData"]["IndoorHumiditySensorAvailable"]
        )
        not_fault = bool(
            self.zone_info["latestData"]["uiData"]["IndoorHumiditySensorNotFault"]
        )
        return available and not_fault

    def is_heat_mode(self) -> int:
        """
        Refresh the cached zone information and return heat mode.

        inputs:
            None
        returns:
            (int): 1 heat mode, else 0
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
            (int): 1 if cool mode, else 0
        """
        return int(
            self.get_system_switch_position()
            == self.system_switch_position[tc.ThermostatCommonZone.COOL_MODE]
        )

    def is_dry_mode(self) -> int:
        """
        Return the dry mode.

        inputs:
            None
        returns:
            (int): 1 if dry mode, else 0
        """
        return int(
            self.get_system_switch_position()
            == self.system_switch_position[tc.ThermostatCommonZone.DRY_MODE]
        )

    def is_fan_mode(self) -> int:
        """
        Refresh the cached zone information and return the fan mode.

        Fan mode on Honeywell is defined as in off mode with fan set to
        on or circulate modes.
        inputs:
            None
        returns:
            (int): fan mode, 1=enabled, 0=disabled.
        """
        return int(
            self.get_system_switch_position()
            == self.system_switch_position[tc.ThermostatCommonZone.OFF_MODE]
            and (self.is_fan_on_mode() or self.is_fan_circulate_mode())
        )

    def is_auto_mode(self) -> int:
        """
        Return the auto mode.

        inputs:
            None
        returns:
            (int): 1 if auto mode, else 0
        """
        return int(
            self.get_system_switch_position()
            == self.system_switch_position[tc.ThermostatCommonZone.AUTO_MODE]
        )

    def is_eco_mode(self) -> int:
        """
        Return the eco mode.

        inputs:
            None
        returns:
            (int): 1 if auto mode, else 0
        """
        return int(
            self.get_system_switch_position()
            == self.system_switch_position[tc.ThermostatCommonZone.ECO_MODE]
        )

    def is_heating(self) -> int:
        """
        Refresh the cached zone information and return the heat active mode.
        inputs:
            None
        returns:
            (int) 1 if heating is active, else 0.
        """
        self.refresh_zone_info()
        return int(
            self.is_heat_mode()
            and self.get_display_temp() < self.get_heat_setpoint_raw()
        )

    def is_cooling(self) -> int:
        """
        Refresh the cached zone information and return the cool active mode.
        inputs:
            None
        returns:
            (int): 1 if cooling is active, else 0.
        """
        self.refresh_zone_info()
        return int(
            self.is_cool_mode()
            and self.get_display_temp() > self.get_cool_setpoint_raw()
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
        return int(
            (self.is_fan_on() or self.is_fan_circulate_mode()) and self.is_power_on()
        )

    def is_fan_circulate_mode(self) -> int:
        """Return 1 if fan is in circulate mode, else 0."""
        self.refresh_zone_info()
        return int(self.zone_info["latestData"]["fanData"]["fanMode"] == 2)

    def is_fan_auto_mode(self) -> int:
        """Return 1 if fan is in auto mode, else 0."""
        self.refresh_zone_info()
        return int(self.zone_info["latestData"]["fanData"]["fanMode"] == 0)

    def is_fan_on_mode(self) -> int:
        """Return 1 if fan is in always on mode, else 0."""
        self.refresh_zone_info()
        return int(self.zone_info["latestData"]["fanData"]["fanMode"] == 1)

    def is_power_on(self) -> int:
        """Return 1 if power relay is active, else 0."""
        self.refresh_zone_info()
        # just a guess, not sure what position 0 is yet.
        return int(self.zone_info["latestData"]["uiData"]["SystemSwitchPosition"] > 0)

    def is_fan_on(self) -> int:
        """Return 1 if fan relay is active, else 0."""
        self.refresh_zone_info()
        return int(self.zone_info["latestData"]["fanData"]["fanIsRunning"])

    def get_wifi_strength(self) -> float:  # noqa R0201
        """Return the wifi signal strength in dBm."""
        self.refresh_zone_info()
        return float(util.BOGUS_INT)

    def get_wifi_status(self) -> bool:  # noqa R0201
        """Return the wifi connection status."""
        return not self.zone_info["communicationLost"]

    def get_battery_voltage(self) -> float:  # noqa R0201
        """Return the battery voltage in volts.

        This tstat is on line power so any valid response
        from tstat returns line power value.
        """
        return 120.0 if self.zone_info["deviceLive"] else 0.0

    def get_battery_status(self) -> bool:  # noqa R0201
        """Return the battery status.

        For this tstat any positive number returns True.
        """
        return self.get_battery_voltage() > 0.0

    def get_schedule_heat_sp(self) -> float:  # used
        """
        Refresh the cached zone information and return the
        schedule heat setpoint.

        inputs:
            None
        returns:
            (float): heating set point in °F.
        """
        self.refresh_zone_info()
        return float(self.zone_info["latestData"]["uiData"]["ScheduleHeatSp"])

    def get_schedule_cool_sp(self) -> float:
        """
        Refresh the cached zone information and return the
        schedule cool setpoint.

        inputs:
            None
        returns:
            (float): cooling set point in °F.
        """
        self.refresh_zone_info()
        return float(self.zone_info["latestData"]["uiData"]["ScheduleCoolSp"])

    def get_is_invacation_hold_mode(self) -> bool:  # used
        """
        Refresh the cached zone information and return the
          'IsInVacationHoldMode' setting.

        inputs:
            None
        returns:
            (booL): True if is in vacation hold mode.
        """
        self.refresh_zone_info()
        return bool(int(self.zone_info["latestData"]["uiData"]["IsInVacationHoldMode"]))

    def get_vacation_hold(self) -> bool:
        """
        Refresh the cached zone information and return the
        VacationHold setting.

        inputs:
            None
        returns:
            (bool): True if vacation hold is set.
        """
        self.refresh_zone_info()
        return bool(self.zone_info["latestData"]["uiData"]["VacationHold"])

    def get_vacation_hold_until_time(self) -> int:
        """
        Refresh the cached zone information and return
        the 'VacationHoldUntilTime'.
        inputs:
            None
        returns:
            (int) vacation hold time until in minutes
        """
        self.refresh_zone_info()
        return int(self.zone_info["latestData"]["uiData"]["VacationHoldUntilTime"])

    def get_temporary_hold_until_time(self) -> int:  # used
        """
        Refresh the cached zone information and return the
        'TemporaryHoldUntilTime'.

        inputs:
            None
        returns:
            (int) temporary hold time until in minutes.
        """
        self.refresh_zone_info()
        return int(self.zone_info["latestData"]["uiData"]["TemporaryHoldUntilTime"])

    def get_setpoint_change_allowed(self) -> bool:
        """
        Refresh the cached zone information and return the
        'SetpointChangeAllowed' setting.

        'SetpointChangeAllowed' will be True in heating mode,
        False in OFF mode (assume True in cooling mode too)
        inputs:
            None
        returns:
            (bool): True if set point changes are allowed.
        """
        self.refresh_zone_info()
        return bool(self.zone_info["latestData"]["uiData"]["SetpointChangeAllowed"])

    def get_system_switch_position(self) -> int:  # used
        """
        Refresh the cached zone information and return the
        'SystemSwitchPosition'.

        'SystemSwitchPosition' = 1 for heat, 2 for off
        inputs:
            None
        returns:
            (int) current mode for unit, should match value
                  in self.system_switch_position
        """
        self.refresh_zone_info()
        return int(self.zone_info["latestData"]["uiData"]["SystemSwitchPosition"])

    def set_heat_setpoint(self, temp: int) -> None:
        """
        Set a new heat setpoint.

        This will also attempt to turn the thermostat to 'Heat'
        inputs:
            temp(int): desired temperature.
        returns:
            None
        """
        # logger.info(f"setting heat on with a target temp of: {temp}")
        return self.submit_control_changes(
            {
                "HeatSetpoint": temp,
                "StatusHeat": 0,  # follow schedule
                "StatusCool": 0,  # follow schedule
                "SystemSwitch": self.system_switch_position[self.HEAT_MODE],
            }
        )

    def set_cool_setpoint(self, temp: int) -> None:
        """
        Set a new cool setpoint.

        This will also attempt to turn the thermostat to 'Cool'
        inputs:
            temp(int): desired temperature.
        returns:
            None
        """
        # logger.info(f"setting heat on with a target temp of: {temp}")
        return self.submit_control_changes(
            {
                "CoolSetpoint": temp,
                "StatusHeat": 0,  # follow schedule
                "StatusCool": 0,  # follow schedule
                "SystemSwitch": self.system_switch_position[self.COOL_MODE],
            }
        )

    def refresh_zone_info(self, force_refresh=False) -> None:
        """
        Refresh the zone_info attribute.

        Method overridden from base class to add retry on connection errors.
        Retry up to 24 hours for extended internet outages.
        inputs:
            force_refresh(bool): not used in this method
        returns:
            None, populates self.zone_info dict.
        """
        now_time = time.time()
        # refresh if past expiration date or force_refresh option
        if force_refresh or (
            now_time >= (self.last_fetch_time + self.fetch_interval_sec)
        ):
            all_zones_info = get_zones_info_with_retries(
                self.pyhtcc.get_zones_info, self.thermostat_type, self.zone_name
            )
            for zone_data in all_zones_info:
                if zone_data["DeviceID"] == self.device_id:
                    pyhtcc.logger.debug(
                        f"Refreshed zone info for \
                                        {self.device_id}"
                    )
                    self.zone_info = zone_data
                    self.last_fetch_time = now_time


# add default requests session default timeout to prevent TimeoutExceptions
# see ticket #93 for details
# pylint: disable=wrong-import-order,wrong-import-position
from requests.adapters import HTTPAdapter  # noqa E402

# network timeout limit
# 6s upper is 1.9 on pi4 and laptop
# 6s upper is 2.17 on Azure pipeline
HTTP_TIMEOUT = 2.5  # 6 sigma limit in seconds


class TimeoutHTTPAdapter(HTTPAdapter):
    """Override TimeoutHTTPAdapter to include timeout parameter."""

    def __init__(self, *args, **kwargs):
        self.timeout = HTTP_TIMEOUT
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):  # pylint: disable=arguments-differ
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)


if __name__ == "__main__":
    # verify environment
    env.get_python_version()
    env.show_package_version(pyhtcc)

    # get zone override
    api.uip = api.UserInputs(argv_list=None, thermostat_type=honeywell_config.ALIAS)
    zone_number = api.uip.get_user_inputs(api.uip.zone_name, api.input_flds.zone)

    _, Zone = tc.thermostat_basic_checkout(
        honeywell_config.ALIAS, zone_number, ThermostatClass, ThermostatZone
    )

    tc.print_select_data_from_all_zones(
        honeywell_config.ALIAS,
        honeywell_config.get_available_zones(),
        ThermostatClass,
        ThermostatZone,
        display_wifi=True,
        display_battery=True,
    )

    # measure thermostat response time
    if honeywell_config.check_response_time:
        MEASUREMENTS = 30
        meas_data = Zone.measure_thermostat_repeatability(
            MEASUREMENTS,
            func=Zone.pyhtcc.get_zones_info,
            measure_response_time=True,
        )
        ppp = pprint.PrettyPrinter(indent=4)
        ppp.pprint(meas_data)
