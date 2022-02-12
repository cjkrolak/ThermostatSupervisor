"""
Thermostat API.

This file should be updated for any new thermostats supported and
any changes to thermostat configs.
"""
# built ins
import sys

# local imports
from thermostatsupervisor import emulator_config
from thermostatsupervisor import honeywell_config
from thermostatsupervisor import kumocloud_config
from thermostatsupervisor import kumolocal_config
from thermostatsupervisor import mmm_config
from thermostatsupervisor import sht31_config
from thermostatsupervisor import utilities as util

# thermostat types
DEFAULT_THERMOSTAT = honeywell_config.ALIAS

# list of thermostat config modules supported
config_modules = [emulator_config,
                  honeywell_config,
                  kumocloud_config,
                  kumolocal_config,
                  mmm_config,
                  sht31_config
                  ]

SUPPORTED_THERMOSTATS = {
    # "module" = module to import
    # "type" = thermostat type index number
    # "zones" = zone numbers supported
    # "modes" = modes supported
}
for config_module in config_modules:
    SUPPORTED_THERMOSTATS.update(
        {config_module.ALIAS: config_module.supported_configs})

# dictionary of required env variables for each thermostat type
thermostats = {
}
for config_module in config_modules:
    thermostats.update(
        {config_module.ALIAS: {"required_env_variables":
                               config_module.required_env_variables}})


def update_thermostat_specific_values(thermostat_type):
    """
    Update thermostat-specific values in user_inputs dict.
    """
    user_inputs["thermostat_type"] = thermostat_type
    user_inputs["zone"]["valid_range"] = SUPPORTED_THERMOSTATS[
            thermostat_type]["zones"]
    user_inputs["target_mode"]["valid_range"] = SUPPORTED_THERMOSTATS[
            thermostat_type]["modes"]


# runtime override parameters
user_inputs = {
    "script": {
        "order": 0,
        "value": None,
        "type": str,
        "default": "supervise.py",
        "valid_range": None,
        "sflag": "-s",
        "lflag": "--script",
        "help": "script name"},
    "thermostat_type": {
        "order": 1,
        "value": None, "type": str,
        "default": DEFAULT_THERMOSTAT,
        "valid_range": list(SUPPORTED_THERMOSTATS.keys()),
        "sflag": "-t",
        "lflag": "--thermostat_type",
        "help": "thermostat type"},
    "zone": {
        "order": 2,
        "value": None,
        "type": int,
        "default": 0,
        "valid_range": None,
        "sflag": "-z",
        "lflag": "--zone",
        "help": "target zone number"},
    "poll_time_sec": {
        "order": 3,
        "value": None,
        "type": int,
        "default": 60 * 10,
        "valid_range": range(0, 24 * 60 * 60),
        "sflag": "-p",
        "lflag": "--poll_time",
        "help": "poll time (sec)"},
    "connection_time_sec": {
        "order": 4,
        "value": None,
        "type": int,
        "default": 60 * 10 * 8,
        "valid_range": range(0, 24 * 60 * 60 * 60),
        "sflag": "-c",
        "lflag": "--connection_time",
        "help": "server connection time (sec)"},
    "tolerance": {
        "order": 5,
        "value": None,
        "type": int,
        "default": 2,
        "valid_range": range(0, 10),
        "sflag": "-to",
        "lflag": "--tolerance",
        "help": "tolerance (deg F)"},
    "target_mode": {
        "order": 6,
        "value": None,
        "type": str,
        "default": "OFF_MODE",
        "valid_range": None,
        "sflag": "-m",
        "lflag": "--target_mode",
        "help": "target thermostat mode"},
    "measurements": {
        "order": 7,
        "value": None,
        "type": int,
        "default": 10000,
        "valid_range": range(1, 1100),
        "sflag": "-n",
        "lflag": "--measurements",
        "help": "number of measurements"},
}


def get_argv_position(input_dict, key):
    """
    Return the argv list position for specified key.

    inputs:
        key(str): argv key.
    returns:
        (int): position in argv list
    """
    return user_inputs[key]["order"]


def get_key_at_position(input_dict, position):
    """
    Return the argv list key for specified position.

    inputs:
        input_dict(dict): user input dictionary
        position(int): position in argv list
    returns:
        key(str): argv key.
    """
    # initialization
    max_position = -1
    key_at_max_position = None

    # traverse dict and find first element with order matching desired val
    for key, val in input_dict.items():
        # log last k,v pair
        if val.get("order") > max_position:
            max_position = val["order"]
            key_at_max_position = key
        # return desired key
        if val.get("order") == position:
            return key

    # handle -1 case
    if position == -1:
        return key_at_max_position

    raise ValueError(f"no element was found in dictionary with "
                     "'position'={position}")


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
    print("\nchecking required environment variables:")
    key_status = True  # default, all keys present
    for key in thermostats[tstat]["required_env_variables"]:
        # any env key ending in '_' should have zone number appended to it.
        if key[-1] == '_':
            # append zone info to key
            key = key + str(zone_str)
        print(f"checking required environment key: {key}...", end='')
        util.env_variables[key] = util.get_env_variable(key)["value"]
        if util.env_variables[key] is not None:
            print("OK")
        else:
            util.log_msg(
                f"{tstat}: zone {zone_str}: FATAL error: one or more required"
                f" environemental keys are missing, exiting program",
                mode=util.BOTH_LOG)
            key_status = False
            raise KeyError
    print("\n")
    return key_status


