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


def display_runtime_settings(Zone):
    """
    Display runtime settings to console.

    inputs:
        Zone(obj): thermostat zone object
    returns:
        None
    """
    # poll time setting:
    util.log_msg(
        f"polling time set to {Zone.poll_time_sec / 60.0:.1f} minutes",
        mode=util.BOTH_LOG)

    # reconnection time to thermostat server:
    util.log_msg(
        f"server re-connect time set to {Zone.connection_time_sec / 60.0:.1f}"
        f" minutes",
        mode=util.BOTH_LOG)

    # tolerance to set point:
    util.log_msg(
        f"tolerance to set point is set to "
        f"{util.temp_value_with_units(Zone.tolerance_degrees)}",
        mode=util.BOTH_LOG)


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
    while not api.max_measurement_count_exceeded(measurement):
        # make connection to thermostat
        mod = api.load_hardware_library(thermostat_type)
        zone_num = api.get_user_inputs(api.ZONE_FLD)

        util.log_msg(
            f"connecting to thermostat zone {zone_num} "
            f"(session:{session_count})...",
            mode=util.BOTH_LOG)
        Thermostat = mod.ThermostatClass(zone_num)

        time0 = time.time()  # connection timer

        # dump all meta data
        if debug:
            util.log_msg("thermostat meta data:", mode=util.BOTH_LOG,
                         func_name=1)
            Thermostat.print_all_thermostat_metadata(zone_num)

        # get Zone object based on deviceID
        Zone = mod.ThermostatZone(Thermostat)
        util.log_msg(f"zone name={Zone.zone_name}", mode=util.BOTH_LOG,
                     func_name=1)

        # update runtime overrides
        Zone.update_runtime_parameters(api.user_inputs)

        # display runtime settings
        display_runtime_settings(Zone)

        poll_count = 1
        # poll thermostat settings
        while not api.max_measurement_count_exceeded(measurement):
            # query thermostat for current settings and set points
            current_mode_dict = Zone.get_current_mode(
                session_count, poll_count,
                flag_all_deviations=revert_all_deviations)

            # debug data on change from previous poll
            # note this check is probably hyper-sensitive, since status msg
            # change could trigger this extra report.
            if current_mode_dict != previous_mode_dict:
                if debug:
                    Zone.report_heating_parameters()
                previous_mode_dict = current_mode_dict  # latch

            # revert thermostat mode if not matching target
            print("DEBUG: target_mode=%s" % api.get_user_inputs(
                    api.TARGET_MODE_FLD))
            if not Zone.verify_current_mode(api.get_user_inputs(
                    api.TARGET_MODE_FLD)):
                api.set_user_inputs(api.TARGET_MODE_FLD,
                                    Zone.revert_thermostat_mode(
                                        api.get_user_inputs(
                                            api.TARGET_MODE_FLD)))

            # revert thermostat to schedule if heat override is detected
            if (revert_deviations and Zone.is_controlled_mode() and
                    Zone.is_temp_deviated_from_schedule()):
                Zone.revert_temperature_deviation(
                    Zone.schedule_setpoint, current_mode_dict["status_msg"])

            # polling delay
            time.sleep(Zone.poll_time_sec)

            # refresh zone info
            Zone.refresh_zone_info()

            # reconnect
            if (time.time() - time0) > Zone.connection_time_sec:
                util.log_msg("forcing re-connection to thermostat...",
                             mode=util.BOTH_LOG)
                del Thermostat
                break  # force reconnection

            # increment poll count
            poll_count += 1
            measurement += 1

        # increment connection count
        session_count += 1

    # clean-up and exit
    util.log_msg(
        f"\n{measurement - 1} measurements completed, exiting program\n",
        mode=util.BOTH_LOG)

    # delete packages
    del Zone
    del Thermostat


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

    # parse all runtime parameters
    util.parse_runtime_parameters(argv_dict=api.user_inputs)

    # main supervise function
    supervisor(api.get_user_inputs(api.THERMOSTAT_TYPE_FLD),
               api.get_user_inputs(api.ZONE_FLD))

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
