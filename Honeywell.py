"""
connection to Honeywell thermoststat using pyhtcc

https://pypi.org/project/pyhtcc/

"""
# built-in imports
# from contextlib import redirect_stdout
import datetime
import operator
import pyhtcc

# local imports
import utilities as util


class HoneywellThermostat(pyhtcc.PyHTCC):
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

    def get_all_metadata(self, zone_number=0):
        """
        Get all the current thermostat metadata

        inputs:
          p(object): thermostat object from connection
          zone_number(int): zone number, default=0
        returns:
          dict
        """
        return_data = self.get_metadata(zone_number, parameter=None)
        util.log_msg("all meta data: %s" % return_data,
                     mode=util.DEBUG_LOG + util.CONSOLE_LOG, func_name=1)
        return return_data

    def get_metadata(self, zone_number=0, parameter=None):
        """
        Get the current thermostat metadata settings

        inputs:
          p(object): thermostat object from connection
          zone_number(int): zone number, default=0
          parameter(str): target parameter, None = all settings
        returns:
          dict if parameter=None
          str if parameter != None
        """
        zone_info_list = self.get_zones_info()
        # util.log_msg("zone info: %s" % zone_info_list,
        #              mode=util.DEBUG_LOG + util.CONSOLE_LOG, func_name=1)
        if parameter is None:
            return_data = zone_info_list[zone_number]
            util.log_msg("zone%s info: %s" % (zone_number, return_data),
                         mode=util.DEBUG_LOG + util.CONSOLE_LOG, func_name=1)
            return return_data
        else:
            return_data = zone_info_list[zone_number].get(parameter)
            util.log_msg("zone%s parameter '%s': %s" %
                         (zone_number, parameter, return_data),
                         mode=util.DEBUG_LOG + util.CONSOLE_LOG, func_name=1)
            return return_data

    def get_latestdata(self, zone_number=0):
        """
        Get the current thermostat latest data

        inputs:
          p(object): thermostat object from connection
          zone_number(int): zone number, default=0
        returns:
          dict if parameter=None
          str if parameter != None
        """
        latest_data_dict = self.get_metadata(zone_number).get('latestData')
        util.log_msg("zone%s latestData: %s" % (zone_number, latest_data_dict),
                     mode=util.DEBUG_LOG + util.CONSOLE_LOG, func_name=1)
        return latest_data_dict

    def get_uiData(self, zone_number=0):
        """
        Get the latest thermostat ui data

        inputs:
          p(object): thermostat object from connection
          zone_number(int): zone_number, default=0
        returns:
          dict
        """
        ui_data_dict = self.get_latestdata(zone_number).get('uiData')
        util.log_msg("zone%s latestData: %s" % (zone_number, ui_data_dict),
                     mode=util.DEBUG_LOG + util.CONSOLE_LOG, func_name=1)
        return ui_data_dict

    def get_uiData_param(self, zone_number=0, parameter=None):
        """
        Get the latest thermostat ui data for one specific parameter

        inputs:
          p(object): thermostat object from connection
          zone_number(int): zone_number, default=0
          parameter(str): paramenter name
        returns:
          dict
        """
        parameter_data = self.get_uiData(zone_number=0).get(parameter)
        util.log_msg("zone%s uiData parameter %s: %s" %
                     (zone_number, parameter, parameter_data),
                     mode=util.DEBUG_LOG + util.CONSOLE_LOG,
                     func_name=1)
        return parameter_data


