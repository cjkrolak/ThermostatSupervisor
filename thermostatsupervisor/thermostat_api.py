"""
Thermostat API.

This file should be updated for any new thermostats supported and
any changes to thermostat configs.
"""
# built ins

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
# note script name is omitted, starting with first parameter
user_inputs = {
    "thermostat_type": {
        "order": 0,
        "value": None,
        "type": str,
        "default": DEFAULT_THERMOSTAT,
        "valid_range": list(SUPPORTED_THERMOSTATS.keys()),
        "sflag": "-t",
        "lflag": "--thermostat_type",
        "help": "thermostat type"},
    "zone": {
        "order": 1,
        "value": None,
        "type": int,
        "default": 0,
        "valid_range": None,
        "sflag": "-z",
        "lflag": "--zone",
        "help": "target zone number"},
    "poll_time": {
        "order": 2,
        "value": None,
        "type": int,
        "default": 60 * 10,
        "valid_range": range(0, 24 * 60 * 60),
        "sflag": "-p",
        "lflag": "--poll_time",
        "help": "poll time (sec)"},
    "connection_time": {
        "order": 3,
        "value": None,
        "type": int,
        "default": 60 * 10 * 8,
        "valid_range": range(0, 24 * 60 * 60 * 60),
        "sflag": "-c",
        "lflag": "--connection_time",
        "help": "server connection time (sec)"},
    "tolerance": {
        "order": 4,
        "value": None,
        "type": int,
        "default": 2,
        "valid_range": range(0, 10),
        "sflag": "-d",
        "lflag": "--tolerance",
        "help": "tolerance (deg F)"},
    "target_mode": {
        "order": 5,
        "value": None,
        "type": str,
        "default": "OFF_MODE",
        "valid_range": None,
        "sflag": "-m",
        "lflag": "--target_mode",
        "help": "target thermostat mode"},
    "measurements": {
        "order": 6,
        "value": None,
        "type": int,
        "default": 10000,
        "valid_range": range(1, 10001),
        "sflag": "-n",
        "lflag": "--measurements",
        "help": "number of measurements"},
}
valid_sflags = [user_inputs[k]["sflag"] for k in user_inputs]


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


def get_runtime_argument(key):
    """
    Return the target key's value from user_inputs.
    """
    return user_inputs[key]["value"]


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
