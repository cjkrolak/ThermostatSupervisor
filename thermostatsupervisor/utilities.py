"""Common utility functions and globals."""

# built-in libraries
import argparse
import configparser
import datetime
import inspect
import os
import platform
import socket
import sys


PACKAGE_NAME = 'thermostatsupervisor'  # should match name in __init__.py

# error codes
NO_ERROR = 0
CONNECTION_ERROR = 1
AUTHORIZATION_ERROR = 2
EMAIL_SEND_ERROR = 3
ENVIRONMENT_ERROR = 4
FILE_NOT_FOUND_ERROR = 5
OTHER_ERROR = 99

# bogus values to identify uninitialized data
BOGUS_INT = -123456789
BOGUS_BOOL = False
BOGUS_STR = "<missing value>"
bogus_dict = {}

# logging options
CONSOLE_LOG = 0x001  # print to console
DATA_LOG = 0x010  # print to data log
BOTH_LOG = 0x011  # log to both console and data logs
DEBUG_LOG = 0x100  # print only if debug mode is on

FILE_PATH = ".//data"
MAX_LOG_SIZE_BYTES = 2**20  # logs rotate at this max size
HTTP_TIMEOUT = 60  # timeout in seconds

# set unit test IP address, same as client
unit_test_mode = False  # in unit test mode


def get_function_name(stack_value=1):
    """
    Return function name from stack.

    inputs:
        stack_val(int): position in stack, 1=caller, 2=caller's parent
    returns:
        (str): function name
    """
    return inspect.stack()[stack_value][3]


def log_msg(msg, mode, func_name=-1, file_name=None):
    """
    Log message to file, console, etc.

    inputs:
        msg(str): message to log
        mode(int): log destination(s), see logging options at top of file
        func_name(int): if > 1, will include func name from this stack position
        file_name(str): if None will use default name
    returns:
        (dict): {status, tbd}
    """
    return_buffer = {
        "status": NO_ERROR,
    }

    # set debug mode
    debug_enabled = getattr(log_msg, "debug", False)
    debug_msg = mode & DEBUG_LOG
    filter_debug_msg = debug_msg and not debug_enabled

    # define filename
    if file_name is not None:
        log_msg.file_name = file_name

    # build message string
    if func_name > 0:
        msg = f"[{get_function_name(func_name)}]: {msg}"

    # log to data file
    if (mode & DATA_LOG) and not filter_debug_msg:
        # create directory if needed
        if not os.path.exists(FILE_PATH):
            print(f"data folder '{FILE_PATH}' created.")
            os.makedirs(FILE_PATH)

        # build full file name
        full_path = get_full_file_path(log_msg.file_name)

        # check file size and rotate if necessary
        file_size_bytes = get_file_size_bytes(full_path)
        file_size_bytes = log_rotate_file(full_path, file_size_bytes,
                                          MAX_LOG_SIZE_BYTES)

        # write to file
        write_to_file(full_path, file_size_bytes, msg)

    # print to console
    if (mode & CONSOLE_LOG) and not filter_debug_msg:
        print(msg)

    return return_buffer


# global default log file name if none is specified
log_msg.file_name = "default_log.txt"


def get_file_size_bytes(full_path):
    """
    Get the file size for the specified log file.

    inputs:
        full_path(str): full file name and path.
    returns:
        file_size_bytes(int): file size in bytes
    """
    try:
        file_size_bytes = os.path.getsize(full_path)
    except FileNotFoundError:
        # file does not exist
        file_size_bytes = 0
    return file_size_bytes


def log_rotate_file(full_path, file_size_bytes, max_size_bytes):
    """
    Rotate log file to prevent file from getting too large.

    inputs:
        full_path(str): full file name and path.
        file_size_bytes(int): file size in bytes
        max_size_bytes(int): max allowable file size.
    returns:
        file_size_bytes(int): file size in bytes
    """
    if file_size_bytes > max_size_bytes:
        # rotate log file
        current_date = datetime.datetime.today().strftime(
            '%d-%b-%Y-%H-%M-%S')
        os.rename(full_path, full_path[:-4] + "-" +
                  str(current_date) + '.txt')
        file_size_bytes = 0
    return file_size_bytes


