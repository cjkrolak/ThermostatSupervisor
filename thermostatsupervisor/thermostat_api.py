"""
Thermostat API.

This file should be updated for any new thermostats supported and
any changes to thermostat configs.
"""
# built ins
import bunch

# local imports
from thermostatsupervisor import emulator_config
from thermostatsupervisor import honeywell_config
from thermostatsupervisor import kumocloud_config
from thermostatsupervisor import kumolocal_config
from thermostatsupervisor import mmm_config
from thermostatsupervisor import sht31_config
from thermostatsupervisor import utilities as util
from thermostatsupervisor.sht31_flask_server import input_flds

# thermostat types
DEFAULT_THERMOSTAT = emulator_config.ALIAS
DEFAULT_ZONE_NAME = util.default_parent_key

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


# runtime override parameters
# note script name is omitted, starting with first parameter
# index 0 (script name) is not included in this dict because it is
# not a runtime argument
input_flds = bunch.Bunch()
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
        self.default_parent_key = zone_name

        # initialize parent class
        super().__init__(argv_list, help_description, suppress_warnings,
                         thermostat_type, zone_name)

    def initialize_user_inputs(self, parent_keys=None):
        """
        Populate user_inputs dict.

        inputs:
            parent_keys(list): list of parent keys
        """
        print("DEBUG: in %s" % util.get_function_name())
        if parent_keys is None:
            parent_keys = [self.default_parent_key]
        self.valid_sflags = []
        # define the user_inputs dict.
        for parent_key in parent_keys:
            self.user_inputs = {parent_key: {
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
                    "default": 60 * 10 * 8,
                    "valid_range": range(0, 24 * 60 * 60 * 60),
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
                }}
            self.valid_sflags += [self.user_inputs[parent_key][k]["sflag"]
                                  for k in self.user_inputs[parent_key].keys()]

    def dynamic_update_user_inputs(self):
        """
        Update thermostat-specific values in user_inputs dict.

        This function expands each input parameter list to match
        the length of the thermostat parameter field.
        """
        print("DEBUG: in %s" % util.get_function_name())
        # initializ section list to single item list of one thermostat
        section_list = [util.default_parent_key]  # initialize

        # file input will override any type of individual inputs
        input_file = self.get_user_inputs(util.default_parent_key,
                                          input_flds.input_file)
        if input_file is not None:
            self.using_input_file = True
            print(f"DEBUG: reading runtime arguments from '{input_file}'...")
            self.parse_input_file(input_file)
            # scan all sections in INI file in reversed order so that
            # user_inputs contains the first key after casting.
            # section = list(self.user_inputs_file.keys())[0]  # use first key
            section_list = list(self.user_inputs_file.keys())
            print("DEBUG: section list=%s" % section_list)
            # reinit user_inputs dict
            self.initialize_user_inputs(section_list)
            print("DEBUG: user_inputs initialized for data file import: %s" % self.user_inputs)
            # populate user_inputs from user_inputs_file
            for section in section_list:
                print("DEBUG: section=%s" % section)
                for fld in input_flds:
                    if fld == input_flds.input_file:
                        # input file field will not be in the file
                        continue
                    print("DEBUG: fld %s: type=%s" % (fld, self.user_inputs[section][fld]["type"]))
                    print("DEBUG: checking types %s, %s, %s" % (int, float, str))
                    if self.user_inputs[section][fld]["type"] in [int, float, str]:
                        # cast data type when reading value
                        self.user_inputs[section][fld]["value"] = (
                            self.user_inputs[section][fld]["type"](
                                self.user_inputs_file[section].get(
                                    input_flds[fld])))
                        # cast original input value in user_inputs_file as well
                        print("DEBUG: casting %s to %s(%s)" %
                              (self.user_inputs_file[section][input_flds[fld]],
                               self.user_inputs[section][fld]["value"],
                               self.user_inputs[section][fld]["type"]))
                        self.user_inputs_file[section][input_flds[fld]] = \
                            self.user_inputs[section][fld]["value"]
                    else:
                        # no casting, just read raw from list
                        self.user_inputs[section][fld]["value"] = \
                            ((self.user_inputs_file[section].get(input_flds[
                                fld])))
        # update user_inputs parent_key with zone_name
        # if user_inputs has already been populated
        elif (self.get_user_inputs(list(self.user_inputs.keys())[0],
                                   input_flds.thermostat_type) is not None):
            print("DEBUG: updating parent_key in user_inputs dict")
            # argv inputs, only currenty supporting 1 zone
            # verify only 1 parent key exists
            current_keys = list(self.user_inputs.keys())
            if len(current_keys) != 1:
                raise KeyError("user_input keys=%s, expected only 1 key" %
                               current_keys)

            # update parent key to be zone_name
            print("DEBUG(%s): user_inputs before parent_key update: %s" %
                  (util.get_function_name(), self.user_inputs))
            current_key = current_keys[0]
            print("DEBUG current_key=%s" % current_key)
            print("DEBUG: thermostat_type=%s" % self.get_user_inputs(
                       current_key, input_flds.thermostat_type))
            print("DEBUG: zone=%s" % self.get_user_inputs(
                       current_key, input_flds.zone))
            new_key = (self.get_user_inputs(
                       current_key, input_flds.thermostat_type) + "_" +
                       str(self.get_user_inputs(current_key, input_flds.zone)))
            self.user_inputs[new_key] = self.user_inputs.pop(current_key)
            print("DEBUG(%s): user_inputs after parent_key update: %s" %
                  (util.get_function_name(), self.user_inputs))
            self.zone_name = new_key  # set Zone name
            section_list = [new_key]
            self.default_parent_key = new_key
        else:
            print("DEBUG: empty else block, user_inputs=%s" % self.user_inputs)
            print("%s" % self.get_user_inputs(list(self.user_inputs.keys())[0],
                                   input_flds.thermostat_type))
            print("DEBUG: (%s) empty else block" % util.get_function_name())

        # if thermostat is not set yet, default it based on module
        # TODO - code block needs update for multi-zone
        for section in section_list:
            thermostat_type = self.get_user_inputs(section,
                                                   input_flds.thermostat_type)
            if thermostat_type is None:
                thermostat_type = self.thermostat_type
            self.user_inputs[section][input_flds.zone]["valid_range"] = \
                SUPPORTED_THERMOSTATS[thermostat_type]["zones"]
            self.user_inputs[section][input_flds.target_mode]["valid_range"] = \
                SUPPORTED_THERMOSTATS[thermostat_type]["modes"]

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


def load_user_inputs(config_module):
    """
    Load the user inputs and return the zone number.

    inputs:
        config_module(obj): config module
    returns:
        zone_number(int): zone number
    """
    global uip
    zone_name = config_module.default_zone_name
    uip = UserInputs(argv_list=config_module.argv,
                     thermostat_type=config_module.ALIAS,
                     zone_name=zone_name)
    zone_number = uip.get_user_inputs(zone_name,
                                      input_flds.zone)
    return zone_number
