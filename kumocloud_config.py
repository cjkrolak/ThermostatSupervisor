"""
kumocloud config file.
"""
ALIAS = "kumocloud"

# all context variables required by code should be registered here
env_variables = {
    "KUMO_USERNAME": None,
    "KUMO_PASSWORD": None,
    }

# min required env variables on all runs
required_env_variables = {
    "GMAIL_USERNAME": None,
    "GMAIL_PASSWORD": None,
    'KUMO_USERNAME': None,
    'KUMO_PASSWORD': None,
    }

# supported thermostat configs
supported_configs = {"module": "kumocloud",
                     "type": 4,
                     "zones": [0, 1],
                     "modes": ["OFF_MODE", "HEAT_MODE", "COOL_MODE",
                               "DRY_MODE", "AUTO_MODE"]}