def write_to_file(full_path, file_size_bytes, msg):
    """
    Rotate log file to prevent file from getting too large.

    inputs:
        full_path(str): full file name and path.
        file_size_bytes(int): file size in bytes
        msg(str): message to write.
    returns:
        (int): number of bytes written to file.
    """
    if file_size_bytes == 0:
        write_mode = "w"  # writing
    else:
        write_mode = "a"  # appending
    with open(full_path, write_mode, encoding="utf8") as file_handle:
        msg_to_write = msg + "\n"
        file_handle.write(msg_to_write)
    return utf8len(msg_to_write)


def is_windows_environment():
    """Return True if running on Windows PC."""
    print(f"DEBUG: platform={platform.system().upper()}")
    return 'WINDOWS' in platform.system().upper()


def get_full_file_path(file_name):
    """
    Return full file path.

    inputs:
        file_name(str): name of file with extension
    returns:
        (str) full file name and path
    """
    return FILE_PATH + "//" + file_name


def utf8len(input_string):
    """
    Return length of string in bytes.

    inputs:
        input_string(str): input string.
    returns:
        (int): length of string in bytes.
    """
    return len(input_string.encode('utf-8'))


def temp_value_with_units(raw, disp_unit='F', precision=1) -> str:
    """
    Return string representing temperature and units.

    inputs:
        raw(int or float): temperature value.
        disp_unit(str): display unit character.
        precision(int): number of digits after decimal.
    returns:
        (str): temperature and units.
    """
    if disp_unit.upper() not in ['C', 'F', 'K']:
        raise ValueError(f"{get_function_name()}: '{disp_unit}' is not a "
                         "valid temperature unit")

    # if string try to convert to float
    if isinstance(raw, str):
        if '°' in raw:
            return raw  # pass-thru
        try:
            raw = float(raw)
        except ValueError:
            pass

    if raw is None:
        formatted = f"{raw}"
    elif precision == 0:
        formatted = f"{raw:.0f}"
    else:
        formatted = f"{raw:.{precision}f}"
    return f'{formatted}°{disp_unit}'


def humidity_value_with_units(raw, disp_unit=' RH', precision=0) -> str:
    """
    Return string representing humidity and units.

    inputs:
        raw(int or float): humidity value.
        disp_unit(str): display unit character.
        precision(int): number of digits after decimal.
    returns:
        (str): temperature and units.
    """
    if disp_unit.upper() not in ['RH', ' RH']:
        raise ValueError(f"{get_function_name()}: '{disp_unit}' is not a "
                         " valid humidity unit")

    # if string try to convert to float
    if isinstance(raw, str):
        if '%' in raw:
            return raw  # pass-thru
        try:
            raw = float(raw)
        except ValueError:
            pass

    if raw is None:
        formatted = f"{raw}"
    elif precision == 0:
        formatted = f"{raw:.0f}"
    else:
        formatted = f"{raw:.{precision}f}"
    return f'{formatted}%{disp_unit}'


def get_key_from_value(input_dict, val):
    """
    Return first key found in dict from value provided.

    inputs:
        input_dict(dict): target dictionary
        val(str or int):  value
    returns:
        (str or int): dictionary key
    """
    for key, value in input_dict.items():
        if val == value:
            return key
    raise KeyError(f"key not found in dict '{input_dict}' with value='{val}'")


def c_to_f(tempc) -> float:
    """
    Convert from Celsius to Fahrenheit.

    inputs:
        tempc(int, float): temp in deg c.
    returns:
        (float): temp in deg f.
    """
    if isinstance(tempc, type(None)):
        return tempc  # pass thru
    elif isinstance(tempc, (int, float)):
        return tempc * 9.0 / 5 + 32
    else:
        raise TypeError(f"raw value '{tempc}' is not an int or float")


def f_to_c(tempf) -> float:
    """
    Convert from Fahrenheit to Celsius.

    inputs:
        tempc(int, float): temp in deg f.
    returns:
        (float): temp in deg c.
    """
    if isinstance(tempf, type(None)):
        return tempf  # pass thru
    elif isinstance(tempf, (int, float)):
        return (tempf - 32) * 5 / 9.0
    else:
        raise TypeError(f"raw value '{tempf}' is not an int or float")