class HoneywellZone(pyhtcc.Zone):
    """Extend the Zone class with additional methods to get and set
       uiData parameters."""

    OFF_MODE = "OFF_MODE"
    HEAT_MODE = "HEAT_MODE"
    COOL_MODE = "COOL_MODE"
    system_switch_position = {
        COOL_MODE: 0,  # assumed, need to verify
        HEAT_MODE: 1,
        OFF_MODE: 2,
        }

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

    def report_heating_parameters(self):
        """
        Display critical thermostat settings and reading to the screen.
        inputs:
            zone(obj): Zone object
        returns:
            None
        """
        # current temp as measured by thermostat
        util.log_msg("display temp=%s" % self.get_display_temp(),
                     mode=util.BOTH_LOG, func_name=1)

        # heating status
        if self.get_system_switch_position() == \
                self.system_switch_position[self.HEAT_MODE]:
            util.log_msg("heat mode=%s" % self.get_heat_mode(),
                         mode=util.BOTH_LOG)
            util.log_msg("heat setpoint=%s" %
                         self.get_heat_setpoint(), mode=util.BOTH_LOG)
            # util.log_msg("heat setpoint raw=%s" %
            #              zone.get_heat_setpoint_raw())
            util.log_msg("schedule heat sp=%s" %
                         self.get_schedule_heat_sp(), mode=util.BOTH_LOG)
            util.log_msg("\n", mode=util.BOTH_LOG)

        # cooling status
        if self.get_system_switch_position() == \
                self.system_switch_position[self.COOL_MODE]:
            util.log_msg("cool mode=%s" % self.get_cool_mode(),
                         mode=util.BOTH_LOG)
            util.log_msg("cool setpoint=%s" %
                         self.get_cool_setpoint(), mode=util.BOTH_LOG)
            # util.log_msg("cool setpoint raw=%s" %
            #              zone.get_cool_setpoint_raw(), mode=util.BOTH_LOG)
            util.log_msg("schedule cool sp=%s" %
                         self.get_schedule_cool_sp(), mode=util.BOTH_LOG)
            util.log_msg("\n", mode=util.BOTH_LOG)

        # hold settings
        util.log_msg("is in vacation hold mode=%s" %
                     self.get_is_invacation_hold_mode(), mode=util.BOTH_LOG)
        util.log_msg("vacation hold=%s" % self.get_vacation_hold(),
                     mode=util.BOTH_LOG)
        util.log_msg("vacation hold until time=%s" %
                     self.get_vacation_hold_until_time(), mode=util.BOTH_LOG)
        util.log_msg("temporary hold until time=%s" %
                     self.get_temporary_hold_until_time(), mode=util.BOTH_LOG)

    def get_current_mode(self, poll_count, print_status=True,
                         flag_all_deviations=False):
        """
        Determine whether thermostat is following schedule or if it has been
        deviated from schedule.

        inputs:
            zone(obj):  TCC Zone object
            poll_count(int): poll number for reporting
            print_status(bool):  True to print status line
            flag_all_deviations(bool):  True: flag all deviations
                                        False(default): only flag energy
                                                        consuming deviations,
                                                        e.g. heat setpoint
                                                        above schedule,
                                                        cool setpoint
                                                        below schedule
        returns:
            dictionary of heat/cool mode status, deviation status,
            and hold status
        """
        # initialize variables
        cool_deviation = False  # cooling set point deviates from schedule
        heat_deviation = False  # heating set point deviates from schedule
        hold_mode = False  # True if not following schedule
        heat_schedule_point = -1  # heating schedule set point
        heat_set_point = -1  # heating current set point
        cool_schedule_point = -1  # cooling schedule set point
        cool_set_point = -1  # cooling current set point
        mode = "OFF MODE"  # mode for display, "OFF MODE", "HEAT MODE",
        #                    "COOL MODE"
        hold_temporary = False  # True if hold will revert on next
        #                         schedule event

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
        display_temp = self.get_display_temp()

        # check for heat deviation
        heat_mode = (self.get_system_switch_position() ==
                     self.system_switch_position[self.HEAT_MODE])
        if heat_mode:
            mode = "HEAT MODE"
            heat_set_point = self.get_heat_setpoint_raw()
            heat_schedule_point = self.get_schedule_heat_sp()
            if heat_operator(heat_set_point, heat_schedule_point):
                status_msg = ("[heat deviation] actual=%s, set point=%s,"
                              " override=%s" %
                              (display_temp, heat_schedule_point,
                               heat_set_point))
                heat_deviation = True

        # check for cool deviation
        cool_mode = (self.get_system_switch_position() ==
                     self.system_switch_position[self.COOL_MODE])
        if cool_mode:
            mode = "COOL MODE"
            cool_set_point = self.get_cool_setpoint_raw()
            cool_schedule_point = self.get_schedule_cool_sp()
            if cool_operator(cool_set_point, cool_schedule_point):
                status_msg = ("[cool deviation] actual=%s, set point=%s,"
                              " override=%s" %
                              (display_temp, cool_schedule_point,
                               cool_set_point))
                cool_deviation = True

        # hold cooling
        if (heat_deviation or cool_deviation and
                self.get_is_invacation_hold_mode()):
            hold_mode = True  # True = not following schedule
            hold_temporary = self.get_temporary_hold_until_time() > 0
            status_msg += (" (%s)" % ["persistent",
                                      "temporary"][hold_temporary])
        else:
            status_msg = ("[following schedule] actual=%s, set point=%s,"
                          " override=%s" %
                          (display_temp, heat_schedule_point, heat_set_point))

        full_status_msg = ("%s: (poll=%s) %s %s" %
                           (datetime.datetime.now().
                            strftime("%Y-%m-%d %H:%M:%S"),
                            poll_count, mode, status_msg))
        if print_status:
            util.log_msg(full_status_msg, mode=util.BOTH_LOG)

        # return status
        return_buffer["heat_mode"] = heat_mode
        return_buffer["cool_mode"] = cool_mode
        return_buffer["heat_deviation"] = heat_deviation
        return_buffer["cool_deviation"] = cool_deviation
        return_buffer["hold_mode"] = hold_mode
        return_buffer["status_msg"] = full_status_msg
        return return_buffer
