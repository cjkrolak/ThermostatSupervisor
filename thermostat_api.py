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

# Honeywell TCC authorization credentials from env vars.
# TCC_UNAME_KEY = 'TCC_USERNAME'
# TCC_PASSWORD_KEY = 'TCC_PASSWORD'
# tcc_uname = os.environ.get(TCC_UNAME_KEY, "<" +
#                            TCC_UNAME_KEY + "_KEY_MISSING>")
# tcc_pwd = os.environ.get(TCC_PASSWORD_KEY, "<" +
#                          TCC_PASSWORD_KEY + "_KEY_MISSING>")

# thermostats dict contains static thermostat parameters that
# are required outside of the thermostat class.
thermostats = {
    HONEYWELL: {
        "thermostat_constructor": h.HoneywellThermostat,
        # "args": [tcc_uname, tcc_pwd],  # args passed into constructor
        "zone": zone_number,
        "required_env_variables": {
            "TCC_USERNAME": None,
            "TCC_PASSWORD": None,
            "GMAIL_USERNAME": None,
            "GMAIL_PASSWORD": None,
            },
        },
    MMM50: {
        "thermostat_constructor": mmm.MMM50Thermostat,
        "args": [mmm_ip[zone_number]],  # args passed into constructor
        "zone": zone_number,
        "required_env_variables": {
            "GMAIL_USERNAME": None,
            "GMAIL_PASSWORD": None,
            },
        },
    SHT31: {
        "thermostat_constructor": sht31.SHT31Thermometer,
        "args": [sht31_ip[zone_number], sht31_port[zone_number]],
        "zone": zone_number,
        "required_env_variables": {
            "GMAIL_USERNAME": None,
            "GMAIL_PASSWORD": None,
            "SHT31_REMOTE_IP_ADDRESS_0": None,
            "SHT31_REMOTE_IP_ADDRESS_1": None,
            },
        }
}

# runtime overrides
# dict values will be populated in supervise.main
user_inputs = {
    "thermostat_type": None,
    "zone": None,
    "poll_time_sec": None,
    "connection_time_sec": None,
    }


def set_target_zone(tstat, zone):
    """
    Set the target Zone.

    For 3m50 and SHT31, the zone is defined by IP.
    For all other thermostats zone number is passed thru.

    inputs:
        zone(int):  zone number
    returns:
        None, updates thermostat dict.
    """
    if tstat == MMM50:
        thermostats[tstat]["args"] = [mmm_ip[zone]]
    elif tstat == SHT31:
        thermostats[tstat]["args"] = [sht31_ip[zone]]
    thermostats[tstat]["zone"] = zone


def verify_required_env_variables(tstat):
    """
    Verify all required env variables are present for thermostat
    configuration in use.

    inputs:
        tstat(int) thermostat type mapping to thermostat_api
    returns:
        (bool): True if all keys are present, else False
    """
    key_status = True  # default, all keys present
    for key in thermostats[tstat]["required_env_variables"]:
        print("checking required environment key: %s..." % key, end='')
        util.env_variables[key] = util.get_env_variable(key)["value"]
        if util.env_variables[key] is not None:
            print("OK")
        else:
            key_status = False
    print("\n")
    return key_status
