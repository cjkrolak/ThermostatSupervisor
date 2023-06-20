"""
connection to sht31 thermometer over REST API
data structure expected:
{
    "measurements": 1,
    "Temp(F) mean": 88.55024032959489,
    "Temp(C) std": 0.0,
    "Temp(F) std": 0.0,
    "Humidity(%RH) mean": 49.491111619745176,
    "Humidity(%RH) std": 0.0
}
"""
# built-in imports
import json
import os
import threading
import time
import traceback

# third party imports
import requests

# local imports
from thermostatsupervisor import environment as env
from thermostatsupervisor import sht31_config
from thermostatsupervisor import thermostat_api as api
from thermostatsupervisor import thermostat_common as tc
from thermostatsupervisor import utilities as util


class ThermostatClass(tc.ThermostatCommon):
    """SHT31 thermometer functions."""

    def __init__(self, zone, path=sht31_config.flask_folder.production,
                 verbose=True):
        """
        Constructor, connect to thermostat.

        inputs:
            zone(str):  zone of thermostat.
            path(str):  path on flask server, default = production
                        sht31_ip dict above must have correct IP address for
                        each zone.
            verbose(bool): debug flag.
        """
        # construct the superclass
        super().__init__()

        # set tstat type and debug flag
        self.thermostat_type = sht31_config.ALIAS
        self.verbose = verbose

        # zone configuration
        self.zone_name = int(zone)
        self.ip_address = self.get_target_zone_id(self.zone_name)
        self.path = path

        # URL and port configuration
        self.port = str(sht31_config.FLASK_PORT)  # Flask server port on host
        if (self.zone_name == sht31_config.UNIT_TEST_ZONE and
                self.path == sht31_config.flask_folder.production):
            self.path = sht31_config.flask_folder.unit_test
            self.unit_test_seed = "?seed=" + str(sht31_config.UNIT_TEST_SEED)
        else:
            # self.path = ""
            self.unit_test_seed = ""
        self.measurements = "?measurements=" + str(sht31_config.MEASUREMENTS)
        self.url = (sht31_config.FLASK_URL_PREFIX + self.ip_address + ":" +
                    self.port + self.path + self.measurements +
                    self.unit_test_seed)
        self.device_id = self.url
        self.retry_delay = 60  # delay before retrying a bad reading

        # if in unit test mode, spawn flask server with emulated data on client
        if self.zone_name == sht31_config.UNIT_TEST_ZONE:
            self.spawn_flask_server()

    def get_target_zone_id(self, zone=0):
        """
        Return the target zone ID (aka IP address for sht31) from the
        zone number provided.

        inputs:
            zone(int): specified zone number
        returns:
            (str):  IP address of target zone.
        """
        env_str = self.get_env_key(zone)
        ip_address = self.get_ip_address(env_str)
        return ip_address

    def get_env_key(self, zone_str):
        """
        Return env key for the zone specified.

        inputs:
            zone_str(str or int): zone number
        returns:
            (str): env var key
        """
        return 'SHT31_REMOTE_IP_ADDRESS' + '_' + str(zone_str)

    def get_ip_address(self, env_key):
        """
        Return IP address from env key and cache value in dict.

        inputs:
            env_key(str): env var key.
        returns:
            (str):  IP address
        """
        return env.get_env_variable(env_key)["value"]

    def spawn_flask_server(self):
        """
        Spawn a local flask server for unit testing.

        inputs: None
        returns:
        """
        # flask server used in unit test mode
        from thermostatsupervisor import sht31_flask_server as sht31_fs  # noqa E402, C0415
        # pylint: disable=import-outside-toplevel

        # setup flask runtime variables
        sht31_fs.uip = sht31_fs.UserInputs(
            [os.path.realpath(__file__),
             sht31_config.FLASK_DEBUG_MODE])

        # start flask server thread
        self.flask_server = threading.Thread(
            target=sht31_fs.app.run,
            args=('0.0.0.0', sht31_config.FLASK_PORT,
                  sht31_config.FLASK_DEBUG_MODE),
            kwargs=sht31_config.FLASK_KWARGS)
        self.flask_server.daemon = True  # make thread daemonic
        self.flask_server.start()
        util.log_msg(f"thread alive status={self.flask_server.is_alive()}",
                     mode=util.BOTH_LOG, func_name=1)
        util.log_msg("Flask server setup is complete",
                     mode=util.BOTH_LOG, func_name=1)

    def print_all_thermostat_metadata(self, zone, debug=False):
        """
        Print initial meta data queried from thermostat.

        inputs:
            zone(int): target zone
            debug(bool): debug flag
        returns:
            (dict): return data
        """
        return_data = self.exec_print_all_thermostat_metadata(
            self.get_all_metadata, [zone, debug])
        return return_data

    def get_all_metadata(self, zone, retry=True):
        """
        Get all the current thermostat metadata.

        inputs:
            zone(int): target zone
            retry(bool): if True will retry once.
        returns:
            (dict) results dict.
        """
        return self.get_metadata(zone, None, retry)

    def get_metadata(self, zone, parameter=None, retry=True):
        """
        Get current thermostat metadata.

        inputs:
            zone(str or int): (unused) target zone
            parameter(str): target parameter, if None will fetch all.
            retry(bool): if True will retry once.
        returns:
            (dict) empty dict.
        """
        try:
            response = requests.get(self.url, timeout=util.HTTP_TIMEOUT)
        except requests.exceptions.ConnectionError as ex:
            util.log_msg(
                f"FATAL ERROR: unable to connect to sht31 thermometer at url "
                f"'{self.url}'",
                mode=util.BOTH_LOG,
                func_name=1)
            raise ex
        try:
            if parameter is None:
                return response.json()
            else:
                return response.json()[parameter]
        except json.decoder.JSONDecodeError as ex:
            util.log_msg(traceback.format_exc(),
                         mode=util.BOTH_LOG,
                         func_name=1)
            if retry:
                util.log_msg(
                    f"waiting {self.retry_delay} seconds and retrying SHT31 "
                    f"measurement one time...",
                    mode=util.BOTH_LOG,
                    func_name=1)
                time.sleep(self.retry_delay)
                self.get_metadata(zone, parameter, retry=False)
            else:
                raise RuntimeError("FATAL ERROR: SHT31 server "
                                   "is not responding") from ex


