"""Common utilitity functions and globals."""

# built-in libraries
import argparse
import datetime
import importlib.util
import inspect
import os
import platform
import socket
import sys
import traceback

# third party libraries
import psutil

# thermostat config files
from thermostatsupervisor import honeywell_config
from thermostatsupervisor import kumocloud_config
from thermostatsupervisor import kumolocal_config
from thermostatsupervisor import mmm_config
from thermostatsupervisor import sht31_config
from _ast import mod

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
MIN_PYTHON_MAJOR_VERSION = 3  # minimum python major version required
MIN_PYTHON_MINOR_VERSION = 7  # minimum python minor version required

# all environment variables required by code should be registered here
env_variables = {
    "GMAIL_USERNAME": None,
    "GMAIL_PASSWORD": None,
}
env_variables.update(honeywell_config.env_variables)
env_variables.update(kumocloud_config.env_variables)
env_variables.update(kumolocal_config.env_variables)
env_variables.update(mmm_config.env_variables)
env_variables.update(sht31_config.env_variables)


def get_local_ip():
    """Get local IP address for this PC."""
    socket_obj = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        socket_obj.connect(('10.255.255.255', 1))
        ip_address = socket_obj.getsockname()[0]
    except Exception:
        log_msg(traceback.format_exc(),
                mode=BOTH_LOG, func_name=1)
        ip_address = '127.0.0.1'
    finally:
        socket_obj.close()
    return ip_address


# set unit test IP address, same as client
unit_test_mode = False  # in unit test mode
unit_test_ip_address = get_local_ip()


def get_env_variable(env_key):
    """
    Get environment variable.

    Results will be logged but passwords will be masked off.

    inputs:
       env_key(str): env variable of interest
       debug(bool): verbose debugging
    returns:
       (dict): {status, value, key}
    """
    # defaults
    return_buffer = {
        "status": NO_ERROR,
        "value": None,
        "key": env_key,
    }

    try:
        # unit test key is not required to be in env var list
        if env_key == sht31_config.UNIT_TEST_ENV_KEY:
            return_buffer["value"] = unit_test_ip_address
        else:
            return_buffer["value"] = os.environ[env_key]

        # mask off any password keys
        if "PASSWORD" in return_buffer["key"]:
            value_shown = "(hidden)"
        else:
            value_shown = return_buffer["value"]

        log_msg(f"{env_key}={value_shown}",
                mode=DEBUG_LOG)
    except KeyError:
        log_msg(f"FATAL ERROR: required environment variable '{env_key}'"
                " is missing.", mode=CONSOLE_LOG + DATA_LOG)
        return_buffer["status"] = ENVIRONMENT_ERROR
    return return_buffer


def load_all_env_variables():
    """
    Load all environment variables into a dictionary.

    inputs:
        None
    returns:
        None, populates env_variables dict.
    """
    for key in env_variables:
        log_msg(f"checking key: {key}",
                mode=BOTH_LOG, func_name=1)
        env_variables[key] = get_env_variable(key)["value"]


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


def is_interactive_environment():
    """Return True if script is run through IDE."""
    parent = psutil.Process(os.getpid()).parent().name()
    if parent == "cmd.exe":
        return False
    elif parent == "bash":
        return False
    elif parent == "eclipse.exe":
        return True
    else:
        print(f"DEBUG: parent process={parent}")
        raise OSError(f"unrecognized environment: {parent}")


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
        formatted = "%d" % (raw)
    else:
        formatted = "%.*f" % (precision, raw)
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
        formatted = "%d" % (raw)
    else:
        formatted = "%.*f" % (precision, raw)
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


