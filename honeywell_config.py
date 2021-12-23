"""
Honeywell config file.
"""
ALIAS = "honeywell"

# all context variables required by code should be registered here
env_variables = {
    "TCC_USERNAME": None,
    "TCC_PASSWORD": None,
    }

# min required env variables on all runs
required_env_variables = {
    "TCC_USERNAME": None,
    "TCC_PASSWORD": None,
    "GMAIL_USERNAME": None,
    "GMAIL_PASSWORD": None,
    }

# supported thermostat configs
supported_configs = {"module": "honeywell",
                     "type": 1,
                     "zones": [0],
                     "modes": ["OFF_MODE", "HEAT_MODE", "COOL_MODE"]}
