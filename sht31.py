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
import pprint
import requests
import sys

# local imports
import thermostat_common as tc
import utilities as util


class SHT31Thermometer(tc.ThermostatCommonZone):
    """SHT31 thermometer functions."""

    system_switch_position = {
        tc.ThermostatCommonZone.COOL_MODE: tc.bogus_int,
        tc.ThermostatCommonZone.HEAT_MODE: tc.bogus_int,
        tc.ThermostatCommonZone.OFF_MODE: 0,
        tc.ThermostatCommonZone.AUTO_MODE: tc.bogus_int,
        }

    def __init__(self, ip_address, *_, **__):
        """
        Constructor, connect to thermostat.

        inputs:
            ip_address(str):  ip address of thermostat
        """
        self.device_id = 0  # not currently used since IP identifies device
        self.ip_address = ip_address
        self.port = "5000"  # Flask server port on SHT31 host
        self.url = "http://" + self.ip_address + ":" + self.port
        self.tempfield = util.API_TEMP_FIELD  # must match flask API
        self.humidityfield = util.API_HUMIDITY_FIELD  # must match flask API

    def get_target_zone_id(self):
        """
        Return the target zone ID.

        inputs:
            None
        returns:
            (str):  IP address of target zone.
        """
        return self.ip_address

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


if __name__ == "__main__":

    ip_main_sht31 = "192.168.86.15"
    util.log_msg.debug = True  # debug mode set

    # set ip address
    if len(sys.argv) > 1 and sys.argv[1] in [ip_main_sht31, ip_main_sht31]:
        ip = sys.argv[1]
    else:
        # default
        ip = ip_main_sht31

    tstat = SHT31Thermometer(ip)
    zone = SHT31Thermometer(ip, tstat)
    print("current thermostat settings...")
    print("tmode1: %s" % zone.get_system_switch_position())
    print("heat mode=%s" % zone.get_heat_mode())
    print("cool mode=%s" % zone.get_cool_mode())
    print("temporary hold minutes=%s" % zone.get_temporary_hold_until_time())
    print("thermostat meta data=%s" % tstat.get_all_metadata())
    print("thermostat tempF=%s" % tstat.get_metadata(tstat.tempfield))
    print("thermostat display tempF=%s" % tstat.get_display_temp())
