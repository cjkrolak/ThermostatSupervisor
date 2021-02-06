"""
connection to Honeywell thermoststat using pyhtcc

https://pypi.org/project/pyhtcc/

"""
import datetime
import operator
import os
import pprint
import pyhtcc
import time

import email_notification

# from pyhtcc import PyHTCC
# from pyhtcc import Zone
# globals
OFF_MODE = "OFF_MODE"
HEAT_MODE = "HEAT_MODE"
COOL_MODE = "COOL_MODE"
system_switch_position = {
    COOL_MODE: 0,  # assumed, need to verify
    HEAT_MODE: 1,
    OFF_MODE: 2,
    }


class PyHTCC(pyhtcc.PyHTCC):
    """Extend the PyHTCC class with additional methods."""
    def get_zone_device_ids(self) -> list:
        """
        Returns a list of DeviceIDs corresponding with each one corresponding
        to a particular zone.
        """
        zone_id_lst = []
        for _, zone in enumerate(self.get_zones_info()):
            zone_id_lst.append(zone['DeviceID'])
        return zone_id_lst


class Zone(pyhtcc.Zone):
    """Extend the Zone class with additional methods to get and set
       uiData parameters."""

    def get_display_temp(self) -> int:
        """Refresh the cached zone information then return DispTemperature"""
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']['DispTemperature'])

    def get_heat_mode(self) -> int:
        """Refresh the cached zone information and return the heat setpoint"""
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']['StatusHeat'])

    def get_cool_mode(self) -> int:
        """Refresh the cached zone information and return the heat setpoint"""
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']['StatusCool'])

    def get_schedule_heat_sp(self) -> int:
        """Refresh the cached zone information and return the heat setpoint."""
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']['ScheduleHeatSp'])

    def get_schedule_cool_sp(self) -> int:
        """Refresh the cached zone information and return the heat setpoint."""
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']['ScheduleCoolSp'])

    def get_is_invacation_hold_mode(self) -> bool:
        """Refresh the cached zone information and return the
          'IsInVacationHoldMode' setting."""
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']
                   ['IsInVacationHoldMode'])

    def get_vacation_hold(self) -> bool:
        """ refreshes the cached zone information and return the
            VacationHold setting """
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']['VacationHold'])

    def get_vacation_hold_until_time(self) -> int:
        """ refreshes the cached zone information and return
            the 'VacationHoldUntilTime' """
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']
                   ['VacationHoldUntilTime'])

    def get_temporary_hold_until_time(self) -> int:
        """ refreshes the cached zone information and return the
            'TemporaryHoldUntilTime' """
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']
                   ['TemporaryHoldUntilTime'])

    def get_setpoint_change_allowed(self) -> bool:
        """ refreshes the cached zone information and return the
            'SetpointChangeAllowed' setting
            'SetpointChangeAllowed' will be True in heating mode,
            False in OFF mode (assume True in cooling mode too)
        """
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']
                   ['SetpointChangeAllowed'])

    def get_system_switch_position(self) -> int:
        """ refreshes the cached zone information and return the 'SystemSwitchPosition'
            'SystemSwitchPosition' = 1 for heat, 2 for off
        """
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']
                   ['SystemSwitchPosition'])

    def set_heat_setpoint(self, temp: int) -> None:
        """
        Sets a new heat setpoint.
        This will also attempt to turn the thermostat to 'Heat'
        """
        # logger.info(f"setting heat on with a target temp of: {temp}")
        return self.submit_control_changes({
            'HeatSetpoint': temp,
            'StatusHeat': 0,  # follow schedule
            'StatusCool': 0,  # follow schedule
            'SystemSwitch': 1,
        })

    def set_cool_setpoint(self, temp: int) -> None:
        """
        Sets a new cool setpoint.
        This will also attempt to turn the thermostat to 'Cool'
        """
        # logger.info(f"setting heat on with a target temp of: {temp}")
        return self.submit_control_changes({
            'CoolSetpoint': temp,
            'StatusHeat': 0,  # follow schedule
            'StatusCool': 0,  # follow schedule
            'SystemSwitch': 1,
        })


