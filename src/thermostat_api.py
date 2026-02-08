"""
Thermostat API.

This file should be updated for any new thermostats supported and
any changes to thermostat configs.
"""

# built ins
import munch

# local imports
from src import blink_config
from src import emulator_config
from src import honeywell_config
from src import kumocloud_config
from src import kumocloudv3_config
from src import kumolocal_config
from src import mmm_config
from src import nest_config
from src import sht31_config
from src import site_config
from src import environment as env
from src import utilities as util

# thermostat types
DEFAULT_THERMOSTAT = emulator_config.ALIAS
DEFAULT_ZONE_NAME = util.default_parent_key

KEY_MISSING_SUFFIX = "_KEY_MISSING>"

# list of thermostat config modules supported
config_modules = [
    blink_config,
    emulator_config,
    honeywell_config,
    kumocloud_config,
    kumocloudv3_config,
    kumolocal_config,
    mmm_config,
    nest_config,
    sht31_config,
    site_config,
]

SUPPORTED_THERMOSTATS = {
    # "module" = module to import
    # "type" = thermostat type index number
    # "zones" = zone numbers supported
    # "modes" = modes supported
}
for config_module in config_modules:
    SUPPORTED_THERMOSTATS.update({config_module.ALIAS: config_module.supported_configs})

