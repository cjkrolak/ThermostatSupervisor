"""
blink config file.
"""
ALIAS = "blink"

# camera zone names
CABIN_DOORBELL = "cabin doorbell"
DRIVEWAY = "driveway"
BEACH = "beach"
FRONT_YARD = "front yard"
BACK_YARD = "back yard"
WEST = "west"
NORTH = "north"
SOUTH = "south"
NW_SE = "nw-se"

# constants
MAX_HEAT_SETPOINT = 68
MIN_COOL_SETPOINT = 70

MEASUREMENTS = 1  # number of MEASUREMENTS to average
API_TEMPF_MEAN = "temperature_calibrated"

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

# metadata dict
# 'zone_name' is a placeholder, used at Thermostat class level.
metadata = {
    0: {"zone_name": DRIVEWAY},
    1: {"zone_name": BEACH},
    2: {"zone_name": FRONT_YARD},
    3: {"zone_name": BACK_YARD},
    4: {"zone_name": CABIN_DOORBELL},
    5: {"zone_name": WEST},
    6: {"zone_name": NORTH},
    7: {"zone_name": SOUTH},
    8: {"zone_name": NW_SE},
}

# supported thermostat configs
supported_configs = {"module": "blink",
                     "type": 6,
                     "zones": list(metadata.keys()),
                     "modes": ["OFF_MODE"]}

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
