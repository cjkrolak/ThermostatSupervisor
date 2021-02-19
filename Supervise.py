"""
Thermostat Supervisor
"""
# built ins
import os
import pprint
import sys
import time

# local imports
import email_notification
import Honeywell as h
import utilities as util


def main(thermostat_type):
    """
    Thermostat Supervisor Routine.

    inputs:
        thermostat_type(str): currently support "Honeywell".
    returns:
        None
    """
    # set log file name
    util.log_msg.file_name = thermostat_type + ".txt"

    util.log_msg("%s TCC thermostat monitoring service\n" % thermostat_type,
                 mode=util.BOTH_LOG)

    # session variables
    util.log_msg("session settings:", mode=util.BOTH_LOG)
    debug = False  # verbose debugging information

    # poll time setting:
    # min practical value is 2 minutes based on empirical test
    # max value is 3, higher settings will cause HTTP errors, why?
    poll_time_sec = 3 * 60
    util.log_msg("polling time set to %.1f minutes" %
                 (poll_time_sec / 60.0), mode=util.BOTH_LOG)

    # reconnection time to TCC server:
    connection_time_sec = 8 * 60 * 60
    util.log_msg("server re-connect time set to %.1f minutes" %
                 (connection_time_sec / 60.0), mode=util.BOTH_LOG)

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
        username = os.environ['TCC_USERNAME']
        password = os.environ['TCC_PASSWORD']
        util.log_msg("connecting to thermostat (session=%s)..." %
                     connection_count, mode=util.BOTH_LOG)
        thermostat = h.HoneywellThermostat(username, password)  # connect
        t0 = time.time()  # connection timer

        # dump all meta data
        if debug:
            thermostat.get_all_metadata()

        # dump uiData in a readable format
        if debug:
            return_data = thermostat.get_latestdata()
            pp = pprint.PrettyPrinter(indent=4)
            pp.pprint(return_data)

        # get Zone object based on deviceID
        device_id = thermostat.get_zone_device_ids()[0]
        zone = h.HoneywellZone(device_id, thermostat)

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
                zone.set_heat_setpoint(zone.get_schedule_cool_sp())

            # polling delay
            time.sleep(poll_time_sec)

            # refresh zone info
            zone.refresh_zone_info()

            # reconnect
            if (time.time() - t0) > connection_time_sec:
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
    if len(sys.argv) > 1 and sys.argv[1] in util.SUPPORTED_THERMOSTATS:
        tstat_type = sys.argv[1]
    else:
        # default
        tstat_type = util.HONEYWELL

    main(tstat_type)
