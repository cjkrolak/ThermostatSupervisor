"""
Thermostat API.

This file should be updated for any new thermostats supported and
any changes to thermostat configs.
"""
# built ins
import imp
import sys
import traceback

# local imports
import honeywell_config
import kumocloud_config
import sht31_config
import utilities as util


# thermostat types
MMM50 = "mmm50"
KUMOLOCAL = "kumolocal"
DEFAULT_THERMOSTAT = honeywell_config.ALIAS

SUPPORTED_THERMOSTATS = {
    # "module" = module to import
    # "type" = thermostat type index number
    # "zones" = zone numbers supported
    MMM50: {"module": "mmm", "type": 2, "zones": [0, 1],
            "modes": ["OFF_MODE", "HEAT_MODE", "COOL_MODE"]},
    KUMOLOCAL: {"module": "kumolocal", "type": 5, "zones": [0, 1],
                "modes": ["OFF_MODE", "HEAT_MODE", "COOL_MODE",
                          "DRY_MODE", "AUTO_MODE"]},
    }
SUPPORTED_THERMOSTATS.update(
    {honeywell_config.ALIAS: honeywell_config.supported_configs})
SUPPORTED_THERMOSTATS.update(
    {kumocloud_config.ALIAS: kumocloud_config.supported_configs})
SUPPORTED_THERMOSTATS.update(
    {sht31_config.ALIAS: sht31_config.supported_configs})

# target zone for monitoring
zone_number = 0  # default

thermostats = {
    honeywell_config.ALIAS: {
        "required_env_variables": honeywell_config.required_env_variables,
        },
    MMM50: {
        "required_env_variables": {
            "GMAIL_USERNAME": None,
            "GMAIL_PASSWORD": None,
            },
        },
    sht31_config.ALIAS: {
        "required_env_variables": sht31_config.required_env_variables,
        },
    kumocloud_config.ALIAS: {
        "required_env_variables": kumocloud_config.required_env_variables,
        },
    KUMOLOCAL: {
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
user_input_list = ["thermostat_type",
                   "zone",
                   "poll_time_sec",
                   "connection_time_sec",
                   "tolerance_degrees",
                   "target_mode",
                   "measurements",
                   ]
user_inputs = dict.fromkeys(user_input_list, None)


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
        (int or str): user input runtime value.
    """
    if input_list is None:
        input_list = []
    # cast input for these keys into uppercase
    # all other keys are cast lowercase.
    uppercase_key_list = ["target_mode"]

    if not input_list:
        target = sys.argv
    else:
        target = input_list
    if not isinstance(position, int):
        raise TypeError("'position' argument must be an int, "
                        "actual=%s is type(%s)" %
                        (position, type(position)))
    try:
        if key in uppercase_key_list:
            result = datatype(target[position].upper())
        else:
            result = datatype(target[position].lower())
    except IndexError:
        result = default_value
    if result != default_value and result not in valid_range:
        util.log_msg("WARNING: '%s' is not a valid choice for '%s', "
                     "using default(%s)" % (result, key, default_value),
                     mode=util.BOTH_LOG, func_name=1)
        result = default_value

    # populate the user_input dictionary
    user_inputs[key] = result
    return result


def parse_all_runtime_parameters(input_list=None):
    """
    Parse all possible runtime parameters.

    inputs:
        input_list(list): list of argv overrides
    returns:
        (dict) of all runtime parameters.
    """
    if input_list is None:
        input_list = []
    param = {}
    if input_list:
        util.log_msg("parse_all_runtime_parameters from list: %s" % input_list,
                     mode=util.DEBUG_LOG + util.CONSOLE_LOG, func_name=1)
    else:
        util.log_msg("parse_all_runtime_parameters from sys.argv: %s" %
                     sys.argv, mode=util.DEBUG_LOG + util.CONSOLE_LOG,
                     func_name=1)
    # parse thermostat type parameter (argv[1] if present):
    param["thermostat_type"] = parse_runtime_parameter(
        "thermostat_type", 1, str, DEFAULT_THERMOSTAT,
        list(SUPPORTED_THERMOSTATS.keys()), input_list=input_list)

    # parse zone number parameter (argv[2] if present):
    param["zone"] = parse_runtime_parameter(
        "zone", 2, int, 0, SUPPORTED_THERMOSTATS[
            param["thermostat_type"]]["zones"],
        input_list=input_list)

    # parse the poll time override (argv[3] if present):
    param["poll_time_sec"] = parse_runtime_parameter(
        "poll_time_sec", 3, int, None, range(0, 24 * 60 * 60),
        input_list=input_list)

    # parse the connection time override (argv[4] if present):
    param["connection_time_sec"] = parse_runtime_parameter(
        "connection_time_sec", 4, int, None, range(0, 24 * 60 * 60),
        input_list=input_list)

    # parse the tolerance override (argv[5] if present):
    param["tolerance_degrees"] = parse_runtime_parameter(
        "tolerance_degrees", 5, int, None, range(0, 10),
        input_list=input_list)

    # parse the target mode (argv[6] if present):
    param["target_mode"] = parse_runtime_parameter(
        "target_mode", 6, str, None, SUPPORTED_THERMOSTATS[
            param["thermostat_type"]]["modes"], input_list=input_list)

    # parse the number of measurements (argv[7] if present):
    param["measurements"] = parse_runtime_parameter(
        "measurements", 7, int, 1e9, range(1, 11),
        input_list=input_list)

    return param


# dynamic import
def dynamic_module_import(name):
    """
    Find and load python module.

    inputs:
        name(str): module name
    returns:
        mod(module): module object
    """
    fp, path, desc = find_module(name)
    mod = load_module(name, fp, path, desc)
    return mod


def find_module(name):
    """
    Find the module and return its description and path.

    inputs:
        name(str): module name
    returns:
        fp(_io.TextIOWrapper): file pointer
        path(str): path to file
        desc(tuple): file descriptor
    """
    try:
        fp, path, desc = imp.find_module(name)
    except ImportError as e:
        util.log_msg(traceback.format_exc(),
                     mode=util.BOTH_LOG, func_name=1)
        util.log_msg("module not found: " + name,
                     mode=util.BOTH_LOG, func_name=1)
        raise e
    return fp, path, desc


def load_module(name, fp, path, desc):
    """
    Load the module into memory.

    inputs:
        fp(_io.TextIOWrapper): file pointer
        path(str): path to file
        desc(tuple): file descriptor
    returns:
        mod(python module)
    """
    try:
        # load_modules loads the module
        # dynamically and takes the filepath
        # module and description as parameter
        mod = imp.load_module(name, fp, path, desc)
    except Exception as e:
        util.log_msg(traceback.format_exc(),
                     mode=util.BOTH_LOG, func_name=1)
        util.log_msg("module load failed: " + name,
                     mode=util.BOTH_LOG, func_name=1)
        raise e
    finally:
        fp.close()
    return mod


def load_hardware_library(thermostat_type):
    """
    Dynamic load library for requested hardware type.

    inputs:
        thermostat_type(str): thermostat type
    returns:
        module
    """
    mod = dynamic_module_import(
        SUPPORTED_THERMOSTATS[thermostat_type]["module"])
    return mod


def max_measurement_count_exceeded(measurement):
    """
    Return True if max measurement reached.

    inputs:
        measurement(int): current measurement value
    returns:
        (bool): True if max measurement reached.
    """
    max_measurements = user_inputs["measurements"]
    if max_measurements is None:
        return False
    elif measurement > max_measurements:
        return True
    else:
        return False
