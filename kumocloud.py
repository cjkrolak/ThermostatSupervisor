"""KumoCloud integration"""
import os
import pprint
import pykumo
import time

# local imports
import thermostat_api as api
import thermostat_common as tc
import utilities as util

# Kumocloud zone configuration (on local net)
MAIN_KUMO = 0  # zone 0
BASEMENT_KUMO = 1  # zone 1
kc_metadata = {
    MAIN_KUMO: {"ip_address": "192.168.86.229",  # local IP, for ref only.
                "zone_name": "Main Level",  # customize for your site.
                },
    BASEMENT_KUMO: {"ip_address": "192.168.86.236",  # local IP, for ref only.
                    "zone_name": "Basement",  # customize for your site.
                    },
}


class ThermostatClass(pykumo.KumoCloudAccount):
    """KumoCloud thermostat functions."""

    def __init__(self, zone):
        """
        Constructor, connect to thermostat.

        inputs:
            zone(str):  zone of thermostat.
        """
        # Kumocloud server auth credentials from env vars
        self.KC_UNAME_KEY = 'KUMO_USERNAME'
        self.KC_PASSWORD_KEY = 'KUMO_PASSWORD'
        self.kc_uname = (os.environ.get(self.KC_UNAME_KEY, "<" +
                         self.KC_UNAME_KEY + "_KEY_MISSING>"))
        self.kc_pwd = (os.environ.get(
            self.KC_PASSWORD_KEY, "<" +
            self.KC_PASSWORD_KEY + "_KEY_MISSING>"))
        self.args = [self.kc_uname, self.kc_pwd]

        # construct the superclass
        self._need_fetch = True  # force data fetch
        super(ThermostatClass, self).__init__(*self.args)
        self.thermostat_type = api.KUMOCLOUD

        # configure zone info
        self.zone_number = int(zone)
        self.zone_name = None  # initialize
        self.device_id = self.get_target_zone_id(self.zone_number)
        self.serial_number = None  # will be populated when unit is queried.

    def get_target_zone_id(self, zone_number=0):
        """
        Return the target zone ID.

        inputs:
            zone_number(int):  zone number.
        returns:
            (int): device_id
        """
        return zone_number

    def get_all_thermostat_metadata(self, zone=None, debug=False):
        """Get all thermostat meta data for zone from kumocloud.

        inputs:
            zone(int): specified zone, if None will print all zones.
            debug(bool): if True will print unit details.
        returns:
            (dict): JSON dict
        """
        units = list(self.get_indoor_units())  # will also query unit
        if debug:
            print("indoor unit serial numbers: %s" % str(units))
        for serial_number in units:
            if debug:
                print("Unit %s: address: %s credentials: %s" %
                      (self.get_name(serial_number),
                       self.get_address(serial_number),
                       self.get_credentials(serial_number)))
        if zone is None:
            # returned cached raw data for all zones
            raw_json = self.get_raw_json()  # does not fetch results,
        else:
            # return cached raw data for specified zone
            self.serial_number = units[zone]
            raw_json = self.get_raw_json()[2]['children'][0][
                'zoneTable'][units[zone]]
        return raw_json

    def print_all_thermostat_metadata(self, zone=None, debug=False):
        """Print all metadata for zone to the screen.

        inputs:
            zone(int): specified zone, if None will print all zones.
            debug(bool): debug flag
        returns:
            None, prints result to screen
        """
        raw_json = self.get_all_thermostat_metadata(zone, debug=debug)
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(raw_json)


