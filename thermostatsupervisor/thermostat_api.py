"""
Thermostat API.

This file should be updated for any new thermostats supported and
any changes to thermostat configs.
"""
# built ins
import munch

# local imports
from thermostatsupervisor import blink_config
from thermostatsupervisor import emulator_config
from thermostatsupervisor import honeywell_config
from thermostatsupervisor import kumocloud_config
from thermostatsupervisor import kumolocal_config
from thermostatsupervisor import mmm_config
from thermostatsupervisor import sht31_config
from thermostatsupervisor import environment as env
from thermostatsupervisor import utilities as util

# thermostat types
DEFAULT_THERMOSTAT = emulator_config.ALIAS
DEFAULT_ZONE_NAME = util.default_parent_key

# list of thermostat config modules supported
config_modules = [blink_config,
                  emulator_config,
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


# runtime override parameters
# note script name is omitted, starting with first parameter
# index 0 (script name) is not included in this dict because it is
# not a runtime argument
input_flds = munch.Munch()
input_flds.thermostat_type = "thermostat_type"
input_flds.zone = "zone"
input_flds.poll_time = "poll_time"
input_flds.connection_time = "connection_time"
input_flds.tolerance = "tolerance"
input_flds.target_mode = "target_mode"
input_flds.measurements = "measurements"
input_flds.input_file = "input_file"

uip = None  # user inputs object


class UserInputs(util.UserInputs):
    """Manage runtime arguments for thermostat_api."""

    def __init__(self, argv_list=None, help_description=None,
                 suppress_warnings=False, thermostat_type=DEFAULT_THERMOSTAT,
                 zone_name=DEFAULT_ZONE_NAME):
        """
        UserInputs constructor for thermostat_api.

        inputs:
            argv_list(list): override runtime values.
            help_description(str): description field for help text.
            suppress_warnings(bool): True to suppress warning msgs.
            thermostat_type(str): thermostat type.
            zone_name(str): thermostat zone name (e.g. 'living room')
        """
        self.argv_list = argv_list
        self.help_description = help_description
        self.suppress_warnings = suppress_warnings
        self.thermostat_type = thermostat_type  # default if not provided
        self.zone_name = zone_name
        print(f"DEBUG ({util.get_function_name()}: "
              f"self.zone_name={self.zone_name}")

        # initialize parent class
        super().__init__(argv_list, help_description, suppress_warnings,
                         zone_name)

    def initialize_user_inputs(self, parent_keys=None):
        """
        Populate user_inputs dict.

        inputs:
            parent_keys(list): list of parent keys
        """
        if parent_keys is None:
            parent_keys = [self.default_parent_key]
        self.valid_sflags = []
        self.user_inputs = {}  # init
        # define the user_inputs dict.
        for parent_key in parent_keys:
            self.user_inputs[parent_key] = {
                input_flds.thermostat_type: {
                    "order": 1,  # index in the argv list
                    "value": None,
                    "type": str,
                    "default": self.thermostat_type,
                    "valid_range": list(SUPPORTED_THERMOSTATS.keys()),
                    "sflag": "-t",
                    "lflag": "--" + input_flds.thermostat_type,
                    "help": "thermostat type",
                    "required": False,  # default value is set if missing.
                    },
                input_flds.zone: {
                    "order": 2,  # index in the argv list
                    "value": None,
                    "type": int,
                    "default": 0,
                    "valid_range": None,  # updated once thermostat is known
                    "sflag": "-z",
                    "lflag": "--" + input_flds.zone,
                    "help": "target zone number",
                    "required": False,  # defaults to idx 0 in supported zones
                    },
                input_flds.poll_time: {
                    "order": 3,  # index in the argv list
                    "value": None,
                    "type": int,
                    "default": 60 * 10,
                    "valid_range": range(0, 24 * 60 * 60),
                    "sflag": "-p",
                    "lflag": "--" + input_flds.poll_time,
                    "help": "poll time (sec)",
                    "required": False,
                    },
                input_flds.connection_time: {
                    "order": 4,  # index in the argv list
                    "value": None,
                    "type": int,
                    "default": 24 * 60 * 60,  # 1 day
                    "valid_range": range(0, 7 * 24 * 60 * 60),  # up to 1 wk
                    "sflag": "-c",
                    "lflag": "--" + input_flds.connection_time,
                    "help": "server connection time (sec)",
                    "required": False,
                    },
                input_flds.tolerance: {
                    "order": 5,  # index in the argv list
                    "value": None,
                    "type": int,
                    "default": 2,
                    "valid_range": range(0, 10),
                    "sflag": "-d",
                    "lflag": "--" + input_flds.tolerance,
                    "help": "tolerance (deg F)",
                    "required": False,
                    },
                input_flds.target_mode: {
                    "order": 6,  # index in the argv list
                    "value": None,
                    "type": str,
                    "default": "UNKNOWN_MODE",
                    "valid_range": None,  # updated once thermostat is known
                    "sflag": "-m",
                    "lflag": "--" + input_flds.target_mode,
                    "help": "target thermostat mode",
                    "required": False,
                    },
                input_flds.measurements: {
                    "order": 7,  # index in the argv list
                    "value": None,
                    "type": int,
                    "default": 10000,
                    "valid_range": range(1, 10001),
                    "sflag": "-n",
                    "lflag": "--" + input_flds.measurements,
                    "help": "number of measurements",
                    "required": False,
                    },
                input_flds.input_file: {
                    "order": 8,  # index in the argv list
                    "value": None,
                    # "type": lambda x: self.is_valid_file(x),
                    "type": str,  # argparse.FileType('r', encoding='UTF-8'),
                    "default": None,
                    "valid_range": None,
                    "sflag": "-f",
                    "lflag": "--" + input_flds.input_file,
                    "help": "input file",
                    "required": False,
                    },
            }
            self.valid_sflags += [self.user_inputs[parent_key][k]["sflag"]
                                  for k in self.user_inputs[parent_key].keys()]

    def dynamic_update_user_inputs(self):
        """
        Update thermostat-specific values in user_inputs dict.

        This function expands each input parameter list to match
        the length of the thermostat parameter field.
        """
        # initializ section list to single item list of one thermostat
        self.parent_keys = [self.default_parent_key]  # initialize

        # file input will override any type of individual inputs
        input_file = self.get_user_inputs(self.default_parent_key,
                                          input_flds.input_file)
        if input_file is not None:
            # aise Exception("dynamic_update_user_inputs found")
            self.using_input_file = True
            print(f"DEBUG: reading runtime arguments from '{input_file}'...")
            self.parse_input_file(input_file)
            # scan all sections in INI file in reversed order so that
            # user_inputs contains the first key after casting.
            # section = list(self.user_inputs_file.keys())[0]  # use first key
            self.parent_keys = list(self.user_inputs_file.keys())
            # reinit user_inputs dict based on INI file structure
            self.initialize_user_inputs(self.parent_keys)
            # populate user_inputs from user_inputs_file
            for section in self.parent_keys:
                for fld in input_flds:
                    if fld == input_flds.input_file:
                        # input file field will not be in the file
                        continue
                    if (self.user_inputs[section][fld]["type"]
                            in [int, float, str]):
                        # cast data type when reading value
                        try:
                            self.user_inputs[section][fld]["value"] = (
                                self.user_inputs[section][fld]["type"](
                                    self.user_inputs_file[section].get(
                                        input_flds[fld])))
                        except Exception:
                            print(f"exception in section={section}, fld={fld}")
                            raise
                        # cast original input value in user_inputs_file as well
                        self.user_inputs_file[section][input_flds[fld]] = \
                            self.user_inputs[section][fld]["value"]
                    else:
                        # no casting, just read raw from list
                        self.user_inputs[section][fld]["value"] = \
                            ((self.user_inputs_file[section].get(input_flds[
                                fld])))
            # for now set zone name to first zone in file
            self.zone_name = self.parent_keys[0]
            print(f"DEBUG ({util.get_function_name()}: "
                  f"self.zone_name={self.zone_name}")
        # update user_inputs parent_key with zone_name
        # if user_inputs has already been populated
        elif (self.get_user_inputs(list(self.user_inputs.keys())[0],
                                   input_flds.thermostat_type) is not None):
            # argv inputs, only currenty supporting 1 zone
            # verify only 1 parent key exists
            current_keys = list(self.user_inputs.keys())
            if len(current_keys) != 1:
                raise KeyError(f"user_input keys={current_keys}, expected only"
                               " 1 key")

            # update parent key to be zone_name
            current_key = current_keys[0]
            new_key = (self.get_user_inputs(
                       current_key, input_flds.thermostat_type) + "_" +
                       str(self.get_user_inputs(current_key, input_flds.zone)))
            self.user_inputs[new_key] = self.user_inputs.pop(current_key)

            # update paremeters for new parent keys
            self.zone_name = new_key  # set Zone name
            print(f"DEBUG ({util.get_function_name()}: "
                  f"self.zone_name={self.zone_name}")
            self.default_parent_key = new_key
            self.parent_keys = list(self.user_inputs.keys())
        else:
            runtime_args = (self.get_user_inputs(list(
                self.user_inputs.keys())[0], input_flds.thermostat_type))
            print(f"runtime args: {runtime_args}")

        # if thermostat is not set yet, default it based on module
        # TODO - code block needs update for multi-zone
        for zone_name in self.parent_keys:
            thermostat_type = self.get_user_inputs(zone_name,
                                                   input_flds.thermostat_type)
            if thermostat_type is None:
                thermostat_type = self.thermostat_type
            try:
                self.user_inputs[zone_name][input_flds.zone]["valid_range"] = \
                    SUPPORTED_THERMOSTATS[thermostat_type]["zones"]
            except KeyError:
                print(f"\nKeyError: one or more keys are invalid (zone_name="
                      f"{zone_name}, zone_number={input_flds.zone}, "
                      f"thermostat_type={thermostat_type})\n")
                raise
            try:
                self.user_inputs[zone_name][input_flds.target_mode][
                    "valid_range"] = \
                    SUPPORTED_THERMOSTATS[thermostat_type]["modes"]
            except KeyError:
                print(f"\nKeyError: one or more keys are invalid (zone_name="
                      f"{zone_name}, target_mode={input_flds.target_mode}, "
                      f"thermostat_type={thermostat_type})\n")
                raise

    def max_measurement_count_exceeded(self, measurement):
        """
        Return True if max measurement reached.

        inputs:
            measurement(int): current measurement value
        returns:
            (bool): True if max measurement reached.
        """
        max_measurements = self.get_user_inputs(self.zone_name, "measurements")
        if max_measurements is None:
            return False
        elif measurement > max_measurements:
            return True
        else:
            return False


def verify_required_env_variables(tstat, zone_str, verbose=True):
    """
    Verify all required env variables are present for thermostat
    configuration in use.

    inputs:
        tstat(int) thermostat type mapping to thermostat_api
        zone_str(str): zone input as a string
        verbose(bool): debug flag.
    returns:
        (bool): True if all keys are present, else False
    """
    if verbose:
        print("\nchecking required environment variables:")
    key_status = True  # default, all keys present
    for key in thermostats[tstat]["required_env_variables"]:
        # any env key ending in '_' should have zone number appended to it.
        if key[-1] == '_':
            # append zone info to key
            key = key + str(zone_str)
        if verbose:
            print(f"checking required environment key: {key}...", end='')
        env.env_variables[key] = env.get_env_variable(key)["value"]
        if env.env_variables[key] is not None:
            if verbose:
                print("OK")
        else:
            util.log_msg(
                f"{tstat}: zone {zone_str}: FATAL error: one or more required"
                f" environemental keys are missing, exiting program",
                mode=util.BOTH_LOG)
            key_status = False
            raise KeyError
    if verbose:
        print("\n")
    return key_status


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
    mod = env.dynamic_module_import(pkg_name)
    return mod


def load_user_inputs(config_mod):
    """
    Load the default user inputs and return the zone number.

    inputs:
        config_mod(obj): config module
    returns:
        zone_number(int): zone number
    """
    global uip
    zone_name = config_mod.default_zone_name
    print(f"DEBUG in load user inputs, zone_name={zone_name}")
    uip = UserInputs(argv_list=config_mod.argv,
                     thermostat_type=config_mod.ALIAS,
                     zone_name=zone_name)
    zone_number = uip.get_user_inputs(uip.zone_name,
                                      input_flds.zone)
    return zone_number
