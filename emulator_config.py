"""
emulator thermostat config file.
"""
ALIAS = "emulator"
max_heat_setpoint = 66
min_cool_setpoint = 78

# all environment variables required by code should be registered here
env_variables = {
    }

# min required env variables on all runs
required_env_variables = {
    "GMAIL_USERNAME": None,
    "GMAIL_PASSWORD": None,
    }

# supported thermostat configs
supported_configs = {"module": "emulator",
                     "type": 0,
                     "zones": [0, 1],
                     "modes": ["OFF_MODE", "HEAT_MODE", "COOL_MODE",
                               "DRY_MODE", "AUTO_MODE"]}
