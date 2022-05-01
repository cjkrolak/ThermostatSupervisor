"""
Thermostat Supervisor
"""
# built ins
import sys
import time

# local imports
from thermostatsupervisor import environment as env
from thermostatsupervisor import thermostat_api as api
from thermostatsupervisor import utilities as util

argv = []  # runtime parameter override


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

    # load hardware library
    mod = api.load_hardware_library(thermostat_type)

    # verify env variables are present
    api.verify_required_env_variables(thermostat_type, zone_str)

    # connection timer loop
    session_count = 1
    measurement = 1

    # outer loop: sessions
    while not api.uip.max_measurement_count_exceeded(measurement):
        # make connection to thermostat
        zone_num = api.uip.get_user_inputs(api.uip.zone_name,
                                           api.input_flds.zone)
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

        # display banner and session settings
        Zone.display_session_settings()

        # set start time for poll
        Zone.session_start_time_sec = time.time()

        # update runtime overrides
        Zone.update_runtime_parameters()

        # display runtime settings
        Zone.display_runtime_settings()

        # supervisor inner loop
        measurement = Zone.supervisor_loop(Thermostat, session_count,
                                           measurement, debug)

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
    # TODO - update for multi-zone application
    supervisor(api.uip.get_user_inputs(api.uip.parent_keys[0],
                                       api.input_flds.thermostat_type),
               api.uip.get_user_inputs(api.uip.parent_keys[0],
                                       api.input_flds.zone)
               )

    return True


if __name__ == "__main__":

    # if argv list is set use that, else use sys.argv
    if argv:
        argv_inputs = argv
    else:
        argv_inputs = sys.argv

    # verify environment
    env.get_python_version()

    exec_supervise(debug=True, argv_list=argv_inputs)
