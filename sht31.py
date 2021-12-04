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
import pprint
import requests
import threading
import time
import traceback

# local imports
import thermostat_api as api
import thermostat_common as tc
import utilities as util

# SHT31 thermometer zones
LOFT_SHT31 = 0  # zone 0, local IP 192.168.86.15
LOFT_SHT31_REMOTE = 1  # zone 1


class ThermostatClass(tc.ThermostatCommon):
    """SHT31 thermometer functions."""

    def __init__(self, zone):
        """
        Constructor, connect to thermostat.

        inputs:
            zone(str):  zone of thermostat.
            sht31_ip dict above must have correct IP address for each
            zone.
        """
        # construct the superclass
        super(ThermostatClass, self).__init__()

        # zone configuration
        self.thermostat_type = api.SHT31
        self.zone_number = int(zone)
        self.ip_address = self.get_target_zone_id(self.zone_number)

        # URL and port configuration
        self.port = "5000"  # Flask server port on SHT31 host
        if self.zone_number == util.UNIT_TEST_ZONE:
            self.dir = "/diag"
            # self.dir = util.FLASK_UNIT_TEST_FOLDER  # unit test directory
        else:
            self.dir = ""
        self.url = "http://" + self.ip_address + ":" + self.port + self.dir
        self.device_id = self.url
        self.retry_delay = 60  # delay before retrying a bad reading

        # if in unit test mode, spawn flask server with emulated data
        if self.zone_number == util.UNIT_TEST_ZONE:
            self.spawn_flask_server()

    def get_target_zone_id(self, zone_number=0):
        """
        Return the target zone ID (aka IP address for sht31) from the
        zone number provided.

        inputs:
            zone_number(int): specified zone number
        returns:
            (str):  IP address of target zone.
        """
        env_str = self.get_env_key(zone_number)
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
        return ('SHT31_REMOTE_IP_ADDRESS' + '_' + str(zone_str))

    def get_ip_address(self, env_key):
        """
        Return IP address from env key and cache value in dict.

        inputs:
            env_key(str): env var key.
        returns:
            (str):  IP address
        """
        return util.get_env_variable(env_key)["value"]

    def spawn_flask_server(self):
        """
        Spawn a local flask server for unit testing.

        inputs: None
        returns:
        """
        # flask server used in unit test mode
        import sht31_flask_server as sht31_fs  # noqa E402

        sht31_fs.debug = False
        sht31_fs.measurements = 10
        sht31_fs.unit_test_mode = True
        self.flask_server = threading.Thread(target=sht31_fs.app.run,
                                             args=('0.0.0.0', 5000,
                                                   False))
        self.flask_server.daemon = True  # make thread daemonic
        self.flask_server.start()
        util.log_msg("thread alive status=%s" %
                     self.flask_server.is_alive(),
                     mode=util.BOTH_LOG, func_name=1)
        util.log_msg("Flask server setup is complete",
                     mode=util.BOTH_LOG, func_name=1)

    def print_all_thermostat_metadata(self):
        """
        Print initial meta data queried from thermostat.

        inputs:
            None
        returns:
            None
        """
        # dump metadata in a readable format
        return_data = self.get_all_metadata()
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(return_data)

    def get_all_metadata(self, retry=True):
        """
        Get all the current thermostat metadata.

        inputs:
            retry(bool): if True will retry once.
        returns:
            (dict) empty dict.
        """
        try:
            r = requests.get(self.url)
        except requests.exceptions.ConnectionError as e:
            util.log_msg("FATAL ERROR: unable to connect to sht31 "
                         "thermometer at url '%s'" %
                         self.url, mode=util.BOTH_LOG, func_name=1)
            raise e
        try:
            return r.json()
        except json.decoder.JSONDecodeError as e:
            util.log_msg(traceback.format_exc(),
                         mode=util.BOTH_LOG,
                         func_name=1)
            if retry:
                util.log_msg("waiting %s seconds and retrying SHT31 "
                             "measurement one time..." %
                             self.retry_delay, mode=util.BOTH_LOG,
                             func_name=1)
                time.sleep(self.retry_delay)
                self.get_all_metadata(retry=False)
            else:
                raise Exception("FATAL ERROR: SHT31 server "
                                "is not responding") from e


