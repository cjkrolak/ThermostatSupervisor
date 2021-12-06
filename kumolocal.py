"""KumoCloud integration using local API for data."""
import os
import pprint
import pykumo
import time

# local imports
import kumolocal_config
import thermostat_api as api
import thermostat_common as tc
import utilities as util


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
        super(ThermostatClass, self).__init__(*self.args)
        self.thermostat_type = kumolocal_config.ALIAS

        # configure zone info
        self.zone_number = int(zone)
        self.zone_name = None  # initialize
        self.device_id = None  # initialize
        self.device_id = self.get_target_zone_id(self.zone_number)
        self.serial_number = None  # will be populated when unit is queried.

    def get_target_zone_id(self, zone_number=0):
        """
        Return the target zone ID.

        inputs:
            zone_number(int):  zone number.
        returns:
            (obj): PyKumo object
        """
        self.zone_name = kumolocal_config.kc_metadata[zone_number]["zone_name"]
        # populate the zone dictionary
        # establish local interface to kumos, must be on local net
        kumos = self.make_pykumos()
        device_id = kumos[self.zone_name]
        # print zone name the first time it is known
        if self.device_id is None:
            util.log_msg("zone %s name = '%s', device_id=%s" %
                         (zone_number, self.zone_name, device_id),
                         mode=util.DEBUG_LOG + util.CONSOLE_LOG,
                         func_name=1)
        self.device_id = device_id

        # return the target zone object
        return self.device_id

    def get_all_thermostat_metadata(self, zone=None):
        """Get all thermostat meta data for zone from kumocloud.

        inputs:
            zone(): specified zone, if None will print all zones.
        returns:
            (dict): JSON dict
        """
        try:
            units = list(self.get_indoor_units())  # will also query unit
        except UnboundLocalError:  # patch for issue #205
            util.log_msg("WARNING: Kumocloud refresh failed due to "
                         "timeout", mode=util.BOTH_LOG, func_name=1)
            time.sleep(10)
            units = list(self.get_indoor_units())  # retry
        util.log_msg("indoor unit serial numbers: %s" % str(units),
                     mode=util.DEBUG_LOG+util.CONSOLE_LOG, func_name=1)
        for serial_number in units:
            util.log_msg("Unit %s: address: %s credentials: %s" %
                         (self.get_name(serial_number),
                          self.get_address(serial_number),
                          self.get_credentials(serial_number)),
                         mode=util.DEBUG_LOG+util.CONSOLE_LOG, func_name=1)
        if zone is None:
            # returned cached raw data for all zones
            raw_json = self.get_raw_json()  # does not fetch results,
        else:
            # return cached raw data for specified zone
            self.serial_number = units[zone]
            raw_json = self.get_raw_json()[2]['children'][0][
                'zoneTable'][units[zone]]
        return raw_json

    def print_all_thermostat_metadata(self, zone=None):
        """Print all metadata for zone to the screen.

        inputs:
            zone(): specified zone, if None will print all zones.
        returns:
            None, prints result to screen
        """
        raw_json = self.get_all_thermostat_metadata(zone)
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(raw_json)


class ThermostatZone(tc.ThermostatCommonZone):
    """
    KumoCloud single zone on local network.

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
        self.system_switch_position[tc.ThermostatCommonZone.COOL_MODE] = "cool"
        self.system_switch_position[tc.ThermostatCommonZone.HEAT_MODE] = "heat"
        self.system_switch_position[tc.ThermostatCommonZone.OFF_MODE] = "off"
        self.system_switch_position[tc.ThermostatCommonZone.DRY_MODE] = "auto"
        self.system_switch_position[tc.ThermostatCommonZone.AUTO_MODE] = "dry"

        # zone info
        self.thermostat_type = kumolocal_config.ALIAS
        self.device_id = Thermostat_obj.device_id
        self.Thermostat = Thermostat_obj
        self.zone_number = Thermostat_obj.zone_number

        # runtime parameter defaults
        self.poll_time_sec = 10 * 60  # default to 10 minutes
        self.connection_time_sec = 8 * 60 * 60  # default to 8 hours

        # server data cache expiration parameters
        self.fetch_interval_sec = 10  # age of server data before refresh
        self.last_fetch_time = time.time() - 2 * self.fetch_interval_sec

    def get_display_temp(self) -> float:  # used
        """
        Refresh the cached zone information and return Indoor Temp in Deg F.

        inputs:
            None
        returns:
            (float): indoor temp in deg F.
        """
        self.refresh_zone_info()
        return util.c_to_f(self.device_id.get_current_temperature())

    def get_display_humidity(self) -> (float, None):
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

    def get_heat_mode(self) -> int:
        """
        Refresh the cached zone information and return the heat mode.

        inputs:
            None
        returns:
            (int) heat mode, 1=enabled, 0=disabled.
        """
        self.refresh_zone_info()
        return int(self.device_id.get_mode() ==
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
        return int(self.device_id.get_mode() ==
                   self.system_switch_position[
                       tc.ThermostatCommonZone.COOL_MODE])

    def get_dry_mode(self) -> int:
        """
        Refresh the cached zone information and return the dry mode.

        inputs:
            None
        returns:
            (int): dry mode, 1=enabled, 0=disabled.
        """
        self.refresh_zone_info()
        return int(self.device_id.get_mode() ==
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
        return util.c_to_f(self.device_id.get_heat_setpoint())

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

    def get_system_switch_position(self) -> str:  # used
        """
        Return the system switch position, same as mode.

        inputs:
            None
        returns:
            (str) current mode for unit, should match value
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
            temp(int): desired temperature in deg F.
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
            self.device_id = \
                self.Thermostat.get_target_zone_id(self.zone_number)

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

    tc.thermostat_basic_checkout(api, kumolocal_config.ALIAS,
                                 ThermostatClass,
                                 ThermostatZone)
