"""
kumolocal config file.
"""
ALIAS = "kumolocal"
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
supported_configs = {"module": "kumolocal",
                     "type": 5,
                     "zones": [0, 1],
                     "modes": ["OFF_MODE", "HEAT_MODE", "COOL_MODE",
                               "DRY_MODE", "AUTO_MODE"]}

# Kumocloud zone configuration (on local net)
MAIN_KUMO = 0  # zone 0
BASEMENT_KUMO = 1  # zone 1
kc_metadata = {
    MAIN_KUMO: {"ip_address": "192.168.86.229",  # local IP, for ref only.
                "zone_name": "Main Level",  # customize for your site.
                },
    BASEMENT_KUMO: {"ip_address": "192.168.86.236",  # local IP, for ref only.
                    "zone_name": "Basement",  # customize for your site.
                    },
}
