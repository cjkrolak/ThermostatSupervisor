"""
Honeywell config file.
"""
ALIAS = "honeywell"
default_zone = 0

# all environment variables specific to this thermostat type
env_variables = {
    "TCC_USERNAME": None,
    "TCC_PASSWORD": None,
}

# min required env variables on all runs
required_env_variables = {
    "TCC_USERNAME": None,
    "TCC_PASSWORD": None,
}

# supported thermostat configs
supported_configs = {"module": "honeywell",
                     "type": 1,
                     "zones": [default_zone],
                     "modes": ["OFF_MODE", "HEAT_MODE", "COOL_MODE",
                               "UNKNOWN_MODE"]}
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