class ThermostatZone(tc.ThermostatCommonZone):
    """SHT31 thermometer zone functions."""

    def __init__(self, Thermostat_obj):
        """
        Constructor, connect to thermostat.

        inputs:
            Thermostat_obj(obj): associated Thermostat_obj
        """
        # construct the superclass
        super(ThermostatZone, self).__init__()

        # switch config for this thermostat
        # SHT31 is a monitor only, does not support heat/cool modes.
        self.system_switch_position[tc.ThermostatCommonZone.OFF_MODE] = 0

        # zone configuration
        self.thermostat_type = api.SHT31
        self.device_id = Thermostat_obj.device_id
        self.url = Thermostat_obj.device_id
        self.zone_number = Thermostat_obj.zone_number

        # runtime defaults
        self.poll_time_sec = 1 * 60  # default to 1 minute
        self.connection_time_sec = 8 * 60 * 60  # default to 8 hours

        self.tempfield = util.API_TEMP_FIELD  # must match flask API
        self.humidityfield = util.API_HUMIDITY_FIELD  # must match flask API
        self.retry_delay = Thermostat_obj.retry_delay

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
            r = requests.get(self.url)
        except requests.exceptions.ConnectionError as e:
            util.log_msg("FATAL ERROR: unable to connect to sht31 "
                         "thermometer at url '%s'" %
                         self.url, mode=util.BOTH_LOG, func_name=1)
            raise e
        if parameter is None:
            try:
                return r.json()
            except json.decoder.JSONDecodeError as e:
                util.log_msg(traceback.format_exc(),
                             mode=util.BOTH_LOG,
                             func_name=1)
                if retry:
                    util.log_msg("waiting %s seconds and retrying SHT31 "
                                 "measurement one time..." %
                                 self.retry_delay, mode=util.BOTH_LOG,
                                 func_name=1)
                    time.sleep(self.retry_delay)
                    self.get_metadata(parameter=None, retry=False)
                else:
                    raise Exception("FATAL ERROR: SHT31 server "
                                    "is not responding") from e
        else:
            try:
                return r.json()[parameter]
            except json.decoder.JSONDecodeError as e:
                util.log_msg(traceback.format_exc(),
                             mode=util.BOTH_LOG,
                             func_name=1)
                if retry:
                    util.log_msg("waiting %s seconds and retrying SHT31 "
                                 "measurement one time..." %
                                 self.retry_delay, mode=util.BOTH_LOG,
                                 func_name=1)
                    time.sleep(self.retry_delay)
                    self.get_metadata(parameter, retry=False)
                else:
                    raise Exception("FATAL ERROR: SHT31 server "
                                    "is not responding") from e
            except KeyError as e:
                util.log_msg(traceback.format_exc(),
                             mode=util.BOTH_LOG,
                             func_name=1)
                if "message" in r.json():
                    util.log_msg("WARNING in Flask response: '%s'" %
                                 r.json()["message"], mode=util.BOTH_LOG,
                                 func_name=1)
                if retry:
                    util.log_msg("waiting %s seconds and retrying SHT31 "
                                 "measurement one time..." %
                                 self.retry_delay, mode=util.BOTH_LOG,
                                 func_name=1)
                    time.sleep(self.retry_delay)
                    self.get_metadata(parameter, retry=False)
                else:
                    raise Exception("FATAL ERROR: SHT31 server "
                                    "response did not contain key '%s'"
                                    ", raw response=%s" %
                                    (parameter, r.json())) from e

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

    def get_heat_mode(self) -> int:
        """
        Return the heat mode.

        inputs:
            None
        returns:
            (int): heat mode.
        """
        return self.system_switch_position[self.OFF_MODE]

    def get_cool_mode(self) -> int:
        """
        Return the cool mode.

        inputs:
            None
        returns:
            (int): cool mode.
        """
        return self.system_switch_position[self.OFF_MODE]

    def get_dry_mode(self) -> int:
        """
        Return the dry mode.

        inputs:
            None
        returns:
            (int): dry mode, 1=enabled, 0=disabled.
        """
        return self.system_switch_position[self.OFF_MODE]

    def get_system_switch_position(self) -> int:
        """ Return the thermostat mode.

        inputs:
            None
        returns:
            (int): thermostat mode, see tc.system_switch_position for details.
        """
        return self.system_switch_position[self.OFF_MODE]


if __name__ == "__main__":

    tc.thermostat_basic_checkout(api, api.SHT31,
                                 ThermostatClass,
                                 ThermostatZone)
