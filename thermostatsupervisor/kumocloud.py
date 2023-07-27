"""KumoCloud integration"""
import os
import time
import traceback

# local imports
from thermostatsupervisor import environment as env
from thermostatsupervisor import kumocloud_config
from thermostatsupervisor import thermostat_api as api
from thermostatsupervisor import thermostat_common as tc
from thermostatsupervisor import utilities as util

# pykumo import
PYKUMO_DEBUG = False  # debug uses local pykumo repo instead of pkg
if PYKUMO_DEBUG and not env.is_azure_environment():
    mod_path = "..\\pykumo\\pykumo"
    if env.is_interactive_environment():
        mod_path = "..\\" + mod_path
    pykumo = env.dynamic_module_import("pykumo",
                                       mod_path)
else:
    import pykumo  # noqa E402, from path / site packages


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
        self.KC_UNAME_KEY = 'KUMO_USERNAME'
        self.KC_PASSWORD_KEY = 'KUMO_PASSWORD'
        self.kc_uname = (os.environ.get(self.KC_UNAME_KEY, "<" +
                         self.KC_UNAME_KEY + "_KEY_MISSING>"))
        self.kc_pwd = (os.environ.get(
            self.KC_PASSWORD_KEY, "<" +
            self.KC_PASSWORD_KEY + "_KEY_MISSING>"))

        # construct the superclass
        # call both parent class __init__
        self._need_fetch = True  # force data fetch
        self.args = [self.kc_uname, self.kc_pwd]
        pykumo.KumoCloudAccount.__init__(self, *self.args)
        tc.ThermostatCommon.__init__(self)

        # set tstat type and debug flag
        self.thermostat_type = kumocloud_config.ALIAS
        self.verbose = verbose

        # configure zone info
        self.zone_number = int(zone)
        self.zone_name = kumocloud_config.metadata[self.zone_number][
            "zone_name"]
        self.device_id = self.get_target_zone_id(self.zone_name)
        self.serial_number = None  # will be populated when unit is queried.
        self.zone_info = None

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
            zone_index = [i for i in kumocloud_config.metadata if
                          kumocloud_config.metadata[i][
                              "zone_name"] == self.zone_name][0]
        except IndexError:
            print(f"ERROR: zone_name={self.zone_name} not present in meta data"
                  f" dict, valid values are {kumocloud_config.metadata.keys()}")
            raise
        return zone_index

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
        """Get all thermostat meta data for zone from kumocloud.

        inputs:
            zone(int): specified zone, if None will print all zones.
            parameter(str): target parameter, if None will return all.
            debug(bool): if True will print unit details.
        returns:
            (int, float, str, dict): depends on parameter
        """
        try:
            serial_num_lst = list(self.get_indoor_units())  # will query unit
        except UnboundLocalError:  # patch for issue #205
            util.log_msg("WARNING: Kumocloud refresh failed due to "
                         "timeout", mode=util.BOTH_LOG, func_name=1)
            time.sleep(30)
            serial_num_lst = list(self.get_indoor_units())  # retry
        if debug:
            util.log_msg(f"indoor unit serial numbers: {str(serial_num_lst)}",
                         mode=util.DEBUG_LOG + util.CONSOLE_LOG, func_name=1)
        for idx, serial_number in enumerate(serial_num_lst):
            if debug:
                util.log_msg(f"Unit {self.get_name(serial_number)}: address: "
                             f"{self.get_address(serial_number)} credentials: "
                             f"{self.get_credentials(serial_number)}",
                             mode=util.DEBUG_LOG +
                             util.CONSOLE_LOG,
                             func_name=1)
            # populate meta data dict
            if debug:
                print(f"zone index={idx}, serial_number={serial_number}")
            kumocloud_config.metadata[idx]["serial_number"] = serial_number

        # raw_json list:
        # [0]: token, username, device fields
        # [1]: lastupdate date
        # [2]: zone meta data
        # [3]: device token
        if zone is None:
            # returned cached raw data for all zones
            raw_json = self.get_raw_json()[2]  # does not fetch results,
        else:
            # if zone name input, find zone index
            if not isinstance(zone, int):
                zone = self.get_zone_index_from_name()
            # return cached raw data for specified zone, will be a dict
            self.serial_number = serial_num_lst[zone]
            raw_json = self.get_raw_json()[2]['children'][0][
                'zoneTable'][serial_num_lst[zone]]

        if parameter is None:
            return raw_json
        else:
            return raw_json[parameter]

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
        self.poll_time_sec = 10 * 60  # default to 10 minutes
        self.connection_time_sec = 8 * 60 * 60  # default to 8 hours

        # server data cache expiration parameters
        self.fetch_interval_sec = 10  # age of server data before refresh
        self.last_fetch_time = time.time() - 2 * self.fetch_interval_sec

        # switch config for this thermostat
        self.system_switch_position[
            tc.ThermostatCommonZone.HEAT_MODE] = 1  # "Heat" 0 0001
        self.system_switch_position[
            tc.ThermostatCommonZone.OFF_MODE] = 16  # "Off"  1 0000
        self.system_switch_position[
            tc.ThermostatCommonZone.FAN_MODE] = 7  # "Fan"   0 0111
        self.system_switch_position[
            tc.ThermostatCommonZone.DRY_MODE] = 2  # dry     0 0010
        self.system_switch_position[
            tc.ThermostatCommonZone.COOL_MODE] = 3  # cool   0 0011
        self.system_switch_position[
            tc.ThermostatCommonZone.AUTO_MODE] = 33  # auto   0 0101

        # zone info
        self.verbose = verbose
        self.thermostat_type = kumocloud_config.ALIAS
        self.device_id = Thermostat_obj.device_id
        self.Thermostat = Thermostat_obj
        self.zone_info = Thermostat_obj.get_all_metadata(
            Thermostat_obj.zone_number)
        self.zone_number = Thermostat_obj.zone_number
        self.zone_name = self.get_zone_name()  # get real zone name from device

    def get_parameter(self, key, parent_key=None, grandparent_key=None,
                      default_val=None):
        """
        Get parameter from zone dictionary.

        inputs:
            key(str): target dict key
            parent_key(str): first level dict key
            grandparent_key(str): second level dict key
            default_val(str, int, float): default value on key errors
        """
        return_val = default_val
        if grandparent_key is not None:
            try:
                # check parent keys
                grandparent_dict = self.zone_info[grandparent_key]
                parent_dict = grandparent_dict[parent_key]
                return_val = parent_dict[key]
            except KeyError:
                if default_val is None:
                    # if no default val, then display detailed key error
                    util.log_msg(traceback.format_exc(),
                                 mode=util.BOTH_LOG, func_name=1)
                    util.log_msg(f"raw zone_info dict={self.zone_info}",
                                 mode=util.BOTH_LOG, func_name=1)
                    raise
        elif parent_key is not None:
            try:
                parent_dict = self.zone_info[parent_key]
                return_val = parent_dict[key]
            except KeyError:
                if default_val is None:
                    # if no default val, then display detailed key error
                    util.log_msg(traceback.format_exc(),
                                 mode=util.BOTH_LOG, func_name=1)
                    util.log_msg(f"raw zone_info dict={self.zone_info}",
                                 mode=util.BOTH_LOG, func_name=1)
                    raise
        else:
            try:
                return_val = self.zone_info[key]
            except (KeyError, TypeError):
                if default_val is None:
                    # if no default val, then display detailed key error
                    util.log_msg(traceback.format_exc(),
                                 mode=util.BOTH_LOG, func_name=1)
                    util.log_msg(f"target key={key}, "
                                 f"raw zone_info dict={self.zone_info}",
                                 mode=util.BOTH_LOG, func_name=1)
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
        zone_name = self.get_parameter('label')
        # update metadata dict.
        kumocloud_config.metadata[self.zone_number]["zone_name"] = zone_name
        return zone_name

    def get_display_temp(self) -> float:  # used
        """
        Refresh the cached zone information and return Indoor Temp in Deg F.

        inputs:
            None
        returns:
            (float): indoor temp in deg F.
        """
        self.refresh_zone_info()
        return util.c_to_f(self.get_parameter('room_temp',
                                              'reportedCondition',
                                              default_val=util.BOGUS_INT))

    def get_display_humidity(self) -> (float, None):
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
            return util.c_to_f(self.get_parameter('humidity',
                                                  'reportedCondition',
                                                  default_val=util.BOGUS_INT))

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
        return self.get_parameter('humidistat', 'inputs',
                                  'acoilSettings')

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
        return self.get_parameter('power', 'reportedCondition', default_val=0)

    def is_fan_on(self):
        """Return 1 if fan relay is active, else 0."""
        if self.is_power_on():
            fan_speed = self.get_parameter('fan_speed', 'reportedCondition')
            if fan_speed is None:
                return 0  # no fan_speed key, return 0
            else:
                return int(fan_speed > 0 or
                           self.get_parameter('fan_speed_text', 'more',
                                              'reportedCondition') != 'off')
        else:
            return 0

    def is_defrosting(self):
        """Return 1 if defrosting is active, else 0."""
        self.refresh_zone_info()
        return int(self.get_parameter('defrost', 'status_display',
                                      'reportedCondition'))

    def is_standby(self):
        """Return 1 if standby is active, else 0."""
        self.refresh_zone_info()
        return int(self.get_parameter('standby', 'status_display',
                                      'reportedCondition'))

    def get_heat_setpoint_raw(self) -> int:  # used
        """
        Refresh the cached zone information and return the heat setpoint.

        inputs:
            None
        returns:
            (int): heating set point in degrees F.
        """
        self.refresh_zone_info()
        # if power is off then sp_heat may be missing
        return util.c_to_f(self.get_parameter('sp_heat',
                                              'reportedCondition',
                                              default_val=-1))

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
        return kumocloud_config.MAX_HEAT_SETPOINT  # max heat set point allowed

    def get_schedule_cool_sp(self) -> int:
        """
        Return the schedule cool setpoint.

        inputs:
            None
        returns:
            (int): scheduled cooling set point in degrees F.
        """
        return kumocloud_config.MIN_COOL_SETPOINT  # min cool set point allowed

    def get_cool_setpoint_raw(self) -> int:
        """
        Return the cool setpoint.

        inputs:
            None
        returns:
            (int): cooling set point in degrees F.
        """
        self.refresh_zone_info()
        # if power is off then sp_heat may be missing
        return util.c_to_f(self.get_parameter('sp_cool',
                                              'reportedCondition',
                                              default_val=-1))

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
            return self.system_switch_position[
                tc.ThermostatCommonZone.OFF_MODE]
        else:
            return self.get_parameter('operation_mode',
                                      'reportedCondition')

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
        util.log_msg("WARNING: this method not implemented yet for this "
                     "thermostat type",
                     mode=util.BOTH_LOG, func_name=1)

    def set_cool_setpoint(self, temp: int) -> None:
        """
        Set a new cool setpoint.

        This will also attempt to turn the thermostat to 'Cool'
        inputs:
            temp(int): desired temperature in deg F.
        returns:
            None
        """
        # self.device_id.set_cool_setpoint(self._f_to_c(temp))
        # TODO needs implementation
        del temp
        util.log_msg("WARNING: this method not implemented yet for this "
                     "thermostat type",
                     mode=util.BOTH_LOG, func_name=1)

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
        if (force_refresh or (now_time >=
                              (self.last_fetch_time +
                               self.fetch_interval_sec))):
            self.Thermostat._need_fetch = True \
                # pylint: disable=protected-access
            try:
                self.Thermostat._fetch_if_needed() \
                    # pylint: disable=protected-access
            except UnboundLocalError:  # patch for issue #205
                util.log_msg("WARNING: Kumocloud refresh failed due to "
                             "timeout", mode=util.BOTH_LOG, func_name=1)
            self.last_fetch_time = now_time
            # refresh device object
            self.zone_info = self.Thermostat.get_all_metadata(
                self.zone_number)

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
                             thermostat_type=kumocloud_config.ALIAS)
    zone_number = api.uip.get_user_inputs(api.uip.zone_name,
                                          api.input_flds.zone)

    tc.thermostat_basic_checkout(
        kumocloud_config.ALIAS,
        zone_number,
        ThermostatClass, ThermostatZone)

    tc.thermostat_get_all_zone_temps(
        kumocloud_config.ALIAS,
        kumocloud_config.supported_configs["zones"],
        ThermostatClass,
        ThermostatZone)
