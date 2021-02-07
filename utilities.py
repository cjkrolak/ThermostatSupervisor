"""Common utilitity functions and globals."""

import datetime
import inspect
import os

# error codes
NO_ERROR = 0
CONNECTION_ERROR = 1
AUTHORIZATION_ERROR = 2
EMAIL_SEND_ERROR = 3
ENVIRONMENT_ERROR = 4
FILE_NOT_FOUND_ERROR = 5
OTHER_ERROR = 99

# logging options
CONSOLE_LOG = 0x001  # print to console
DATA_LOG = 0x010  # print to data log
BOTH_LOG = 0x011  # log to both console and data logs
DEBUG_LOG = 0x100  # print only if debug mode is on

file_path = ".\\data\\"
max_log_size_bytes = 1024  # logs rotate at this max size


def get_env_variable(env_key):
    """
    Get environment variable.

    inputs:
       env_key(str): env variable of interest
       debug(bool): verbose debugging
    returns:
       (dict): {status, value}
    """
    # defaults
    return_buffer = {
        "status": NO_ERROR,
        "value": None,
        "key": env_key,
        }

    try:
        return_buffer["value"] = os.environ[env_key]
        log_msg("%s=%s" % (env_key, return_buffer["value"]),
                mode=DEBUG_LOG)
    except KeyError:
        log_msg("FATAL ERROR: required environment variable '%s'"
                " is missing." % env_key, mode=CONSOLE_LOG + DATA_LOG)
        return_buffer["status"] = ENVIRONMENT_ERROR
    return return_buffer


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
        # build full file name
        full_path = get_full_file_path(log_msg.file_name)

        # log rotate
        try:
            file_size_bytes = os.path.getsize(full_path)
        except FileNotFoundError:
            # file does not exist
            file_size_bytes = 0
        if file_size_bytes > max_log_size_bytes:
            # rotate log file
            current_date = datetime.datetime.today().strftime(
                '%d-%b-%Y-%H-%M-%S')
            os.rename(full_path, full_path[:-4] + "-" +
                      str(current_date) + '.txt')
            file_size_bytes = 0

        # write to file
        if file_size_bytes == 0:
            f = open(full_path, "w")  # writing
        else:
            f = open(full_path, "a")  # appending
        f.write(msg + "\n")
        f.close()

    # print to console
    if (mode & CONSOLE_LOG) and not filter_debug_msg:
        print(msg)

    return return_buffer


def get_full_file_path(file_name):
    """
    Return full file path.

    inputs:
        file_name(str): name of file with extension
    returns:
        (str) full file name and path
    """
    return file_path + file_name


def utf8len(s):
    """Return length of string in bytes."""
    return len(s.encode('utf-8'))