def is_host_on_local_net(host_name, ip_address=None, verbose=False):
    """
    Return True if specified host is on local network.
    socket.gethostbyaddr() throws exception for some IP address
    so preferred way to use this function is to pass in only the
    hostname and leave the IP as default (None).
    inputs:
        host_name(str): expected host name.
        ip_address(str): target IP address on local net.
        verbose(bool): if True, print out status.
    returns:
        tuple(bool, str): True if confirmed on local net, else False.
                          ip_address if known
    """
    host_found = None
    # find by hostname alone if IP is None
    if ip_address is None:
        try:
            host_found = socket.gethostbyname(host_name)
        except socket.gaierror:
            return False, None
        if host_found:
            if verbose:
                print(f"host {host_name} found at {host_found} on local net")
            return True, host_found
        else:
            if verbose:
                print(f"host {host_name} is not detected on local net")
            return False, None

    else:
        # match both IP and host if both are provided.
        try:
            host_found = socket.gethostbyaddr(ip_address)
        except socket.herror:  # exception if DNS name is not set
            return False, None
        if host_name == host_found[0]:
            return True, ip_address
        else:
            print(f"DEBUG: expected host={host_name}, "
                  f"actual host={host_found}")
            return False, None


# default parent_key if user_inputs are not pulled from file
default_parent_key = "argv"