class ThermostatZone(tc.ThermostatCommonZone):
    """
    KumoCloud single zone from kumocloud.

    Class needs to be updated for multi-zone support.
    """

    def __init__(self, Thermostat_obj):
        """
        Zone constructor.

        inputs:
            Thermostat(obj): Thermostat class instance.
        """
        # construct the superclass, requires auth setup first
        super(ThermostatZone, self).__init__()

        # switch config for this thermostat
        self.system_switch_position[
            tc.ThermostatCommonZone.HEAT_MODE] = 1  # "Heat"
        self.system_switch_position[
            tc.ThermostatCommonZone.OFF_MODE] = 16  # "Off"
        # TODO - these modes need verification
        self.system_switch_position[tc.ThermostatCommonZone.COOL_MODE] = "Cool"
        self.system_switch_position[tc.ThermostatCommonZone.DRY_MODE] = "Auto"
        self.system_switch_position[tc.ThermostatCommonZone.AUTO_MODE] = "Dry"

        # zone info
        self.thermostat_type = api.KUMOCLOUD
        self.device_id = Thermostat_obj.device_id
        self.Thermostat = Thermostat_obj
        self.zone_number = Thermostat_obj.zone_number
        self.zone_data = Thermostat_obj.get_all_thermostat_metadata(
            Thermostat_obj.zone_number)

        # runtime parameter defaults
        self.poll_time_sec = 10 * 60  # default to 10 minutes
        self.connection_time_sec = 8 * 60 * 60  # default to 8 hours

        # server data cache expiration parameters
        self.fetch_interval_sec = 10  # age of server data before refresh
        self.last_fetch_time = time.time() - 2 * self.fetch_interval_sec

    def get_parameter(self, key, parent_key=None, grandparent_key=None,
                      default_val=None):
        """
        Get parameter from zone dictionary.

        inputs:
            target_key(str): target dict key
            parent_key(str): first level dict key
            grandparent_key(str): second level dict key
            default_val(str, int, float): default value on key errors
        """
        return_val = default_val
        if grandparent_key is not None:
            try:
                # check parent keys
                grandparent_dict = self.zone_data[grandparent_key]
                parent_dict = grandparent_dict[parent_key]
                return_val = parent_dict[key]
            except KeyError as e:
                raise e
        elif parent_key is not None:
            try:
                parent_dict = self.zone_data[parent_key]
                return_val = parent_dict[key]
            except KeyError as e:
                raise e
        else:
            try:
                return_val = self.zone_data[key]
            except KeyError as e:
                raise e
        return return_val

    def get_display_temp(self) -> float:  # used
        """
        Refresh the cached zone information and return Indoor Temp in Deg F.

        inputs:
            None
        returns:
            (float): indoor temp in deg F.
        """
        self.refresh_zone_info()
        return self._c_to_f(self.get_parameter('room_temp',
                                               'reportedCondition'))

    def get_display_humidity(self) -> (float, None):
        """
        Refresh the cached zone information and return IndoorHumidity.

        inputs:
            None
        returns:
            (float, None): indoor humidity in %RH, None if not supported.
        """
        self.refresh_zone_info()
        if not self.get_is_humidity_supported():
            return None
        else:
            # untested, don't have humidity support
            return self._c_to_f(self.get_parameter('humidity',
                                                   'reportedCondition'))

    def get_is_humidity_supported(self) -> bool:  # used
        """
        Refresh the cached zone information and return the
          True if humidity sensor data is trustworthy.

        inputs:
            None
        returns:
            (booL): True if is in humidity sensor is available and not faulted.
        """
        return self.get_parameter('humidistat', 'inputs',
                                  'acoilSettings')

    def get_heat_mode(self) -> int:
        """
        Refresh the cached zone information and return the heat mode.

        inputs:
            None
        returns:
            (int) heat mode, 1=enabled, 0=disabled.
        """
        self.refresh_zone_info()
        return int(self.get_system_switch_position() ==
                   self.system_switch_position[
                       tc.ThermostatCommonZone.HEAT_MODE])

    def get_cool_mode(self) -> int:
        """
        Refresh the cached zone information and return the cool mode.

        inputs:
            None
        returns:
            (int): cool mode, 1=enabled, 0=disabled.
        """
        self.refresh_zone_info()
        return int(self.get_system_switch_position() ==
                   self.system_switch_position[
                       tc.ThermostatCommonZone.COOL_MODE])

    def get_dry_mode(self) -> int:
        """
        Refresh the cached zone information and return the dry mode.

        inputs:
            None
        returns:
            (int): cool mode, 1=enabled, 0=disabled.
        """
        self.refresh_zone_info()
        return int(self.get_system_switch_position() ==
                   self.system_switch_position[
                       tc.ThermostatCommonZone.DRY_MODE])

    def get_heat_setpoint_raw(self) -> int:  # used
        """
        Refresh the cached zone information and return the heat setpoint.

        inputs:
            None
        returns:
            (int): heating set point in degrees F.
        """
        self.refresh_zone_info()
        return self._c_to_f(self.get_parameter('sp_heat',
                                               'reportedCondition'))

    def get_schedule_heat_sp(self) -> int:  # used
        """
        Return the schedule heat setpoint.

        inputs:
            None
        returns:
            (int): scheduled heating set point in degrees.
        """
        return 72  # max heat set point allowed

    def get_schedule_cool_sp(self) -> int:
        """
        Return the schedule cool setpoint.

        inputs:
            None
        returns:
            (int): scheduled cooling set point in degrees F.
        """
        return 70  # min cool set point allowed

    def get_cool_setpoint_raw(self) -> int:
        """
        Return the cool setpoint.

        inputs:
            None
        returns:
            (int): cooling set point in degrees F.
        """
        self.refresh_zone_info()
        return self._c_to_f(self.get_parameter('sp_cool',
                                               'reportedCondition'))

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

    def get_system_switch_position(self) -> str:  # used
        """
        Return the system switch position.

        inputs:
            None
        returns:
            (str) current mode for unit, should match value
                  in self.system_switch_position
        """
        self.refresh_zone_info()
        # return self.get_parameter('operation_mode_text', 'more',
        #                           'reportedCondition')
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
        print("WARNING %s not implemented yet for this thermostat type" %
              util.get_function_name())
        return

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
        print("WARNING %s not implemented yet for this thermostat type" %
              util.get_function_name())
        return

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
            print("DEBUG: refreshing data from cloud")
            self.Thermostat._need_fetch = True \
                # pylint: disable=protected-access
            self.Thermostat._fetch_if_needed() \
                # pylint: disable=protected-access
            self.last_fetch_time = now_time
            # refresh device object
            self.zone_data = self.Thermostat.get_all_thermostat_metadata(
                self.zone_number)

    def report_heating_parameters(self):
        """
        Display critical thermostat settings and reading to the screen.

        inputs:
            None
        returns:
            None
        """
        # current temp as measured by thermostat
        util.log_msg("display temp=%s" % self.get_display_temp(),
                     mode=util.BOTH_LOG, func_name=1)

        # heating status
        if self.get_system_switch_position() == \
                self.system_switch_position[self.HEAT_MODE]:
            util.log_msg("heat mode=%s" % self.get_heat_mode(),
                         mode=util.BOTH_LOG)
            util.log_msg("heat setpoint=%s" %
                         self.get_heat_setpoint_raw(), mode=util.BOTH_LOG)
            util.log_msg("schedule heat sp=%s" %
                         self.get_schedule_heat_sp(), mode=util.BOTH_LOG)
            util.log_msg("\n", mode=util.BOTH_LOG)

        # cooling status
        if self.get_system_switch_position() == \
                self.system_switch_position[self.COOL_MODE]:
            util.log_msg("cool mode=%s" % self.get_cool_mode(),
                         mode=util.BOTH_LOG)
            util.log_msg("cool setpoint=%s" %
                         self.get_cool_setpoint_raw(), mode=util.BOTH_LOG)
            util.log_msg("schedule cool sp=%s" %
                         self.get_schedule_cool_sp(), mode=util.BOTH_LOG)
            util.log_msg("\n", mode=util.BOTH_LOG)

        # hold settings
        util.log_msg("is in vacation hold mode=%s" %
                     self.get_is_invacation_hold_mode(), mode=util.BOTH_LOG)
        util.log_msg("vacation hold=%s" % self.get_vacation_hold(),
                     mode=util.BOTH_LOG)
        util.log_msg("vacation hold until time=%s" %
                     self.get_vacation_hold_until_time(), mode=util.BOTH_LOG)
        util.log_msg("temporary hold until time=%s" %
                     self.get_temporary_hold_until_time(), mode=util.BOTH_LOG)