def connect(username, password):
    """
    Connect to Honeywell Thermostat
    inputs:
        username(str): TCC web site username
        password(str): TCC web site password
    returns:

    """
    p = pyhtcc.PyHTCC(username, password)
    return p


def get_all_metadata(p, zone_number=0, debug=False):
    """
    Get all the current thermostat metadata

    inputs:
      p(object): thermostat object from connection
      zone_number(int): zone number, default=0
      debug(bool): enable debug print statements
    returns:
      dict
    """
    return_data = get_metadata(p, zone_number, parameter=None)
    if debug:
        print("all meta data: %s" % return_data)
    return return_data


def get_metadata(p, zone_number=0, parameter=None, debug=False):
    """
    Get the current thermostat metadata settings

    inputs:
      p(object): thermostat object from connection
      zone_number(int): zone number, default=0
      parameter(str): target parameter, None = all settings
      debug(bool): enable debug print statements
    returns:
      dict if parameter=None
      str if parameter != None
    """
    zone_info_list = p.get_zones_info()
    # print("zone info: %s" % zone_info_list)
    if parameter is None:
        return_data = zone_info_list[zone_number]
        if debug:
            print("zone%s info: %s" % (zone_number, return_data))
        return return_data
    else:
        return_data = zone_info_list[zone_number].get(parameter)
        if debug:
            print("zone%s parameter '%s': %s" % (zone_number, parameter,
                                                 return_data))
        return return_data


def get_latestdata(p, zone_number=0, debug=False):
    """
    Get the current thermostat latest data

    inputs:
      p(object): thermostat object from connection
      zone_number(int): zone number, default=0
      debug(bool): enable debug print statements
    returns:
      dict if parameter=None
      str if parameter != None
    """
    latest_data_dict = get_metadata(p, zone_number).get('latestData')
    if debug:
        print("zone%s latestData: %s" % (zone_number, latest_data_dict))
    return latest_data_dict


def get_uiData(p, zone_number=0, debug=False):
    """
    Get the latest thermostat ui data

    inputs:
      p(object): thermostat object from connection
      zone_number(int): zone_number, default=0
      debug(bool): enable debug print statements
    returns:
      dict
    """
    ui_data_dict = get_latestdata(p, zone_number, debug).get('uiData')
    if debug:
        print("zone%s latestData: %s" % (zone_number, ui_data_dict))
    return ui_data_dict


def get_uiData_param(p, zone_number=0, parameter=None, debug=False):
    """
    Get the latest thermostat ui data for one specific parameter

    inputs:
      p(object): thermostat object from connection
      zone_number(int): zone_number, default=0
      parameter(str): paramenter name
      debug(bool): enable debug print statements
    returns:
      dict
    """
    parameter_data = get_uiData(p, zone_number=0, debug=False).get(parameter)
    if debug:
        print("zone%s uiData parameter %s: %s" % (zone_number, parameter,
                                                  parameter_data))
    return parameter_data


def report_heating_parameters(zone):
    """
    Display critical thermostat settings and reading to the screen.
    """
    # current temp as measured by thermostat
    print("display temp=%s" % zone.get_display_temp())

    # heating status
    if zone.get_system_switch_position() == system_switch_position[HEAT_MODE]:
        print("heat mode=%s" % zone.get_heat_mode())
        print("heat setpoint=%s" % zone.get_heat_setpoint())
        # print("heat setpoint raw=%s" % zone.get_heat_setpoint_raw())
        print("schedule heat sp=%s" % zone.get_schedule_heat_sp())
        print("\n")

    # cooling status
    if zone.get_system_switch_position() == system_switch_position[COOL_MODE]:
        print("cool mode=%s" % zone.get_cool_mode())
        print("cool setpoint=%s" % zone.get_cool_setpoint())
        # print("cool setpoint raw=%s" % zone.get_cool_setpoint_raw())
        print("schedule cool sp=%s" % zone.get_schedule_cool_sp())
        print("\n")

    # hold settings
    print("is in vacation hold mode=%s" % zone.get_is_invacation_hold_mode())
    print("vacation hold=%s" % zone.get_vacation_hold())
    print("vacation hold until time=%s" % zone.get_vacation_hold_until_time())
    print("temporary hold until time=%s" %
          zone.get_temporary_hold_until_time())


