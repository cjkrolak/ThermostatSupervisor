"""
mmm config file.
"""
ALIAS = "mmm50"

# all environment variables required by code should be registered here
env_variables = {
    }

# min required env variables on all runs
required_env_variables = {
    "GMAIL_USERNAME": None,
    "GMAIL_PASSWORD": None,
    }

# supported thermostat configs
supported_configs = {"module": "mmm",
                     "type": 2,
                     "zones": [0, 1],
                     "modes": ["OFF_MODE", "HEAT_MODE", "COOL_MODE"]}

# 3m50 thermostat IP addresses (on local net)
# user should configure these zones and IP addresses for their application.
MAIN_3M50 = 0  # zone 0
BASEMENT_3M50 = 1  # zone 1
mmm_metadata = {
    MAIN_3M50: {"ip_address": "192.168.86.82",  # local IP
                "zone_name": "Main Level",
                "host_name": "thermostat-fd-b3-be.lan",
                },
    BASEMENT_3M50: {"ip_address": "192.168.86.83",  # local IP
                    "zone_name": "Basement",
                    "host_name": "thermostat-27-67-11.lan",
                    }
}