if __name__ == "__main__":

    util.log_msg.debug = True  # debug mode set

    # get zone from user input
    zone_input = api.parse_all_runtime_parameters()[1]

    # verify required env vars
    api.verify_required_env_variables(api.KUMOCLOUD, zone_input)

    # import hardware module
    mod = api.load_hardware_library(api.KUMOCLOUD)

    # create Thermostat object
    Thermostat = ThermostatClass(zone_input)
    Thermostat.print_all_thermostat_metadata(Thermostat.zone_number)

    # create Zone object
    Zone = ThermostatZone(Thermostat)

    # update runtime overrides
    Zone.update_runtime_parameters(api.user_inputs)

    print("current thermostat settings...")
    print("system switch position: %s" % Zone.get_system_switch_position())
    print("current temp: %s" % Zone.get_display_temp())
    print("current humidity: %s" % Zone.get_display_humidity())
    print("heat set point=%s" % Zone.get_heat_setpoint_raw())
    print("cool set point=%s" % Zone.get_cool_setpoint_raw())
    print("heat schedule set point=%s" % Zone.get_schedule_heat_sp())
    print("cool schedule set point=%s" % Zone.get_schedule_cool_sp())
    print("(schedule) heat program=%s" % Zone.get_schedule_program_heat())
    print("(schedule) cool program=%s" % Zone.get_schedule_program_cool())
    print("hold=%s" % Zone.get_vacation_hold())
    print("heat mode=%s" % Zone.get_heat_mode())
    print("cool mode=%s" % Zone.get_cool_mode())
    print("dry mode=%s" % Zone.get_dry_mode())
    print("temporary hold minutes=%s" % Zone.get_temporary_hold_until_time())
