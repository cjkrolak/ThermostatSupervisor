"""
Thermostat API.

This file should be updated for any new thermostats supported and
any changes to thermostat configs.
"""
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

# target zone for monitoring
zone_number = 0  # default

thermostats = {
    HONEYWELL: {
        "thermostat_constructor": h.HoneywellThermostat,
        "required_env_variables": {
            "TCC_USERNAME": None,
            "TCC_PASSWORD": None,
            "GMAIL_USERNAME": None,
            "GMAIL_PASSWORD": None,
            },
        },
    MMM50: {
        "thermostat_constructor": mmm.MMM50Thermostat,
        "required_env_variables": {
            "GMAIL_USERNAME": None,
            "GMAIL_PASSWORD": None,
            },
        },
    SHT31: {
        "thermostat_constructor": sht31.SHT31Thermometer,
        "required_env_variables": {
            "GMAIL_USERNAME": None,
            "GMAIL_PASSWORD": None,
            "SHT31_REMOTE_IP_ADDRESS_": None,  # prefix only, excludes zone
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


def verify_required_env_variables(tstat, zone_str):
    """
    Verify all required env variables are present for thermostat
    configuration in use.

    inputs:
        tstat(int) thermostat type mapping to thermostat_api
        zone_str(str): zone input as a string
    returns:
        (bool): True if all keys are present, else False
    """
    key_status = True  # default, all keys present
    for key in thermostats[tstat]["required_env_variables"]:
        # any env key ending in '_' should have zone number appended to it.
        if key[-1] == '_':
            # append zone info to key
            key = key + str(zone_str)
        print("checking required environment key: %s..." % key, end='')
        util.env_variables[key] = util.get_env_variable(key)["value"]
        if util.env_variables[key] is not None:
            print("OK")
        else:
            util.log_msg("%s: zone %s: FATAL error: one or more required "
                         "environemental keys are missing, exiting program" %
                         (tstat, zone_str), mode=util.BOTH_LOG)
            key_status = False
            raise KeyError
    print("\n")
    return key_status