def parse_runtime_parameter(key, datatype, default_value,
                            valid_range, argv_list=None):
    """
    Parse the runtime parameter parameter list and store in a dict.

    inputs:
        key(str): name of runtime parameter in api.user_input dict.
        datatype(int or str): data type to cast input str to.
        default_value(int or str):  default value.
        valid_range(list, dict, range): set of valid values.
        argv_list(list):  argv or list
    returns:
        (int or str): user input runtime value.
        This function also updates api.user_inputs dictionary
    """
    # if no override exists in argv_list, use argv value
    try:
        proposed_val = str(argv_list[get_argv_position(key)])
        util.log_msg(
            f"key='{key}': using user override value "
            f"'{argv_list[get_argv_position(key)]}'",
            mode=util.DEBUG_LOG +
            util.CONSOLE_LOG,
            func_name=1)
    except TypeError:
        util.log_msg(
            f"key='{key}': argv parsing error, using default value "
            f"'{default_value}'",
            mode=util.DEBUG_LOG +
            util.CONSOLE_LOG,
            func_name=1)
        proposed_val = str(default_value)
    except IndexError:
        util.log_msg(
            f"key='{key}': argv parameter missing, using default value "
            f"'{default_value}'",
            mode=util.DEBUG_LOG +
            util.CONSOLE_LOG,
            func_name=1)
        proposed_val = str(default_value)

    # cast input for these keys into uppercase and target data type.
    # all other keys are cast lowercase.
    uppercase_key_list = ["target_mode"]

    # truncate decimal if converting to int to avoid float str->int error
    if datatype == int and '.' in proposed_val:
        proposed_val = proposed_val[:proposed_val.index('.')]

    # datatype conversion and type cast
    if key in uppercase_key_list:
        proposed_val = datatype(proposed_val.upper())
    else:
        proposed_val = datatype(proposed_val.lower())

    # check for valid range
    if proposed_val != default_value and proposed_val not in valid_range:
        util.log_msg(
            f"WARNING: '{proposed_val}' is not a valid choice for '{key}', "
            f"using default({default_value})",
            mode=util.BOTH_LOG,
            func_name=1)
        proposed_val = default_value

    # populate the user_input dictionary
    user_inputs[key]["value"] = proposed_val
    return proposed_val


def parse_all_runtime_parameters(argv_list=None):
    """
    Parse all possible runtime parameters.

    inputs:
        argv_list(list): list of argv overrides
    returns:
        (dict) of all runtime parameters.
    """
    if argv_list is None:
        argv_list = []
    result = {}
    if argv_list:
        util.log_msg(
            f"parse_all_runtime_parameters from user dictionary: {argv_list}",
            mode=util.DEBUG_LOG +
            util.CONSOLE_LOG,
            func_name=1)
    else:
        util.log_msg(
            f"parse_all_runtime_parameters from sys.argv: {sys.argv}",
            mode=util.DEBUG_LOG +
            util.CONSOLE_LOG,
            func_name=1)
        argv_list = sys.argv

    # parse thermostat type parameter (argv[1] if present):
    result["thermostat_type"] = parse_runtime_parameter(
        "thermostat_type", str, DEFAULT_THERMOSTAT,
        list(SUPPORTED_THERMOSTATS.keys()), argv_list=argv_list)

    # parse zone number parameter (argv[2] if present):
    result["zone"] = parse_runtime_parameter(
        "zone", int, 0, SUPPORTED_THERMOSTATS[
            result["thermostat_type"]]["zones"],
        argv_list=argv_list)

    # parse the poll time override (argv[3] if present):
    result["poll_time_sec"] = parse_runtime_parameter(
        "poll_time_sec", int, 10 * 60, range(0, 24 * 60 * 60),
        argv_list=argv_list)

    # parse the connection time override (argv[4] if present):
    result["connection_time_sec"] = parse_runtime_parameter(
        "connection_time_sec", int, 24 * 60 * 60, range(0, 24 * 60 * 60),
        argv_list=argv_list)

    # parse the tolerance override (argv[5] if present):
    result["tolerance_degrees"] = parse_runtime_parameter(
        "tolerance_degrees", int, 2, range(0, 10),
        argv_list=argv_list)

    # parse the target mode (argv[6] if present):
    result["target_mode"] = parse_runtime_parameter(
        "target_mode", str, "OFF_MODE", SUPPORTED_THERMOSTATS[
            result["thermostat_type"]]["modes"], argv_list=argv_list)

    # parse the number of measurements (argv[7] if present):
    result["measurements"] = parse_runtime_parameter(
        "measurements", int, 1e6, range(1, 11),
        argv_list=argv_list)

    return result


def load_hardware_library(thermostat_type):
    """
    Dynamic load 3rd party library for requested hardware type.

    inputs:
        thermostat_type(str): thermostat alias string
    returns:
        (obj): loaded python module
    """
    pkg_name = (util.PACKAGE_NAME + "." +
                SUPPORTED_THERMOSTATS[thermostat_type]["module"])
    mod = util.dynamic_module_import(pkg_name)
    return mod


def max_measurement_count_exceeded(measurement):
    """
    Return True if max measurement reached.

    inputs:
        measurement(int): current measurement value
    returns:
        (bool): True if max measurement reached.
    """
    max_measurements = user_inputs["measurements"]["value"]
    if max_measurements is None:
        return False
    elif measurement > max_measurements:
        return True
    else:
        return False
