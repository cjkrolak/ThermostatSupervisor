"""
Thermostat API.

This file should be updated for any new thermostats supported and
any changes to thermostat configs.
"""
# built ins
import imp
import sys
import traceback

# thermostat config files
from supervisor import honeywell_config
from supervisor import kumocloud_config
from supervisor import kumolocal_config
from supervisor import mmm_config
from supervisor import sht31_config

# local imports
from supervisor import utilities as util


# thermostat types
DEFAULT_THERMOSTAT = honeywell_config.ALIAS

SUPPORTED_THERMOSTATS = {
    # "module" = module to import
    # "type" = thermostat type index number
    # "zones" = zone numbers supported
    # "modes" = modes supported
    }
for config_module in [honeywell_config, kumocloud_config, kumolocal_config,
                      mmm_config, sht31_config]:
    SUPPORTED_THERMOSTATS.update(
        {config_module.ALIAS: config_module.supported_configs})

# target zone for monitoring
zone_number = 0  # default

# dictionary of required env variables for each thermostat type
thermostats = {
}
for config_module in [honeywell_config, kumocloud_config, kumolocal_config,
                      mmm_config, sht31_config]:
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
    key_status = True  # default, all keys present
    for key in thermostats[tstat]["required_env_variables"]:
        # any env key ending in '_' should have zone number appended to it.
        if key[-1] == '_':
            # append zone info to key
            key = key + str(zone_str)
        print("checking required context key: %s..." % key, end='')
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
                     mode=util.BOTH_LOG, func_name=1)
    except TypeError:
        util.log_msg("key='%s': argv parsing error, using default value '%s'" %
                     (key, default_value), mode=util.BOTH_LOG, func_name=1)
        proposed_val = str(default_value)
    except IndexError:
        util.log_msg("key='%s': argv parameter missing, "
                     "using default value '%s'" %
                     (key, default_value), mode=util.BOTH_LOG, func_name=1)
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


# dynamic import
def dynamic_module_import(name):
    """
    Find and load python module.

    TODO: this module results in a resourcewarning within unittest:
    sys:1: ResourceWarning: unclosed <socket.socket fd=628,
    family=AddressFamily.AF_INET, type=SocketKind.SOCK_DGRAM, proto=0,
    laddr=('0.0.0.0', 64963)>

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

    Note: this function will close fp.

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
