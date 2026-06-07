"""
kumolocal config file.
"""

import configparser
import os

from src import kumo_common_zones

ALIAS = "kumolocal"

# thermostat zones
LIVING_ROOM = 0  # zone 0
KITCHEN = 1  # zone 1
BASEMENT = 2  # zone 2

# constants
MAX_HEAT_SETPOINT = 68
MIN_COOL_SETPOINT = 70

# all environment variables specific to this thermostat type
env_variables = {
    "KUMO_USERNAME": None,
    "KUMO_PASSWORD": None,
}

# supported thermostat configs
supported_configs = {
    "module": "kumolocal",
    "type": 5,
    "zones": [LIVING_ROOM, KITCHEN, BASEMENT],
    "modes": [
        "OFF_MODE",
        "HEAT_MODE",
        "COOL_MODE",
        "DRY_MODE",
        "AUTO_MODE",
        "UNKNOWN_MODE",
    ],
    "zip_code": "55760",  # Zip code for outdoor weather data
}

# Path to INI file with local IP addresses (relative to project root)
INI_FILE = "kumolocal.ini"


# metadata dict
# 'zone_name' is a placeholder, used at Thermostat class level.
# 'zone_name' is updated by device memory via Zone.get_zone_name()
# 'host_name' is used for DNS lookup to determine if device
# 'ip_address' is loaded from kumolocal.ini; falls back to defaults below.
# 'local_net_available' is set by local network detection
metadata = {
    LIVING_ROOM: {
        "ip_address": "192.168.86.84",  # default; overridden by kumolocal.ini
        "zone_name": kumo_common_zones.ZONE_NAME_LIVING_ROOM,
        "host_name": "tbd",  # used for DNS lookup
        "local_net_available": None,  # updated by local network detection
    },
    KITCHEN: {
        "ip_address": "192.168.86.24",  # default; overridden by kumolocal.ini
        "zone_name": kumo_common_zones.ZONE_NAME_KITCHEN,
        "host_name": "tbd",  # used for DNS lookup
        "local_net_available": None,  # updated by local network detection
    },
    BASEMENT: {
        "ip_address": "192.168.86.47",  # default; overridden by kumolocal.ini
        "zone_name": kumo_common_zones.ZONE_NAME_BASEMENT,
        "host_name": "tbd",  # used for DNS lookup
        "local_net_available": None,  # updated by local network detection
    },
}


def load_ip_addresses_from_ini(ini_file=None):
    """Load IP addresses from kumolocal.ini and update the metadata dict.

    Each section name in the INI file must match the zone_name for a zone
    (e.g. "Living Room", "Kitchen", "Basement").  If the file is not found,
    the default IP addresses already in the metadata dict are kept.

    inputs:
        ini_file (str or None): path to the INI file.  When None, resolves
            to INI_FILE relative to the directory containing this module's
            project root (two levels up from src/).
    returns:
        (bool): True if the file was found and parsed, False otherwise.
    """
    if ini_file is None:
        # Resolve project root: .../ThermostatSupervisor/src/ -> project root
        src_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(src_dir)
        ini_file = os.path.join(project_root, INI_FILE)

    config = configparser.ConfigParser()
    if not config.read(ini_file):
        return False

    # Build a normalized-name -> zone_id reverse lookup
    name_to_zone = {
        "".join(c.lower() for c in meta["zone_name"] if c.isalnum()): zone_id
        for zone_id, meta in metadata.items()
    }

    for section in config.sections():
        normalized = "".join(c.lower() for c in section if c.isalnum())
        zone_id = name_to_zone.get(normalized)
        if zone_id is not None:
            ip = config[section].get("ip_address", "").strip()
            if ip:
                metadata[zone_id]["ip_address"] = ip

    return True


# Load IP addresses from INI file at module import time.
# Failures are silent so that importing this module never raises.
load_ip_addresses_from_ini()


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
    "16",  # poll time in sec
    "356",  # reconnect time in sec
    "4",  # tolerance
    "OFF_MODE",  # thermostat mode
    "2",  # number of measurements
]

# flag to check thermostat response time during basic checkout
check_response_time = False
