"""emulator integration"""
import os
import pickle
import random
import time
import traceback
from typing import Union

# local imports
from thermostatsupervisor import emulator_config
from thermostatsupervisor import environment as env
from thermostatsupervisor import thermostat_api as api
from thermostatsupervisor import thermostat_common as tc
from thermostatsupervisor import utilities as util


class ThermostatClass(tc.ThermostatCommon):
    """Emulator thermostat functions."""

    def __init__(self, zone, verbose=True):
        """
        Constructor, connect to thermostat.

        inputs:
            zone(str):  zone of thermostat.
            verbose(bool): debug flag.
        """
        # construct the superclass
        # call both parent class __init__
        tc.ThermostatCommon.__init__(self)

        # set tstat type and debug flag
        self.thermostat_type = emulator_config.ALIAS
        self.verbose = verbose

        # configure zone info
        self.zone_name = int(zone)
        self.device_id = self.get_target_zone_id(self.zone_name)
        self.serial_number = None  # will be populated when unit is queried.
        self.meta_data_dict = {}
        self.initialize_meta_data_dict()

    def initialize_meta_data_dict(self):
        """Initialize the meta data dict"""
        # add zone keys
        for key in emulator_config.supported_configs["zones"]:
            self.meta_data_dict[key] = {}

    def get_target_zone_id(self, zone=0):
        """
        Return the target zone ID.

        inputs:
            zone(int):  zone number.
        returns:
            (int): device_id
        """
        return zone

    def get_all_metadata(self, zone=None, retry=False):
        """Get all thermostat meta data for zone from emulator.

        inputs:
            zone(int): specified zone, if None will print all zones.
            retry(bool): if True will retry the request, not currrently implemented.
        returns:
            (dict): JSON dict
        """
        del retry  # unused on emulator
        return self.get_metadata(zone)

    def get_metadata(self, zone=None, trait=None, parameter=None):
        """Get all thermostat meta data for zone from emulator.

        inputs:
            zone(int): specified zone, if None will print all zones.
            trait(str): trait or parent key, if None will assume a non-nested
            dict
            parameter(str): target parameter, if None will return all.
            debug(bool): if True will print unit details.
        returns:
            (int, float, str, dict): depends on parameter
        """
        del trait  # unused on emulator
        if zone is None:
            # returned cached raw data for all zones
            meta_data_dict = self.meta_data_dict
        else:
            # return cached raw data for specified zone
            meta_data_dict = self.meta_data_dict[zone]
        if parameter is None:
            return meta_data_dict
        else:
            try:
                return meta_data_dict[parameter]
            except KeyError:
                print(
                    f"ERROR: parameter {parameter} does not exist in "
                    f"meta_data_dict: {meta_data_dict}"
                )
                raise

    def print_all_thermostat_metadata(self, zone):
        """Print all metadata for zone to the screen.

        inputs:
            zone(int): specified zone, if None will print all zones.
        returns:
            None, prints result to screen
        """
        self.exec_print_all_thermostat_metadata(self.get_all_metadata, [zone])


