"""
emulator thermostat config file.
"""
ALIAS = "emulator"

# constants
MAX_HEAT_SETPOINT = 66.0  # float
MIN_COOL_SETPOINT = 78.0  # float
STARTING_MODE = "OFF_MODE"  # thermostat set mode when emulator starts
STARTING_TEMP = 72.0  # starting temperature when emulator starts
NORMAL_TEMP_VARIATION = 16.0  # reported value variation +/- this value
STARTING_HUMIDITY = 45.0  # starting humidity when emulator starts
NORMAL_HUMIDITY_VARIATION = 3.0  # reported val variation +/- this val

# all environment variables specific to this thermostat type
env_variables = {
}

# min required env variables on all runs
required_env_variables = {
}

# supported thermostat configs
supported_configs = {"module": "emulator",
                     "type": 0,
                     "zones": [0, 1],
                     "modes": ["OFF_MODE", "HEAT_MODE", "COOL_MODE",
                               "DRY_MODE", "AUTO_MODE", "UNKNOWN_MODE"]}

default_zone = supported_configs["zones"][0]
default_zone_name = ALIAS + "_" + str(default_zone)

argv = [
    "supervise.py",  # module
    ALIAS,  # thermostat
    str(default_zone),  # zone
    "19",  # poll time in sec
    "359",  # reconnect time in sec
    "3",  # tolerance
    "OFF_MODE",  # thermostat mode
    "2",  # number of measurements
    ]
