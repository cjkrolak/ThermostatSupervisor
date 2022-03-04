"""
kumocloud config file.
"""
ALIAS = "kumocloud"
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
                     "zones": [0, 1],
                     "modes": ["OFF_MODE", "HEAT_MODE", "COOL_MODE",
                               "DRY_MODE", "AUTO_MODE", "UNKNOWN_MODE"]}
