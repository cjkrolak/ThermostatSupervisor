"""
Thermostat API.

This file should be updated for any new thermostats supported and
any changes to thermostat configs.
"""
# built-ins
import os

# local imports
import honeywell as h
import mmm as mmm


# thermostat types
HONEYWELL = "honeywell"
MMM50 = "mmm50"
SUPPORTED_THERMOSTATS = {
    HONEYWELL: {"type": 1, "zones": [0]},
    MMM50: {"type": 2, "zones": [0, 1]},
    }

# thermostat IP addresses (local net)
MAIN_3M50 = 0  # zone 0
BASEMENT_3M50 = 1  # zone 1
mmm_ip = {
    MAIN_3M50: "192.168.86.82",
    BASEMENT_3M50: "192.168.86.83",
}

# target zone for monitoring
zone_number = 0  # default

# Class constructor parameters for each thermostat
thermostats = {
    HONEYWELL: {
        "thermostat_constructor": h.HoneywellThermostat,
        "args": [os.environ['TCC_USERNAME'], os.environ['TCC_PASSWORD']],
        "zone_constructor": h.HoneywellZone,
        "zone": zone_number
        },
    MMM50: {
        "thermostat_constructor": mmm.MMM50Thermostat,
        "args": [mmm_ip[zone_number]],
        "zone_constructor": mmm.MMM50Thermostat,
        "zone": zone_number
        }
}


def set_target_zone(zone):
    """Set the target Zone."""
    # refresh zone information
    thermostats[MMM50]["args"] = [mmm_ip[zone]]
    thermostats[MMM50]["zone"] = zone
