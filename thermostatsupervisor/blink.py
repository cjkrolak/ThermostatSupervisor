"""Blink Camera."""
import os
import time

# local imports
from thermostatsupervisor import blink_config
from thermostatsupervisor import thermostat_api as api
from thermostatsupervisor import thermostat_common as tc
from thermostatsupervisor import environment as env
from thermostatsupervisor import utilities as util

# Blink library
BLINK_DEBUG = False  # debug uses local blink repo instead of pkg
if BLINK_DEBUG and not env.is_azure_environment():
    blinkpy = env.dynamic_module_import("blinkpy",
                                        "..\\..\\pykumo\\pykumo")
else:
    from blinkpy import auth  # noqa E402, from path / site packages
    from blinkpy import blinkpy  # noqa E402, from path / site packages


class ThermostatClass(blinkpy.Blink, tc.ThermostatCommon):
    """Blink Camera thermostat functions."""

    def __init__(self, zone):
        """
        Constructor, connect to thermostat.

        inputs:
            zone(str):  zone of thermostat.
        """
        # Blink server auth credentials from env vars
        self.BL_UNAME_KEY = 'BLINK_USERNAME'
        self.BL_PASSWORD_KEY = 'BLINK_PASSWORD'
        self.bl_uname = (os.environ.get(self.BL_UNAME_KEY, "<" +
                         self.BL_UNAME_KEY + "_KEY_MISSING>"))
        self.bl_pwd = (os.environ.get(
            self.BL_PASSWORD_KEY, "<" +
            self.BL_PASSWORD_KEY + "_KEY_MISSING>"))
        self.auth_dict = {"username": self.bl_uname, "password": self.bl_pwd}
        self.BL_2FA_KEY = "BLINK_2FA"
        self.bl_2fa = (os.environ.get(
            self.BL_2FA_KEY, "<" +
            self.BL_2FA_KEY + "_KEY_MISSING>"))

        # call both parent class __init__
        self.args = [self.bl_uname, self.bl_pwd]
        blinkpy.Blink.__init__(self, *self.args)
        tc.ThermostatCommon.__init__(self)
        self.thermostat_type = blink_config.ALIAS

        # establish connection
        self.blink = blinkpy.Blink()
        auth_ = auth.Auth(self.auth_dict, no_prompt=True)
        self.blink.auth = auth_
        self.blink.start()
        self.blink.auth.send_auth_key(self.blink, self.bl_2fa)
        self.blink.setup_post_verify()

        # get cameras
        self.camera_metadata = {}
        self.get_cameras()

        # configure zone info
        self.zone_number = zone
        self.zone_name = self.get_zone_name()
        self.device_id = None  # initialize
        self.device_id = self.get_target_zone_id(self.zone_number)
        self.serial_number = None  # will be populated when unit is queried.

    def get_zone_name(self):
        """
        Return the name associated with the zone number from metadata dict.

        inputs:
            None
        returns:
            (str) zone name
        """
        return blink_config.metadata[self.zone_number]["zone_name"]

    def get_target_zone_id(self, zone=0):
        """
        Return the target zone ID.

        inputs:
            zone(int): zone number.
        returns:
            (obj): Blink object
        """
        # return the target zone object
        return zone

    def get_cameras(self):
        """
        Get the blink cameras
        """
        for name, camera in self.blink.cameras.items():
            print(name)
            print(camera.attributes)
            self.camera_metadata[name] = camera.attributes

    def get_all_metadata(self, zone=None, debug=False):
        """Get all thermostat meta data for device_id from local API.

        inputs:
            zone(): specified zone
            debug(bool): debug flag.
        returns:
            (dict): dictionary of meta data.
        """
        return self.get_metadata(zone, None, debug)

    def get_metadata(self, zone=None, parameter=None, debug=False):
        """Get thermostat meta data for device_id from local API.

        inputs:
            zone(): specified zone
            parameter(str): target parameter, if None will return all.
            debug(bool): debug flag.
        returns:
            (dict): dictionary of meta data.
        """
        zone_name = blink_config.metadata[self.zone_number]["zone_name"]
        for name, camera in self.blink.cameras.items():
            if name == zone_name:
                if debug:
                    print(f"found camera {name}: {camera.attributes}")
                if parameter is None:
                    return camera.attributes
                else:
                    return camera.attributes[parameter]
        raise ValueError(f"Camera zone {zone}({zone_name}) was not found")

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
        super().__init__()

        # runtime parameter defaults
        self.poll_time_sec = 10 * 60  # default to 10 minutes
        self.connection_time_sec = 8 * 60 * 60  # default to 8 hours

        # server data cache expiration parameters
        self.fetch_interval_sec = 10  # age of server data before refresh
        self.last_fetch_time = time.time() - 2 * self.fetch_interval_sec

        # switch config for this thermostat
        self.system_switch_position[tc.ThermostatCommonZone.COOL_MODE] = "cool"
        self.system_switch_position[tc.ThermostatCommonZone.HEAT_MODE] = "heat"
        self.system_switch_position[tc.ThermostatCommonZone.OFF_MODE] = "off"
        self.system_switch_position[tc.ThermostatCommonZone.DRY_MODE] = "dry"
        self.system_switch_position[tc.ThermostatCommonZone.AUTO_MODE] = "auto"
        self.system_switch_position[tc.ThermostatCommonZone.FAN_MODE] = "vent"

        # zone info
        self.thermostat_type = blink_config.ALIAS
        self.device_id = Thermostat_obj.device_id
        self.Thermostat = Thermostat_obj
        self.zone_number = Thermostat_obj.zone_number
        self.zone_name = Thermostat_obj.zone_name
        self.zone_name = self.get_zone_name()

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

    def get_zone_name(self):
        """
        Return the name associated with the zone number from metadata dict.

        inputs:
            None
        returns:
            (str) zone name
        """
        return blink_config.metadata[self.zone_number]["zone_name"]

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

    def is_heat_mode(self) -> int:
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

    def is_cool_mode(self) -> int:
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

    def is_dry_mode(self) -> int:
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
        self.refresh_zone_info()
        return int(self.device_id.get_mode() ==
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
        return int(self.device_id.get_mode() != 'off')

    def is_fan_on(self):
        """Return 1 if fan relay is active, else 0."""
        self.refresh_zone_info()
        return int(self.device_id.get_fan_speed() != 'off')

    def is_defrosting(self):
        """Return 1 if defrosting is active, else 0."""
        self.refresh_zone_info()
        return int(self.device_id.get_status('defrost') == "True")

    def is_standby(self):
        """Return 1 if standby is active, else 0."""
        self.refresh_zone_info()
        return int(self.device_id.get_standby())

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
        return blink_config.MAX_HEAT_SETPOINT  # max heat set point allowed

    def get_schedule_cool_sp(self) -> int:
        """
        Return the schedule cool setpoint.

        inputs:
            None
        returns:
            (int): scheduled cooling set point in degrees F.
        """
        return blink_config.MIN_COOL_SETPOINT  # min cool set point allowed

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

    def get_system_switch_position(self) -> int:  # used
        """
        Return the system switch position, same as mode.

        inputs:
            None
        returns:
            (int) current mode for unit, should match value
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
        return
        # now_time = time.time()
        # # refresh if past expiration date or force_refresh option
        # if (force_refresh or (now_time >=
        #                       (self.last_fetch_time +
        #                        self.fetch_interval_sec))):
        #     self.Thermostat._need_fetch = True \
        #         # pylint: disable=protected-access
        #     try:
        #         self.Thermostat._fetch_if_needed() \
        #             # pylint: disable=protected-access
        #     except UnboundLocalError:  # patch for issue #205
        #         util.log_msg("WARNING: Kumocloud refresh failed due to "
        #                      "timeout", mode=util.BOTH_LOG, func_name=1)
        #     self.last_fetch_time = now_time
        #     # refresh device object
        #     self.device_id = \
        #         self.Thermostat.get_target_zone_id(self.zone_name)

    def report_heating_parameters(self, switch_position=None):
        """
        Display critical thermostat settings and reading to the screen.

        inputs:
            switch_position(int): switch position override, used for testing.
        returns:
            None
        """
        # current temp as measured by thermostat
        util.log_msg(
            f"display temp="
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
        util.log_msg(
            f"temporary hold until time="
            f"{self.get_temporary_hold_until_time()}",
            mode=util.BOTH_LOG)


if __name__ == "__main__":

    # verify environment
    env.get_python_version()

    # get zone override
    api.uip = api.UserInputs(argv_list=None,
                             thermostat_type=blink_config.ALIAS)
    zone_number = api.uip.get_user_inputs(api.uip.zone_name,
                                          api.input_flds.zone)

    tc.thermostat_basic_checkout(
        blink_config.ALIAS,
        zone_number,
        ThermostatClass, ThermostatZone)
