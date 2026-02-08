"""
kumocloudv3 config file.
"""

from src import kumo_common_zones

ALIAS = "kumocloudv3"

# thermostat zones
# NOTE: Zone assignments are dynamically updated from v3 API at runtime
# The values below are defaults/fallbacks in case dynamic assignment fails
# v3 API zone assignments are not static - sometimes zone 0 is MAIN_LIVING,
# other times zone 1 is MAIN_LIVING, depending on the actual installation
MAIN_LIVING = 0  # zone 0 (default, updated dynamically at runtime)
KITCHEN = 1  # zone 1 (default, updated dynamically at runtime)
BASEMENT = 2  # zone 2 (default, updated dynamically at runtime)

# constants
MAX_HEAT_SETPOINT = 68
MIN_COOL_SETPOINT = 70

# all environment variables specific to this thermostat type
env_variables = {
    "KUMO_USERNAME": None,
    "KUMO_PASSWORD": None,
}

# supported thermostat configs
supported_configs = {
    "module": "kumocloudv3",
    "type": 4,
    "zones": [MAIN_LIVING, KITCHEN, BASEMENT],
    "modes": [
        "OFF_MODE",
        "HEAT_MODE",
        "COOL_MODE",
        "DRY_MODE",
        "AUTO_MODE",
        "UNKNOWN_MODE",
    ],
    "zip_code": "55760",  # Zip code for outdoor weather data
}

# metadata dict
# 'zone_name' is updated by Zone.get_zone_name()
# 'host_name' is just for reference
metadata = {
    MAIN_LIVING: {
        "zone_name": kumo_common_zones.ZONE_NAME_MAIN_LEVEL,
        "host_name": "tbd",
        "serial_number": None,
    },
    KITCHEN: {
        "zone_name": kumo_common_zones.ZONE_NAME_KITCHEN,
        "host_name": "tbd",
        "serial_number": None,
    },
    BASEMENT: {
        "zone_name": kumo_common_zones.ZONE_NAME_BASEMENT,
        "host_name": "tbd",
        "serial_number": None,
    },
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
default_zone_name = metadata[default_zone]["zone_name"]

argv = [
    "supervise.py",  # module
    ALIAS,  # thermostat
    str(default_zone),  # zone
    "18",  # poll time in sec
    "358",  # reconnect time in sec
    "2",  # tolerance
    "OFF_MODE",  # thermostat mode
    "2",  # number of measurements
]

# flag to check thermostat response time during basic checkout
check_response_time = False