def is_host_on_local_net(host_name, ip_address=None):
    """
    Return True if specified host is on local network.

    socket.gethostbyaddr() throws exception for some IP address
    so preferred way to use this function is to pass in only the
    hostname and leave the IP as default (None).

    inputs:
        host_name(str): expected host name.
        ip_address(str): target IP address on local net.
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
            print(f"host {host_name} found at {host_found}")
            return True, host_found
        else:
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


def is_azure_environment():
    """
    Return True if machine is Azure pipeline.

    Function assumes '192.' IP addresses are not Azure,
    everything else is Azure.
    """
    return '192.' not in get_local_ip()


def get_python_version(min_major_version=MIN_PYTHON_MAJOR_VERSION,
                       min_minor_version=MIN_PYTHON_MINOR_VERSION,
                       display_version=True):
    """
    Print current Python version to the screen.

    inputs:
        min_major_version(int): min allowed major version
        min_minor_version(int): min allowed minor version
        display_version(bool): True to print to screen.
    return:
        (tuple): (major version, minor version)
    """
    major_version = sys.version_info.major
    minor_version = sys.version_info.minor

    # display version
    if display_version:
        print(f"running on Python version {major_version}.{minor_version}")

    # check major version
    major_version_fail = False
    if min_major_version is not None:
        if not isinstance(min_major_version, (int, float)):
            raise TypeError(f"input parameter 'min_major_version is type "
                            f"({type(min_major_version)}), not int or float")
        if major_version < min_major_version:
            major_version_fail = True

    # check major version
    minor_version_fail = False
    if min_minor_version is not None:
        if not isinstance(min_minor_version, (int, float)):
            raise TypeError(f"input parameter 'min_minor_version is type "
                            f"({type(min_minor_version)}), not int or float")
        if minor_version < min_minor_version:
            minor_version_fail = True

    if major_version_fail or minor_version_fail:
        raise OSError(
            f"current python major version ({major_version}.{minor_version}) "
            f"is less than min python version required "
            f"({min_major_version}.{min_minor_version})")

    return (major_version, minor_version)


def dynamic_module_import(name, path=None):
    """
    Find and load python module.

    TODO: this module results in a resourcewarning within unittest:
    sys:1: ResourceWarning: unclosed <socket.socket fd=628,
    family=AddressFamily.AF_INET, type=SocketKind.SOCK_DGRAM, proto=0,
    laddr=('0.0.0.0', 64963)>

    inputs:
        name(str): module name
        path(str): file path (either relative or abs path),
                   if path is None then will import from installed packages
    returns:
        mod(module): module object
    """
    try:
        if path:
            # local file import from relative or abs path
            print(f"DEBUG attempting local import from {os.getcwd()}...")
            print(f"target dir contents={os.listdir(path)}")
            sys.path.insert(1, path)
            mod = importlib.import_module(name)
            if mod is None:
                raise ModuleNotFoundError(f"module '{name}' could not "
                                          f"be found at {path}")
        else:
            # installed package import
            spec = importlib.util.find_spec(name, path)
            if spec is None:
                raise ModuleNotFoundError(f"module '{name}' could "
                                          "not be found")
            mod = spec.loader.load_module()
    except Exception as ex:
        log_msg(traceback.format_exc(),
                mode=BOTH_LOG, func_name=1)
        log_msg("module load failed: " + name,
                mode=BOTH_LOG, func_name=1)
        raise ex
    else:
        return mod


def parse_runtime_parameters(argv_list=None, argv_dict=None):
    """
    Parse all runtime parameters from list, argv list or named
    arguments.

    If argv_list is input then algo will default to input list.
    ElIf hyphen is found in argv the algo will default to named args.
    inputs:
       argv_list: list override for sys.argv
       argv_dict(dict): dictionary of runtime args with these elements:
        <key>: {  # key = argument name
            "order": 0,  # order in the argv list
            "value": None,   # initialized to None
            "type": str,  # datatype
            "default": "supervise.py",  # default value
            "sflag": "-s",  # short flag identifier
            "lflag": "--script",  # long flag identifier
            "help": "script name"},  # help text
            "valid": None,  # valid choices
    returns:
      argv_dict(dict)
    """
    print("DEBUG: sys.argv=%s" % sys.argv)
    if not argv_dict:
        raise ValueError("argv_dict cannot be None")
    valid_sflags = [argv_dict[k]["sflag"] for k in argv_dict]
    if argv_list:
        # argument list input
        print("parsing arguments from input list")
        argv_dict = parse_argv_list(argv_list, argv_dict)
    elif (flag in sys.argv for flag in valid_sflags):
        # named arguments from sys.argv
        print("parsing named arguments from sys.argv")
        argv_dict = parse_named_arguments(argv_dict=argv_dict)
    else:
        # sys.argv parsing
        print("parsing arguments from sys.argv")
        argv_dict = parse_argv_list(sys.argv, argv_dict)

    argv_dict = validate_argv_inputs(argv_dict)

    return argv_dict


def parse_named_arguments(argv_list=None, argv_dict=None, description=None):
    """
    Parse all possible named arguments.

    inputs:
        argv_list(list): override sys.argv (for testing)
        argv_dict(dict): dictionary of runtime args with these elements:
        <key>: {  # key = argument name
            "order": 0,  # order in the argv list
            "value": None,   # initialized to None
            "type": str,  # datatype
            "default": "supervise.py",  # default value
            "sflag": "-s",  # short flag identifier
            "lflag": "--script",  # long flag identifier
            "help": "script name"},  # help text
            "valid": None,  # valid choices
        description(str): description for help screen.
    returns:
        (dict) of all runtime parameters.
    """
    # setup parser
    parser = argparse.ArgumentParser(description=description)

    # load parser contents
    print("DEBUG: argv_dict=%s" % argv_dict)
    for _, attr in argv_dict.items():
        print("DEBUG: attr=%s" % attr)
        parser.add_argument(attr["lflag"], attr["sflag"], help=attr["help"],
                            type=attr["type"], default=attr["default"])

    # parse the argument list
    if argv_list is not None:
        # test mode, override sys.argv
        args = parser.parse_args(argv_list[1:])
    else:
        print("DEBUG: sys.argv=%s" % sys.argv)
        args = parser.parse_args()
    print("DEBUG: args=%s" % args)
    for key in argv_dict:
        if key == "script":
            # add script name
            argv_dict[key]["value"] = sys.argv[0]
        else:
            print("DEBUG: args[%s]=%s" % (key, getattr(args, key, None)))
            argv_dict[key]["value"] = getattr(args, key, None)
            if isinstance(argv_dict[key]["value"], str):
                # str parsing has leading spaces for some reason
                argv_dict[key]["value"] = argv_dict[key]["value"].strip()

    return argv_dict


def parse_argv_list(argv_list=None, argv_dict=None):
    """
    Parse un-named arguments from list.

    inputs:
        argv_list(list): list of runtime arguments in the order
        specified in argv_dict "order" fields.
    returns:
        (dict) of all runtime parameters.
    """
    # if argv list is set use that, else use sys.argv
    if argv_list:
        log_msg(
            f"parse_all_runtime_parameters from user input list: {argv_list}",
            mode=DEBUG_LOG +
            CONSOLE_LOG,
            func_name=1)
        argv_inputs = argv_list
    else:
        log_msg(
            f"parse_all_runtime_parameters from sys.argv: {sys.argv}",
            mode=DEBUG_LOG +
            CONSOLE_LOG,
            func_name=1)
        argv_inputs = sys.argv

    print("DEBUG: argv_dict is type(%s): %s" % (type(argv_dict), argv_dict))
    # populate dict with values from list
    for k, v in argv_dict.items():
        if v["order"] <= len(argv_inputs) - 1:
            argv_dict[k]["value"] = argv_dict[k]["type"](
                argv_inputs[v["order"]])

    return argv_dict


def validate_argv_inputs(argv_dict):
    """
    Validate argv inputs and update reset to defaults if necessary.

    inputs:
        argv_dict(dict): dictionary of runtime args with these elements:
        <key>: {  # key = argument name
            "order": 0,  # order in the argv list
            "value": None,   # initialized to None
            "type": str,  # datatype
            "default": "supervise.py",  # default value
            "sflag": "-s",  # short flag identifier
            "lflag": "--script",  # long flag identifier
            "help": "script name"},  # help text
            "valid": None,  # valid choices
    returns:
        (dict) of all runtime parameters.
    """
    for key, attr in argv_dict.items():
        proposed_value = attr["value"]
        default_value = attr["default"]
        proposed_type = type(proposed_value)
        expected_type = attr["type"]
        # missing value check
        if proposed_value is None:
            log_msg(
                f"key='{key}': argv parameter missing, using default value "
                f"'{default_value}'",
                mode=DEBUG_LOG +
                CONSOLE_LOG,
                func_name=1)
            attr["value"] = attr["default"]

        # wrong datatype check
        elif proposed_type != expected_type:
            log_msg(
                f"key='{key}': datatype error, expected={expected_type}, "
                f"actual={proposed_type}, using default value "
                f"'{default_value}'",
                mode=DEBUG_LOG +
                CONSOLE_LOG,
                func_name=1)
            attr["value"] = attr["default"]

        # out of range check
        elif (attr["valid_range"] is not None and
              proposed_value not in attr["valid_range"]):
            log_msg(
                f"WARNING: '{proposed_value}' is not a valid choice for "
                f"'{key}', using default({default_value})",
                mode=BOTH_LOG,
                func_name=1)
            attr["value"] = attr["default"]

    return argv_dict


