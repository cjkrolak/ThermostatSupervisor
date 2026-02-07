"""Common utility functions and globals."""

# built-in libraries
import argparse
import configparser
import datetime
import inspect
import os
import socket
import sys
import time
import traceback

# third-party libraries
import requests

# local imports

PACKAGE_NAME = "src"  # should match name in __init__.py

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
STDOUT_LOG = 0b0001  # print to console
DATA_LOG = 0b0010  # print to data log
BOTH_LOG = 0b0011  # log to both console and data logs
DEBUG_LOG = 0b0100  # print only if debug mode is on
STDERR_LOG = 0b1000  # print to stderr
QUIET_LOG = 0b10000  # reduced verbosity for console, full logging to file
DUAL_STREAM_LOG = 0b10010  # quiet console + full file logging

# unique log modes (excluding combinations)
log_modes = {
    STDOUT_LOG: "stdout log",
    DATA_LOG: "data log",
    DEBUG_LOG: "print only if debug mode enabled",
    STDERR_LOG: "stderr log",
    QUIET_LOG: "reduced verbosity console",
    DUAL_STREAM_LOG: "quiet console + full file logging",
}

FILE_PATH = ".//data"
MAX_LOG_SIZE_BYTES = 2**20  # logs rotate at this max size
STDOUT_CAPTURE_HOURS = 24  # hours of stdout to capture in dual stream mode
STDOUT_CAPTURE_FILE = "stdout_capture.txt"  # filename for captured stdout
HTTP_TIMEOUT = 60  # timeout in seconds
MIN_WIFI_DBM = -70.0  # min viable WIFI signal strength

# set unit test IP address, same as client
unit_test_mode = False  # in unit test mode
log_stdout_to_stderr = False  # in flask server mode


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

    # cast STDOUT_LOG to STDERR_LOG in flask server mode
    if log_stdout_to_stderr and (mode & STDOUT_LOG):
        if not (mode & STDERR_LOG):
            # Convert STDOUT to STDERR when not already present
            mode = mode + STDERR_LOG - STDOUT_LOG
        else:
            # Remove STDOUT when STDERR is already present to avoid duplicates
            mode = mode - STDOUT_LOG

    # define filename
    if file_name is not None:
        log_msg.file_name = file_name  # type: ignore[attr-defined]

    # build message string
    if func_name > 0:
        msg = f"[{get_function_name(func_name)}]: {msg}"

    # log to data file
    if (mode & DATA_LOG) and not filter_debug_msg:
        # create directory if needed
        if not os.path.exists(FILE_PATH):
            # Log directory creation to stderr to avoid polluting stdout
            print(f"data folder '{FILE_PATH}' created.", file=sys.stderr)
            os.makedirs(FILE_PATH)

        # build full file name
        full_path = get_full_file_path(log_msg.file_name)  # type: ignore[attr-defined]

        # check file size and rotate if necessary
        file_size_bytes = get_file_size_bytes(full_path)
        file_size_bytes = log_rotate_file(
            full_path, file_size_bytes, MAX_LOG_SIZE_BYTES
        )

        # write to file
        write_to_file(full_path, file_size_bytes, msg)

    # print to console
    if (mode & STDOUT_LOG) and not filter_debug_msg and not (mode & DUAL_STREAM_LOG):
        print(msg)

    # print to error stream
    if (mode & STDERR_LOG) and not filter_debug_msg:
        print(msg, file=sys.stderr)

    # handle dual stream logging (quiet console + full file + stdout capture)
    if (mode & DUAL_STREAM_LOG) and not filter_debug_msg:
        # Capture full message to stdout capture file
        manage_stdout_capture_file(msg)

        # Print only summary/reduced message to console for certain verbose cases
        if _is_verbose_retry_message(msg):
            summary_msg = _create_summary_message(msg)
            print(summary_msg)
        else:
            # Print full message for non-verbose cases
            print(msg)

    # handle quiet logging (reduced verbosity)
    if (mode & QUIET_LOG) and not filter_debug_msg and not (mode & DUAL_STREAM_LOG):
        if _is_verbose_retry_message(msg):
            summary_msg = _create_summary_message(msg)
            print(summary_msg)
        else:
            print(msg)

    return return_buffer


