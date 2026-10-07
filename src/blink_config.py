"""
blink config file.
"""

ALIAS = "blink"

# constants
MAX_HEAT_SETPOINT = 68
MIN_COOL_SETPOINT = 70

MEASUREMENTS = 1  # number of MEASUREMENTS to average

# API field names
API_TEMPF_MEAN = "temperature_calibrated"
API_WIFI_STRENGTH = "wifi_strength"
API_BATTERY_VOLTAGE = "battery_voltage"
API_BATTERY_STATUS = "battery"


# all environment variables specific to this thermostat type
env_variables = {
    "BLINK_USERNAME": None,
    "BLINK_PASSWORD": None,
    "BLINK_2FA": None,
}

# BLINK_2FA is optional and loaded through runtime fallback logic.
required_env_variables = {
    "BLINK_USERNAME": None,
    "BLINK_PASSWORD": None,
}

# Per-zone metadata, keyed by the configured zone number. Blink zones can span
# locations, so a zone zip code overrides the global default for weather data.
# `zone_name` is required and should match the name used in the Blink app.
# Zone numbers are arbitrary. Other thermostat configs may also include
# `host_name`, `ip_address`, `serial_number`, or runtime status fields.
metadata = {
    # cabin back zones
    0: {"zone_name": "garage door", "zip_code": "55760"},
    1: {"zone_name": "main driveway", "zip_code": "55760"},
    2: {"zone_name": "front yard", "zip_code": "55760"},
    3: {"zone_name": "back yard", "zip_code": "55760"},
    4: {"zone_name": "road", "zip_code": "55760"},
    5: {"zone_name": "garage back", "zip_code": "55760"},
    6: {"zone_name": "cabin doorbell", "zip_code": "55760"},
    # home zones
    7: {"zone_name": "west", "zip_code": "55378"},
    8: {"zone_name": "north", "zip_code": "55378"},
    9: {"zone_name": "south", "zip_code": "55378"},
    10: {"zone_name": "nw-se", "zip_code": "55378"},
    11: {"zone_name": "home driveway", "zip_code": "55378"},
    12: {"zone_name": "cat camera", "zip_code": "55378"},
    13: {"zone_name": "home doorbell", "zip_code": "55378"},
    # cabin front zones
    14: {"zone_name": "front dogs", "zip_code": "55760"},
    15: {"zone_name": "beach", "zip_code": "55760"},
    16: {"zone_name": "dock", "zip_code": "55760"},
    17: {"zone_name": "deck", "zip_code": "55760"},
    18: {"zone_name": "basement kitchen", "zip_code": "55760"},
    19: {"zone_name": "loft", "zip_code": "55760"},
    20: {"zone_name": "garage", "zip_code": "55760"},
}

# supported thermostat configs
supported_configs = {
    "module": "blink",
    "type": 6,
    "zones": list(metadata.keys()),
    "modes": ["OFF_MODE"],
    # Keep one default for thermostat types or zones without a specific value.
    "zip_code": "55760",
}


def get_available_zones():
    """
    Return list of available zones.

    for this thermostat type, available zones is all zones.

    inputs:
        None.
    returns:
        (list) available zones.
    """
    return supported_configs["zones"]


default_zone = supported_configs["zones"][0]
default_zone_name = metadata[default_zone]["zone_name"]

argv = [
    "supervise.py",  # module
    ALIAS,  # thermostat
    str(default_zone),  # zone
    "300",  # poll time in sec (5 minutes to reduce server load)
    "7200",  # reconnect time in sec (2 hours)
    "4",  # tolerance
    "OFF_MODE",  # thermostat mode
    "2",  # number of measurements
]

# flag to check thermostat response time during basic checkout
check_response_time = False
