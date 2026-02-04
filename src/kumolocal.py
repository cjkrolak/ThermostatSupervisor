"""KumoCloud integration using local API for data."""

# built-in imports
import logging
import os
import pprint
import time
from typing import Union

# third party imports

# local imports
from src import kumolocal_config
from src import thermostat_api as api
from src import thermostat_common as tc
from src import environment as env
from src import utilities as util

# pykumo
PYKUMO_DEBUG = False  # debug uses local pykumo repo instead of pkg
if PYKUMO_DEBUG and not env.is_azure_environment():
    mod_path = "..\\pykumo\\pykumo"
    if env.is_interactive_environment():
        mod_path = "..\\" + mod_path
    pykumo = env.dynamic_module_import("pykumo", mod_path)
else:
    import pykumo  # noqa E402, from path / site packages


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


class ThermostatClass(pykumo.KumoCloudAccount, tc.ThermostatCommon):
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
        self.args = [self.kc_uname, self.kc_pwd]
        # kumocloud account init sets the self._url
        pykumo.KumoCloudAccount.__init__(self, *self.args)
        tc.ThermostatCommon.__init__(self)

        # integrate pykumo logger with supervisor logging system
        self._setup_pykumo_logging()

        # set tstat type and debug flag
        self.thermostat_type = kumolocal_config.ALIAS
        self.verbose = verbose

        # configure zone info
        self.zone_number = int(zone)
        self.zone_name = self.get_zone_name()
        self.device_id = None  # initialize
        self.device_id = self.get_target_zone_id(self.zone_number)
        self.serial_number = None  # will be populated when unit is queried.

        # detect local network availability for this zone
        self.detect_local_network_availability()

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
                pykumo_logger.setLevel(logging.DEBUG)

                # Prevent propagation to avoid duplicate messages
                pykumo_logger.propagate = False

            except Exception as exc:
                # Log setup failure but don't break initialization
                util.log_msg(
                    f"Failed to setup logging for {module_name}: {exc}",
                    mode=util.DATA_LOG + util.STDERR_LOG,
                    func_name=1,
                )

    def get_zone_name(self):
        """
        Return the name associated with the zone number from metadata dict.

        inputs:
            None
        returns:
            (str) zone name
        """
        return kumolocal_config.metadata[self.zone_number]["zone_name"]

    def get_target_zone_id(self, zone=0):
        """
        Return the target zone ID.

        inputs:
            zone(int): zone number.
        returns:
            (obj): PyKumo object
        """
        # populate the zone dictionary
        # establish local interface to kumos, must be on local net
        kumos = self.make_pykumos()
        device_id = kumos[self.zone_name]
        # print zone name the first time it is known
        if self.device_id is None and self.verbose:
            util.log_msg(
                f"zone {zone} name='{self.zone_name}', device_id={device_id}",
                mode=util.DEBUG_LOG + util.STDOUT_LOG,
                func_name=1,
            )
        self.device_id = device_id

        # return the target zone object
        return self.device_id

    def detect_local_network_availability(self):
        """
        Detect if kumolocal devices are available on the local network.

        Updates kumolocal_config.metadata with detected network information.

        inputs:
            None
        returns:
            None (updates metadata dict)
        """
        try:
            serial_num_lst = self._get_indoor_units_list()
            if not serial_num_lst:
                return

            self._check_zones_availability(serial_num_lst)

        except Exception as exc:
            self._handle_detection_error(exc)

    def _get_indoor_units_list(self):
        """Get list of indoor units."""
        serial_num_lst = list(self.get_indoor_units())

        if not serial_num_lst and self.verbose:
            util.log_msg(
                "No kumolocal units found in kumocloud account",
                mode=util.DEBUG_LOG + util.STDOUT_LOG,
                func_name=1,
            )

        return serial_num_lst

    def _check_zones_availability(self, serial_num_lst):
        """Check availability for each zone."""
        for zone_idx, serial_number in enumerate(serial_num_lst):
            if zone_idx not in kumolocal_config.metadata:
                continue

            self._process_zone_availability(zone_idx, serial_number)

    def _process_zone_availability(self, zone_idx, serial_number):
        """Process availability check for a single zone."""
        local_address = self.get_address(serial_number)
        device_name = self.get_name(serial_number)

        if self._has_valid_local_address(local_address):
            self._check_and_update_available_zone(zone_idx, device_name, local_address)
        else:
            self._update_unavailable_zone(zone_idx, device_name)

    def _has_valid_local_address(self, local_address):
        """Check if local address is valid."""
        return local_address and local_address != "0.0.0.0"

    def _check_and_update_available_zone(self, zone_idx, device_name, local_address):
        """Check and update zone with valid local address."""
        is_available, detected_ip = util.is_host_on_local_net(
            host_name=device_name,
            ip_address=local_address,
            verbose=self.verbose,
        )

        if self.verbose:
            print(f"is_available={is_available}, detected_ip={detected_ip}")

        self._update_zone_metadata(zone_idx, device_name, local_address, is_available)

    def _update_zone_metadata(self, zone_idx, device_name, local_address, is_available):
        """Update zone metadata with detection results."""
        zone_meta = kumolocal_config.metadata[zone_idx]
        zone_meta["ip_address"] = local_address
        zone_meta["host_name"] = device_name
        zone_meta["local_net_available"] = is_available

        if self.verbose:
            status = "available" if is_available else "not available"
            util.log_msg(
                f"Zone {zone_idx} ({device_name}): "
                f"local network {status} at {local_address}",
                mode=util.DEBUG_LOG + util.STDOUT_LOG,
                func_name=1,
            )

    def _update_unavailable_zone(self, zone_idx, device_name):
        """Update zone metadata for unavailable zone."""
        zone_meta = kumolocal_config.metadata[zone_idx]
        zone_meta["local_net_available"] = False

        if self.verbose:
            util.log_msg(
                f"Zone {zone_idx} ({device_name}): "
                f"no local address available from kumocloud",
                mode=util.DEBUG_LOG + util.STDOUT_LOG,
                func_name=1,
            )

    def _handle_detection_error(self, exc):
        """Handle detection errors."""
        if self.verbose:
            util.log_msg(
                f"Warning: local network detection failed: {exc}",
                mode=util.DEBUG_LOG + util.STDOUT_LOG,
                func_name=1,
            )

    def get_kumocloud_thermostat_metadata(self, zone=None, debug=False, retry=False):
        """Get all thermostat meta data for zone from kumocloud.

        inputs:
            zone(): specified zone, if None will print all zones.
            debug(bool): debug flag.
            retry(bool): if True will retry with extended retry mechanism
        returns:
            (dict): JSON dict
        """
        del debug  # unused

        def _get_metadata_internal():
            try:
                serial_num_lst = list(self.get_indoor_units())  # will query unit
            except UnboundLocalError:  # patch for issue #205
                util.log_msg(
                    "WARNING: Kumocloud refresh failed due to timeout",
                    mode=util.BOTH_LOG,
                    func_name=1,
                )
                time.sleep(10)
                serial_num_lst = list(self.get_indoor_units())  # retry
            util.log_msg(
                f"indoor unit serial numbers: {str(serial_num_lst)}",
                mode=util.DEBUG_LOG + util.STDOUT_LOG,
                func_name=1,
            )

            # validate serial number list
            if not serial_num_lst:
                raise tc.AuthenticationError(
                    "pykumo meta data is blank, probably"
                    " due to an Authentication Error,"
                    " check your credentials."
                )

            for serial_number in serial_num_lst:
                util.log_msg(
                    f"Unit {self.get_name(serial_number)}: address: "
                    f"{self.get_address(serial_number)} credentials: "
                    f"{self.get_credentials(serial_number)}",
                    mode=util.DEBUG_LOG + util.STDOUT_LOG,
                    func_name=1,
                )
            if zone is None:
                # returned cached raw data for all zones
                raw_json = self.get_raw_json()  # does not fetch results,
            else:
                # return cached raw data for specified zone
                try:
                    self.serial_number = serial_num_lst[zone]
                except IndexError as exc:
                    raise IndexError(
                        f"ERROR: Invalid Zone, index ({zone}) does "
                        "not exist in serial number list "
                        f"({serial_num_lst})"
                    ) from exc

                # Safely access nested raw JSON structure with detailed error reporting
                try:
                    raw_data = self.get_raw_json()
                    if raw_data is None:
                        raise KeyError(
                            "Raw JSON data is None - likely authentication "
                            "or connection issue"
                        )

                    if len(raw_data) <= 2:
                        raise KeyError(
                            f"Raw JSON data structure invalid - expected "
                            f"at least 3 elements, got {len(raw_data)}"
                        )

                    level_2_data = raw_data[2]
                    if "children" not in level_2_data:
                        raise KeyError(
                            "Missing 'children' key in raw JSON data at level 2"
                        )

                    children_data = level_2_data["children"]
                    if not children_data or len(children_data) == 0:
                        raise KeyError("Empty 'children' array in raw JSON data")

                    first_child = children_data[0]
                    if "zoneTable" not in first_child:
                        raise KeyError(
                            "Missing 'zoneTable' key in first child of " "raw JSON data"
                        )

                    zone_table = first_child["zoneTable"]
                    zone_serial = serial_num_lst[zone]
                    if zone_serial not in zone_table:
                        available_zones = list(zone_table.keys())
                        raise KeyError(
                            f"Zone serial number '{zone_serial}' not found "
                            f"in zoneTable. Available zones: {available_zones}"
                        )

                    raw_json = zone_table[zone_serial]

                except KeyError as exc:
                    # Re-raise with more context about when this error occurred
                    serial_info = (
                        serial_num_lst[zone]
                        if zone < len(serial_num_lst)
                        else "unknown"
                    )
                    error_msg = (
                        f"KeyError during metadata retrieval for zone {zone} "
                        f"(serial: {serial_info}): {str(exc)}. This often "
                        "occurs immediately after setting temperature when "
                        "the thermostat metadata structure is temporarily "
                        "inconsistent."
                    )
                    util.log_msg(
                        f"ERROR: {error_msg}",
                        mode=util.BOTH_LOG,
                        func_name=1,
                    )
                    raise KeyError(error_msg) from exc
            return raw_json

        if retry:
            # Use standardized extended retry mechanism
            return util.execute_with_extended_retries(
                func=_get_metadata_internal,
                thermostat_type=getattr(self, "thermostat_type", "KumoLocal"),
                zone_name=str(getattr(self, "zone_name", zone)),
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
                email_notification=None,  # KumoLocal doesn't import email_notification
            )
        else:
            # Single attempt without retry
            return _get_metadata_internal()

    def get_all_metadata(self, zone=None, retry=False):
        """Get all thermostat meta data for device_id from local API.

        inputs:
            zone(): specified zone
            retry(bool): if True will retry with extended retry mechanism.
        returns:
            (dict): dictionary of meta data.
        """
        return self.get_metadata(zone, retry=retry)

    def get_metadata(self, zone=None, trait=None, parameter=None, retry=False):
        """Get thermostat meta data for device_id from local API.

        inputs:
            zone(str or int): (unused) specified zone
            trait(str): trait or parent key, if None will assume a non-nested
                        dict
            parameter(str): target parameter, if None will return all.
            retry(bool): if True will retry with extended retry mechanism
        returns:
            (dict): dictionary of meta data.
        """
        del trait  # not used on Kumolocal
        del zone  # unused

        def _get_metadata_internal():
            # refresh device status
            self.device_id.update_status()
            meta_data = {}
            meta_data["status"] = self.device_id.get_status()
            # pylint: disable=protected-access
            meta_data["sensors"] = self.device_id._sensors
            # pylint: disable=protected-access
            meta_data["profile"] = self.device_id._profile
            if parameter is None:
                return meta_data
            else:
                return meta_data[parameter]

        if retry:
            # Use standardized extended retry mechanism
            return util.execute_with_extended_retries(
                func=_get_metadata_internal,
                thermostat_type="KumoLocal",
                zone_name=str(getattr(self, "zone_name", "unknown")),
                number_of_retries=5,
                initial_retry_delay_sec=60,
                exception_types=(
                    KeyError,
                    AttributeError,
                    ConnectionError,
                    TimeoutError,
                ),
                email_notification=None,  # KumoLocal doesn't import email_notification
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

    def is_local_network_available(self, zone=None):
        """
        Check if kumolocal device is available on local network.

        inputs:
            zone(int): zone number, defaults to self.zone_number
        returns:
            bool: True if device is available on local network, False otherwise
        """
        zone_number = zone if zone is not None else self.zone_number
        if zone_number in kumolocal_config.metadata:
            value = kumolocal_config.metadata[zone_number].get(
                "local_net_available", False
            )
            # Handle case where value is None (not yet detected)
            return value if value is not None else False
        return False


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

        # server data cache expiration parameters
        self.fetch_interval_sec = 60  # age of server data before refresh
        self.last_fetch_time = time.time() - 2 * self.fetch_interval_sec

        # switch config for this thermostat
        self.system_switch_position[tc.ThermostatCommonZone.COOL_MODE] = "cool"
        self.system_switch_position[tc.ThermostatCommonZone.HEAT_MODE] = "heat"
        self.system_switch_position[tc.ThermostatCommonZone.OFF_MODE] = "off"
        self.system_switch_position[tc.ThermostatCommonZone.DRY_MODE] = "dry"
        self.system_switch_position[tc.ThermostatCommonZone.AUTO_MODE] = "auto"
        self.system_switch_position[tc.ThermostatCommonZone.FAN_MODE] = "vent"

        # zone info
        self.verbose = verbose
        self.thermostat_type = kumolocal_config.ALIAS
        self.device_id = Thermostat_obj.device_id
        self.Thermostat = Thermostat_obj
        self.zone_number = Thermostat_obj.zone_number
        self.zone_name = Thermostat_obj.zone_name
        self.zone_name = self.get_zone_name()

    def get_zone_name(self):
        """
        Return the name associated with the zone number from device memory.

        inputs:
            None
        returns:
            (str) zone name
        """
        self.refresh_zone_info()
        zone_name = self.device_id.get_name()
        # update metadata dict
        kumolocal_config.metadata[self.zone_number]["zone_name"] = zone_name
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
        return util.c_to_f(self.device_id.get_current_temperature())

    def get_display_humidity(self) -> Union[float, None]:
        """
        Refresh the cached zone information and return IndoorHumidity.

        inputs:
            None
        returns:
            (float, None): indoor humidity in %RH, None if not supported.
        """
        self.refresh_zone_info()
        return self.device_id.get_current_humidity()

    def get_is_humidity_supported(self) -> bool:  # used
        """
        Refresh the cached zone information and return the
          True if humidity sensor data is trustworthy.

        inputs:
            None
        returns:
            (booL): True if is in humidity sensor is available and not faulted.
        """
        return self.get_display_humidity() is not None

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
        return int(0)  # not supported

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

    def is_power_on(self):
        """Return 1 if power relay is active, else 0."""
        self.refresh_zone_info()
        return int(self.device_id.get_mode() != "off")

    def is_fan_on(self):
        """Return 1 if fan relay is active, else 0."""
        self.refresh_zone_info()
        return int(self.device_id.get_fan_speed() != "off")

    def is_defrosting(self) -> int:
        """Return 1 if defrosting is active, else 0."""
        self.refresh_zone_info()
        return int(self.device_id.get_status("defrost") == "True")

    def is_standby(self) -> int:
        """Return 1 if standby is active, else 0."""
        self.refresh_zone_info()
        return int(self.device_id.get_standby())

    def get_heat_setpoint_raw(self) -> float:  # used
        """
        Refresh the cached zone information and return the heat setpoint.

        inputs:
            None
        returns:
            (float): heating set point in °F.
        """
        self.refresh_zone_info()
        return util.c_to_f(self.device_id.get_heat_setpoint())

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
        return float(kumolocal_config.MAX_HEAT_SETPOINT)  # max heat set point allowed

    def get_schedule_cool_sp(self) -> float:
        """
        Return the schedule cool setpoint.

        inputs:
            None
        returns:
            (float): scheduled cooling set point in °F.
        """
        return float(kumolocal_config.MIN_COOL_SETPOINT)  # min cool set point allowed

    def get_cool_setpoint_raw(self) -> float:
        """
        Return the cool setpoint.

        inputs:
            None
        returns:
            (float): cooling set point in °F.
        """
        self.refresh_zone_info()
        return util.c_to_f(self.device_id.get_cool_setpoint())

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
        Return the system switch position, same as mode.

        inputs:
            None
        returns:
            (int or str) current mode for unit, should match value
                  in self.system_switch_position
        """
        self.refresh_zone_info()
        return self.device_id.get_mode()

    def set_heat_setpoint(self, temp: int) -> None:
        """
        Set a new heat setpoint.

        This will also attempt to turn the thermostat to 'Heat'
        inputs:
            temp(int): desired temperature in F
        returns:
            None
        """
        self.device_id.set_heat_setpoint(util.f_to_c(temp))

    def set_cool_setpoint(self, temp: int) -> None:
        """
        Set a new cool setpoint.

        This will also attempt to turn the thermostat to 'Cool'
        inputs:
            temp(int): desired temperature in ° F.
        returns:
            None
        """
        self.device_id.set_cool_setpoint(util.f_to_c(temp))

    def refresh_zone_info(self, force_refresh=False):
        """
        Refresh zone info from KumoCloud.

        inputs:
            force_refresh(bool): if True, ignore expiration timer.
        returns:
            None, device_id object is refreshed.
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
            self.device_id = self.Thermostat.get_target_zone_id(self.zone_name)


if __name__ == "__main__":
    # verify environment
    env.get_python_version()
    env.show_package_version(pykumo)

    # get zone override
    api.uip = api.UserInputs(argv_list=None, thermostat_type=kumolocal_config.ALIAS)
    zone_number = api.uip.get_user_inputs(api.uip.zone_name, api.input_flds.zone)

    _, Zone = tc.thermostat_basic_checkout(
        kumolocal_config.ALIAS, zone_number, ThermostatClass, ThermostatZone
    )

    tc.print_select_data_from_all_zones(
        kumolocal_config.ALIAS,
        kumolocal_config.get_available_zones(),
        ThermostatClass,
        ThermostatZone,
        display_wifi=False,
        display_battery=False,
    )

    # measure thermostat response time
    if kumolocal_config.check_response_time:
        MEASUREMENTS = 30
        meas_data = Zone.measure_thermostat_repeatability(
            MEASUREMENTS,
            func=Zone.pyhtcc.get_zones_info,
            measure_response_time=True,
        )
        ppp = pprint.PrettyPrinter(indent=4)
        ppp.pprint(meas_data)