def get_current_mode(zone, poll_count, print_status=True,
                     flag_all_deviations=False):
    """
    Determine whether thermostat is following schedule or if it has been
    deviated from schedule.

    inputs:
        zone(obj):  TCC Zone object
        poll_count(int): poll number for reporting
        print_status(bool):  True to print status line
        flag_all_deviations(bool):  True: flag all deviations
                                    False(default): only flag energy consuming
                                                    deviations,
                                                    e.g. heat setpoint above
                                                    schedule, cool setpoint
                                                    below schedule
    returns:
        dictionary of heat/cool mode status, deviation status, and hold status
    """
    # initialize variables
    cool_deviation = False  # cooling set point deviates from schedule
    heat_deviation = False  # heating set point deviates from schedule
    hold_mode = False  # True if not following schedule
    heat_schedule_point = -1  # heating schedule set point
    heat_set_point = -1  # heating current set point
    cool_schedule_point = -1  # cooling schedule set point
    cool_set_point = -1  # cooling current set point
    mode = "OFF MODE"  # mode for display, "OFF MODE", "HEAT MODE", "COOL MODE"
    hold_temporary = False  # True if hold will revert on next schedule event

    if flag_all_deviations:
        cool_operator = operator.ne
        heat_operator = operator.ne
    else:
        cool_operator = operator.lt
        heat_operator = operator.gt

    return_buffer = {
        "heat_mode": False,  # in heating mode
        "cool_mode": False,  # in cooling mode
        "heat_deviation": False,  # True if heat is deviated above schedule
        "cool_deviation": False,  # True if cool is deviated below schedule
        "hold_mode": False,  # True if hold is enabled
        "status_msg": "",  # status message
        }

    # current temperature
    display_temp = zone.get_display_temp()

    # check for heat deviation
    heat_mode = (zone.get_system_switch_position() ==
                 system_switch_position[HEAT_MODE])
    if heat_mode:
        mode = "HEAT MODE"
        heat_set_point = zone.get_heat_setpoint_raw()
        heat_schedule_point = zone.get_schedule_heat_sp()
        if heat_operator(heat_set_point, heat_schedule_point):
            status_msg = ("[heat deviation] actual=%s, set point=%s,"
                          " override=%s" %
                          (display_temp, heat_schedule_point, heat_set_point))
            heat_deviation = True

    # check for cool deviation
    cool_mode = (zone.get_system_switch_position() ==
                 system_switch_position[COOL_MODE])
    if cool_mode:
        mode = "COOL MODE"
        cool_set_point = zone.get_cool_setpoint_raw()
        cool_schedule_point = zone.get_schedule_cool_sp()
        if cool_operator(cool_set_point, cool_schedule_point):
            status_msg = ("[cool deviation] actual=%s, set point=%s,"
                          " override=%s" %
                          (display_temp, cool_schedule_point, cool_set_point))
            cool_deviation = True

    # hold cooling
    if heat_deviation or cool_deviation and zone.get_is_invacation_hold_mode():
        hold_mode = True  # True = not following schedule
        hold_temporary = zone.get_temporary_hold_until_time() > 0
        status_msg += (" (%s)" % ["persistent", "temporary"][hold_temporary])
    else:
        status_msg = ("[following schedule] actual=%s, set point=%s,"
                      " override=%s" %
                      (display_temp, heat_schedule_point, heat_set_point))

    full_status_msg = ("%s: (poll=%s) %s %s" % (datetime.datetime.now().
                                                strftime("%Y-%m-%d %H:%M:%S"),
                                                poll_count, mode, status_msg))
    if print_status:
        print(full_status_msg)

    # return status
    return_buffer["heat_mode"] = heat_mode
    return_buffer["cool_mode"] = cool_mode
    return_buffer["heat_deviation"] = heat_deviation
    return_buffer["cool_deviation"] = cool_deviation
    return_buffer["hold_mode"] = hold_mode
    return_buffer["status_msg"] = full_status_msg
    return return_buffer


