"""Common utilitity functions and globals."""

# built-in libraries
import datetime
import inspect
import os
import platform
import psutil
import socket

# thermostat config files
import honeywell_config
import kumocloud_config
import kumolocal_config
import mmm_config
import sht31_config

# error codes
NO_ERROR = 0
CONNECTION_ERROR = 1
AUTHORIZATION_ERROR = 2
EMAIL_SEND_ERROR = 3
ENVIRONMENT_ERROR = 4
FILE_NOT_FOUND_ERROR = 5
OTHER_ERROR = 99

# bogus values to identify uninitialized data
bogus_int = -13
bogus_bool = False
bogus_str = "<missing value>"
bogus_dict = {}

# logging options
CONSOLE_LOG = 0x001  # print to console
DATA_LOG = 0x010  # print to data log
BOTH_LOG = 0x011  # log to both console and data logs
DEBUG_LOG = 0x100  # print only if debug mode is on

file_path = ".//data"
max_log_size_bytes = 2**20  # logs rotate at this max size

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
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


# set unit test IP address, same as client
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

        log_msg("%s=%s" % (env_key, value_shown),
                mode=DEBUG_LOG)
    except KeyError:
        log_msg("FATAL ERROR: required environment variable '%s'"
                " is missing." % env_key, mode=CONSOLE_LOG + DATA_LOG)
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
        log_msg("checking key: %s" % key,
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
        msg = "[%s]: %s" % (get_function_name(func_name), msg)

    # log to data file
    if (mode & DATA_LOG) and not filter_debug_msg:
        # create directory if needed
        if not os.path.exists(file_path):
            print("data folder '%s' created." % file_path)
            os.makedirs(file_path)

        # build full file name
        full_path = get_full_file_path(log_msg.file_name)

        # check file size and rotate if necessary
        file_size_bytes = get_file_size_bytes(full_path)
        file_size_bytes = log_rotate_file(full_path, file_size_bytes,
                                          max_log_size_bytes)

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
        f = open(full_path, "w")  # writing
    else:
        f = open(full_path, "a")  # appending
    msg_to_write = msg + "\n"
    f.write(msg_to_write)
    f.close()
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
    return file_path + "//" + file_name


def utf8len(s):
    """
    Return length of string in bytes.

    inputs:
        s(str): input string.
    returns:
        (int): length of string in bytes.
    """
    return len(s.encode('utf-8'))


def is_interactive_environment():
    """Return True if script is run through IDE."""
    parent = psutil.Process(os.getpid()).parent().name()
    if parent == "cmd.exe":
        return False
    elif parent == "eclipse.exe":
        return True
    else:
        print("DEBUG: parent process=%s" % parent)
        return True


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
        raise ValueError("%s: '%s' is not a valid temperature unit" %
                         (get_function_name(), disp_unit))

    # if string try to convert to float
    if isinstance(raw, str):
        if '°' in raw:
            return raw  # pass-thru
        try:
            float(raw)
        except ValueError:
            pass

    if raw is None:
        formatted = "%s" % (raw)
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
        raise ValueError("%s: '%s' is not a valid humidity unit" %
                         (get_function_name(), disp_unit))

    # if string try to convert to float
    if isinstance(raw, str):
        if '%' in raw:
            return raw  # pass-thru
        try:
            float(raw)
        except ValueError:
            pass

    if raw is None:
        formatted = "%s" % (raw)
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
    raise KeyError("key not found in dict '%s' with value='%s'" %
                   (input_dict, val))


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
        raise TypeError("raw value '%s' is not an int or float" % tempc)


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
        raise TypeError("raw value '%s' is not an int or float" % tempf)


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
        (bool): True if confirmed on local net, else False.
    """
    host_found = None
    # find by hostname alone if IP is None
    if ip_address is None:
        try:
            host_found = socket.gethostbyname(host_name)
        except socket.gaierror:
            return False
        if host_found:
            print("host %s found at %s" % (host_name, host_found))
            return True
        else:
            return False

    else:
        # match both IP and host if both are provided.
        try:
            host_found = socket.gethostbyaddr(ip_address)
        except socket.herror:  # exception if DNS name is not set
            return False
        if host_name == host_found[0]:
            return True
        else:
            print("DEBUG: expected host=%s, actual host=%s" %
                  (host_name, host_found))
            return False


def is_azure_environment():
    """
    Return True if machine is Azure pipeline.

    Function assumes '192.' IP addresses are not Azure,
    everything else is Azure.
    """
    return '192.' not in get_local_ip()
