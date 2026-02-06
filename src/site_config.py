"""
Site configuration for managing multiple thermostats.

This module defines site configurations that can supervise multiple
thermostats simultaneously with independent settings for each.
"""

ALIAS = "site"

# all environment variables specific to site operations
env_variables = {}

# min required env variables on all runs
required_env_variables = {}


def get_default_site_config():
    """
    Get the default site configuration.

    Returns:
        dict: Default site configuration with sample thermostats.
    """
    return {
        "site_name": "default_site",
        "thermostats": [
            {
                "thermostat_type": "emulator",
                "zone": 0,
                "enabled": True,
                "poll_time": 60,
                "connection_time": 300,
                "tolerance": 2,
                "target_mode": "OFF_MODE",
                "measurements": 2,
            },
            {
                "thermostat_type": "emulator",
                "zone": 1,
                "enabled": True,
                "poll_time": 60,
                "connection_time": 300,
                "tolerance": 2,
                "target_mode": "OFF_MODE",
                "measurements": 2,
            },
        ],
    }


# supported site configs
supported_configs = {
    "module": "site",
    "type": 100,  # unique type ID for site
    "sites": ["default_site"],
}
