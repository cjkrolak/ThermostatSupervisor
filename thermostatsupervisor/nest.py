"""
Nest integration.
using python-google-nest package
pypi ref: https://pypi.org/project/python-google-nest/
github ref: https://github.com/axlan/python-nest/
API ref: https://developers.google.com/nest/device-access/traits
"""
# built-in libraries
import json
import os
import pprint
import time

# thrid party libaries

# local imports
from thermostatsupervisor import nest_config
from thermostatsupervisor import thermostat_api as api
from thermostatsupervisor import thermostat_common as tc
from thermostatsupervisor import environment as env
from thermostatsupervisor import utilities as util

# python-nest package import
# note this code uses python-google-nest package.
# Installing python-nest package will corrupt the python-google-nest install
NEST_DEBUG = False  # debug uses local nest repo instead of pkg
if NEST_DEBUG and not env.is_azure_environment():
    mod_path = "..\\python-nest\\nest"
    if env.is_interactive_environment():
        mod_path = "..\\" + mod_path
    nest = env.dynamic_module_import("nest", mod_path)
else:
    import nest  # python-google-nest


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

        # gcloud token cache
        self.access_token_cache_file = nest_config.cache_file_location
        self.cache_period = nest_config.cache_period_sec

        # get credentials from env vars
        self.client_id = os.environ.get("GCLOUD_CLIENT_ID")
        self.client_secret = os.environ.get("GCLOUD_CLIENT_SECRET")
        self.project_id = os.environ.get("DAC_PROJECT_ID")
        self.credentials_from_env = (
            self.client_id and self.client_secret and self.project_id
        )

        if nest_config.use_credentials_file or not self.credentials_from_env:
            # get credentials from file
            self.google_app_credential_file = nest_config.credentials_file_location
            print(
                "retreiving Google Nest credientials from "
                f"{self.google_app_credential_file}..."
            )
            with open(self.google_app_credential_file, encoding="utf8") as json_file:
                data = json.load(json_file)
                self.client_id = data["web"]["client_id"]
                self.client_secret = data["web"]["client_secret"]
                # project_id is the project id UUID
                self.project_id = data["web"]["dac_project_id"]

        # establish thermostat object
        self.thermostat_obj = nest.Nest(
            project_id=self.project_id,
            client_id=self.client_id,
            client_secret=self.client_secret,
            access_token=None,
            access_token_cache_file=self.access_token_cache_file,
            reautherize_callback=self.reautherize_callback,
            cache_period=self.cache_period,
        )
        # get device data
        self.devices = self.get_device_data()

        # configure zone info
        self.zone_number = int(zone)
        self.zone_name = self.get_zone_name()
        self.device_id = None  # initialize
        self.device_id = self.get_target_zone_id(self.zone_number)
        self.serial_number = None  # will be populated when unit is queried.

    def get_device_data(self):
        """
        get device data from network.

        inputs:
            None
        returns:
            (list) list of device objects
        """
        self.devices = self.thermostat_obj.get_devices()
        # TODO is there a chance that meta data changes?
        return self.devices

    def get_zone_name(self):
        """
        get zone name for specified zone number.

        inputs:
            None
        returns:
            (str) zone name
        """
        self.zone_name = self.get_metadata(
            self.zone_number, trait="Info", parameter="customName"
        )
        return self.zone_name

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
            callable[(str), (str)]: callback function.
        """
        print(f"Please go to {authorization_url} and authorize access")
        return input("Enter the full callback URL: ")

    def get_target_zone_id(self, zone=0):
        """
        Return the target zone ID.

        inputs:
            zone(int): zone number.
        returns:
            (obj): nest Device object
        """
        return self.devices[zone]

    def get_all_metadata(self, zone=nest_config.default_zone, retry=False):
        """Get all thermostat meta data for select zone.

        inputs:
            zone(): specified zone
            retry(bool): retry flag
        returns:
            (dict): dictionary of meta data.
        """
        del retry  # not used
        return self.get_metadata(zone)

    def get_metadata(self, zone=None, trait=None, parameter=None):
        """Get thermostat meta data for zone.

        inputs:
            zone(str or int): specified zone
            trait(str): trait or parent key, if None will assume a non-nested
                        dict.
            parameter(str): target parameter, if None will return all.
        returns:
            (dict): dictionary of meta data.
        """
        # if zone input is str assume it is zone name, convert to zone_num.
        if isinstance(zone, str):
            zone_num = util.get_key_from_value(nest_config.metadata, zone)
        elif isinstance(zone, int):
            zone_num = zone
        else:
            raise TypeError(
                f"type {type(zone)} not supported for zone input"
                "parmaeter in get_metadata function"
            )

        meta_data = self.devices[zone_num].traits
        # return all meta data for zone
        if parameter is None:
            return meta_data

        # trait must be specified if parameter is specified.
        if trait is None:
            raise NotImplementedError(
                "nest get_metadata() requires a trait "
                f"parameter along when querying "
                f"parameter='{parameter}'"
            )
        else:
            # return parameter
            return meta_data[trait][parameter]

    def print_all_thermostat_metadata(self, zone):
        """Print all metadata for zone to the screen.

        inputs:
            zone(int): specified zone, if None will print all zones.
        returns:
            None, prints result to screen
        """
        self.exec_print_all_thermostat_metadata(self.get_all_metadata, [zone])


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
        self.system_switch_position[tc.ThermostatCommonZone.COOL_MODE] = "COOL"
        self.system_switch_position[tc.ThermostatCommonZone.HEAT_MODE] = "HEAT"
        self.system_switch_position[tc.ThermostatCommonZone.OFF_MODE] = "OFF"
        self.system_switch_position[tc.ThermostatCommonZone.DRY_MODE] = "not supported"
        self.system_switch_position[tc.ThermostatCommonZone.AUTO_MODE] = "HEATCOOL"

        # zone info
        self.verbose = verbose
        self.thermostat_type = nest_config.ALIAS
        self.devices = Thermostat_obj.devices
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
        devices = nest.Device.filter_for_trait(self.devices, trait_name)

        # will reuse the cached result unless cache_period has elapsed
        trait_value = devices[self.zone_number].traits[trait_name]
        return trait_value

    def send_cmd(self, cmd_name, par_name, par_value):
        """
        set thermostat trait.

        inputs:
            cmd_name(str): command name (a.k.a. trait)
            par_name(str): parameter name
            par_value(str): parameter value
            ref: https://developers.google.com/nest/device-access/traits
        returns:
            (dict) body of response
        """
        # will reuse the cached result unless cache_period has elapsed
        devices = nest.Device.filter_for_cmd(self.devices, cmd_name)

        # will trigger a request to POST the cmd
        result = devices[self.zone_number].send_cmd(cmd_name, {par_name: par_value})
        return result

    def get_zone_name(self):
        """
        Return the name associated with the zone number from device memory.

        inputs:
            None
        returns:
            (str) zone name
        """
        self.refresh_zone_info()
        zone_name = self.get_trait("Info")["customName"]
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
        display_temp_c = self.get_trait("Temperature")["ambientTemperatureCelsius"]
        display_temp_f = util.c_to_f(display_temp_c)
        return display_temp_f

    def get_display_humidity(self) -> (float, None):
        """
        Refresh the cached zone information and return IndoorHumidity.

        inputs:
            None
        returns:
            (float, None): indoor humidity in %RH, None if not supported.
        """
        self.refresh_zone_info()
        return float(self.get_trait("Humidity")["ambientHumidityPercent"])

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
        return int(
            self.get_trait("ThermostatMode")["mode"]
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
        self.refresh_zone_info()
        return int(
            self.get_trait("ThermostatMode")["mode"]
            == self.system_switch_position[tc.ThermostatCommonZone.COOL_MODE]
        )

    def is_dry_mode(self) -> int:
        """
        Refresh the cached zone information and return the dry mode.

        For nest there is no fan mode, just a fan timer, so this function
        should always return 0.

        inputs:
            None
        returns:
            (int): dry mode, 1=enabled, 0=disabled.
        """
        self.refresh_zone_info()
        return int(
            self.get_trait("ThermostatMode")["mode"]
            == self.system_switch_position[tc.ThermostatCommonZone.DRY_MODE]
        )

    def is_fan_mode(self) -> int:
        """
        Refresh the cached zone information and return the fan mode.

        For nest there is no fan mode, just a fan timer, so this function
        should always return 0.

        inputs:
            None
        returns:
            (int): fan mode, 1=enabled, 0=disabled.
        """
        self.refresh_zone_info()
        return int(
            self.get_trait("ThermostatMode")["mode"]
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
        self.refresh_zone_info()
        return int(
            self.get_trait("ThermostatMode")["mode"]
            == self.system_switch_position[tc.ThermostatCommonZone.AUTO_MODE]
        )

    def is_off_mode(self) -> int:
        """
        Refresh the cached zone information and return the off mode.

        inputs:
            None
        returns:
            (int): off mode, 1=enabled, 0=disabled.
        """
        self.refresh_zone_info()
        return int(
            self.get_trait("ThermostatMode")["mode"]
            == self.system_switch_position[tc.ThermostatCommonZone.OFF_MODE]
        )

    def is_heating(self):
        """Return 1 if heating relay is active, else 0."""
        self.refresh_zone_info()
        return int(self.get_trait("ThermostatHvac")["status"] == "HEATTING")

    def is_cooling(self):
        """Return 1 if cooling relay is active, else 0."""
        self.refresh_zone_info()
        return int(self.get_trait("ThermostatHvac")["status"] == "COOLING")

    def is_drying(self):
        """Return 1 if drying relay is active, else 0."""
        return 0  # not applicable for nest

    def is_auto(self):
        """Return 1 if auto relay is active, else 0."""
        self.refresh_zone_info()
        return int(
            self.get_trait("ThermostatHvac")["status"] in ("HEATING", "COOLING")
            and self.is_auto_mode()
        )

    def is_fanning(self):
        """Return 1 if fan relay is active, else 0."""
        self.refresh_zone_info()
        return int(self.get_trait("Fan")["timerMode"] == "ON")

    def is_power_on(self):
        """Return 1 if power relay is active, else 0."""
        self.refresh_zone_info()
        return int(self.get_trait("Connectivity")["status"] == "ONLINE")

    def is_fan_on(self):
        """Return 1 if fan relay is active, else 0."""
        self.refresh_zone_info()
        return int(self.get_trait("Fan")["timerMode"] == "ON")

    def get_wifi_strength(self) -> float:  # noqa R0201
        """Return the wifi signal strength in dBm."""
        return float(util.BOGUS_INT)

    def get_wifi_status(self) -> bool:  # noqa R0201
        """Return the wifi connection status."""
        self.refresh_zone_info()
        return int(self.get_trait("Connectivity")["status"] == "ONLINE")

    def get_battery_voltage(self) -> float:  # noqa R0201
        """Return the battery voltage in volts.

        This tstat is on HVAC line power so any valid response
        from tstat returns line power value.
        """
        return 24.0 if self.get_wifi_status() else 0.0

    def get_battery_status(self) -> bool:  # noqa R0201
        """Return the battery status.

        For this tstat any positive number returns True.
        """
        return self.get_battery_voltage() > 0.0

    def get_heat_setpoint_raw(self) -> float:  # used
        """
        Refresh the cached zone information and return the heat setpoint.

        Nest heat setpoint is only populated in heat or auto modes.

        inputs:
            None
        returns:
            (float): heating set point in °F.
        """
        self.refresh_zone_info()
        if self.is_heat_mode() or self.is_auto_mode():
            return util.c_to_f(
                self.get_trait("ThermostatTemperatureSetpoint")["heatCelsius"]
            )
        else:
            # set point value is only valid for current mode
            return float(util.BOGUS_INT)  # TODO, what should this value be?

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
        return float(nest_config.MAX_HEAT_SETPOINT)

    def get_schedule_cool_sp(self) -> float:
        """
        Return the schedule cool setpoint.

        inputs:
            None
        returns:
            (float): scheduled cooling set point in °F.
        """
        return float(nest_config.MIN_COOL_SETPOINT)

    def get_cool_setpoint_raw(self) -> float:
        """
        Return the cool setpoint.

        Nest cool setpoint is only populated in cool or auto modes.

        inputs:
            None
        returns:
            (float): cooling set point in °F.
        """
        self.refresh_zone_info()
        if self.is_cool_mode() or self.is_auto_mode():
            return util.c_to_f(
                self.get_trait("ThermostatTemperatureSetpoint")["coolCelsius"]
            )
        else:
            # set point value is only valid for current mode
            return float(util.BOGUS_INT)  # TODO, what should this value be?

    def get_cool_setpoint(self) -> str:
        """Return cool setpoint with units as a string."""
        return util.temp_value_with_units(self.get_cool_setpoint_raw())

    def get_safety_temperature(self) -> int:
        """
        Get the safety temperature setting.

        inputs:
            None
        returns:
            (int): cooling set point in °F.
        """
        return NotImplementedError(
            "Safety Temperature is not yet available through nest API"
        )

    def get_is_invacation_hold_mode(self) -> bool:  # used
        """
        Return the
          'IsInVacationHoldMode' setting.

        inputs:
            None
        returns:
            (booL): True if is in vacation hold mode.
        """
        return False  # no hold mode

    def get_vacation_hold(self) -> bool:
        """
        Return the
        VacationHold setting.

        inputs:
            None
        returns:
            (bool): True if vacation hold is set.
        """
        return False  # no hold mode

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
        return self.get_trait("ThermostatMode")["mode"]

    def set_heat_setpoint(self, temp: int) -> None:
        """
        Set a new heat setpoint.

        This will also attempt to turn the thermostat to 'Heat'
        inputs:
            temp(int): desired temperature in F
        returns:
            None
        """
        self.send_cmd(
            "ThermostatTemperatureSetpoint.SetHeat", "heatCelsius", util.f_to_c(temp)
        )

    def set_cool_setpoint(self, temp: int) -> None:
        """
        Set a new cool setpoint.

        This will also attempt to turn the thermostat to 'Cool'
        inputs:
            temp(int): desired temperature in °F.
        returns:
            None
        """
        self.send_cmd(
            "ThermostatTemperatureSetpoint.SetCool", "coolCelsius", util.f_to_c(temp)
        )

    def refresh_zone_info(self, force_refresh=False):
        """
        Refresh zone info from Nest server.

        inputs:
            force_refresh(bool): if True, ignore expiration timer.
        returns:
            None, device object is refreshed.
        """
        now_time = time.time()
        # refresh if past expiration date or force_refresh option
        if force_refresh or (
            now_time >= (self.last_fetch_time + self.fetch_interval_sec)
        ):
            self.Thermostat.get_device_data()
            self.last_fetch_time = now_time

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
            f"display temp=" f"{util.temp_value_with_units(self.get_display_temp())}",
            mode=util.BOTH_LOG,
            func_name=1,
        )

        # get switch position
        if switch_position is None:
            switch_position = self.get_system_switch_position()

        # heating status
        if switch_position == self.system_switch_position[self.HEAT_MODE]:
            util.log_msg(f"heat mode={self.is_heat_mode()}", mode=util.BOTH_LOG)
            util.log_msg(
                f"heat setpoint={self.get_heat_setpoint_raw()}", mode=util.BOTH_LOG
            )
            util.log_msg(
                f"schedule heat sp={self.get_schedule_heat_sp()}", mode=util.BOTH_LOG
            )

        # cooling status
        if switch_position == self.system_switch_position[self.COOL_MODE]:
            util.log_msg(f"cool mode={self.is_cool_mode()}", mode=util.BOTH_LOG)
            util.log_msg(
                f"cool setpoint={self.get_cool_setpoint_raw()}", mode=util.BOTH_LOG
            )
            util.log_msg(
                f"schedule cool sp={self.get_schedule_cool_sp()}", mode=util.BOTH_LOG
            )

        # hold settings
        util.log_msg(
            f"is in vacation hold mode={self.get_is_invacation_hold_mode()}",
            mode=util.BOTH_LOG,
        )
        util.log_msg(f"vacation hold={self.get_vacation_hold()}", mode=util.BOTH_LOG)
        util.log_msg(
            f"vacation hold until time={self.get_vacation_hold_until_time()}",
            mode=util.BOTH_LOG,
        )
        util.log_msg(
            f"temporary hold until time=" f"{self.get_temporary_hold_until_time()}",
            mode=util.BOTH_LOG,
        )


if __name__ == "__main__":
    # verify environment
    env.get_python_version()

    # get zone override
    api.uip = api.UserInputs(argv_list=None, thermostat_type=nest_config.ALIAS)
    zone_number = api.uip.get_user_inputs(api.uip.zone_name, api.input_flds.zone)

    _, Zone = tc.thermostat_basic_checkout(
        nest_config.ALIAS, zone_number, ThermostatClass, ThermostatZone
    )

    tc.print_select_data_from_all_zones(
        nest_config.ALIAS,
        nest_config.get_available_zones(),
        ThermostatClass,
        ThermostatZone,
        display_wifi=True,
        display_battery=True,
    )

    # measure thermostat response time
    if nest_config.check_response_time:
        MEASUREMENTS = 30
        meas_data = Zone.measure_thermostat_repeatability(
            MEASUREMENTS,
            poll_interval_sec=nest_config.cache_period_sec + 0.5,
            func=Zone.get_zone_name,
            measure_response_time=True,
        )
        ppp = pprint.PrettyPrinter(indent=4)
        ppp.pprint(meas_data)
