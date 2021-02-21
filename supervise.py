"""
Thermostat Supervisor
"""
# built ins
import sys
import time

# local imports
import email_notification
import thermostat_api as api
import utilities as util


def main(thermostat_type):
    """
    Thermostat Supervisor Routine.

    inputs:
        thermostat_type(str): thermostat type, see thermostat_api for list
                              of supported thermostats.
    returns:
        None
    """
    # set log file name
    util.log_msg.file_name = thermostat_type + ".txt"

    util.log_msg("%s thermostat monitoring service\n" % thermostat_type,
                 mode=util.BOTH_LOG)

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
    connection_count = 1
    while True:
        # make connection to thermostat through myTotalConnect Comfort site
        thermostat_constructor = \
            api.thermostats[thermostat_type]["thermostat_constructor"]
        args = api.thermostats[thermostat_type]["args"]
        zone_num = api.thermostats[thermostat_type]["zone"]
        util.log_msg("connecting to thermostat zone %s (session=%s)..." %
                     (zone_num, connection_count), mode=util.BOTH_LOG)
        thermostat = thermostat_constructor(*args)

        # poll time setting:
        util.log_msg("polling time set to %.1f minutes" %
                     (thermostat.poll_time_sec / 60.0), mode=util.BOTH_LOG)

        # reconnection time to TCC server:
        util.log_msg("server re-connect time set to %.1f minutes" %
                     (thermostat.connection_time_sec / 60.0),
                     mode=util.BOTH_LOG)

        t0 = time.time()  # connection timer

        # dump all meta data
        if debug:
            thermostat.get_all_thermostat_metadata()

        # get Zone object based on deviceID
        zone_constructor = api.thermostats[thermostat_type]["zone_constructor"]
        device_id = thermostat.get_target_zone_id()
        zone = zone_constructor(device_id, thermostat)

        poll_count = 1
        # poll thermostat settings
        while True:
            # query TCC for current thermostat settings and set points
            current_mode = zone.get_current_mode(
                poll_count, flag_all_deviations=revert_all_deviations)

            # debug data on change from previous poll
            if current_mode != previous_mode:
                if debug:
                    zone.report_heating_parameters()
                previous_mode = current_mode  # latch

            # revert thermostat to schedule if heat override is detected
            if (revert_thermostat_deviation and current_mode["heat_mode"] and
                    current_mode["heat_deviation"]):
                email_notification.send_email_alert(
                    subject="heat deviation alert",
                    body=current_mode["status_msg"])
                util.log_msg("\n*** heat deviation detected, "
                             "reverting thermostat to"
                             " heat schedule ***\n", mode=util.BOTH_LOG)
                zone.set_heat_setpoint(zone.get_schedule_heat_sp())

            # revert thermostat to schedule if cool override is detected
            if (revert_thermostat_deviation and current_mode["cool_mode"] and
                    current_mode["cool_deviation"]):
                email_notification.send_email_alert(
                    subject="cool deviation alert",
                    body=current_mode["status_msg"])
                util.log_msg("\n*** cool deviation detected, reverting "
                             "thermostat to cool schedule ***\n",
                             mode=util.BOTH_LOG)
                zone.set_cool_setpoint(zone.get_schedule_cool_sp())

            # polling delay
            time.sleep(thermostat.poll_time_sec)

            # refresh zone info
            zone.refresh_zone_info()

            # reconnect
            if (time.time() - t0) > thermostat.connection_time_sec:
                util.log_msg("forcing re-connection to thermostat...",
                             mode=util.BOTH_LOG)
                del thermostat
                break  # force reconnection

            # increment poll count
            poll_count += 1

        # increment connection count
        connection_count += 1


if __name__ == "__main__":

    util.log_msg.debug = True  # debug mode set

    # set thermostat type
    if len(sys.argv) > 1 and sys.argv[1] in api.SUPPORTED_THERMOSTATS:
        tstat_type = sys.argv[1]
    else:
        # default
        tstat_type = api.HONEYWELL
        tstat_type = api.MMM50

    # set the monitoring zone
    api.set_target_zone(1)

    main(tstat_type)