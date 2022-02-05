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

# runtime overrides
argv_order = {
    0: "script",
    1: "thermostat_type",
    2: "zone",
    3: "poll_time_sec",
    4: "connection_time_sec",
    5: "tolerance_degrees",
    6: "target_mode",
    7: "measurements",
}

# initialize user input (runtime overrides) dict
user_inputs = {}
for k, v in argv_order.items():
    user_inputs[v] = None


def get_argv_position(key):
    """
    Return the argv list position for specified key.

    inputs:
        key(str): argv key.
    returns:
        (int): position in argv list
    """
    return util.get_key_from_value(argv_order, key)


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
            util.log_msg("%s: zone %s: FATAL error: one or more required "
                         "environemental keys are missing, exiting program" %
                         (tstat, zone_str), mode=util.BOTH_LOG)
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
        util.log_msg("key='%s': using user override value '%s'" %
                     (key, argv_list[get_argv_position(key)]),
                     mode=util.DEBUG_LOG + util.CONSOLE_LOG, func_name=1)
    except TypeError:
        util.log_msg("key='%s': argv parsing error, using default value '%s'" %
                     (key, default_value),
                     mode=util.DEBUG_LOG + util.CONSOLE_LOG, func_name=1)
        proposed_val = str(default_value)
    except IndexError:
        util.log_msg("key='%s': argv parameter missing, "
                     "using default value '%s'" %
                     (key, default_value),
                     mode=util.DEBUG_LOG + util.CONSOLE_LOG, func_name=1)
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
        util.log_msg("WARNING: '%s' is not a valid choice for '%s', "
                     "using default(%s)" % (proposed_val, key, default_value),
                     mode=util.BOTH_LOG, func_name=1)
        proposed_val = default_value

    # populate the user_input dictionary
    user_inputs[key] = proposed_val
    return proposed_val


def parse_all_runtime_parameters(argv_list=None):
    """
    Parse all possible runtime parameters.

    inputs:
        argv_list(dict): dict of argv overrides
    returns:
        (dict) of all runtime parameters.
    """
    if argv_list is None:
        argv_list = []
    result = {}
    if argv_list:
        util.log_msg("parse_all_runtime_parameters from user dictionary: %s" %
                     argv_list, mode=util.DEBUG_LOG + util.CONSOLE_LOG,
                     func_name=1)
    else:
        util.log_msg("parse_all_runtime_parameters from sys.argv: %s" %
                     sys.argv, mode=util.DEBUG_LOG + util.CONSOLE_LOG,
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
    max_measurements = user_inputs["measurements"]
    if max_measurements is None:
        return False
    elif measurement > max_measurements:
        return True
    else:
        return False
