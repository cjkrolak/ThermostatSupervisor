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
import pprint
import requests
import time
import traceback

# local imports
import thermostat_api as api
import thermostat_common as tc
import utilities as util


# SHT31 thermometer device IDs
LOFT_SHT31 = 0  # zone 0
LOFT_SHT31_REMOTE = 1  # zone 1
UNITTEST_SHT31 = 99  # unit test emulator

# SHT31 IP address and port info
sht31_ip = {
    LOFT_SHT31: "192.168.86.15",  # local IP
    LOFT_SHT31_REMOTE: util.bogus_str,  # placeholder, remote IP
    UNITTEST_SHT31: "127.0.0.1",
    }
sht31_port = {
    LOFT_SHT31: "5000",
    LOFT_SHT31_REMOTE: "5000",
    UNITTEST_SHT31: "5000",
    }


class ThermostatClass(tc.ThermostatCommon):
    """SHT31 thermometer functions."""

    def __init__(self, zone, *_, **__):
        """
        Constructor, connect to thermostat.

        inputs:
            zone(str):  zone of thermostat.
            sht31_ip dict above must have correct IP address for each
            zone.
        """
        # construct the superclass
        super(ThermostatClass, self).__init__(*_, **__)

        # zone configuration
        self.thermostat_type = api.SHT31
        self.zone_number = int(zone)
        self.ip_address = self.get_target_zone_id(self.zone_number)

        # URL and port configuration
        self.port = "5000"  # Flask server port on SHT31 host
        self.url = "http://" + self.ip_address + ":" + self.port
        self.device_id = self.url
        self.retry_delay = 60  # delay before retrying a bad reading

    def get_target_zone_id(self, zone_number=0):
        """
        Return the target zone ID (aka IP address for sht31) from the
        zone number provided.

        inputs:
            zone_number(int): specified zone number
        returns:
            (str):  IP address of target zone.
        """
        # update IP dict based on env key
        env_str = get_env_key(zone_number)
        ip_address = get_ip_address(env_str)
        sht31_ip[zone_number] = ip_address
        return ip_address

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
        r = requests.get(self.url)
        try:
            return r.json()
        except json.decoder.JSONDecodeError as e:
            util.log_msg(traceback.format_exc(),
                         mode=util.DEBUG_LOG + util.CONSOLE_LOG,
                         func_name=1)
            if retry:
                print("waiting %s seconds and retrying SHT31 measurement "
                      "one time..." % self.retry_delay)
                time.sleep(self.retry_delay)
                self.get_all_metadata(retry=False)
            else:
                raise Exception("FATAL ERROR: SHT31 server "
                                "is not responding") from e


class ThermostatZone(tc.ThermostatCommonZone):
    """SHT31 thermometer zone functions."""

    # SHT31 is a monitor only, does not support heat/cool modes.
    system_switch_position = {
        tc.ThermostatCommonZone.COOL_MODE: util.bogus_int,
        tc.ThermostatCommonZone.HEAT_MODE: util.bogus_int,
        tc.ThermostatCommonZone.OFF_MODE: 0,
        tc.ThermostatCommonZone.AUTO_MODE: util.bogus_int,
        }

    def __init__(self, device_id, Thermostat_obj, *_, **__):
        """
        Constructor, connect to thermostat.

        inputs:
            device_id(str): device id, aka URL for this thermostat.
            Thermostat_obj(obj): associated Thermostat_obj
        """
        # construct the superclass
        super(ThermostatZone, self).__init__(*_, **__)

        # zone configuration
        self.thermostat_type = api.SHT31
        self.device_id = device_id
        self.url = device_id
        self.zone_number = self.get_target_zone_number(device_id)

        # runtime defaults
        self.poll_time_sec = 1 * 60  # default to 1 minute
        self.connection_time_sec = 8 * 60 * 60  # default to 8 hours

        self.tempfield = util.API_TEMP_FIELD  # must match flask API
        self.humidityfield = util.API_HUMIDITY_FIELD  # must match flask API
        self.retry_delay = Thermostat_obj.retry_delay

    def get_target_zone_number(self, device_id):
        """
        Return the target zone number from the device id provided.

        inputs:
            device_id(str): full URL with port.
        returns:
            (int):  zone number.
        """
        # strip off https header
        ip_address = device_id[device_id.find("//")+2:]
        # strip off port information from URL
        ip_address = ip_address[:ip_address.rfind(":")]
        zone_number = list(sht31_ip.keys())[
            list(sht31_ip.values()).index(ip_address)]

        return zone_number

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
        r = requests.get(self.url)
        if parameter is None:
            try:
                return r.json()
            except json.decoder.JSONDecodeError as e:
                util.log_msg(traceback.format_exc(),
                             mode=util.DEBUG_LOG + util.CONSOLE_LOG,
                             func_name=1)
                if retry:
                    print("waiting %s seconds and retrying SHT31 measurement "
                          "one time..." % self.retry_delay)
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
                             mode=util.DEBUG_LOG + util.CONSOLE_LOG,
                             func_name=1)
                if retry:
                    print("waiting %s seconds and retrying SHT31 measurement "
                          "one time..." % self.retry_delay)
                    time.sleep(self.retry_delay)
                    self.get_metadata(parameter, retry=False)
                else:
                    raise Exception("FATAL ERROR: SHT31 server "
                                    "is not responding") from e
            except KeyError as e:
                util.log_msg(traceback.format_exc(),
                             mode=util.DEBUG_LOG + util.CONSOLE_LOG,
                             func_name=1)
                if "message" in r.json():
                    print("WARNING in Flask response: '%s'" %
                          r.json()["message"])
                if retry:
                    print("waiting %s seconds and retrying SHT31 measurement "
                          "one time..." % self.retry_delay)
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

    def get_system_switch_position(self) -> int:
        """ Return the thermostat mode.

        inputs:
            None
        returns:
            (int): thermostat mode, see tc.system_switch_position for details.
        """
        return self.system_switch_position[self.OFF_MODE]


def get_env_key(zone_str):
    """
    Return env key for the zone specified.

    inputs:
        zone_str(str or int): zone number
    returns:
        (str): env var key
    """
    return ('SHT31_REMOTE_IP_ADDRESS' + '_' + str(zone_str))


def get_ip_address(env_key):
    """
    Return IP address from env key and cache value in dict.

    inputs:
        env_key(str): env var key.
    returns:
        (str):  IP address
    """
    return os.environ.get(env_key, "<" + env_key + "_KEY_MISSING>")


if __name__ == "__main__":

    util.log_msg.debug = True  # debug mode set

    # get zone from user input
    zone_input = api.parse_all_runtime_parameters()[1]

    # verify required env vars
    api.verify_required_env_variables(api.SHT31, zone_input)

    # import hardware module
    mod = api.load_hardware_library(api.SHT31)

    # create Thermostat object
    Thermostat = ThermostatClass(zone_input)
    Thermostat.print_all_thermostat_metadata()

    # create Zone object
    Zone = ThermostatZone(Thermostat.device_id, Thermostat)

    # update runtime overrides
    Zone.update_runtime_parameters(api.user_inputs)

    print("current thermostat settings...")
    print("tmode1: %s" % Zone.get_system_switch_position())
    print("heat mode=%s" % Zone.get_heat_mode())
    print("cool mode=%s" % Zone.get_cool_mode())
    print("temporary hold minutes=%s" % Zone.get_temporary_hold_until_time())
    print("thermostat meta data=%s" % Thermostat.get_all_metadata())
    print("thermostat display tempF=%s" % Zone.get_display_temp())
