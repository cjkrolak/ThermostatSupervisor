"""
kumocloudv3 config file.
"""
ALIAS = "kumocloudv3"

# thermostat zones
MAIN_LEVEL = 0  # zone 0
BASEMENT = 1  # zone 1

# constants
MAX_HEAT_SETPOINT = 68
MIN_COOL_SETPOINT = 70

# all environment variables specific to this thermostat type
env_variables = {
    "KUMO_USERNAME": None,
    "KUMO_PASSWORD": None,
}

# min required env variables on all runs
required_env_variables = {
    "KUMO_USERNAME": None,
    "KUMO_PASSWORD": None,
}

# supported thermostat configs
supported_configs = {
    "module": "kumocloudv3",
    "type": 4,
    "zones": [MAIN_LEVEL, BASEMENT],
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
    MAIN_LEVEL: {
        "zone_name": "Main Level",
        "host_name": "tbd",
        "serial_number": None,
    },
    BASEMENT: {
        "zone_name": "basement",
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