# global default log file name if none is specified
log_msg.file_name = "default_log.txt"  # type: ignore[attr-defined]


def _is_verbose_retry_message(msg):
    """
    Determine if a message is a verbose retry-related message that should be
    summarized for console output.

    inputs:
        msg(str): message to check
    returns:
        (bool): True if message should be summarized for console
    """
    verbose_indicators = [
        "Traceback (most recent call last):",
        "pyhtcc.pyhtcc.UnauthorizedError:",
        "Got unauthorized response from server",
        "WARNING: exception on trial",
        "execute_with_extended_retries:",
        "Delaying",
        "prior to retry",
        "ERROR: exhausted",
        "retries during",
        "<html",  # HTML error responses
        "<!DOCTYPE html",
    ]
    return any(indicator in msg for indicator in verbose_indicators)


def _create_summary_message(msg):
    """
    Create a summary message for verbose retry errors.

    inputs:
        msg(str): original verbose message
    returns:
        (str): summarized message for console output
    """
    if "WARNING: exception on trial" in msg:
        # Extract trial information
        parts = msg.split()
        trial_info = ""
        for i, part in enumerate(parts):
            if part == "trial" and i + 1 < len(parts):
                trial_info = f" (trial {parts[i + 1]})"
                break
        return f"[Retry] Connection error{trial_info} - details in log file"

    elif "Traceback" in msg:
        return "[Error] Exception occurred - full traceback in log file"

    elif "pyhtcc.pyhtcc.UnauthorizedError" in msg:
        return "[Auth] Authorization error - retrying..."

    elif "execute_with_extended_retries" in msg:
        if "starting" in msg:
            return "[Retry] Starting retry sequence - progress tracked in log file"
        elif "trial" in msg:
            # Extract trial info for progress tracking
            parts = msg.split()
            trial_info = ""
            for i, part in enumerate(parts):
                if part == "trial" and i + 2 < len(parts):
                    trial_info = f" {parts[i + 1]} of {parts[i + 3]}"
                    break
            return f"[Retry] Progress{trial_info} - details in log file"
        else:
            return "[Retry] Operation in progress - details in log file"

    elif "Delaying" in msg and "prior to retry" in msg:
        # Extract delay time
        parts = msg.split()
        delay_time = ""
        for i, part in enumerate(parts):
            if part == "Delaying" and i + 1 < len(parts):
                delay_time = parts[i + 1]
                break
        return f"[Retry] Waiting {delay_time}s before next attempt..."

    elif "ERROR: exhausted" in msg and "retries" in msg:
        return "[Error] All retry attempts failed - check log for details"

    elif "<html" in msg or "<!DOCTYPE html" in msg:
        return "[Response] HTML error response received - details in log file"

    else:
        # For other verbose messages, show first line only
        first_line = msg.split("\n")[0]
        if len(first_line) > 80:
            return first_line[:77] + "..."
        return first_line


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
        current_date = datetime.datetime.today().strftime("%d-%b-%Y-%H-%M-%S")
        os.rename(full_path, full_path[:-4] + "-" + str(current_date) + ".txt")
        file_size_bytes = 0
    return file_size_bytes


def log_rotate_file_by_time(full_path, max_age_hours):
    """
    Rotate log file based on age to prevent files from getting too old.

    inputs:
        full_path(str): full file name and path.
        max_age_hours(int): maximum age in hours before rotation
    returns:
        file_rotated(bool): True if file was rotated
    """
    try:
        # Get file modification time
        file_mod_time = os.path.getmtime(full_path)
        current_time = time.time()
        age_hours = (current_time - file_mod_time) / 3600

        if age_hours > max_age_hours:
            # Rotate log file with timestamp
            current_date = datetime.datetime.fromtimestamp(file_mod_time).strftime(
                "%d-%b-%Y-%H-%M-%S"
            )
            backup_path = full_path[:-4] + "-" + str(current_date) + ".txt"
            os.rename(full_path, backup_path)
            return True
    except FileNotFoundError:
        # File does not exist, no rotation needed
        pass
    except OSError:
        # Handle permission or other OS errors gracefully
        pass
    return False


