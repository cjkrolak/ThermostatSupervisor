"""
blink config file.
"""

ALIAS = "blink"

# constants
MAX_HEAT_SETPOINT = 68
MIN_COOL_SETPOINT = 70

MEASUREMENTS = 1  # number of MEASUREMENTS to average

# API field names
API_TEMPF_MEAN = "temperature_calibrated"
API_WIFI_STRENGTH = "wifi_strength"
API_BATTERY_VOLTAGE = "battery_voltage"
API_BATTERY_STATUS = "battery"


# all environment variables specific to this thermostat type
env_variables = {
    "BLINK_USERNAME": None,
    "BLINK_PASSWORD": None,
    "BLINK_2FA": None,
}

# min required env variables on all runs
required_env_variables = {
    "BLINK_USERNAME": None,
    "BLINK_PASSWORD": None,
    "BLINK_2FA": None,
}

# metadata dict
# 'zone_name' is a placeholder, used at Thermostat class level.
# update this list to match your zones as named in the blink app
# zone number assignments are arbitrary.
metadata = {
    # cabin zones
    0: {"zone_name": "cabin driveway"},
    1: {"zone_name": "beach"},
    2: {"zone_name": "front yard"},
    3: {"zone_name": "back yard"},
    4: {"zone_name": "front dogs"},
    5: {"zone_name": "road"},
    6: {"zone_name": "dock"},
    7: {"zone_name": "cabin garage"},
    8: {"zone_name": "loft"},
    9: {"zone_name": "cabin doorbell"},
    # home zones
    10: {"zone_name": "west"},
    11: {"zone_name": "north"},
    12: {"zone_name": "south"},
    13: {"zone_name": "nw-se"},
    14: {"zone_name": "home driveway"},
    15: {"zone_name": "cat camera"},
    16: {"zone_name": "home doorbell"},
}

# supported thermostat configs
supported_configs = {
    "module": "blink",
    "type": 6,
    "zones": list(metadata.keys()),
    "modes": ["OFF_MODE"],
    "zip_code": "55760",  # Zip code for outdoor weather data (zones 0-9)
    # Note: zones 10-16 are in a different location (55378) but weather
    # is fetched once per thermostat type for efficiency
}


def get_available_zones():
    """
    Return list of available zones.

    for this thermostat type, available zones is all zones.

    inputs:
        None.
    returns:
        (list) available zones.
    """
    return supported_configs["zones"]


default_zone = supported_configs["zones"][0]
default_zone_name = metadata[default_zone]

argv = [
    "supervise.py",  # module
    ALIAS,  # thermostat
    str(default_zone),  # zone
    "16",  # poll time in sec
    "356",  # reconnect time in sec
    "4",  # tolerance
    "OFF_MODE",  # thermostat mode
    "2",  # number of measurements
]

# flag to check thermostat response time during basic checkout
check_response_time = False
