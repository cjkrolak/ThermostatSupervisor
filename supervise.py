"""
Thermostat Supervisor
"""
# built ins
import time

# local imports
import email_notification
import thermostat_api as api
import utilities as util


def main(thermostat_type, zone_str):
    """
    Thermostat Supervisor Routine.

    inputs:
        thermostat_type(str): thermostat type, see thermostat_api for list
                              of supported thermostats.
        zone_str(str):        zone number input from user
    returns:
        None
    """
    # set log file name
    util.log_msg.file_name = (thermostat_type + "_" +
                              str(zone_str) + ".txt")

    util.log_msg("%s thermostat zone %s monitoring service\n" %
                 (thermostat_type, zone_str), mode=util.BOTH_LOG)

    # verify env variables are present
    api.verify_required_env_variables(thermostat_type, zone_str)

    # session variables
    util.log_msg("session settings:", mode=util.BOTH_LOG)
    debug = False  # verbose debugging information

    # mode parameters
    revert_thermostat_deviation = True  # revert thermostat if temp deviated
    revert_all_deviations = False  # True will flag all deviations,
    # False will only revert energy consuming deviations
    util.log_msg("thermostat %s for %s\n" %
                 (["is being monitored", "will be reverted"]
                  [revert_thermostat_deviation],
                  ["energy consuming deviations\n("
                   "e.g. heat setpoint above schedule "
                   "setpoint, cool setpoint below schedule"
                   " setpoint)",
                   "all schedule deviations"]
                  [revert_all_deviations]), mode=util.BOTH_LOG)

    # starting parameters
    previous_mode = {}

    # connection timer loop
    session_count = 1
    while True:
        # make connection to thermostat
        mod = api.load_hardware_library(thermostat_type)
        zone_num = api.user_inputs["zone"]

        util.log_msg("connecting to thermostat zone %s (session:%s)..." %
                     (zone_num, session_count), mode=util.BOTH_LOG)
        Thermostat = mod.ThermostatClass(zone_num)
        print("DEBUG: thermostat constructor complete")

        t0 = time.time()  # connection timer

        # dump all meta data
        if debug:
            print("thermostat meta data:")
            Thermostat.print_all_thermostat_metadata()

        # get Zone object based on deviceID
        Zone = mod.ThermostatZone(Thermostat)

        # update runtime overrides
        Zone.update_runtime_parameters(api.user_inputs)

        # poll time setting:
        util.log_msg("polling time set to %.1f minutes" %
                     (Zone.poll_time_sec / 60.0), mode=util.BOTH_LOG)

        # reconnection time to thermostat server:
        util.log_msg("server re-connect time set to %.1f minutes" %
                     (Zone.connection_time_sec / 60.0),
                     mode=util.BOTH_LOG)

        # tolerance to set point:
        util.log_msg("tolerance to set point is set to %d degrees" %
                     (Zone.tolerance_degrees),
                     mode=util.BOTH_LOG)

        poll_count = 1
        # poll thermostat settings
        while True:
            # query thermostat for current settings and set points
            current_mode = Zone.get_current_mode(
                session_count, poll_count,
                flag_all_deviations=revert_all_deviations)

            # debug data on change from previous poll
            if current_mode != previous_mode:
                if debug:
                    Zone.report_heating_parameters()
                previous_mode = current_mode  # latch

            # revert thermostat mode if not matching target
            if not Zone.verify_current_mode(api.user_inputs["target_mode"]):
                api.user_inputs["target_mode"] = \
                    Zone.revert_thermostat_mode(api.user_inputs["target_mode"])

            # revert thermostat to schedule if heat override is detected
            if (revert_thermostat_deviation and current_mode["heat_mode"] and
                    current_mode["heat_deviation"]):
                email_notification.send_email_alert(
                    subject=("%s heat deviation alert on zone %s" %
                             (thermostat_type, zone_num)),
                    body=current_mode["status_msg"])
                util.log_msg("\n*** %s heat deviation detected on zone %s,"
                             " reverting thermostat to heat schedule ***\n" %
                             (thermostat_type, zone_num),
                             mode=util.BOTH_LOG)
                Zone.set_heat_setpoint(Zone.get_schedule_heat_sp())

            # revert thermostat to schedule if cool override is detected
            if (revert_thermostat_deviation and current_mode["cool_mode"] and
                    current_mode["cool_deviation"]):
                email_notification.send_email_alert(
                    subject=("%s cool deviation alert on zone %s" %
                             (thermostat_type, zone_num)),
                    body=current_mode["status_msg"])
                util.log_msg("\n*** %s cool deviation detected on zone %s,"
                             " reverting thermostat to cool schedule ***\n" %
                             (thermostat_type, zone_num),
                             mode=util.BOTH_LOG)
                Zone.set_cool_setpoint(Zone.get_schedule_cool_sp())

            # polling delay
            time.sleep(Zone.poll_time_sec)

            # refresh zone info
            # print("DEBUG: %s: refreshing zone..." % util.get_function_name())
            Zone.refresh_zone_info()

            # reconnect
            if (time.time() - t0) > Zone.connection_time_sec:
                util.log_msg("forcing re-connection to thermostat...",
                             mode=util.BOTH_LOG)
                del Thermostat
                break  # force reconnection

            # increment poll count
            poll_count += 1

        # increment connection count
        session_count += 1


if __name__ == "__main__":

    util.log_msg.debug = True  # debug mode set

    # parse all runtime parameters
    user_inputs = api.parse_all_runtime_parameters()
    tstat_type = user_inputs[0]
    zone_input = user_inputs[1]

    # main supervise function
    main(tstat_type, zone_input)
