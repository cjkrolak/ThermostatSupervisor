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


def main(thermostat_type, zone):
    """
    Thermostat Supervisor Routine.

    inputs:
        thermostat_type(str): thermostat type, see thermostat_api for list
                              of supported thermostats.
        zone(str):      zone number
    returns:
        None
    """
    # set log file name
    util.log_msg.file_name = (thermostat_type + "_" +
                              str(zone) + ".txt")

    util.log_msg("%s thermostat zone %s monitoring service\n" %
                 (thermostat_type, zone), mode=util.BOTH_LOG)
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
        # make connection to thermostat through myTotalConnect Comfort site
        thermostat_constructor = \
            api.thermostats[thermostat_type]["thermostat_constructor"]
        args = api.thermostats[thermostat_type]["args"]
        zone_num = api.thermostats[thermostat_type]["zone"]
        util.log_msg("connecting to thermostat zone %s (session:%s)..." %
                     (zone_num, session_count), mode=util.BOTH_LOG)
        thermostat = thermostat_constructor(*args)

        # grab meta data
        # thermostat.get_all_thermostat_metadata()

        # poll time setting:
        poll_time_sec = api.thermostats[thermostat_type]["poll_time_sec"]
        util.log_msg("polling time set to %.1f minutes" %
                     (poll_time_sec / 60.0), mode=util.BOTH_LOG)

        # reconnection time to TCC server:
        connection_time_sec = \
            api.thermostats[thermostat_type]["connection_time_sec"]
        util.log_msg("server re-connect time set to %.1f minutes" %
                     (connection_time_sec / 60.0),
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
                session_count, poll_count,
                flag_all_deviations=revert_all_deviations)

            # debug data on change from previous poll
            if current_mode != previous_mode:
                if debug:
                    zone.report_heating_parameters()
                previous_mode = current_mode  # latch

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
                zone.set_heat_setpoint(zone.get_schedule_heat_sp())

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
                zone.set_cool_setpoint(zone.get_schedule_cool_sp())

            # polling delay
            time.sleep(poll_time_sec)

            # refresh zone info
            # print("DEBUG: %s: refreshing zone..." % util.get_function_name())
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
        session_count += 1


if __name__ == "__main__":

    util.log_msg.debug = True  # debug mode set

    # parse thermostat type parameter (argv[1] if present):
    tstat_default = api.HONEYWELL  # default thermostat type
    try:
        tstat_type = sys.argv[1].lower()
    except IndexError:
        tstat_type = tstat_default
    if tstat_type not in api.SUPPORTED_THERMOSTATS:
        print("WARNING: '%s' is not a valid choice for thermostat, "
              "using default(%s)" % (tstat_type, tstat_default))
        tstat_type = tstat_default

    # parse zone number parameter (argv[2] if present):
    zone_default = 0
    try:
        zone_input = int(sys.argv[2])
    except (IndexError, ValueError):
        zone_input = zone_default
    if zone_input not in api.SUPPORTED_THERMOSTATS[tstat_type]["zones"]:
        print("WARNING: zone %s is not a valid choice for %s thermostat, "
              "using default(%s)" % (zone_input, tstat_type, zone_default))
        zone_input = zone_default
    api.set_target_zone(tstat_type, zone_input)

    # parse the poll time override (argv[3] if present):
    if len(sys.argv) > 3:
        poll_time_default = -1
        try:
            poll_time_input = int(sys.argv[3])
        except (IndexError, ValueError):
            poll_time_input = poll_time_default
        if poll_time_input <= 0:
            print("WARNING: poll time override of %s seconds is not a valid "
                  "value, using default" % poll_time_input)
        else:
            api.set_poll_time(tstat_type, poll_time_input)

    # parse the connection time override (argv[4] if present):
    if len(sys.argv) > 4:
        connection_time_default = -1
        try:
            connection_time_input = int(sys.argv[4])
        except (IndexError, ValueError):
            connection_time_input = connection_time_default
        if connection_time_input <= 0:
            print("WARNING: connection time override of %s seconds is not "
                  "a valid value, using default" % connection_time_input)
        else:
            api.set_connection_time(tstat_type, connection_time_input)

    # main supervise function
    main(tstat_type, zone_input)
