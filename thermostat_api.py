"""
Thermostat API.

This file should be updated for any new thermostats supported and
any changes to thermostat configs.
"""
# built ins
import sys

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
    "tolerance_degrees": None,
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


def parse_runtime_parameter(key, position, datatype, default_value,
                            valid_range, input_list=None):
    """
    Parse the runtime parameter.

    inputs:
        key(str): name of runtime parameter in api.user_input dict.
        position(int): position of runtime variable in command line.
        datatype(int or str): data type to cast input str to.
        default_value(int or str):  default value.
        valid_range(list):  range of valid values for input parameter.
        input_list(list):  list of input variables, if None will use args.
    returns:
        (int or str): input value
    """
    if input_list is None:
        target = sys.argv
    else:
        target = input_list

    try:
        result = datatype(target[position].lower())
    except IndexError:
        result = default_value
    if result not in valid_range:
        print("WARNING: '%s' is not a valid choice for '%s', "
              "using default(%s)" % (result, key, default_value))
        result = default_value

    # populate the user_input dictionary
    user_inputs[key] = result
    return result


def parse_all_runtime_parameters():
    """
    Parse all possible runtime parameters.

    inputs:
        None
    returns:
        (list) of all runtime parameters.
    """
    # parse thermostat type parameter (argv[1] if present):
    tstat_type = parse_runtime_parameter("thermostat_type", 1, str,
                                         HONEYWELL,
                                         SUPPORTED_THERMOSTATS)

    # parse zone number parameter (argv[2] if present):
    zone_input = parse_runtime_parameter("zone", 2, int, 0,
                                         SUPPORTED_THERMOSTATS[
                                             tstat_type]["zones"])

    # parse the poll time override (argv[3] if present):
    poll_time_input = parse_runtime_parameter("poll_time_sec", 3, int, 10 * 60,
                                              range(0, 24 * 60 * 60))

    # parse the connection time override (argv[4] if present):
    connection_time_input = parse_runtime_parameter("connection_time_sec", 4,
                                                    int, 8 * 60 * 60,
                                                    range(0, 24 * 60 * 60))

    # parse the tolerance override (argv[5] if present):
    tolerance_degrees_input = parse_runtime_parameter("tolerance_degrees", 5,
                                                      int, 2, range(0, 10))
    return [tstat_type, zone_input, poll_time_input, connection_time_input,
            tolerance_degrees_input]