class ThermostatZone(tc.ThermostatCommonZone):
    """SHT31 thermometer zone functions."""

    def __init__(self, Thermostat_obj, verbose=True):
        """
        Constructor, connect to thermostat.

        inputs:
            Thermostat_obj(obj): associated Thermostat_obj
            verbose(bool): debug flag.
        """
        # construct the superclass
        super().__init__()

        # switch config for this thermostat
        # SHT31 is a monitor only, does not support heat/cool modes.
        self.system_switch_position[tc.ThermostatCommonZone.OFF_MODE] = 0

        # zone configuration
        self.verbose = verbose
        self.thermostat_type = sht31_config.ALIAS
        self.device_id = Thermostat_obj.device_id
        self.url = Thermostat_obj.device_id
        self.zone_name = Thermostat_obj.zone_name
        self.zone_name = self.get_zone_name(self.zone_name)

        # runtime defaults
        self.poll_time_sec = 1 * 60  # default to 1 minute
        self.connection_time_sec = 8 * 60 * 60  # default to 8 hours

        self.tempfield = sht31_config.API_TEMPF_MEAN  # must match flask API
        self.humidityfield = sht31_config.API_HUMIDITY_MEAN  # must match API
        self.retry_delay = Thermostat_obj.retry_delay

    def get_zone_name(self, zone) -> str:  # used
        """
        Return zone name.

        inputs:
            zone(int): zone number
        returns:
            (str): zone name
        """
        return sht31_config.metadata[zone]["zone_name"]

    def get_metadata(self, parameter=None, retry=True):
        """
        Get the current thermostat metadata settings.

        inputs:
          parameter(str): target parameter, None = all settings
          retry(bool): if True, will retry on Exception
        returns:
          dict if parameter=None
          str if parameter != None
        """
        try:
            response = requests.get(self.url, timeout=util.HTTP_TIMEOUT)
        except requests.exceptions.ConnectionError as ex:
            util.log_msg(
                f"FATAL ERROR: unable to connect to sht31 thermometer at url "
                f"'{self.url}'",
                mode=util.BOTH_LOG,
                func_name=1)
            raise ex
        if parameter is None:
            try:
                return response.json()
            except json.decoder.JSONDecodeError as ex:
                util.log_msg(traceback.format_exc(),
                             mode=util.BOTH_LOG,
                             func_name=1)
                if retry:
                    util.log_msg(
                        f"waiting {self.retry_delay} seconds and retrying "
                        f"SHT31 measurement one time...",
                        mode=util.BOTH_LOG,
                        func_name=1)
                    time.sleep(self.retry_delay)
                    self.get_metadata(parameter=None, retry=False)
                else:
                    raise RuntimeError("FATAL ERROR: SHT31 server "
                                       "is not responding") from ex
        else:
            try:
                return response.json()[parameter]
            except json.decoder.JSONDecodeError as ex:
                util.log_msg(traceback.format_exc(),
                             mode=util.BOTH_LOG,
                             func_name=1)
                if retry:
                    util.log_msg(
                        f"waiting {self.retry_delay} seconds and retrying "
                        f"SHT31 measurement one time...",
                        mode=util.BOTH_LOG,
                        func_name=1)
                    time.sleep(self.retry_delay)
                    self.get_metadata(parameter, retry=False)
                else:
                    raise RuntimeError("FATAL ERROR: SHT31 server "
                                       "is not responding") from ex
            except KeyError as ex:
                util.log_msg(traceback.format_exc(),
                             mode=util.BOTH_LOG,
                             func_name=1)
                if "message" in response.json():
                    util.log_msg(
                        f"WARNING in Flask response: "
                        f"'{response.json()['message']}'",
                        mode=util.BOTH_LOG,
                        func_name=1)
                if retry:
                    util.log_msg(
                        f"waiting {self.retry_delay} seconds and retrying "
                        f"SHT31 measurement one time...",
                        mode=util.BOTH_LOG,
                        func_name=1)
                    time.sleep(self.retry_delay)
                    self.get_metadata(parameter, retry=False)
                else:
                    raise KeyError(
                        f"FATAL ERROR: SHT31 server response did not contain "
                        f"key '{parameter}', raw response={response.json()}"
                        ) from ex

    def get_display_temp(self) -> float:
        """
        Return Temperature.

        inputs:
            None
        returns:
            (float): temperature in degrees.
        """
        return float(self.get_metadata(self.tempfield))

    def get_display_humidity(self) -> (float, None):
        """
        Return Humidity.

        inputs:
            None
        returns:
            (float, None): humidity in %RH, None if not supported.
        """
        raw_humidity = self.get_metadata(self.humidityfield)
        if raw_humidity is not None:
            return float(raw_humidity)
        else:
            return raw_humidity

    def get_is_humidity_supported(self) -> bool:
        """Return humidity sensor status."""
        return self.get_display_humidity() is not None

    def is_heat_mode(self) -> int:
        """Return the heat mode."""
        return 0  # not applicable

    def is_cool_mode(self) -> int:
        """Return the cool mode."""
        return 0  # not applicable

    def is_dry_mode(self) -> int:
        """Return the dry mode."""
        return 0  # not applicable

    def is_auto_mode(self) -> int:
        """Return the auto mode."""
        return 0  # not applicable

    def is_fan_mode(self) -> int:
        """Return the fan mode."""
        return 0  # not applicable

    def is_off_mode(self) -> int:
        """Return the off mode."""
        return 1  # always off

    def is_heating(self) -> int:
        """Return 1 if actively heating, else 0."""
        return 0  # not applicable

    def is_cooling(self) -> int:
        """Return 1 if actively cooling, else 0."""
        return 0  # not applicable

    def is_drying(self):
        """Return 1 if drying relay is active, else 0."""
        return 0  # not applicable

    def is_auto(self):
        """Return 1 if auto relay is active, else 0."""
        return 0  # not applicable

    def is_fanning(self):
        """Return 1 if fan relay is active, else 0."""
        return 0  # not applicable

    def is_power_on(self):
        """Return 1 if power relay is active, else 0."""
        return 1  # always on

    def is_fan_on(self):
        """Return 1 if fan relay is active, else 0."""
        return 0  # not applicable

    def is_defrosting(self):
        """Return 1 if defrosting is active, else 0."""
        return 0  # not applicable

    def is_standby(self):
        """Return 1 if standby is active, else 0."""
        return 0  # not applicable

    def get_system_switch_position(self) -> int:
        """ Return the thermostat mode.

        inputs:
            None
        returns:
            (int): thermostat mode, see tc.system_switch_position for details.
        """
        return self.system_switch_position[self.OFF_MODE]

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
                f"heat setpoint={self.get_heat_setpoint()}",
                mode=util.BOTH_LOG)
            # util.log_msg("heat setpoint raw=%s" %
            #              zone.get_heat_setpoint_raw())
            util.log_msg(
                f"schedule heat sp={self.get_schedule_heat_sp()}",
                mode=util.BOTH_LOG)

        # cooling status
        if switch_position == \
                self.system_switch_position[self.COOL_MODE]:
            util.log_msg(f"cool mode={self.is_cool_mode()}",
                         mode=util.BOTH_LOG)
            util.log_msg(
                f"cool setpoint={self.get_cool_setpoint()}",
                mode=util.BOTH_LOG)
            # util.log_msg("cool setpoint raw=%s" %
            #              zone.get_cool_setpoint_raw(), mode=util.BOTH_LOG)
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
                             thermostat_type=sht31_config.ALIAS)
    zone_number = api.uip.get_user_inputs(api.uip.zone_name,
                                          api.input_flds.zone)

    tc.thermostat_basic_checkout(
        sht31_config.ALIAS,
        zone_number,
        ThermostatClass, ThermostatZone)

    # tc.thermostat_get_all_zone_temps(
    #     sht31_config.ALIAS,
    #     sht31_config.supported_configs["zones"],
    #     ThermostatClass,
    #     ThermostatZone)
