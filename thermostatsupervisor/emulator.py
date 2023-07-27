"""emulator integration"""
import random
import traceback

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

    def get_all_metadata(self, zone=None, debug=False):
        """Get all thermostat meta data for zone from kumocloud.

        inputs:
            zone(int): specified zone, if None will print all zones.
            debug(bool): if True will print unit details.
        returns:
            (dict): JSON dict
        """
        return self.get_metadata(zone, None, debug)

    def get_metadata(self, zone=None, parameter=None, debug=False):
        """Get all thermostat meta data for zone from emulator.

        inputs:
            zone(int): specified zone, if None will print all zones.
            parameter(str): target parameter, if None will return all.
            debug(bool): if True will print unit details.
        returns:
            (int, float, str, dict): depends on parameter
        """
        del debug  # unused
        if zone is None:
            # returned cached raw data for all zones
            meta_data_dict = self.meta_data_dict
        else:
            # return cached raw data for specified zone
            meta_data_dict = self.meta_data_dict[zone]
        if parameter is None:
            return meta_data_dict
        else:
            return meta_data_dict[parameter]

    def print_all_thermostat_metadata(self, zone, debug=False):
        """Print all metadata for zone to the screen.

        inputs:
            zone(int): specified zone, if None will print all zones.
            debug(bool): debug flag
        returns:
            None, prints result to screen
        """
        self.exec_print_all_thermostat_metadata(
            self.get_all_metadata, [zone, debug])


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
        self.poll_time_sec = 1 * 60  # default to 1 minutes
        self.connection_time_sec = 1 * 60 * 60  # default to 1 hours

        # switch config for this thermostat, numbers are unique and arbitrary
        self.system_switch_position[
            tc.ThermostatCommonZone.OFF_MODE] = 0
        self.system_switch_position[
            tc.ThermostatCommonZone.HEAT_MODE] = 1
        self.system_switch_position[
            tc.ThermostatCommonZone.COOL_MODE] = 2
        self.system_switch_position[
            tc.ThermostatCommonZone.DRY_MODE] = 3
        self.system_switch_position[
            tc.ThermostatCommonZone.AUTO_MODE] = 4
        self.system_switch_position[
            tc.ThermostatCommonZone.FAN_MODE] = 5

        # zone info
        self.verbose = verbose
        self.thermostat_type = emulator_config.ALIAS
        self.device_id = Thermostat_obj.device_id
        self.Thermostat = Thermostat_obj
        self.zone_name = Thermostat_obj.zone_name
        self.zone_info = Thermostat_obj.get_all_metadata(
            Thermostat_obj.zone_name)
        self.zone_name = self.get_zone_name()
        self.initialize_meta_data_dict()

    def initialize_meta_data_dict(self):
        """Initialize the meta data dict"""
        # add parameters and values
        self.set_heat_setpoint(emulator_config.STARTING_TEMP)
        self.set_cool_setpoint(emulator_config.STARTING_TEMP)
        self.set_parameter('display_temp', emulator_config.STARTING_TEMP)
        self.set_parameter('display_humidity',
                           emulator_config.STARTING_HUMIDITY)
        self.set_parameter('humidity_support', True)
        self.set_parameter('power_on', True)
        self.set_parameter('fan_on', True)
        self.set_parameter('fan_speed', 3)
        self.set_parameter('defrost', False)
        self.set_parameter('standby', False)
        self.set_parameter('vacation_hold', False)
        self.set_mode(emulator_config.STARTING_MODE)

    def get_parameter(self, key,
                      default_val=None):
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
            util.log_msg(traceback.format_exc(),
                         mode=util.BOTH_LOG, func_name=1)
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
        Refresh the cached zone information and return Indoor Temp in Deg F
        with +/- 1 degree noise value.

        inputs:
            None
        returns:
            (float): indoor temp in deg F.
        """
        self.refresh_zone_info()
        return (self.get_parameter('display_temp') +
                random.uniform(-emulator_config.NORMAL_TEMP_VARIATION,
                               emulator_config.NORMAL_TEMP_VARIATION))

    def get_display_humidity(self) -> (float, None):
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
        else:
            return (self.get_parameter('display_humidity') +
                    random.uniform(-emulator_config.NORMAL_HUMIDITY_VARIATION,
                                   emulator_config.NORMAL_HUMIDITY_VARIATION))

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
        return self.get_parameter('humidity_support')

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
        self.set_parameter('switch_position',
                           self.system_switch_position[
                               getattr(tc.ThermostatCommonZone, target_mode)])

    def is_heat_mode(self) -> int:
        """
        Refresh the cached zone information and return the heat mode.

        inputs:
            None
        returns:
            (int) heat mode, 1=enabled, 0=disabled.
        """
        return int(self.get_system_switch_position() ==
                   self.system_switch_position[
                       tc.ThermostatCommonZone.HEAT_MODE])

    def is_cool_mode(self) -> int:
        """
        Refresh the cached zone information and return the cool mode.

        inputs:
            None
        returns:
            (int): cool mode, 1=enabled, 0=disabled.
        """
        return int(self.get_system_switch_position() ==
                   self.system_switch_position[
                       tc.ThermostatCommonZone.COOL_MODE])

    def is_dry_mode(self) -> int:
        """
        Refresh the cached zone information and return the dry mode.

        inputs:
            None
        returns:
            (int): dry mode, 1=enabled, 0=disabled.
        """
        return int(self.get_system_switch_position() ==
                   self.system_switch_position[
                       tc.ThermostatCommonZone.DRY_MODE])

    def is_fan_mode(self) -> int:
        """
        Refresh the cached zone information and return the fan mode.

        inputs:
            None
        returns:
            (int): fan mode, 1=enabled, 0=disabled.
        """
        return int(self.get_system_switch_position() ==
                   self.system_switch_position[
                       tc.ThermostatCommonZone.FAN_MODE])

    def is_auto_mode(self) -> int:
        """
        Refresh the cached zone information and return the auto mode.

        inputs:
            None
        returns:
            (int): auto mode, 1=enabled, 0=disabled.
        """
        return int(self.get_system_switch_position() ==
                   self.system_switch_position[
                       tc.ThermostatCommonZone.AUTO_MODE])

    def is_off_mode(self) -> int:
        """
        Refresh the cached zone information and return the off mode.

        inputs:
            None
        returns:
            (int): off mode, 1=enabled, 0=disabled.
        """
        return int(self.get_system_switch_position() ==
                   self.system_switch_position[
                       tc.ThermostatCommonZone.OFF_MODE])

    def is_heating(self):
        """Return 1 if heating relay is active, else 0."""
        return int(self.is_heat_mode() and self.is_power_on() and
                   self.get_heat_setpoint_raw() > self.get_display_temp())

    def is_cooling(self):
        """Return 1 if cooling relay is active, else 0."""
        return int(self.is_cool_mode() and self.is_power_on() and
                   self.get_cool_setpoint_raw() < self.get_display_temp())

    def is_drying(self):
        """Return 1 if drying relay is active, else 0."""
        return int(self.is_dry_mode() and self.is_power_on() and
                   self.get_cool_setpoint_raw() < self.get_display_temp())

    def is_auto(self):
        """Return 1 if auto relay is active, else 0."""
        return int(self.is_auto_mode() and self.is_power_on() and
                   (self.get_cool_setpoint_raw() < self.get_display_temp() or
                    self.get_heat_setpoint_raw() > self.get_display_temp()))

    def is_fanning(self):
        """Return 1 if fan relay is active, else 0."""
        return int(self.is_fan_on() and self.is_power_on())

    def is_power_on(self):
        """Return 1 if power relay is active, else 0."""
        self.refresh_zone_info()
        return self.get_parameter('power_on')

    def is_fan_on(self):
        """Return 1 if fan relay is active, else 0."""
        self.refresh_zone_info()
        return self.get_parameter('fan_speed') > 0

    def is_defrosting(self):
        """Return 1 if defrosting is active, else 0."""
        self.refresh_zone_info()
        return int(self.get_parameter('defrost'))

    def is_standby(self):
        """Return 1 if standby is active, else 0."""
        self.refresh_zone_info()
        return int(self.get_parameter('standby'))

    def get_heat_setpoint_raw(self) -> int:  # used
        """
        Refresh the cached zone information and return the heat setpoint.

        inputs:
            None
        returns:
            (int): heating set point in degrees F.
        """
        self.refresh_zone_info()
        return self.get_parameter('heat_setpoint')

    def get_heat_setpoint(self) -> str:
        """Return heat setpoint with units as a string."""
        return util.temp_value_with_units(self.get_heat_setpoint_raw())

    def get_schedule_heat_sp(self) -> int:  # used
        """
        Return the schedule heat setpoint.

        inputs:
            None
        returns:
            (int): scheduled heating set point in degrees.
        """
        return emulator_config.MAX_HEAT_SETPOINT  # max heat set point allowed

    def get_schedule_cool_sp(self) -> int:
        """
        Return the schedule cool setpoint.

        inputs:
            None
        returns:
            (int): scheduled cooling set point in degrees F.
        """
        return emulator_config.MIN_COOL_SETPOINT  # min cool set point allowed

    def get_cool_setpoint_raw(self) -> int:
        """
        Return the cool setpoint.

        inputs:
            None
        returns:
            (int): cooling set point in degrees F.
        """
        self.refresh_zone_info()
        return self.get_parameter('cool_setpoint')

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
        return self.get_parameter('vacation_hold')

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
        return self.get_parameter('vacation_hold')

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
            return self.system_switch_position[
                tc.ThermostatCommonZone.OFF_MODE]
        else:
            return self.get_parameter('switch_position')

    def set_heat_setpoint(self, temp: int) -> None:
        """
        Set a new heat setpoint.

        inputs:
            temp(int): desired temperature in F
        returns:
            None
        """
        self.set_parameter('heat_setpoint', temp)

    def set_cool_setpoint(self, temp: int) -> None:
        """
        Set a new cool setpoint.

        inputs:
            temp(int): desired temperature in deg F.
        returns:
            None
        """
        self.set_parameter('cool_setpoint', temp)

    def refresh_zone_info(self, force_refresh=False):
        """
        Refresh zone info from KumoCloud.

        inputs:
            force_refresh(bool): if True, ignore expiration timer.
        returns:
            None, zone_data is refreshed.
        """
        del force_refresh
        # do nothing

    def report_heating_parameters(self, switch_position=None):
        """
        Display critical thermostat settings and reading to the screen.

        inputs:
            switch_position(int): switch position override, used for testing.
        returns:
            None
        """
        # current temp as measured by thermostat
        util.log_msg(f"display temp="
                     f"{util.temp_value_with_units(self.get_display_temp())}",
                     mode=util.BOTH_LOG,
                     func_name=1)

        # get switch position
        if switch_position is None:
            switch_position = self.get_system_switch_position()

        # heating status
        if switch_position == \
                self.system_switch_position[self.HEAT_MODE]:
            util.log_msg(f"heat mode={self.is_heat_mode()}",
                         mode=util.BOTH_LOG)
            util.log_msg(
                f"heat setpoint={self.get_heat_setpoint_raw()}",
                mode=util.BOTH_LOG)
            util.log_msg(
                f"schedule heat sp={self.get_schedule_heat_sp()}",
                mode=util.BOTH_LOG)

        # cooling status
        if switch_position == \
                self.system_switch_position[self.COOL_MODE]:
            util.log_msg(f"cool mode={self.is_cool_mode()}",
                         mode=util.BOTH_LOG)
            util.log_msg(
                f"cool setpoint={self.get_cool_setpoint_raw()}",
                mode=util.BOTH_LOG)
            util.log_msg(
                f"schedule cool sp={self.get_schedule_cool_sp()}",
                mode=util.BOTH_LOG)

        # hold settings
        util.log_msg(
            f"is in vacation hold mode={self.get_is_invacation_hold_mode()}",
            mode=util.BOTH_LOG)
        util.log_msg(f"vacation hold={self.get_vacation_hold()}",
                     mode=util.BOTH_LOG)
        util.log_msg(
            f"vacation hold until time={self.get_vacation_hold_until_time()}",
            mode=util.BOTH_LOG)
        util.log_msg(f"temporary hold until time="
                     f"{self.get_temporary_hold_until_time()}",
                     mode=util.BOTH_LOG)


if __name__ == "__main__":

    # verify environment
    env.get_python_version()

    # get zone override
    api.uip = api.UserInputs(argv_list=None,
                             thermostat_type=emulator_config.ALIAS)
    zone_number = api.uip.get_user_inputs(api.uip.zone_name,
                                          api.input_flds.zone)

    tc.thermostat_basic_checkout(
        emulator_config.ALIAS,
        zone_number,
        ThermostatClass, ThermostatZone)

    tc.thermostat_get_all_zone_temps(
        emulator_config.ALIAS,
        emulator_config.supported_configs["zones"],
        ThermostatClass,
        ThermostatZone)
