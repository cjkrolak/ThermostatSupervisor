"""
mmm config file.
"""
ALIAS = "mmm50"

# 3m50 thermostat IP addresses (on local net)
# user should configure these zones and IP addresses for their application.
MAIN_3M50 = 0  # zone 0
BASEMENT_3M50 = 1  # zone 1

# all environment variables specific to this thermostat type
env_variables = {
}

# min required env variables on all runs
required_env_variables = {
}

# supported thermostat configs
supported_configs = {"module": "mmm",
                     "type": 2,
                     "zones": [0, 1],
                     "modes": ["OFF_MODE", "HEAT_MODE", "COOL_MODE",
                               "UNKNOWN_MODE"]}

# metadata dict
# 'zone_name' is returned by self.get_zone_name
# 'host_name' is used for dns lookup of IP address for each zone
# 'ip_address' key (if present is used for hard-coding IP address
metadata = {
    MAIN_3M50: {"zone_name": "Main Level",
                "host_name": "thermostat-fd-b3-be.lan",
                },
    BASEMENT_3M50: {"zone_name": "Basement",
                    "host_name": "thermostat-27-67-11.lan",
                    }
}

default_zone = supported_configs["zones"][0]
default_zone_name = metadata[default_zone]["zone_name"]

argv = [
    "supervise.py",  # module
    ALIAS,  # thermostat
    str(default_zone),  # zone
    "18",  # poll time in sec
    "358",  # reconnect time in sec
    "2",  # tolerance
    "OFF_MODE",  # thermostat mode
    "2",  # number of measurements
    ]
