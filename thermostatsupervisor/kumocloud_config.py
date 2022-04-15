"""
kumocloud config file.
"""
ALIAS = "kumocloud"
# thermostat zones
MAIN_LEVEL = 0  # zone 0
BASEMENT = 1  # zone 1

MAX_HEAT_SETPOINT = 68
MIN_COOL_SETPOINT = 70

# all environment variables specific to this thermostat type
env_variables = {
    "KUMO_USERNAME": None,
    "KUMO_PASSWORD": None,
}

# min required env variables on all runs
required_env_variables = {
    'KUMO_USERNAME': None,
    'KUMO_PASSWORD': None,
}

# supported thermostat configs
supported_configs = {"module": "kumocloud",
                     "type": 4,
                     "zones": [MAIN_LEVEL, BASEMENT],
                     "modes": ["OFF_MODE", "HEAT_MODE", "COOL_MODE",
                               "DRY_MODE", "AUTO_MODE", "UNKNOWN_MODE"]}

metadata = {
    MAIN_LEVEL: {"zone_name": "main",
                 "host_name": "tbd",
                 },
    BASEMENT: {"zone_name": "basement",
               "host_name": "tbd",
               },
}

default_zone = supported_configs["zones"][0]
default_zone_name = ALIAS + "_" + str(default_zone)

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
