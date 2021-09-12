"""KumoCloud integration"""
import os
import pprint
import pykumo
import time

# local imports
import thermostat_api as api
import thermostat_common as tc
import utilities as util

# 3m50 thermostat IP addresses (local net)
MAIN_KUMO = 0  # zone 0
BASEMENT_KUMO = 1  # zone 1
kc_metadata = {
    MAIN_KUMO: {"ip_address": "192.168.86.82",  # local IP
                "device_id": None,  # placeholder
                "zone_object": None,
                "zone_name": None},
    BASEMENT_KUMO: {"ip_address": "192.168.86.83",  # local IP
                    "device_id": None,  # placeholder
                    "zone_object": None,
                    "zone_name": None},
}


class KumoCloud(pykumo.KumoCloudAccount):
    """KumoCloud thermostat functions."""

    def __init__(self, zone, *_, **__):
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
        super(KumoCloud, self).__init__(*self.args)
        self.thermostat_type = api.KUMOCLOUD

        # configure zone info
        self.zone_number = int(zone)
        self.device_id = None  # initialize
        self.device_id = self.get_target_zone_id()
        self.zone_constructor = KumoZone

    def get_target_zone_id(self, zone_number=0):
        """
        Return the target zone ID.

        inputs:
            zone_number(int):  zone number.
        returns:
            (int): zone device id number
        """
        # populate the zone dictionary
        kumos = self.make_pykumos()
        zone_number = 0
        for zone_name in kumos:
            kc_metadata[zone_number]["device_id"] = kumos[zone_name]
            kc_metadata[zone_number]["zone_name"] = zone_name
            if zone_number == self.zone_number:
                target_zone_name = zone_name
                # print zone name the first time it is known
                if self.device_id is None:
                    util.log_msg("zone %s name = '%s'" %
                                 (zone_number, zone_name),
                                 mode=util.DEBUG_LOG + util.CONSOLE_LOG,
                                 func_name=1)
            zone_number += 1

        # return the target zone object
        return kumos[target_zone_name]

    def print_all_thermostat_metadata(self):
        """Print all metadata to the screen."""
        units = Thermostat.get_indoor_units()  # will also query unit
        print("Units: %s" % str(units))
        for unit in units:
            print("Unit %s: address: %s credentials: %s" %
                  (Thermostat.get_name(unit), Thermostat.get_address(unit),
                   Thermostat.get_credentials(unit)))
        raw_json = Thermostat.get_raw_json()  # does not fetch results,
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(raw_json)


class KumoZone(tc.ThermostatCommonZone):
    """
    KumoCloud single zone.

    Class needs to be updated for multi-zone support.
    """

    system_switch_position = {
        tc.ThermostatCommonZone.COOL_MODE: "cool",
        tc.ThermostatCommonZone.HEAT_MODE: "heat",
        tc.ThermostatCommonZone.OFF_MODE: "off",
        tc.ThermostatCommonZone.AUTO_MODE: "auto",
        tc.ThermostatCommonZone.DRY_MODE: "dry",
        tc.ThermostatCommonZone.UNKNOWN_MODE: -1,
        }

    def __init__(self, device_id, Tstat, *_, **__):
        """
        Zone constructor.

        inputs:
            device_id(int):  Honeywell device_id on the account,
                             this is the same as the zone number.
            Thermostat(obj): Thermostat object.
        """
        # construct the superclass, requires auth setup first
        super(KumoZone, self).__init__(*_, **__)

        # zone info
        self.thermostat_type = api.KUMOCLOUD
        self.device_id = device_id
        self.Thermostat = Tstat
        self.zone_number = self.get_target_zone_number(device_id)

        # runtime parameter defaults
        self.poll_time_sec = 10 * 60  # default to 10 minutes
        self.connection_time_sec = 8 * 60 * 60  # default to 8 hours

        # server data cache experation parameters
        self.fetch_interval_sec = 10  # age of server data before refresh
        self.last_fetch_time = time.time() - 2 * self.fetch_interval_sec

    def get_target_zone_number(self, device_id):
        """
        Return the target zone number based on the device_id.

        inputs:
            device_id(obj): 3m50 device id object.
        returns:
            (int):  zone number.
        """
        zone_number = -1
        for zone in kc_metadata:
            print("key=%s" % zone)
            if kc_metadata[zone]["device_id"] == device_id:
                zone_number = zone
                break
        return zone_number

    def _c_to_f(self, tempc) -> float:
        """
        Convert from Celsius to Fahrenheit.

        inputs:
            tempc(int, float): temp in deg c.
        returns:
            (float): temp in deg f.
        """
        if isinstance(tempc, (int, float)):
            return tempc * 9.0 / 5 + 32
        else:
            return tempc  # pass-thru

    def _f_to_c(self, tempf) -> float:
        """
        Convert from Fahrenheit to Celsius.

        inputs:
            tempc(int, float): temp in deg f.
        returns:
            (float): temp in deg c.
        """
        if isinstance(tempf, (int, float)):
            return (tempf - 32) * 5 / 9.0
        else:
            return tempf  # pass-thru

    def get_display_temp(self) -> float:  # used
        """
        Refresh the cached zone information and return Indoor Temp in Deg F.

        inputs:
            None
        returns:
            (float): indoor temp in deg F.
        """
        self.refresh_zone_info()
        return self._c_to_f(self.device_id.get_current_temperature())

    def get_display_humidity(self) -> float:
        """
        Refresh the cached zone information and return IndoorHumidity.

        inputs:
            None
        returns:
            (float): indoor humidity in %RH.
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
                   tc.ThermostatCommonZone.HEAT_MODE)

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
                   tc.ThermostatCommonZone.COOL_MODE)

    def get_dry_mode(self) -> int:
        """
        Refresh the cached zone information and return the dry mode.

        inputs:
            None
        returns:
            (int): cool mode, 1=enabled, 0=disabled.
        """
        self.refresh_zone_info()
        return int(self.device_id.get_mode() ==
                   tc.ThermostatCommonZone.DRY_MODE)

    def get_heat_setpoint_raw(self) -> int:  # used
        """
        Refresh the cached zone information and return the heat setpoint.

        inputs:
            None
        returns:
            (int): heating set point in degrees F.
        """
        self.refresh_zone_info()
        return self._c_to_f(self.device_id.get_heat_setpoint())

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
        return self._c_to_f(self.device_id.get_cool_setpoint())

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
            None
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
        self.device_id.set_heat_setpoint(self._f_to_c(temp))

    def set_cool_setpoint(self, temp: int) -> None:
        """
        Set a new cool setpoint.

        This will also attempt to turn the thermostat to 'Cool'
        inputs:
            temp(int): desired temperature in deg F.
        returns:
            None
        """
        self.device_id.set_cool_setpoint(self._f_to_c(temp))

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
            self.Thermostat._fetch_if_needed() \
                # pylint: disable=protected-access
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

    util.log_msg.debug = True  # debug mode set

    # get zone from user input
    zone_input = api.parse_all_runtime_parameters()[1]

    # verify required env vars
    api.verify_required_env_variables(api.KUMOCLOUD, zone_input)

    Thermostat = KumoCloud(zone_input)
    Thermostat.print_all_thermostat_metadata()
    Zone = KumoZone(Thermostat.device_id, Thermostat)

    print("current thermostat settings...")
    print("tmode1: %s" % Zone.get_system_switch_position())
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
