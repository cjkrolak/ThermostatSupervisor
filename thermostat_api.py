"""
Thermostat API.

This file should be updated for any new thermostats supported and
any changes to thermostat configs.
"""
# built-ins
import os

# local imports
import honeywell as h
import mmm
import sht31


# thermostat types
HONEYWELL = "honeywell"
MMM50 = "mmm50"
SHT31 = "sht31"
SUPPORTED_THERMOSTATS = {
    HONEYWELL: {"type": 1, "zones": [0]},
    MMM50: {"type": 2, "zones": [0, 1]},
    SHT31: {"type": 3, "zones": [0]},
    }

# 3m50 thermostat IP addresses (local net)
MAIN_3M50 = 0  # zone 0
BASEMENT_3M50 = 1  # zone 1
mmm_ip = {
    MAIN_3M50: "192.168.86.82",
    BASEMENT_3M50: "192.168.86.83",
}

# sht31 thermometer IP addresses (local net)
LOFT_SHT31 = 0  # zone 0
sht31_ip = {
    LOFT_SHT31: "192.168.86.15",
    }
sht31_port = {
    LOFT_SHT31: "5000",
    }

# target zone for monitoring
zone_number = 0  # default

# Class constructor parameters for each thermostat
thermostats = {
    HONEYWELL: {
        "thermostat_constructor": h.HoneywellThermostat,
        "args": [os.environ['TCC_USERNAME'], os.environ['TCC_PASSWORD']],
        "zone_constructor": h.HoneywellZone,
        "zone": zone_number,
        "poll_time_sec": 10 * 60,  # default to 10 minutes
        # min practical value is 2 minutes based on empirical test
        # max value was 3, higher settings will cause HTTP errors, why?
        # not showing error on Pi at 10 minutes, so changed default to 10 min.
        "connection_time_sec": 8 * 60 * 60,  # default to 8 hours
        },
    MMM50: {
        "thermostat_constructor": mmm.MMM50Thermostat,
        "args": [mmm_ip[zone_number]],
        "zone_constructor": mmm.MMM50Thermostat,
        "zone": zone_number,
        "poll_time_sec": 10 * 60,  # default to 10 minutes
        "connection_time_sec": 8 * 60 * 60,  # default to 8 hours
        },
    SHT31: {
        "thermostat_constructor": sht31.SHT31Thermometer,
        "args": [sht31_ip[zone_number], sht31_port[zone_number]],
        "zone_constructor": sht31.SHT31Thermometer,
        "zone": zone_number,
        "poll_time_sec": 1 * 60,  # default to 10 minutes
        "connection_time_sec": 8 * 60 * 60,  # default to 8 hours
        }
}


def set_target_zone(tstat, zone):
    """Set the target Zone."""
    if tstat == MMM50:
        thermostats[tstat]["args"] = [mmm_ip[zone]]
    thermostats[tstat]["zone"] = zone


def set_poll_time(tstat, poll_time_sec):
    """Set the poll time override from runtime."""
    thermostats[tstat]["poll_time_sec"] = poll_time_sec


def set_connection_time(tstat, connection_time_sec):
    """Set the connection time override from runtime."""
    thermostats[tstat]["connection_time_sec"] = connection_time_sec