def manage_stdout_capture_file(msg):
    """
    Manage stdout capture file with 24-hour retention.

    inputs:
        msg(str): message to write to stdout capture file
    returns:
        (bool): True if message was written successfully
    """
    try:
        full_path = get_full_file_path(STDOUT_CAPTURE_FILE)

        # Create directory if needed
        if not os.path.exists(FILE_PATH):
            os.makedirs(FILE_PATH)

        # Rotate file if older than 24 hours
        log_rotate_file_by_time(full_path, STDOUT_CAPTURE_HOURS)

        # Write message with timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        timestamped_msg = f"[{timestamp}] {msg}"

        # Determine write mode
        write_mode = "a" if os.path.exists(full_path) else "w"

        with open(full_path, write_mode, encoding="utf8") as file_handle:
            file_handle.write(timestamped_msg + "\n")
        return True
    except (OSError, IOError):
        # Handle file system errors gracefully
        return False


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
    return len(input_string.encode("utf-8"))


def temp_value_with_units(raw, disp_unit="F", precision=1) -> str:
    """
    Return string representing temperature and units.

    inputs:
        raw(int or float): temperature value.
        disp_unit(str): display unit character.
        precision(int): number of digits after decimal.
    returns:
        (str): temperature and units.
    """
    if disp_unit.upper() not in ["C", "F", "K"]:
        raise ValueError(
            f"{get_function_name()}: '{disp_unit}' is not a valid temperature unit"
        )

    # if string try to convert to float
    if isinstance(raw, str):
        if "°" in raw:
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
    return f"{formatted}°{disp_unit}"


def humidity_value_with_units(raw, disp_unit=" RH", precision=0) -> str:
    """
    Return string representing humidity and units.

    inputs:
        raw(int or float): humidity value.
        disp_unit(str): display unit character.
        precision(int): number of digits after decimal.
    returns:
        (str): temperature and units.
    """
    if disp_unit.upper() not in ["RH", " RH"]:
        raise ValueError(
            f"{get_function_name()}: '{disp_unit}' is not a valid humidity unit"
        )

    # if string try to convert to float
    if isinstance(raw, str):
        if "%" in raw:
            return raw  # pass-thru
        try:
            raw = float(raw)
        except ValueError:
            pass

    if raw is None:
        return f"{raw}"  # pass-thru
    elif precision == 0:
        formatted = f"{raw:.0f}"
    else:
        formatted = f"{raw:.{precision}f}"
    return f"{formatted}%{disp_unit}"


def _match_value_by_type(value, val):
    """Check if val matches value based on value's type."""
    if isinstance(value, (str, int, float)):
        return val == value
    elif isinstance(value, dict):
        return val in value.keys() or val in value.values()
    elif isinstance(value, list):
        return val in value
    else:
        raise TypeError(f"type {type(value)} not yet supported in get_key_from_value")


def get_key_from_value(input_dict, val):
    """
    Return first key found in dict from value provided.

    Matching criteria depends upon the type of the value contained
    within the input dictionary:
        (str, int, float): exact value match required
        (dict): exact match of one of the child keys or values required
        (list): exact match of one of the list elements provided
        (other type): TypeError raised

    inputs:
        input_dict(dict): target dictionary
        val(str, int, float, dict, list):  value
    returns:
        (str or int): dictionary key
    """
    for key, value in input_dict.items():
        if _match_value_by_type(value, val):
            return key

    # key not found
    raise KeyError(f"key not found in dict '{input_dict}' with value='{val}'")


def c_to_f(tempc) -> float | None:
    """
    Convert from Celsius to Fahrenheit.

    inputs:
        tempc(int, float, None): temp in °C.
    returns:
        (float | None): temp in °F, or None if input is None.
    """
    if isinstance(tempc, type(None)):
        return None  # pass through None
    elif isinstance(tempc, (int, float)):
        return tempc * 9.0 / 5 + 32
    else:
        raise TypeError(f"raw value '{tempc}' is not an int or float")


