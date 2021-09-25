"""
Thermostat API.

This file should be updated for any new thermostats supported and
any changes to thermostat configs.
"""
# built ins
import imp
import sys

# local imports
import utilities as util


# thermostat types
HONEYWELL = "honeywell"
MMM50 = "mmm50"
SHT31 = "sht31"
KUMOCLOUD = "kumocloud"
SUPPORTED_THERMOSTATS = {
    # "module" = module to import
    # "type" = thermostat type index number
    # "zones" = zone numbers supported
    HONEYWELL: {"module": "honeywell", "type": 1, "zones": [0]},
    MMM50: {"module": "mmm", "type": 2, "zones": [0, 1]},
    SHT31: {"module": "sht31", "type": 3, "zones": [0, 1]},
    KUMOCLOUD: {"module": "kumocloud", "type": 4, "zones": [0, 1]},
    }

# target zone for monitoring
zone_number = 0  # default

thermostats = {
    HONEYWELL: {
        "required_env_variables": {
            "TCC_USERNAME": None,
            "TCC_PASSWORD": None,
            "GMAIL_USERNAME": None,
            "GMAIL_PASSWORD": None,
            },
        },
    MMM50: {
        "required_env_variables": {
            "GMAIL_USERNAME": None,
            "GMAIL_PASSWORD": None,
            },
        },
    SHT31: {
        "required_env_variables": {
            "GMAIL_USERNAME": None,
            "GMAIL_PASSWORD": None,
            "SHT31_REMOTE_IP_ADDRESS_": None,  # prefix only, excludes zone
            },
        },
    KUMOCLOUD: {
        "required_env_variables": {
            "GMAIL_USERNAME": None,
            "GMAIL_PASSWORD": None,
            'KUMO_USERNAME': None,
            'KUMO_PASSWORD': None,
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
        valid_range(list, dict, range): set of valid values.
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
    if result != default_value and result not in valid_range:
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
                                         list(SUPPORTED_THERMOSTATS.keys()))

    # parse zone number parameter (argv[2] if present):
    zone_input = parse_runtime_parameter("zone", 2, int, 0,
                                         SUPPORTED_THERMOSTATS[
                                             tstat_type]["zones"])

    # parse the poll time override (argv[3] if present):
    poll_time_input = parse_runtime_parameter("poll_time_sec", 3, int, None,
                                              range(0, 24 * 60 * 60))

    # parse the connection time override (argv[4] if present):
    connection_time_input = parse_runtime_parameter("connection_time_sec", 4,
                                                    int, None,
                                                    range(0, 24 * 60 * 60))

    # parse the tolerance override (argv[5] if present):
    tolerance_degrees_input = parse_runtime_parameter("tolerance_degrees", 5,
                                                      int, None, range(0, 10))
    return [tstat_type, zone_input, poll_time_input, connection_time_input,
            tolerance_degrees_input]


# dynamic import
def dynamic_imp(name):

    # find_module() method is used
    # to find the module and return
    # its description and path
    try:
        fp, path, desc = imp.find_module(name)
    except ImportError:
        print("module not found: " + name)

    try:
        # load_modules loads the module
        # dynamically ans takes the filepath
        # module and description as parameter
        example_package = imp.load_module(name, fp,
                                          path, desc)
    except Exception as e:
        print(e)

    return example_package


def load_hardware_library(thermostat_type):
    """
    Dynamic load library for requested hardware type.

    inputs:
        thermostat_type(str): thermostat type
    returns:
        module
    """
    mod = dynamic_imp(SUPPORTED_THERMOSTATS[thermostat_type]["module"])
    return mod
