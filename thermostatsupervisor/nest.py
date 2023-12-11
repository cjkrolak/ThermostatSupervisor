"""Nest integration."""
# built-in libraries
import json
import time

# thrid party libaries
# note this code uses python-google-nest package.
# Installing python-nest package will corrupt the python-google-nest install
import nest  # python-google-nest

# local imports
from thermostatsupervisor import nest_config
from thermostatsupervisor import thermostat_api as api
from thermostatsupervisor import thermostat_common as tc
from thermostatsupervisor import environment as env
from thermostatsupervisor import utilities as util


class ThermostatClass(tc.ThermostatCommon):
    """Nest thermostat functions."""

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
        self.thermostat_type = nest_config.ALIAS
        self.verbose = verbose

        # get credentials from file
        self.google_app_credential_file = ".//credentials.json"
        self.access_token_cache_file = ".//token_cache.json"
        self.cache_period = 60
        with open(self.google_app_credential_file,
                  encoding="utf8") as json_file:
            data = json.load(json_file)
            print(f"DEBUG: credential file contents = {data}")
            self.client_id = data["web"]["client_id"]
            self.client_secret = data["web"]["client_secret"]
            self.project_id = data["web"]["project_id"]

        # establish thermostat object
        self.thermostat_obj = nest.Nest(
            client_id=self.client_id,
            client_secret=self.client_secret,
            project_id=self.project_id,
            access_token_cache_file=self.access_token_cache_file,
            reautherize_callback=self.reautherize_callback,
            cache_period=self.cache_period)

        # configure zone info
        self.zone_number = int(zone)
        self.zone_name = self.get_zone_name()
        self.device_id = None  # initialize
        self.device_id = self.get_target_zone_id(self.zone_number)
        self.serial_number = None  # will be populated when unit is queried.

    def get_zone_name(self):
        """
        get zone name for specified zone number.
        """
        # Will trigger initial auth and fetch of data
        devices = self.thermostat_obj.get_devices()
        print(f"DEBUG: devices = {devices}")
        self.zone_data = devices[self.zone_number]
        return self.zone_data["name"]

    def reautherize_callback(self, authorization_url):
        """
        re-authorization callback.

        reautherize_callback should be set to a function with the signature
        Callable[[str], str]] it will be called if the user needs to reautherize
        the OAuth tokens. It will be passed the URL to go to, and need to have
        the resulting URL after authentication returned.

        inputs:
            authorization_url(str): authorization URL.
        returns:

        """
        print(f"Please go to {authorization_url} and authorize access")
        return input('Enter the full callback URL: ')

    def get_target_zone_id(self, zone=0):
        """
        Return the target zone ID.

        inputs:
            zone(int): zone number.
        returns:
            (obj): PyKumo object
        """
        return 0

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
            zone(str or int): (unused) specified zone
            parameter(str): target parameter, if None will return all.
            debug(bool): debug flag.
        returns:
            (dict): dictionary of meta data.
        """
        del debug  # unused
        del zone  # unused

        # Will trigger initial auth and fetch of data
        devices = self.thermostat_obj.get_devices()
        print(f"DEBUG: devices = {devices}")
        meta_data = devices[self.zone]
        if parameter is None:
            return meta_data
        else:
            return meta_data[parameter]

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
        self.system_switch_position[tc.ThermostatCommonZone.COOL_MODE] = "COOL"
        self.system_switch_position[tc.ThermostatCommonZone.HEAT_MODE] = "HEAT"
        self.system_switch_position[tc.ThermostatCommonZone.OFF_MODE] = "OFF"
        self.system_switch_position[tc.ThermostatCommonZone.DRY_MODE] = "dry"
        self.system_switch_position[
            tc.ThermostatCommonZone.AUTO_MODE] = "HEATCOOL"

        # zone info
        self.verbose = verbose
        self.thermostat_type = nest_config.ALIAS
        self.device_id = Thermostat_obj.device_id
        self.Thermostat = Thermostat_obj
        self.zone_number = Thermostat_obj.zone_number
        self.zone_name = Thermostat_obj.zone_name
        self.zone_name = self.get_zone_name()

    def get_trait(self, trait_name):
        """
        get thermostat trait.

        inputs:
            trait_name(str): trait name
            ref: https://developers.google.com/nest/device-access/traits
        returns:
            (str) trait value
        """
        # will reuse the cached result unless cache_period has elapsed
        print(f"DEBUG: querying trait {trait_name}")
        devices = nest.Device.filter_for_trait(self.devices, trait_name)
        # will reuse the cached result unless cache_period has elapsed
        trait_value = devices[self.zone_number].traits[trait_name]
        print(f"trait '{trait_name}'= {trait_value}")
        return trait_value

    def set_trait(self, trait_name, trait_value):
        """
        set thermostat trait.

        inputs:
            trait_name(str): trait name
            trait_value(str): trait value
            ref: https://developers.google.com/nest/device-access/traits
        returns:
            (str) trait value
        """
        # will reuse the cached result unless cache_period has elapsed
        print(f"setting trait '{trait_name}'= {trait_value}...")
        devices = nest.Device.filter_for_trait(self.devices, trait_name)
        # will trigger a request to POST the cmd
        devices[self.zone_number].send_cmd(
                trait_name, json.loads(trait_value))
        # verify trait was set
        trait_value = devices[self.zone_number].traits[trait_name]
        print(f"verifying trait '{trait_name}'= {trait_value}...")
        return trait_value

    def get_zone_name(self):
        """
        Return the name associated with the zone number from device memory.

        inputs:
            None
        returns:
            (str) zone name
        """
        self.refresh_zone_info()
        zone_name = self.get_trait("Info")
        # update metadata dict
        nest_config.metadata[self.zone_number]["zone_name"] = zone_name
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
            self.get_trait("Temperature")["ambientTemperatureCelsius"])

    def get_display_humidity(self) -> (float, None):
        """
        Refresh the cached zone information and return IndoorHumidity.

        inputs:
            None
        returns:
            (float, None): indoor humidity in %RH, None if not supported.
        """
        self.refresh_zone_info()
        return self.get_trait("Humidity")["ambientHumidityPercent"]

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
        return int(self.get_trait("ThermostatMode")["mode"] ==
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
        return int(self.get_trait("ThermostatMode")["mode"] ==
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
        return int(self.get_trait("ThermostatMode")["mode"] ==
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
        return int(self.get_trait("ThermostatMode")["mode"] ==
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
        return int(self.get_trait("ThermostatMode")["mode"] ==
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
        return int(self.get_trait("ThermostatMode")["mode"] ==
                   self.system_switch_position[
                       tc.ThermostatCommonZone.OFF_MODE])

    def is_heating(self):
        """Return 1 if heating relay is active, else 0."""
        return int(self.get_trait("ThermostatHvac")["status"] == "HEATING")

    def is_cooling(self):
        """Return 1 if cooling relay is active, else 0."""
        return int(self.get_trait("ThermostatHvac")["status"] == "COOLING")

    def is_auto(self):
        """Return 1 if auto relay is active, else 0."""
        return int(self.get_trait("ThermostatMode")["mode"] == "HEATCOOL")

    def is_fanning(self):
        """Return 1 if fan relay is active, else 0."""
        return int(self.get_trait("Fan")["timerMode"] == "ON")

    def is_power_on(self):
        """Return 1 if power relay is active, else 0."""
        self.refresh_zone_info()
        return int(self.get_trait("Connectivity")["status"] == "ONLINE")

    def is_fan_on(self):
        """Return 1 if fan relay is active, else 0."""
        self.refresh_zone_info()
        return int(self.get_trait("Fan")["timerMode"] == "ON")

    def get_heat_setpoint_raw(self) -> int:  # used
        """
        Refresh the cached zone information and return the heat setpoint.

        inputs:
            None
        returns:
            (int): heating set point in degrees F.
        """
        self.refresh_zone_info()
        return util.c_to_f(
            self.get_trait("ThermostatTemperatureSetpoint")["heatCelsius"])

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
        return nest_config.MAX_HEAT_SETPOINT  # max heat set point allowed

    def get_schedule_cool_sp(self) -> int:
        """
        Return the schedule cool setpoint.

        inputs:
            None
        returns:
            (int): scheduled cooling set point in degrees F.
        """
        return nest_config.MIN_COOL_SETPOINT  # min cool set point allowed

    def get_cool_setpoint_raw(self) -> int:
        """
        Return the cool setpoint.

        inputs:
            None
        returns:
            (int): cooling set point in degrees F.
        """
        self.refresh_zone_info()
        return util.c_to_f(
            self.get_trait("ThermostatTemperatureSetpoint")["coolCelsius"])

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
            temp(int): desired temperature in °F.
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
                self.Thermostat.get_target_zone_id(self.zone_name)

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
                             thermostat_type=nest_config.ALIAS)
    zone_number = api.uip.get_user_inputs(api.uip.zone_name,
                                          api.input_flds.zone)

    tc.thermostat_basic_checkout(
        nest_config.ALIAS,
        zone_number,
        ThermostatClass, ThermostatZone)

    tc.print_select_data_from_all_zones(
        nest_config.ALIAS,
        nest_config.get_available_zones(),
        ThermostatClass,
        ThermostatZone,
        display_wifi=True,
        display_battery=True)