class ThermostatZone(tc.ThermostatCommonZone):
    """Emulator thermostat zone functions."""

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
        self.poll_time_sec = 1 * 60  # default to 1 minutes
        self.connection_time_sec = 1 * 60 * 60  # default to 1 hours

        # server data cache expiration parameters
        self.fetch_interval_sec = 30  # age of server data before refresh
        self.last_fetch_time = time.time() - 2 * self.fetch_interval_sec

        # switch config for this thermostat, numbers are unique and arbitrary
        self.system_switch_position[tc.ThermostatCommonZone.OFF_MODE] = 0
        self.system_switch_position[tc.ThermostatCommonZone.HEAT_MODE] = 1
        self.system_switch_position[tc.ThermostatCommonZone.COOL_MODE] = 2
        self.system_switch_position[tc.ThermostatCommonZone.DRY_MODE] = 3
        self.system_switch_position[tc.ThermostatCommonZone.AUTO_MODE] = 4
        self.system_switch_position[tc.ThermostatCommonZone.FAN_MODE] = 5

        # zone info
        self.verbose = verbose
        self.thermostat_type = emulator_config.ALIAS
        self.device_id = Thermostat_obj.device_id
        self.Thermostat = Thermostat_obj
        self.zone_name = Thermostat_obj.zone_name
        self.zone_info = Thermostat_obj.get_all_metadata(Thermostat_obj.zone_name)
        self.zone_name = self.get_zone_name()

        # deviation file support for testing
        self.deviation_file_path = util.get_full_file_path(
            f"emulator_deviation_zone_{self.device_id}.pkl"
        )

        self.initialize_meta_data_dict()

    def initialize_meta_data_dict(self):
        """Initialize the meta data dict"""
        # add parameters and values
        self.set_heat_setpoint(emulator_config.STARTING_TEMP)
        self.set_cool_setpoint(emulator_config.STARTING_TEMP)
        self.set_parameter("display_temp", emulator_config.STARTING_TEMP)
        self.set_parameter("display_humidity", emulator_config.STARTING_HUMIDITY)
        self.set_parameter("humidity_support", True)
        self.set_parameter("power_on", True)
        self.set_parameter("fan_on", True)
        self.set_parameter("fan_speed", 3)
        self.set_parameter("defrost", False)
        self.set_parameter("standby", False)
        self.set_parameter("vacation_hold", False)
        self.set_mode(emulator_config.STARTING_MODE)

    def get_parameter(self, key, default_val=None):
        """
        Get parameter from zone dictionary.

        inputs:
            key(str): target dict key
            default_val(str, int, float): default value on key errors
        """
        return_val = default_val
        try:
            return_val = self.zone_info[key]
        except KeyError:
            util.log_msg(traceback.format_exc(), mode=util.BOTH_LOG, func_name=1)
        return return_val

    def set_parameter(self, key, target_val=None):
        """
        Set parameter in zone dictionary.

        inputs:
            key(str): target dict key
            target_val(str, int, float): value to set
        """
        self.zone_info[key] = target_val

    def get_zone_name(self):
        """
        Return the name associated with the zone number.

        inputs:
            None
        returns:
            (str) zone name
        """
        self.refresh_zone_info()
        return "emulator_" + str(self.zone_name)

    def get_display_temp(self) -> float:  # used
        """
        Refresh the cached zone information and return Indoor Temp in °F
        with +/- 1 degree noise value.

        inputs:
            None
        returns:
            (float): indoor temp in °F.
        """
        # Check for deviation data first
        deviation_temp = self.get_deviation_value("display_temp")
        if deviation_temp is not None:
            return float(deviation_temp)

        # Normal behavior if no deviation data
        self.refresh_zone_info()
        return self.get_parameter("display_temp") + random.uniform(
            -emulator_config.NORMAL_TEMP_VARIATION,
            emulator_config.NORMAL_TEMP_VARIATION,
        )

    def get_display_humidity(self) -> Union[float, None]:
        """
        Refresh the cached zone information and return IndoorHumidity
        with random +/-1% noise value.

        inputs:
            None
        returns:
            (float, None): indoor humidity in %RH, None if not supported.
        """
        if not self.get_is_humidity_supported():
            return None

        # Check for deviation data first
        deviation_humidity = self.get_deviation_value("display_humidity")
        if deviation_humidity is not None:
            return float(deviation_humidity)

        # Normal behavior if no deviation data
        return self.get_parameter("display_humidity") + random.uniform(
            -emulator_config.NORMAL_HUMIDITY_VARIATION,
            emulator_config.NORMAL_HUMIDITY_VARIATION,
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
        return bool(self.get_parameter("humidity_support"))

    def set_mode(self, target_mode):
        """
        Set the thermostat mode.

        inputs:
            target_mode(str): target mode, refer to supported_configs["modes"]
        returns:
            True if successful, else False
        """
        if self.verbose:
            print(f"setting mode to {target_mode}")
        self.set_parameter(
            "switch_position",
            self.system_switch_position[getattr(tc.ThermostatCommonZone, target_mode)],
        )

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
        return int(
            self.get_system_switch_position()
            == self.system_switch_position[tc.ThermostatCommonZone.ECO_MODE]
        )

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
        return self.get_parameter("power_on")

    def is_fan_on(self):
        """Return 1 if fan relay is active, else 0."""
        self.refresh_zone_info()
        return self.get_parameter("fan_speed") > 0

    def is_defrosting(self):
        """Return 1 if defrosting is active, else 0."""
        self.refresh_zone_info()
        return int(self.get_parameter("defrost"))

    def is_standby(self):
        """Return 1 if standby is active, else 0."""
        self.refresh_zone_info()
        return int(self.get_parameter("standby"))

    def get_heat_setpoint_raw(self) -> float:  # used
        """
        Refresh the cached zone information and return the heat setpoint.

        inputs:
            None
        returns:
            (float): heating set point in °F.
        """
        # Check for deviation data first
        deviation_setpoint = self.get_deviation_value("heat_setpoint")
        if deviation_setpoint is not None:
            return float(deviation_setpoint)

        # Normal behavior if no deviation data
        self.refresh_zone_info()
        return float(self.get_parameter("heat_setpoint"))

    def get_heat_setpoint(self) -> str:
        """Return heat setpoint with units as a string."""
        return util.temp_value_with_units(self.get_heat_setpoint_raw())

    def get_schedule_heat_sp(self) -> float:  # used
        """
        Return the schedule heat setpoint.

        inputs:
            None
        returns:
            (int): scheduled heating set point in °F.
        """
        return float(emulator_config.MAX_HEAT_SETPOINT)  # max heat set point allowed

    def get_schedule_cool_sp(self) -> float:
        """
        Return the schedule cool setpoint.

        inputs:
            None
        returns:
            (float): scheduled cooling set point in °F.
        """
        return float(emulator_config.MIN_COOL_SETPOINT)  # min cool set point allowed

    def get_cool_setpoint_raw(self) -> float:
        """
        Return the cool setpoint.

        inputs:
            None
        returns:
            (float): cooling set point in °F.
        """
        # Check for deviation data first
        deviation_setpoint = self.get_deviation_value("cool_setpoint")
        if deviation_setpoint is not None:
            return float(deviation_setpoint)

        # Normal behavior if no deviation data
        self.refresh_zone_info()
        return float(self.get_parameter("cool_setpoint"))

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
        return bool(self.get_parameter("vacation_hold"))

    def get_vacation_hold(self) -> bool:
        """
        Return the
        VacationHold setting.

        inputs:
            None
        returns:
            (bool): True if vacation hold is set.
        """
        # TODO, are vacationhold unique fields?  what used for?
        return self.get_parameter("vacation_hold")

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
            return self.get_parameter("switch_position")

    def set_heat_setpoint(self, temp: int) -> None:
        """
        Set a new heat setpoint.

        inputs:
            temp(int): desired temperature in F
        returns:
            None
        """
        self.set_parameter("heat_setpoint", temp)

    def set_cool_setpoint(self, temp: int) -> None:
        """
        Set a new cool setpoint.

        inputs:
            temp(int): desired temperature in °F.
        returns:
            None
        """
        self.set_parameter("cool_setpoint", temp)

    def create_deviation_file(self) -> None:
        """
        Create an empty deviation file for this thermostat zone.

        inputs:
            None
        returns:
            None
        """
        deviation_data = {}
        with open(self.deviation_file_path, "wb") as handle:
            pickle.dump(deviation_data, handle)
        if self.verbose:
            util.log_msg(
                f"Created deviation file: {self.deviation_file_path}",
                mode=util.BOTH_LOG,
                func_name=1,
            )

    def set_deviation_value(self, key: str, value) -> None:
        """
        Set a deviation value for a specific parameter.

        inputs:
            key(str): parameter name (e.g., 'display_temp', 'display_humidity')
            value: deviation value to set
        returns:
            None
        """
        # Read existing deviation data or create empty dict
        deviation_data = {}
        if os.path.exists(self.deviation_file_path):
            try:
                with open(self.deviation_file_path, "rb") as handle:
                    deviation_data = pickle.load(handle)
            except (pickle.PickleError, EOFError):
                deviation_data = {}

        # Update the value
        deviation_data[key] = value

        # Write back to file
        with open(self.deviation_file_path, "wb") as handle:
            pickle.dump(deviation_data, handle)

        if self.verbose:
            util.log_msg(
                f"Set deviation value {key}={value} in {self.deviation_file_path}",
                mode=util.BOTH_LOG,
                func_name=1,
            )

    def get_deviation_value(self, key: str, default_val=None):
        """
        Get a deviation value for a specific parameter.

        inputs:
            key(str): parameter name
            default_val: default value if key not found or file doesn't exist
        returns:
            deviation value or default_val
        """
        if not os.path.exists(self.deviation_file_path):
            return default_val

        try:
            with open(self.deviation_file_path, "rb") as handle:
                deviation_data = pickle.load(handle)
                return deviation_data.get(key, default_val)
        except (pickle.PickleError, EOFError):
            return default_val

    def has_deviation_data(self, key: str = None) -> bool:
        """
        Check if deviation data exists.

        inputs:
            key(str): if provided, check for specific key,
                otherwise check if file exists
        returns:
            (bool): True if deviation data exists
        """
        if not os.path.exists(self.deviation_file_path):
            return False

        if key is None:
            return True

        try:
            with open(self.deviation_file_path, "rb") as handle:
                deviation_data = pickle.load(handle)
                return key in deviation_data
        except (pickle.PickleError, EOFError):
            return False

    def clear_deviation_data(self) -> None:
        """
        Clear all deviation data by removing the deviation file.

        inputs:
            None
        returns:
            None
        """
        if os.path.exists(self.deviation_file_path):
            os.remove(self.deviation_file_path)
            if self.verbose:
                util.log_msg(
                    f"Cleared deviation file: {self.deviation_file_path}",
                    mode=util.BOTH_LOG,
                    func_name=1,
                )

    def refresh_zone_info(self, force_refresh=False):
        """
        Refreshes the zone information if the current time exceeds the fetch interval
        or if the force_refresh flag is set to True.
        Args:
            force_refresh (bool): If True, forces the refresh of zone information
                                  regardless of the fetch interval. Default is False.
        """

        now_time = time.time()
        # refresh if past expiration date or force_refresh option
        if force_refresh or (
            now_time >= (self.last_fetch_time + self.fetch_interval_sec)
        ):
            # do nothing
            self.last_fetch_time = now_time


if __name__ == "__main__":
    # verify environment
    env.get_python_version()

    # get zone override
    api.uip = api.UserInputs(argv_list=None, thermostat_type=emulator_config.ALIAS)
    zone_number = api.uip.get_user_inputs(api.uip.zone_name, api.input_flds.zone)

    tc.thermostat_basic_checkout(
        emulator_config.ALIAS, zone_number, ThermostatClass, ThermostatZone
    )

    tc.print_select_data_from_all_zones(
        emulator_config.ALIAS,
        emulator_config.get_available_zones(),
        ThermostatClass,
        ThermostatZone,
        display_wifi=True,
        display_battery=True,
    )
