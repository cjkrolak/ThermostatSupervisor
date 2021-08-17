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
import utilities as util


# thermostat types
HONEYWELL = "honeywell"
MMM50 = "mmm50"
SHT31 = "sht31"
SUPPORTED_THERMOSTATS = {
    HONEYWELL: {"type": 1, "zones": [0]},
    MMM50: {"type": 2, "zones": [0, 1]},
    SHT31: {"type": 3, "zones": [0, 1]},
    }

# 3m50 thermostat IP addresses (local net)
MAIN_3M50 = 0  # zone 0
BASEMENT_3M50 = 1  # zone 1
mmm_ip = {
    MAIN_3M50: "192.168.86.82",  # local IP
    BASEMENT_3M50: "192.168.86.83",  # local IP
}

# sht31 thermometer IP addresses (local net)
LOFT_SHT31 = 0  # zone 0
LOFT_SHT31_REMOTE = 1  # zone 1
remote_ip_env_str = 'SHT31_REMOTE_IP_ADDRESS' + '_' + str(LOFT_SHT31_REMOTE)
sht31_remote_ip = os.environ.get(remote_ip_env_str, "<" +
                                 remote_ip_env_str + "_KEY_MISSING>")
sht31_ip = {
    LOFT_SHT31: "192.168.86.15",  # local IP
    LOFT_SHT31_REMOTE: sht31_remote_ip,  # remote IP
    }
sht31_port = {
    LOFT_SHT31: "5000",
    LOFT_SHT31_REMOTE: "5000",
    }

# target zone for monitoring
zone_number = 0  # default

# Class constructor parameters for each thermostat
TCC_UNAME_KEY = 'TCC_USERNAME'
TCC_PASSWORD_KEY = 'TCC_PASSWORD'
tcc_uname = os.environ.get(TCC_UNAME_KEY, "<" +
                           TCC_UNAME_KEY + "_KEY_MISSING>")
tcc_pwd = os.environ.get(TCC_PASSWORD_KEY, "<" +
                         TCC_PASSWORD_KEY + "_KEY_MISSING>")
thermostats = {
    HONEYWELL: {
        "thermostat_constructor": h.HoneywellThermostat,
        "args": [tcc_uname, tcc_pwd],
        "zone_constructor": h.HoneywellZone,
        "zone": zone_number,
        "poll_time_sec": 10 * 60,  # default to 10 minutes
        # min practical value is 2 minutes based on empirical test
        # max value was 3, higher settings will cause HTTP errors, why?
        # not showing error on Pi at 10 minutes, so changed default to 10 min.
        "connection_time_sec": 8 * 60 * 60,  # default to 8 hours
        "required_env_variables": {
            "TCC_USERNAME": None,
            "TCC_PASSWORD": None,
            "GMAIL_USERNAME": None,
            "GMAIL_PASSWORD": None,
            "GMAIL_TO_USERNAME": None,
            },
        },
    MMM50: {
        "thermostat_constructor": mmm.MMM50Thermostat,
        "args": [mmm_ip[zone_number]],
        "zone_constructor": mmm.MMM50Thermostat,
        "zone": zone_number,
        "poll_time_sec": 10 * 60,  # default to 10 minutes
        "connection_time_sec": 8 * 60 * 60,  # default to 8 hours
        "required_env_variables": {
            "GMAIL_USERNAME": None,
            "GMAIL_PASSWORD": None,
            "GMAIL_TO_USERNAME": None,
            },
        },
    SHT31: {
        "thermostat_constructor": sht31.SHT31Thermometer,
        "args": [sht31_ip[zone_number], sht31_port[zone_number]],
        "zone_constructor": sht31.SHT31Thermometer,
        "zone": zone_number,
        "poll_time_sec": 1 * 60,  # default to 10 minutes
        "connection_time_sec": 8 * 60 * 60,  # default to 8 hours
        "required_env_variables": {
            "GMAIL_USERNAME": None,
            "GMAIL_PASSWORD": None,
            "GMAIL_TO_USERNAME": None,
            "SHT31_REMOTE_IP_ADDRESS_0": None,
            "SHT31_REMOTE_IP_ADDRESS_1": None,
            },
        }
}


def set_target_zone(tstat, zone):
    """
    Set the target Zone.

    For 3m50 and SHT31, the zone is defined by IP.
    """
    if tstat == MMM50:
        thermostats[tstat]["args"] = [mmm_ip[zone]]
    elif tstat == SHT31:
        thermostats[tstat]["args"] = [sht31_ip[zone]]
    thermostats[tstat]["zone"] = zone


def set_poll_time(tstat, poll_time_sec):
    """Set the poll time override from runtime."""
    thermostats[tstat]["poll_time_sec"] = poll_time_sec


def set_connection_time(tstat, connection_time_sec):
    """Set the connection time override from runtime."""
    thermostats[tstat]["connection_time_sec"] = connection_time_sec


def verify_required_env_variables(tstat):
    """
    Verify all required env variables are present for thermostat
    configuration in use.
    """
    for key in thermostats[tstat]["required_env_variables"]:
        print("checking required environment key: %s..." % key, end='')
        try:
            util.env_variables[key] = util.get_env_variable(key)["value"]
            print("OK")
        except KeyError:
            print("NOT FOUND!")
            raise
    print("\n")
