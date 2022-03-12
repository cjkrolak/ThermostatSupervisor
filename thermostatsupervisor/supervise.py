"""
Thermostat Supervisor
"""
# built ins
import sys
import time

# local imports
from thermostatsupervisor import thermostat_api as api
from thermostatsupervisor import utilities as util

argv = []  # runtime parameter override


def display_session_settings(thermostat_type, zone,
                             revert_setting, revert_all_setting):
    """
    Display session settings to console.

    inputs:
        thermostat_type(int): thermostat type
        zone(str or int):  zone
        revert_setting(bool): True to revert deviation
                              False to just monitor
        revert_all_setting(bool): True to revert above and below deviations
                                  False to just revert energy wasting
                                  deviations.
    returns:
        None
    """
    # set log file name
    util.log_msg.file_name = (thermostat_type + "_" +
                              str(zone) + ".txt")

    util.log_msg(
        f"{thermostat_type} thermostat zone {zone} monitoring service\n",
        mode=util.BOTH_LOG)

    util.log_msg("session settings:", mode=util.BOTH_LOG)

    util.log_msg("thermostat %s for %s\n" %
                 (["is being monitored", "will be reverted"]
                  [revert_setting],
                  ["energy consuming deviations\n("
                   "e.g. heat setpoint above schedule "
                   "setpoint, cool setpoint below schedule"
                   " setpoint)",
                   "all schedule deviations"]
                  [revert_all_setting]), mode=util.BOTH_LOG)


def supervisor(thermostat_type, zone_str):
    """
    Monitor specified thermometer and zone for deviations up to max
    measurements.

    inputs:
        thermostat_type(str): thermostat type, see thermostat_api for list
                              of supported thermostats.
        zone_str(str):        zone number input from user
    returns:
        None
    """
    # session variables:
    debug = False  # verbose debugging information

    # Revert deviation or just monitor and alert deviations:
    revert_deviations = True

    # Revert all deviations or just those that waste energy
    revert_all_deviations = False

    # display banner and session settings
    display_session_settings(thermostat_type, zone_str,
                             revert_deviations,
                             revert_all_deviations)

    # verify env variables are present
    api.verify_required_env_variables(thermostat_type, zone_str)

    # starting parameters
    previous_mode_dict = {}

    # connection timer loop
    session_count = 1
    measurement = 1

    while not api.uip.max_measurement_count_exceeded(measurement):
        # make connection to thermostat
        mod = api.load_hardware_library(thermostat_type)
        zone_num = api.uip.get_user_inputs(api.ZONE_FLD)

        util.log_msg(
            f"connecting to thermostat zone {zone_num} "
            f"(session:{session_count})...",
            mode=util.BOTH_LOG)
        Thermostat = mod.ThermostatClass(zone_num)

        # dump all meta data
        if debug:
            util.log_msg("thermostat meta data:", mode=util.BOTH_LOG,
                         func_name=1)
            Thermostat.print_all_thermostat_metadata(zone_num)

        # get Zone object based on deviceID
        Zone = mod.ThermostatZone(Thermostat)
        util.log_msg(f"zone name={Zone.zone_name}", mode=util.BOTH_LOG,
                     func_name=1)

        Zone.session_start_time_sec = time.time()

        # update runtime overrides
        Zone.update_runtime_parameters()

        # display runtime settings
        Zone.display_runtime_settings()

        # supervisor inner loop
        measurement = Zone.supervisor_loop(Thermostat, session_count,
                                           measurement, revert_deviations,
                                           revert_all_deviations, debug)

        # increment connection count
        session_count += 1

    # clean-up and exit
    util.log_msg(
        f"\n{measurement - 1} measurements completed, exiting program\n",
        mode=util.BOTH_LOG)

    # delete packages if necessary
    if 'Zone' in locals():
        del Zone
    if 'Thermostat' in locals():
        del Thermostat
    if 'mod' in locals():
        del mod


def exec_supervise(debug=True, argv_list=None):
    """
    Execute supervisor loop.

    inputs:
        debug(bool): enable debugging mode.
        argv_list(list): argv overrides.
    returns:
        (bool): True if complete.
    """
    util.log_msg.debug = debug  # debug mode set

    # parse all runtime parameters if necessary
    api.uip = api.UserInputs(argv_list)

    # main supervise function
    supervisor(api.uip.get_user_inputs(api.THERMOSTAT_TYPE_FLD),
               api.uip.get_user_inputs(api.ZONE_FLD))

    return True


if __name__ == "__main__":

    # if argv list is set use that, else use sys.argv
    if argv:
        argv_inputs = argv
    else:
        argv_inputs = sys.argv

    # verify environment
    util.get_python_version()

    exec_supervise(debug=True, argv_list=argv_inputs)