def f_to_c(tempf) -> float | None:
    """
    Convert from Fahrenheit to Celsius.

    inputs:
        tempf(int, float, None): temp in °F.
    returns:
        (float | None): temp in °C, or None if input is None.
    """
    if isinstance(tempf, type(None)):
        return None  # pass through None
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
        if verbose:
            print(f"host {host_name} is not detected on local net")
        return False, None

    # match both IP and host if both are provided.
    try:
        host_found = socket.gethostbyaddr(ip_address)
    except socket.herror:  # exception if DNS name is not set
        return False, None
    if host_name == host_found[0]:
        return True, ip_address
    print(f"DEBUG: expected host={host_name}, actual host={host_found}")
    return False, None


# default parent_key if user_inputs are not pulled from file
default_parent_key = "argv"


class UserInputs:
    """Manage runtime arguments."""

    def __init__(
        self,
        argv_list,
        help_description,
        suppress_warnings=False,
        parent_key=default_parent_key,
        *_,
        **__,
    ):
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
        self.parser = argparse.ArgumentParser(description=self.help_description)
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
                valid_sflags.append(self.user_inputs[parent_key][child_key]["sflag"])
        return valid_sflags

    def get_lflag_list(self):
        """Return a list of all lflags."""
        valid_lflags = []
        for parent_key, child_dict in self.user_inputs.items():
            for child_key, _ in child_dict.items():
                valid_lflags.append(self.user_inputs[parent_key][child_key]["lflag"])
        return valid_lflags

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
        valid_lflags = self.get_lflag_list()
        valid_flags = valid_sflags + valid_lflags + ["-h", "--"]  # combine all flags
        if argv_list:
            # argument list input, support parsing list
            argvlist_flags = []
            for elem in argv_list:
                elem_str = str(elem)
                if elem_str.startswith("--"):
                    # For long flags, check the full flag (before any '=')
                    flag_part = elem_str.split("=")[0]
                    argvlist_flags.append(flag_part)
                else:
                    # For short flags, check first 2 characters
                    argvlist_flags.append(elem_str[:2])
            if any([flag in argvlist_flags for flag in valid_flags]):
                log_msg(
                    f"parsing named runtime parameters from user input list: "
                    f"{argv_list}",
                    mode=DEBUG_LOG + STDOUT_LOG,
                    func_name=1,
                )
                self.parse_named_arguments(argv_list=argv_list)
            else:
                log_msg(
                    f"parsing runtime parameters from user input list: {argv_list}",
                    mode=DEBUG_LOG + STDOUT_LOG,
                    func_name=1,
                )
                self.parse_argv_list(parent_key, argv_list)
        elif any([flag in sysargv_sflags for flag in valid_flags]):
            # named arguments from sys.argv
            log_msg(
                f"parsing named runtime parameters from sys.argv: {sys.argv}",
                mode=DEBUG_LOG + STDOUT_LOG,
                func_name=1,
            )
            self.parse_named_arguments()
        else:
            # sys.argv parsing
            log_msg(
                f"parsing runtime parameters from sys.argv: {sys.argv}",
                mode=DEBUG_LOG + STDOUT_LOG,
                func_name=1,
            )
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
            self.parser.add_argument(
                attr["lflag"],
                attr["sflag"],
                default=attr["default"],
                type=attr["type"],
                required=attr["required"],
                help=attr["help"],
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
                self.user_inputs[parent_key][key]["value"] = getattr(args, key, None)
                strip_types = str
                if isinstance(self.user_inputs[parent_key][key]["value"], strip_types):
                    # str parsing has leading spaces for some reason
                    self.user_inputs[parent_key][key]["value"] = self.user_inputs[
                        parent_key
                    ][key]["value"].strip()

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
                if (
                    self.user_inputs[parent_key][child_key]["type"] in [int, float, str]
                ) or self.is_lambda_bool(
                    self.user_inputs[parent_key][child_key]["type"]
                ):
                    # cast data type when reading value
                    self.user_inputs[parent_key][child_key]["value"] = self.user_inputs[
                        parent_key
                    ][child_key]["type"](argv_inputs[val["order"]])
                else:
                    # no casting, just read raw from list
                    self.user_inputs[parent_key][child_key]["value"] = argv_inputs[
                        val["order"]
                    ]

        return self.user_inputs

    def is_lambda_bool(self, input_type):
        """
        Return True if type is a lambda function.

        inputs:
            input_type(type): input type
        returns:
            (bool): True for lambda type
        """
        # cast to string if necessary
        if not isinstance(input_type, str):
            input_type = str(input_type)

        # eval
        return True if "lambda" in input_type else False

    def dynamic_update_user_inputs(self):
        """Update user_inputs dict dynamically based on runtime parameters."""
        pass  # placeholder

    def _determine_expected_type(self, attr):
        """Determine the expected type for an attribute."""
        if attr["type"] == bool:
            raise TypeError(
                "CODING ERROR: UserInput bool "
                "typedefs don't work, use a lambda "
                "function"
            )
        elif self.is_lambda_bool(attr["type"]):
            return bool
        else:
            return attr["type"]

    def _handle_missing_value(self, parent_key, child_key, attr):
        """Handle case where attribute value is missing."""
        if not self.suppress_warnings:
            log_msg(
                f"parent_key={parent_key}, child_key='{child_key}'"
                f": argv parameter missing, using default "
                f"value '{attr['default']}'",
                mode=DEBUG_LOG + STDOUT_LOG,
                func_name=1,
            )
        attr["value"] = attr["default"]

    def _handle_wrong_datatype(
        self, parent_key, child_key, attr, expected_type, proposed_type
    ):
        """Handle case where attribute has wrong datatype."""
        if not self.suppress_warnings:
            log_msg(
                f"parent_key={parent_key}, child_key='{child_key}'"
                f": datatype error, expected="
                f"{expected_type}, actual={proposed_type}, "
                "using default value "
                f"'{attr['default']}'",
                mode=DEBUG_LOG + STDOUT_LOG,
                func_name=1,
            )
        attr["value"] = attr["default"]

    def _handle_out_of_range(self, parent_key, child_key, attr):
        """Handle case where attribute value is out of valid range."""
        if not self.suppress_warnings:
            log_msg(
                f"WARNING: '{attr['value']}' is not a valid "
                f"choice parent_key='{parent_key}', child_key="
                f"'{child_key}', using default '{attr['default']}'",
                mode=BOTH_LOG,
                func_name=1,
            )
        attr["value"] = attr["default"]

    def _validate_single_attribute(self, parent_key, child_key, attr):
        """Validate a single attribute and update if necessary."""
        proposed_value = attr["value"]
        proposed_type = type(proposed_value)
        expected_type = self._determine_expected_type(attr)

        # missing value check
        if proposed_value is None:
            self._handle_missing_value(parent_key, child_key, attr)
        # wrong datatype check
        elif proposed_type != expected_type:
            self._handle_wrong_datatype(
                parent_key, child_key, attr, expected_type, proposed_type
            )
        # out of range check
        elif (
            attr["valid_range"] is not None
            and proposed_value not in attr["valid_range"]
        ):
            self._handle_out_of_range(parent_key, child_key, attr)

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
                self._validate_single_attribute(parent_key, child_key, attr)

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
                print(
                    f"TypeError: parent_key({type(parent_key)})={parent_key}"
                    f", child_key({type(child_key)})={child_key}, "
                    f"field({type(field)})={field})"
                )
                raise
            except KeyError:
                print(
                    f"KeyError: target=[{parent_key}][{child_key}][{field}],"
                    f" raw={self.user_inputs.keys()}"
                )
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
                print(
                    f"TypeError: keys={self.user_inputs.keys()} "
                    f"(type={type(self.user_inputs.keys())})"
                )
                raise
            except KeyError:
                print(
                    f"KeyError: target=[{parent_key}][{child_key}][{field}],"
                    f" raw={self.user_inputs.keys()}"
                )
                raise

    def is_valid_file(self, arg=None):
        """
        Verify file input is valid.

        inputs:
            arg(str): file name with path.
        returns:
            open file handle
        """
        if arg is not None:
            arg = arg.strip()  # remove any leading spaces
        if arg in [None, ""]:
            self.parser.error(f"The file '{arg}' does not exist!")
        elif arg is not None and not os.path.exists(arg):
            self.parser.error(f"The file '{os.path.abspath(arg)}' does not exist!")
        elif arg is not None:
            return open(arg, "r", encoding="utf8")  # return a file handle

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


def _get_default_exception_types():
    """Get default exception types for retry mechanism."""
    return (
        requests.exceptions.ConnectionError,
        requests.exceptions.HTTPError,
        requests.exceptions.Timeout,
        ConnectionError,
        TimeoutError,
    )


def _initialize_retry_parameters(initial_retry_delay_sec):
    """Initialize retry parameters."""
    initial_trial_number = 1
    trial_number = initial_trial_number
    retry_delay_sec = initial_retry_delay_sec
    return initial_trial_number, trial_number, retry_delay_sec


def _handle_server_spamming_detection(tc, ex):
    """Check for and handle server spamming detection."""
    if tc is None:
        return

    # Check for TooManyAttemptsError to detect server spamming
    if "TooManyAttemptsError" in str(type(ex)):
        tc.server_spamming_detected = True
        log_msg(
            "CRITICAL: pyhtcc server spamming detected - "
            "subsequent Honeywell integration tests will be skipped",
            mode=BOTH_LOG,
            func_name=1,
        )


def _send_retry_email_alert(
    email_notification,
    thermostat_type,
    zone_name,
    trial_number,
    number_of_retries,
    time_now,
):
    """Send email alert for retry attempt."""
    if email_notification is None:
        return

    try:
        email_notification.send_email_alert(
            subject=(
                f"{thermostat_type} zone "
                f"{zone_name}: "
                "intermittent error during "
                f"{get_function_name()}"
            ),
            body=(
                f"{get_function_name()}: trial "
                f"{trial_number} of "
                f"{number_of_retries} at "
                f"{time_now}\n{traceback.format_exc()}"
            ),
        )
    except Exception:
        # Don't let email failures prevent retry logic
        pass


def _send_success_email_alert(
    email_notification,
    thermostat_type,
    zone_name,
    trial_number,
    number_of_retries,
    time_now,
):
    """Send email alert for successful retry after failure."""
    if email_notification is None:
        return

    try:
        email_notification.send_email_alert(
            subject=(
                f"{thermostat_type} zone "
                f"{zone_name}: "
                "(mitigated) intermittent connection error "
                f"during {get_function_name()}"
            ),
            body=(
                f"{get_function_name()}: trial "
                f"{trial_number} of {number_of_retries} at "
                f"{time_now}"
            ),
        )
    except Exception:
        # Don't let email failures affect the successful result
        pass


def _handle_retry_exception(
    tc,
    ex,
    trial_number,
    number_of_retries,
    retry_delay_sec,
    time_now,
    email_notification,
    thermostat_type,
    zone_name,
):
    """Handle exception during retry attempt."""
    # Set flag to force re-authentication if available
    if tc is not None:
        tc.connection_ok = False

    _handle_server_spamming_detection(tc, ex)

    # Use dual stream logging for verbose retry messages
    log_msg(
        f"WARNING: exception on trial {trial_number}",
        mode=DUAL_STREAM_LOG,
        func_name=1,
    )
    log_msg(traceback.format_exc(), mode=DUAL_STREAM_LOG, func_name=1)

    msg_suffix = [
        "",
        f" waiting {retry_delay_sec} seconds and then retrying...",
    ][trial_number < number_of_retries]

    log_msg(
        f"{time_now}: exception during "
        f"{get_function_name()}"
        f", on trial {trial_number} of "
        f"{number_of_retries}, probably a"
        " connection issue"
        f"{msg_suffix}",
        mode=DUAL_STREAM_LOG,
        func_name=1,
    )

    # Send warning email if email notification module is available
    _send_retry_email_alert(
        email_notification,
        thermostat_type,
        zone_name,
        trial_number,
        number_of_retries,
        time_now,
    )

    # Exhausted retries, raise exception
    if trial_number >= number_of_retries:
        log_msg(
            f"ERROR: exhausted {number_of_retries} "
            f"retries during {get_function_name()}",
            mode=DUAL_STREAM_LOG,
            func_name=1,
        )
        raise ex


def _handle_retry_delay(trial_number, number_of_retries, retry_delay_sec):
    """Handle delay between retry attempts."""
    if trial_number < number_of_retries:
        log_msg(
            f"Delaying {retry_delay_sec} prior to retry...",
            mode=DUAL_STREAM_LOG,
            func_name=1,
        )
        time.sleep(retry_delay_sec)


def _handle_successful_retry(
    tc,
    trial_number,
    initial_trial_number,
    email_notification,
    thermostat_type,
    zone_name,
    number_of_retries,
    time_now,
):
    """Handle successful function execution after retries."""
    # Log the mitigated failure if we had to retry
    if trial_number > initial_trial_number:
        _send_success_email_alert(
            email_notification,
            thermostat_type,
            zone_name,
            trial_number,
            number_of_retries,
            time_now,
        )

    # Reset connection status if available
    if tc is not None:
        tc.connection_ok = True


def execute_with_extended_retries(
    func,
    thermostat_type: str,
    zone_name: str,
    number_of_retries: int = 5,
    initial_retry_delay_sec: int = 30,
    exception_types: tuple = None,  # type: ignore[assignment]
    email_notification=None,
):
    """
    Execute a function with extended retry logic and exponential backoff.

    This function standardizes the retry mechanism across all thermostat types,
    based on the implementation originally in honeywell.py.

    inputs:
        func(callable): function to execute with retries
        thermostat_type(str): thermostat type for logging/email
        zone_name(str): zone name for logging/email
        number_of_retries(int): maximum number of retry attempts (default: 5)
        initial_retry_delay_sec(int): initial delay between retries in seconds
                                      (default: 30)
        exception_types(tuple): tuple of exception types to catch and retry on
        email_notification(module): email notification module for alerts
    returns:
        result of func() if successful
    raises:
        Exception: if all retries are exhausted
    """
    # Import thermostat_common to access connection_ok flag
    # note this import will cause circular import issue of put at top of file.
    try:
        from src import thermostat_common as tc  # noqa: E402, C0415
    except ImportError:
        tc = None

    # Default exception types if not provided
    if exception_types is None:
        exception_types = _get_default_exception_types()

    initial_trial_number, trial_number, retry_delay_sec = _initialize_retry_parameters(
        initial_retry_delay_sec
    )
    return_val = None

    while trial_number <= number_of_retries:
        time_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Log trial start for debugging
        # (using dual stream for reduced console verbosity)
        if trial_number == 1:
            log_msg(
                f"execute_with_extended_retries: starting {thermostat_type} "
                f"operation for zone {zone_name}",
                mode=DUAL_STREAM_LOG,
                func_name=1,
            )

        log_msg(
            f"execute_with_extended_retries: trial {trial_number} of "
            f"{number_of_retries} at {time_now}",
            mode=DUAL_STREAM_LOG,
            func_name=1,
        )

        try:
            return_val = func()
        except exception_types as ex:
            _handle_retry_exception(
                tc,
                ex,
                trial_number,
                number_of_retries,
                retry_delay_sec,
                time_now,
                email_notification,
                thermostat_type,
                zone_name,
            )

            # Delay between retries
            _handle_retry_delay(trial_number, number_of_retries, retry_delay_sec)

            # Increment retry parameters
            trial_number += 1
            retry_delay_sec += 30  # Linear backoff: add 30 seconds each time

        except Exception as ex:
            log_msg(traceback.format_exc(), mode=DUAL_STREAM_LOG, func_name=1)
            log_msg(
                f"ERROR: unhandled exception {ex} during {get_function_name()}",
                mode=DUAL_STREAM_LOG,
                func_name=1,
            )
            raise ex
        else:  # Good response
            _handle_successful_retry(
                tc,
                trial_number,
                initial_trial_number,
                email_notification,
                thermostat_type,
                zone_name,
                number_of_retries,
                time_now,
            )
            break  # Exit while loop on success

    return return_val