class UserInputs():
    """Manage runtime arguments."""

    def __init__(self, argv_list, help_description, suppress_warnings=False,
                 parent_key=default_parent_key,
                 *_, **__):
        """
        Base Class UserInputs Constructor.

        user_inputs is a dictionary of runtime parameters.
        structure = {<parent_key> : {<child_key: {}}
        dict can have multiple parent_keys and multiple child_keys

        inputs:
            argv_list(list): override runtime values.
            help_description(str): description field for help text.
            suppress_warnings(bool): True to suppress warning msgs.
            parent_key(str, int): parent key
        """
        self.argv_list = argv_list
        self.default_parent_key = parent_key
        self.parent_keys = [parent_key]
        self.help_description = help_description
        self.suppress_warnings = suppress_warnings
        self.parser = argparse.ArgumentParser(
            description=self.help_description)
        self.user_inputs = {}
        self.user_inputs_file = {}
        self.using_input_file = False
        self.initialize_user_inputs()
        # parse the runtime arguments from input list or sys.argv
        self.parse_runtime_parameters(argv_list)

    def initialize_user_inputs(self, parent_keys=None):
        """Populate user_inputs dictionary."""
        pass  # placeholder, is instance-specific

    def get_sflag_list(self):
        """Return a list of all sflags."""
        valid_sflags = []
        for parent_key, child_dict in self.user_inputs.items():
            for child_key, _ in child_dict.items():
                valid_sflags.append(self.user_inputs[parent_key][
                    child_key]["sflag"])
        return valid_sflags

    def parse_runtime_parameters(self, argv_list=None):
        """
        Parse all runtime parameters from list, argv list or named
        arguments.

        If argv_list is input then algo will default to input list.
        ElIf hyphen is found in argv the algo will default to named args.
        inputs:
           argv_list: list override for sys.argv
        returns:
          argv_dict(dict)
        """
        sysargv_sflags = [str(elem)[:2] for elem in sys.argv[1:]]
        if self.user_inputs is None:
            raise ValueError("user_inputs cannot be None")
        parent_key = list(self.user_inputs.keys())[0]
        valid_sflags = self.get_sflag_list()
        valid_sflags += ["-h", "--"]  # add help and double dash
        if argv_list:
            # argument list input, support parsing list
            argvlist_sflags = [str(elem)[:2] for elem in argv_list]
            if any([flag in argvlist_sflags for flag in valid_sflags]):
                log_msg(
                    f"parsing named runtime parameters from user input list: "
                    f"{argv_list}",
                    mode=DEBUG_LOG +
                    CONSOLE_LOG,
                    func_name=1)
                self.parse_named_arguments(argv_list=argv_list)
            else:
                log_msg(
                    f"parsing runtime parameters from user input list: "
                    f"{argv_list}",
                    mode=DEBUG_LOG +
                    CONSOLE_LOG,
                    func_name=1)
                self.parse_argv_list(
                    parent_key, argv_list)
        elif any([flag in sysargv_sflags for flag in valid_sflags]):
            # named arguments from sys.argv
            log_msg(
                f"parsing named runtime parameters from sys.argv: {sys.argv}",
                mode=DEBUG_LOG +
                CONSOLE_LOG,
                func_name=1)
            self.parse_named_arguments()
        else:
            # sys.argv parsing
            log_msg(
                f"parsing runtime parameters from sys.argv: {sys.argv}",
                mode=DEBUG_LOG +
                CONSOLE_LOG,
                func_name=1)
            self.parse_argv_list(parent_key, sys.argv)

        # dynamically update valid range and defaults
        # also can trigger input file parsing based on input flags
        self.dynamic_update_user_inputs()

        # validate inputs
        self.validate_argv_inputs(self.user_inputs)

        return self.user_inputs

    def parse_named_arguments(self, parent_key=None, argv_list=None):
        """
        Parse all possible named arguments.

        inputs:
            parent_key(str): parent key for dict.
            argv_list(list): override sys.argv (for testing)
        returns:
            (dict) of all runtime parameters.
        """
        # set parent key
        if parent_key is None:
            parent_key = self.default_parent_key

        # load parser contents
        for _, attr in self.user_inputs[parent_key].items():
            self.parser.add_argument(attr["lflag"], attr["sflag"],
                                     default=attr["default"],
                                     type=attr["type"],
                                     required=attr["required"],
                                     help=attr["help"]
                                     )
        # parse the argument list
        if argv_list is not None:
            # test mode, override sys.argv
            args = self.parser.parse_args(argv_list[1:])
        else:
            args = self.parser.parse_args()
        for key in self.user_inputs[parent_key]:
            if key == "script":
                # add script name
                self.user_inputs[parent_key][key]["value"] = sys.argv[0]
            else:
                self.user_inputs[parent_key][key]["value"] = getattr(args,
                                                                     key, None)
                strip_types = str
                if isinstance(self.user_inputs[parent_key][key]["value"],
                              strip_types):
                    # str parsing has leading spaces for some reason
                    self.user_inputs[parent_key][key]["value"] = \
                        self.user_inputs[parent_key][key]["value"].strip()

        return self.user_inputs

    def parse_argv_list(self, parent_key, argv_list=None):
        """
        Parse un-named arguments from list.

        inputs:
            parent_key(str): parent key in the user_inputs dict.
            argv_list(list): list of runtime arguments in the order
                             argv_list[0] should be script name.
                             speci5fied in argv_dict "order" fields.
        returns:
            (dict) of all runtime parameters.
        """
        # set parent key
        if parent_key is None:
            parent_key = self.default_parent_key

        # if argv list is set use that, else use sys.argv
        if argv_list:
            argv_inputs = argv_list
        else:
            argv_inputs = sys.argv

        # populate dict with values from list
        for child_key, val in self.user_inputs[parent_key].items():
            if val["order"] <= len(argv_inputs) - 1:
                if (self.user_inputs[parent_key][child_key]["type"] in
                        [int, float, str]):
                    # cast data type when reading value
                    self.user_inputs[parent_key][child_key]["value"] = (
                        self.user_inputs[parent_key][child_key][
                            "type"](argv_inputs[val["order"]]))
                else:
                    # no casting, just read raw from list
                    self.user_inputs[parent_key][child_key]["value"] = \
                        argv_inputs[val["order"]]

        return self.user_inputs

    def dynamic_update_user_inputs(self):
        """Update user_inputs dict dynamically based on runtime parameters."""
        pass  # placeholder

    def validate_argv_inputs(self, argv_dict):
        """
        Validate argv inputs and update reset to defaults if necessary.

        inputs:
            argv_dict(dict): dictionary of runtime args with these elements:
            <parent_key>: {
            <key>: {  # key = argument name
                "order": 0,  # order in the argv list
                "value": None,   # initialized to None
                "type": str,  # datatype
                "default": "supervise.py",  # default value
                "sflag": "-s",  # short flag identifier
                "lflag": "--script",  # long flag identifier
                "help": "script name"},  # help text
                "valid": None,  # valid choices
                "required": True,  # is parameter required?
            }}
        returns:
            (dict) of all runtime parameters, only needed for testing.
        """
        for parent_key, child_dict in argv_dict.items():
            for child_key, attr in child_dict.items():
                proposed_value = attr["value"]
                default_value = attr["default"]
                proposed_type = type(proposed_value)
                expected_type = attr["type"]
                # missing value check
                if proposed_value is None:
                    if not self.suppress_warnings:
                        log_msg(
                            f"parent_key={parent_key}, child_key='{child_key}'"
                            f": argv parameter missing, using default "
                            f"value '{default_value}'",
                            mode=DEBUG_LOG +
                            CONSOLE_LOG,
                            func_name=1)
                    attr["value"] = attr["default"]

                # wrong datatype check
                elif proposed_type != expected_type:
                    if not self.suppress_warnings:
                        log_msg(
                            f"parent_key={parent_key}, child_key='{child_key}'"
                            f": datatype error, expected="
                            f"{expected_type}, actual={proposed_type}, "
                            "using default value "
                            f"'{default_value}'",
                            mode=DEBUG_LOG +
                            CONSOLE_LOG,
                            func_name=1)
                    attr["value"] = attr["default"]

                # out of range check
                elif (attr["valid_range"] is not None and
                      proposed_value not in attr["valid_range"]):
                    if not self.suppress_warnings:
                        log_msg(
                            f"WARNING: '{proposed_value}' is not a valid "
                            f"choice parent_key='{parent_key}', child_key="
                            f"'{child_key}', using default '{default_value}'",
                            mode=BOTH_LOG,
                            func_name=1)
                    attr["value"] = attr["default"]

        return argv_dict

    def get_user_inputs(self, parent_key, child_key, field="value"):
        """
        Return the target key's value from user_inputs.

        inputs:
            parent_key(str): top-level key
            child_key(str): second-level key
            field(str): field name, default = "value"
        returns:
            None
        """
        if child_key is None:
            return self.user_inputs[parent_key][field]
        else:
            try:
                return self.user_inputs[parent_key][child_key][field]
            except TypeError:
                print(f"TypeError: parent_key({type(parent_key)})={parent_key}"
                      f", child_key({type(child_key)})={child_key}, "
                      f"field({type(field)})={field})")
                raise
            except KeyError:
                print(f"KeyError: target=[{parent_key}][{child_key}][{field}],"
                      f" raw={self.user_inputs.keys()}")
                raise

    def set_user_inputs(self, parent_key, child_key, input_val, field="value"):
        """
        Set the target key's value from user_inputs.

        inputs:
            parent_key(str): top-level key
            child_key(str): second-level key
            input_val(str, int, float, etc.):  value to set.
            field(str): field name, default = "value"
        returns:
            None, updates uip.user_inputs dict.
        """
        if child_key is None:
            self.user_inputs[parent_key][field] = input_val
        else:
            try:
                self.user_inputs[parent_key][child_key][field] = input_val
            except TypeError:
                print(f"TypeError: keys={self.user_inputs.keys()} "
                      f"(type={type(self.user_inputs.keys())})")
                raise
            except KeyError:
                print(f"KeyError: target=[{parent_key}][{child_key}][{field}],"
                      f" raw={self.user_inputs.keys()}")
                raise

    def is_valid_file(self, arg):
        """
        Verify file input is valid.

        inputs:
            arg(str): file name with path.
        returns:
            open file handle
        """
        arg = arg.strip()  # remove any leading spaces
        if not os.path.exists(arg):
            self.parser.error(f"The file {os.path.abspath(arg)} "
                              "does not exist!")
        else:
            return open(arg, 'r', encoding="utf8")  # return a file handle

    def parse_input_file(self, input_file):
        """
        Parse an input file into a dict.

        Primary key is the section.
        Secondary key is the parameter.
        """
        input_file = input_file.strip()  # strip any whitespace
        config = configparser.ConfigParser()
        result = config.read(os.path.join(os.getcwd(), input_file))
        if not result:
            raise FileNotFoundError(f"file '{input_file}' was not found")
        sections = config.sections()
        if not sections:
            raise ValueError("INI file must have sections")
        for section in sections:
            self.user_inputs_file[section] = {}
            for key in config[section]:
                self.user_inputs_file[section][key] = config[section][key]
