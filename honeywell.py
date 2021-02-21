"""
connection to Honeywell thermoststat using pyhtcc

https://pypi.org/project/pyhtcc/

"""
# built-in imports
import pprint
import pyhtcc

# local imports
import thermostat_common as tc
import utilities as util


class HoneywellThermostat(pyhtcc.PyHTCC):
    """Extend the PyHTCC class with additional methods."""

    # min practical value is 2 minutes based on empirical test
    # max value is 3, higher settings will cause HTTP errors, why?
    poll_time_sec = 3 * 60

    # reconnection time to TCC server:
    connection_time_sec = 8 * 60 * 60

    def _get_zone_device_ids(self) -> list:
        """Return a list of zone Device IDs."""
        zone_id_lst = []
        for _, zone in enumerate(self.get_zones_info()):
            zone_id_lst.append(zone['DeviceID'])
        return zone_id_lst

    def get_target_zone_id(self, zone_number=0):
        """Return the target zone ID."""
        return self._get_zone_device_ids()[zone_number]

    def get_all_thermostat_metadata(self):
        """Return initial meta data queried from thermostat."""
        # dump all meta data
        self.get_all_metadata()

        # dump uiData in a readable format
        return_data = self.get_latestdata()
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(return_data)

    def get_all_metadata(self, zone_number=0):
        """
        Return all the current thermostat metadata.

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
        Return the current thermostat metadata settings.

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
        Return the current thermostat latest data.

        inputs:
          p(object): thermostat object from connection
          zone_number(int): zone number, default=0
        returns:
          dict
        """
        latest_data_dict = self.get_metadata(zone_number).get('latestData')
        util.log_msg("zone%s latestData: %s" % (zone_number, latest_data_dict),
                     mode=util.DEBUG_LOG + util.CONSOLE_LOG, func_name=1)
        return latest_data_dict

    def get_uiData(self, zone_number=0):
        """
        Return the latest thermostat ui data.

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
        Return the latest thermostat ui data for one specific parameter.

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


class HoneywellZone(pyhtcc.Zone, tc.ThermostatCommonZone):
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

    def get_display_temp(self) -> int:  # used
        """Refresh the cached zone information then return DispTemperature"""
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']['DispTemperature'])

    def get_heat_mode(self) -> int:
        """Refresh the cached zone information and return the heat mode."""
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']['StatusHeat'])

    def get_cool_mode(self) -> int:
        """Refresh the cached zone information and return the cool mode."""
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']['StatusCool'])

    def get_schedule_heat_sp(self) -> int:  # used
        """
        Refresh the cached zone information and return the
        schedule heat setpoint.
        """
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']['ScheduleHeatSp'])

    def get_schedule_cool_sp(self) -> int:
        """
        Refresh the cached zone information and return the
        schedule cool setpoint.
        """
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']['ScheduleCoolSp'])

    def get_is_invacation_hold_mode(self) -> bool:  # used
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

    def get_temporary_hold_until_time(self) -> int:  # used
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

    def get_system_switch_position(self) -> int:  # used
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
        Set a new cool setpoint.

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
