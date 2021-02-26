"""
connection to 3m50 thermoststat

"""
# built-in imports
import datetime
import os
import sys
sys.path.append(os.path.abspath('../radiotherm'))
import radiotherm  # noqa F405
import urllib

# local imports
import thermostat_common as tc  # noqa E402
import utilities as util  # noqa E402

ip_main_3m50 = "192.168.86.82"
ip_basement_3m50 = "192.168.86.83"


class MMM50Thermostat(tc.ThermostatCommonZone):
    """3m50 thermostat functions

    """
    # thermostat poll time interval
    poll_time_sec = 10 * 60

    # reconnection time to thermostat:
    connection_time_sec = 8 * 60 * 60

    def __init__(self, ip_address, *_, **__):
        """
        Constructor, connect to thermostat.

        inputs:
            ip_address(str):  ip address of thermostat on local net
        """
        try:
            self.device_id = radiotherm.get_thermostat(ip_address)
        except urllib.error.URLError as e:
            raise Exception("FATAL ERROR: 3m thermostat not found at "
                            "ip address: %s" % ip_address) from e
        self.ip_address = ip_address

    def get_target_zone_id(self):
        """Return the target zone ID."""
        return self.ip_address

    def get_all_metadata(self):
        """
        Get all the current thermostat metadata

        inputs:
          p(object): thermostat object from connection
          zone_number(int): zone number, default=0
        returns:
          dict
        """
        return {}  # not yet implemented

    def get_metadata(self, parameter=None):
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
        if parameter is None:
            return {}  # not yet implemented
        else:
            return ""  # not yet implemented

    def get_latestdata(self):
        """
        Get the current thermostat latest data

        inputs:
          p(object): thermostat object from connection
          zone_number(int): zone number, default=0
        returns:
          dict if parameter=None
          str if parameter != None
        """
        return {}  # not yet implemented

    def get_uiData(self):
        """
        Get the latest thermostat ui data

        inputs:
          p(object): thermostat object from connection
          zone_number(int): zone_number, default=0
        returns:
          dict
        """
        return {}  # not yet implemented

    def get_uiData_param(self):
        """
        Get the latest thermostat ui data for one specific parameter

        inputs:
          p(object): thermostat object from connection
          zone_number(int): zone_number, default=0
          parameter(str): paramenter name
        returns:
          dict
        """
        return {}  # not yet implemented

    def get_display_temp(self) -> int:
        """Refresh the cached zone information then return DispTemperature"""
        return self.device_id.temp['raw']

    def get_heat_mode(self) -> int:
        """Refresh the cached zone information and return the heat mode."""
        return int(self.device_id.tmode['raw'] ==
                   self.system_switch_position[self.HEAT_MODE])

    def get_cool_mode(self) -> int:
        """Refresh the cached zone information and return the cool mode."""
        return int(self.device_id.tmode['raw'] ==
                   self.system_switch_position[self.COOL_MODE])

    def get_setpoint_list(self, sp_dict, day) -> int:
        """
        Return list of 4 setpoints for the day.

        inputs:
            sp_dict(dictionary): setpoint dictionary
            day(int): day of the week, 0=Monday
        returns:
            list of 8 eleements, representing 4 pairs of elapsed minutes
            and setpoint
        """
        sp_lst = sp_dict['raw'][str(day)]
        if len(sp_lst) != 8:
            raise Exception("setpoint list is not 8 elements long: %s" %
                            sp_lst)
        return sp_dict['raw'][str(day)]

    def get_previous_days_setpoint(self, sp_dict) -> int:
        """
        Return last setpoint from day before today.

        inputs:
            sp_dict(dictionary): setpoint dictionary
        returns:
            (int)last temperature set the day before.
        """
        today = datetime.datetime.today().weekday()
        if today == 0:
            yesterday = 6
        else:
            yesterday = today - 1
        return self.get_setpoint_list(sp_dict, yesterday)[-1]

    def get_schedule_setpoint(self, sp_dict) -> int:
        """
        Return current setpoint.

        inputs:
            sp_dict(dictionary): setpoint dictionary
        returns:
            (int)last temperature set the day before.
        """
        current_sp = self.get_previous_days_setpoint(sp_dict)
        now = datetime.datetime.now()
        minutes_since_midnight = (
            now - now.replace(hour=0, minute=0, second=0, microsecond=0)
            ).total_seconds() / 60
        todays_setpoint_lst = self.get_setpoint_list(sp_dict,
                                                     datetime.datetime.today(
                                                         ).weekday())
        for t in [0, 2, 4, 6]:
            if todays_setpoint_lst[t] > minutes_since_midnight:
                return current_sp
            else:
                # store setpoint corresponding to this time
                current_sp = todays_setpoint_lst[t + 1]

    def get_heat_setpoint(self) -> int:
        """Return the current heat setpoint."""
        return self.device_id.t_heat['raw']

    def get_heat_setpoint_raw(self) -> int:
        """Return the current raw heat setpoint."""
        return self.get_heat_setpoint()

    def get_cool_setpoint(self) -> int:
        """Return the current cool setpoint."""
        return self.device_id.t_cool['raw']

    def get_cool_setpoint_raw(self) -> int:
        """Return the current raw cool setpoint."""
        return self.get_cool_setpoint()

    def get_schedule_program_heat(self) -> int:
        """Return the scheduled heat setpoint."""
        return self.device_id.program_heat['raw']

    def get_schedule_heat_sp(self) -> int:
        """Return the scheduled heat setpoint."""
        return self.get_schedule_setpoint(self.device_id.program_heat)

    def get_schedule_program_cool(self) -> int:
        """Return the sechduled cool setpoint."""
        return self.device_id.program_cool['raw']

    def get_schedule_cool_sp(self) -> int:
        """Return the sechduled cool setpoint."""
        return self.get_schedule_setpoint(self.device_id.program_cool)

    def get_is_invacation_hold_mode(self) -> bool:
        """
        Return the Hold setting.
        0=Disabled, 1=Enabled
        """
        return bool(self.device_id.hold['raw'])

    def get_vacation_hold(self) -> bool:
        """
        Return the Hold setting.
        0=Disabled, 1=Enabled
        """
        return self.device_id.override['raw']

    def get_vacation_hold_until_time(self) -> int:
        """ refreshes the cached zone information and return
            the 'VacationHoldUntilTime' """
        return -1  # not implemented

    def get_temporary_hold_until_time(self) -> int:
        """ refreshes the cached zone information and return the
            'TemporaryHoldUntilTime' """
        if self.get_heat_mode() == 1:
            sp_dict = self.device_id.program_heat
        elif self.get_cool_mode() == 1:
            sp_dict = self.device_id.program_cool
        else:
            raise Exception("unknown heat/cool mode")
        now = datetime.datetime.now()
        minutes_since_midnight = (
            now - now.replace(hour=0, minute=0, second=0,
                              microsecond=0)).total_seconds() / 60
        todays_setpoint_lst = self.get_setpoint_list(sp_dict,
                                                     datetime.datetime.today(
                                                         ).weekday())
        for t in [0, 2, 4, 6]:
            if todays_setpoint_lst[t] > minutes_since_midnight:
                time_delta = todays_setpoint_lst[t] - minutes_since_midnight
                break  # found next timer
            else:
                time_delta = 24 * 60 - minutes_since_midnight

        return int(time_delta)

    def get_setpoint_change_allowed(self) -> bool:
        """ refreshes the cached zone information and return the
            'SetpointChangeAllowed' setting
            'SetpointChangeAllowed' will be True in heating mode,
            False in OFF mode (assume True in cooling mode too)
        """
        return False  # not implemented

    def get_system_switch_position(self) -> int:
        """ Return the thermostat mode
            0 : 'Off',
            1 : 'Heat',
            2 : 'Cool',
            3 : 'Auto'
        """
        return self.device_id.tmode['raw']

    def set_heat_setpoint(self, temp: int) -> None:
        """
        Sets a new heat setpoint.
        This will also attempt to turn the thermostat to 'Heat'
        """
        print("setting heat to %s" % temp)
        self.device_id.t_heat = temp

    def set_cool_setpoint(self, temp: int) -> None:
        """
        Sets a new cool setpoint.
        This will also attempt to turn the thermostat to 'Cool'
        """
        self.device_id.t_cool = temp

    def report_heating_parameters(self):
        """
        Display critical thermostat settings and reading to the screen.
        inputs:
            zone(obj): Zone object
        returns:
            None
        """
        return  # not yet implemented


if __name__ == "__main__":

    util.log_msg.debug = True  # debug mode set

    # set ip address
    if len(sys.argv) > 1 and sys.argv[1] in [ip_main_3m50, ip_basement_3m50]:
        ip = sys.argv[1]
    else:
        # default
        ip = ip_main_3m50

    tstat = MMM50Thermostat(ip)
    zone = MMM50Thermostat(ip, tstat)
    print("current thermostat settings...")
    print("tmode1: %s" % zone.get_system_switch_position())
    print("heat set point=%s" % zone.get_heat_setpoint())
    print("cool set point=%s" % zone.get_cool_setpoint())
    print("(schedule) heat program=%s" % zone.get_schedule_program_heat())
    print("(schedule) cool program=%s" % zone.get_schedule_program_cool())
    print("hold=%s" % zone.get_vacation_hold())
    print("heat mode=%s" % zone.get_heat_mode())
    print("cool mode=%s" % zone.get_cool_mode())
    print("temporary hold minutes=%s" % zone.get_temporary_hold_until_time())
