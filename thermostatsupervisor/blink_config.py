"""
blink config file.
"""
ALIAS = "blink"

# camera zones
CABIN_DOORBELL = "cabin doorbell"
DRIVEWAY = "driveway"
BEACH = "beach"
FRONT_YARD = "front yard"
BACK_YARD = "back yard"

# constants
MAX_HEAT_SETPOINT = 68
MIN_COOL_SETPOINT = 70

# all environment variables specific to this thermostat type
env_variables = {
    "BLINK_USERNAME": None,
    "BLINK_PASSWORD": None,
    "BLINK_2FA": None,
}

# min required env variables on all runs
required_env_variables = {
    'BLINK_USERNAME': None,
    'BLINK_PASSWORD': None,
    "BLINK_2FA": None,
}

# supported thermostat configs
supported_configs = {"module": "blink",
                     "type": 5,
                     "zones": [CABIN_DOORBELL, DRIVEWAY, BEACH, FRONT_YARD,
                               BACK_YARD],
                     "modes": ["OFF_MODE", "HEAT_MODE", "COOL_MODE",
                               "DRY_MODE", "AUTO_MODE", "UNKNOWN_MODE"]}

# metadata dict
# 'zone_name' is a placeholder, used at Thermostat class level.
metadata = {
    0: {"zone_name": DRIVEWAY},
    1: {"zone_name": BEACH},
    2: {"zone_name": FRONT_YARD},
    3: {"zone_name": BACK_YARD},
    4: {"zone_name": CABIN_DOORBELL},
}

default_zone = supported_configs["zones"][0]
default_zone_name = ALIAS + "_" + str(default_zone)

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