def main():
    print("Honeywell TCC thermostat monitoring service\n")

    # session variables
    print("session settings:")
    debug = False  # verbose debugging information

    # poll time setting:
    # min practical value is 2 minutes based on empirical test
    # max value is 3, higher settings will cause HTTP errors, why?
    poll_time_sec = 3 * 60
    print("polling time set to %.1f minutes" % (poll_time_sec / 60.0))

    # reconnection time to TCC server:
    connection_time_sec = 8 * 60 * 60
    print("server re-connect time set to %.1f minutes" %
          (connection_time_sec / 60.0))

    # mode parameters
    revert_thermostat_deviation = True  # revert thermostat if temp deviated
    revert_all_deviations = False  # True will flag all deviations,
    # False will only revert energy consuming deviations
    print("thermostat %s for %s\n" % (["is being monitored",
                                       "will be reverted"]
                                      [revert_thermostat_deviation],
                                      ["energy consuming deviations\n("
                                       "e.g. heat setpoint above schedule "
                                       "setpoint, cool setpoint below schedule"
                                       " setpoint)",
                                       "all schedule deviations"]
                                      [revert_all_deviations]))

    # starting parameters
    previous_mode = {}

    # connection timer loop
    connection_count = 1
    while True:
        # make connection to thermostat through myTotalConnect Comfort site
        username = os.environ['TCC_USERNAME']
        password = os.environ['TCC_PASSWORD']
        print("connecting to TCC (session=%s)..." % connection_count)
        p = PyHTCC(username, password)  # connect
        t0 = time.time()  # connection timer

        # dump all meta data
        if debug:
            get_all_metadata(p, debug=True)

        # dump uiData in a readable format
        if debug:
            return_data = get_latestdata(p, debug=True)
            pp = pprint.PrettyPrinter(indent=4)
            pp.pprint(return_data)

        # get Zone object based on deviceID
        device_id = p.get_zone_device_ids()[0]
        zone = Zone(device_id, p)

        poll_count = 1
        # poll thermostat settings
        while True:
            # query TCC for current thermostat settings and set points
            current_mode = get_current_mode(
                zone, poll_count, flag_all_deviations=revert_all_deviations)

            # debug data on change from previous poll
            if current_mode != previous_mode:
                if debug:
                    report_heating_parameters(zone)
                previous_mode = current_mode  # latch

            # revert thermostat to schedule if heat override is detected
            if (revert_thermostat_deviation and current_mode["heat_mode"] and
                    current_mode["heat_deviation"]):
                email_notification.send_email_alert(
                    subject="heat deviation alert",
                    body=current_mode["status_msg"], debug=True)
                print("\n*** heat deviation detected, reverting thermostat to"
                      " heat schedule ***\n")
                zone.set_heat_setpoint(zone.get_schedule_heat_sp())

            # revert thermostat to schedule if cool override is detected
            if (revert_thermostat_deviation and current_mode["cool_mode"] and
                    current_mode["cool_deviation"]):
                email_notification.send_email_alert(
                    subject="cool deviation alert",
                    body=current_mode["status_msg"], debug=True)
                print("\n*** cool deviation detected, reverting thermostat to "
                      "cool schedule ***\n")
                zone.set_heat_setpoint(zone.get_schedule_cool_sp())

            # polling delay
            time.sleep(poll_time_sec)

            # refresh zone info
            zone.refresh_zone_info()

            # reconnect
            if (time.time() - t0) > connection_time_sec:
                print("forcing re-connection to server...")
                del p
                break  # force reconnection

            # increment poll count
            poll_count += 1

        # increment connection count
        connection_count += 1


if __name__ == "__main__":
    main()
