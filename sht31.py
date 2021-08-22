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
import os
import pprint
import requests
import sys

# local imports
import thermostat_api as api  # used for standalone runs only
import thermostat_common as tc
import utilities as util


# sht31 thermometer IP addresses
LOFT_SHT31 = 0  # zone 0
LOFT_SHT31_REMOTE = 1  # zone 1
sht31_ip = {
    LOFT_SHT31: "192.168.86.15",  # local IP
    LOFT_SHT31_REMOTE: util.bogus_str,  # placeholder, remote IP
    }
sht31_port = {
    LOFT_SHT31: "5000",
    LOFT_SHT31_REMOTE: "5000",
    }


class SHT31Thermometer(tc.ThermostatCommonZone):
    """SHT31 thermometer functions."""

    # SHT31 is a monitor only, does not support heat/cool modes.
    system_switch_position = {
        tc.ThermostatCommonZone.COOL_MODE: util.bogus_int,
        tc.ThermostatCommonZone.HEAT_MODE: util.bogus_int,
        tc.ThermostatCommonZone.OFF_MODE: 0,
        tc.ThermostatCommonZone.AUTO_MODE: util.bogus_int,
        }

    def __init__(self, zone_str, *_, **__):
        """
        Constructor, connect to thermostat.

        inputs:
            zone_str(str):  zone of thermostat.
            sht31_ip dict above must have correct IP address for each
            zone.
        """
        # construct the superclass
        super(SHT31Thermometer, self).__init__(*_, **__)

        # zone configuration
        self.zone_constructor = SHT31Thermometer
        self.zone_number = self.get_target_zone_number(zone_str)
        self.ip_address = self.get_target_zone_id(self.zone_number)
        self.device_id = self.zone_number

        # URL and port configuration
        self.port = "5000"  # Flask server port on SHT31 host
        self.url = "http://" + self.ip_address + ":" + self.port
        self.tempfield = util.API_TEMP_FIELD  # must match flask API
        self.humidityfield = util.API_HUMIDITY_FIELD  # must match flask API

        # runtime defaults
        self.poll_time_sec = 1 * 60  # default to 1 minute
        self.connection_time_sec = 8 * 60 * 60  # default to 8 hours

    def get_target_zone_number(self, zone_str):
        """
        Return the target zone number from the zone provided.

        inputs:
            zone_str(str): specified zone, could be index or IP address
        returns:
            (int):  zone number.
        """
        if '.' in str(zone_str):
            # assume zone == IP address
            zone_number = list(sht31_ip.keys())[
                list(sht31_ip.values()).index(zone_str)]
        else:
            # assume index
            zone_number = int(zone_str)
        return zone_number

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

    def get_all_thermostat_metadata(self):
        """
        Return initial meta data queried from thermostat.

        inputs:
            None
        returns:
            None
        """
        # dump all meta data
        self.get_all_metadata()

        # dump uiData in a readable format
        return_data = self.get_all_metadata()
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(return_data)

    def get_all_metadata(self):
        """
        Get all the current thermostat metadata.

        inputs:
            None
        returns:
            (dict) empty dict.
        """
        r = requests.get(self.url)
        return r.json()

    def get_metadata(self, parameter=None):
        """
        Get the current thermostat metadata settings.

        inputs:
          parameter(str): target parameter, None = all settings
        returns:
          dict if parameter=None
          str if parameter != None
        """
        r = requests.get(self.url)
        if parameter is None:
            return r.json()
        else:
            return r.json()[parameter]

    def get_display_temp(self) -> float:
        """
        Return Temperature.

        inputs:
            None
        returns:
            (float): temperature in degrees.
        """
        return float(self.get_metadata(self.tempfield))

    def get_display_humidity(self) -> float:
        """
        Return Humidity.

        inputs:
            None
        returns:
            (float): humidity in %RH.
        """
        return float(self.get_metadata(self.humidityfield))

    def get_is_humidity_supported(self) -> bool:
        """Return humidity sensor status."""
        return True

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
    if (len(sys.argv) > 1 and
            int(sys.argv[1]) in api.SUPPORTED_THERMOSTATS[api.SHT31]["zones"]):
        zone_input = sys.argv[1]
    else:
        # default
        print("using default zone 0")
        zone_input = "0"
    # verify required env vars
    api.verify_required_env_variables(api.SHT31, zone_input)

    # save zone info
    api.user_inputs["zone"] = zone_input

    Thermostat = SHT31Thermometer(zone_input)
    print("thermostat meta data:")
    Thermostat.get_all_thermostat_metadata()
    Zone = SHT31Thermometer(Thermostat.device_id, Thermostat)
    print("current thermostat settings...")
    print("tmode1: %s" % Zone.get_system_switch_position())
    print("heat mode=%s" % Zone.get_heat_mode())
    print("cool mode=%s" % Zone.get_cool_mode())
    print("temporary hold minutes=%s" % Zone.get_temporary_hold_until_time())
    print("thermostat meta data=%s" % Thermostat.get_all_metadata())
    print("thermostat tempF=%s" %
          Thermostat.get_metadata(Thermostat.tempfield))
    print("thermostat display tempF=%s" % Thermostat.get_display_temp())