# dictionary of required env variables for each thermostat type
thermostats = {}
for config_module in config_modules:
    # Use required_env_variables if explicitly defined, otherwise use env_variables
    # This allows consolidation of duplicate env dicts while preserving special cases
    required_env_vars = getattr(config_module, "required_env_variables", None)
    if required_env_vars is None:
        required_env_vars = getattr(config_module, "env_variables", {})

    thermostats.update(
        {config_module.ALIAS: {"required_env_variables": required_env_vars}}
    )


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

    def __init__(
        self,
        argv_list=None,
        help_description=None,
        suppress_warnings=False,
        thermostat_type=DEFAULT_THERMOSTAT,
        zone_name=DEFAULT_ZONE_NAME,
    ):
        """Initialize UserInputs for thermostat_api.

        Args:
            argv_list (list, optional): Override runtime values. Defaults to None.
            help_description (str, optional): Description field for help text.
                Defaults to None.
            suppress_warnings (bool, optional): True to suppress warning messages.
                Defaults to False.
            thermostat_type (str, optional): Thermostat type alias.
                Defaults to DEFAULT_THERMOSTAT.
            zone_name (str, optional): Thermostat zone name (e.g. 'living room').
                Defaults to DEFAULT_ZONE_NAME.
        """
        self.argv_list = argv_list
        self.help_description = help_description
        self.suppress_warnings = suppress_warnings
        self.thermostat_type = thermostat_type  # default if not provided
        self.zone_name = zone_name

        # initialize parent class
        super().__init__(argv_list, help_description, suppress_warnings, zone_name)

    def initialize_user_inputs(self, parent_keys=None):
        """Populate user_inputs dictionary with thermostat-specific parameters.

        Args:
            parent_keys (list, optional): List of parent keys to initialize.
                Defaults to [self.default_parent_key].
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
                    "help": "tolerance (°F)",
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
                    "default": 52560,  # 1 year at 10min polling (365d × 24h × 6)
                    "valid_range": range(1, 52562),  # up to 1 year + 1 measurement
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
            self.valid_sflags += [
                self.user_inputs[parent_key][k]["sflag"]
                for k in self.user_inputs[parent_key].keys()
            ]

    def dynamic_update_user_inputs(self):
        """
        Update thermostat-specific values in user_inputs dict.

        This function expands each input parameter list to match
        the length of the thermostat parameter field.
        """
        self._initialize_parent_keys()
        input_file = self._get_input_file()

        if input_file is not None:
            self._process_input_file(input_file)
        elif self._has_populated_user_inputs():
            self._process_argv_inputs()
        else:
            self._handle_unpopulated_inputs()

        self._finalize_thermostat_configuration()

    def _initialize_parent_keys(self):
        """Initialize section list to single item list of one thermostat."""
        self.parent_keys = [self.default_parent_key]

    def _get_input_file(self):
        """Get input file from user inputs if specified."""
        return self.get_user_inputs(self.default_parent_key, input_flds.input_file)

    def _process_input_file(self, input_file):
        """Process input file and populate user inputs from file."""
        self.using_input_file = True
        self.parse_input_file(input_file)
        self.parent_keys = list(self.user_inputs_file.keys())
        self.initialize_user_inputs(self.parent_keys)
        self._populate_from_file()
        self.zone_name = self.parent_keys[0]

    def _populate_from_file(self):
        """Populate user_inputs from user_inputs_file."""
        for section in self.parent_keys:
            for fld in input_flds:
                if fld == input_flds.input_file:
                    continue  # input file field will not be in the file

                if self.user_inputs[section][fld]["type"] in [int, float, str]:
                    self._cast_field_value(section, fld)
                else:
                    self._read_raw_field_value(section, fld)

    def _cast_field_value(self, section, fld):
        """Cast data type when reading value from file."""
        try:
            cast_value = self.user_inputs[section][fld]["type"](
                self.user_inputs_file[section].get(input_flds[fld])
            )
            self.user_inputs[section][fld]["value"] = cast_value
            # cast original input value in user_inputs_file as well
            self.user_inputs_file[section][input_flds[fld]] = cast_value
        except Exception:
            print(f"exception in section={section}, fld={fld}")
            raise

    def _read_raw_field_value(self, section, fld):
        """Read raw value without casting from file."""
        self.user_inputs[section][fld]["value"] = self.user_inputs_file[section].get(
            input_flds[fld]
        )

    def _has_populated_user_inputs(self):
        """Check if user_inputs has already been populated."""
        return (
            self.get_user_inputs(
                list(self.user_inputs.keys())[0], input_flds.thermostat_type
            )
            is not None
        )

    def _process_argv_inputs(self):
        """Process argv inputs (only currently supporting 1 zone)."""
        current_keys = list(self.user_inputs.keys())
        if len(current_keys) != 1:
            raise KeyError(f"user_input keys={current_keys}, expected only 1 key")

        current_key = current_keys[0]
        new_key = self._build_zone_key(current_key)
        self.user_inputs[new_key] = self.user_inputs.pop(current_key)
        self._update_zone_parameters(new_key)

    def _build_zone_key(self, current_key):
        """Build new zone key as <zone_name>_<zone_number>."""
        thermostat_type = self.get_user_inputs(current_key, input_flds.thermostat_type)
        zone_number = self.get_user_inputs(current_key, input_flds.zone)
        return f"{thermostat_type}_{zone_number}"

    def _update_zone_parameters(self, new_key):
        """Update parameters for new parent keys."""
        self.zone_name = new_key
        self.default_parent_key = new_key
        self.parent_keys = list(self.user_inputs.keys())

    def _handle_unpopulated_inputs(self):
        """Handle case where inputs haven't been populated yet."""
        runtime_args = self.get_user_inputs(
            list(self.user_inputs.keys())[0], input_flds.thermostat_type
        )
        print(f"runtime args: {runtime_args}")

    def _finalize_thermostat_configuration(self):
        """Set up thermostat configuration for all zones."""
        for zone_name in self.parent_keys:
            thermostat_type = self._get_thermostat_type(zone_name)
            self._configure_zone_ranges(zone_name, thermostat_type)

    def _get_thermostat_type(self, zone_name):
        """Get thermostat type for zone, defaulting if not set."""
        thermostat_type = self.get_user_inputs(zone_name, input_flds.thermostat_type)
        return thermostat_type if thermostat_type is not None else self.thermostat_type

    def _configure_zone_ranges(self, zone_name, thermostat_type):
        """Configure valid ranges for zone and target mode fields."""
        self._set_zone_valid_range(zone_name, thermostat_type)
        self._set_target_mode_valid_range(zone_name, thermostat_type)

    def _set_zone_valid_range(self, zone_name, thermostat_type):
        """Set valid range for zone field."""
        try:
            self.user_inputs[zone_name][input_flds.zone][
                "valid_range"
            ] = SUPPORTED_THERMOSTATS[thermostat_type]["zones"]
        except KeyError:
            print(
                f"\nKeyError: one or more keys are invalid (zone_name="
                f"{zone_name}, zone_number={input_flds.zone}, "
                f"thermostat_type={thermostat_type})\n"
            )
            raise

    def _set_target_mode_valid_range(self, zone_name, thermostat_type):
        """Set valid range for target mode field."""
        try:
            self.user_inputs[zone_name][input_flds.target_mode][
                "valid_range"
            ] = SUPPORTED_THERMOSTATS[thermostat_type]["modes"]
        except KeyError:
            print(
                f"\nKeyError: one or more keys are invalid (zone_name="
                f"{zone_name}, target_mode={input_flds.target_mode}, "
                f"thermostat_type={thermostat_type})\n"
            )
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
    """Verify all required environment variables are present for thermostat config.

    Checks that all required environment variables for the specified thermostat type
    are present in the environment. Some environment variables may require
    zone-specific suffixes (indicated by trailing underscore).

    Args:
        tstat (str): Thermostat type alias (e.g., 'honeywell', 'emulator')
        zone_str (str): Zone identifier as string
        verbose (bool, optional): Enable debug output. Defaults to True.

    Returns:
        bool: True if all required environment variables are present

    Raises:
        KeyError: If required environment variables are missing
    """
    if verbose:
        print("\nchecking required environment variables:")
    key_status = True  # default, all keys present
    for key in thermostats[tstat]["required_env_variables"]:
        # any env key ending in '_' should have zone number appended to it.
        if key[-1] == "_":
            # append zone info to key
            key = key + str(zone_str)
        if verbose:
            print(f"checking required environment key: {key}...", end="")
        env.env_variables[key] = env.get_env_variable(key)["value"]
        if env.env_variables[key] is not None:
            if verbose:
                print("OK")
        else:
            util.log_msg(
                f"{tstat}: zone {zone_str}: FATAL error: one or more required"
                f" environemental keys are missing, exiting program",
                mode=util.BOTH_LOG,
            )
            key_status = False
            raise KeyError
    if verbose:
        print("\n")
    return key_status


def load_hardware_library(thermostat_type):
    """Dynamically load appropriate hardware library for the thermostat type.

    Imports the hardware-specific module for the given thermostat type using dynamic
    module loading. This allows the system to support multiple thermostat brands
    without static imports.

    Args:
        thermostat_type (str): Thermostat type alias (e.g., 'honeywell',
            'emulator')

    Returns:
        module: Loaded Python module for the thermostat type

    Raises:
        ImportError: If the thermostat type module cannot be loaded
        KeyError: If the thermostat type is not supported
    """
    pkg_name = (
        util.PACKAGE_NAME + "." + SUPPORTED_THERMOSTATS[thermostat_type]["module"]
    )
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
    uip = UserInputs(
        argv_list=config_mod.argv, thermostat_type=config_mod.ALIAS, zone_name=zone_name
    )
    zone_number = uip.get_user_inputs(uip.zone_name, input_flds.zone)
    return zone_number
