"""
Thermostat API.

This file should be updated for any new thermostats supported and
any changes to thermostat configs.
"""
# built-ins
import os

# local imports
import Honeywell as h

# thermostat types
HONEYWELL = "Honeywell"
THREEM50 = "THREEM50"
SUPPORTED_THERMOSTATS = {
    HONEYWELL: 1,
    THREEM50: 2,
    }

# thermostat IP addresses (local net)
MAIN_3M50 = "192.168.86.82"
BASEMENT_3M50 = "192.168.86.83"

# Class constructor parameters for each thermostat
thermostats = {
    HONEYWELL: {
        "thermostat_constructor": h.HoneywellThermostat,
        "args": (os.environ['TCC_USERNAME'], os.environ['TCC_PASSWORD']),
        "zone_constructor": h.HoneywellZone,
        },
    THREEM50: {
        }
}
