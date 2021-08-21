"""
connection to 3m50 thermoststat on local net.
"""
# built-in imports
import datetime
import os
import pprint
import socket
import sys
sys.path.append(os.path.abspath('../radiotherm'))
import radiotherm  # noqa F405
import urllib  # noqa E402

# local imports
import thermostat_common as tc  # noqa E402
import utilities as util  # noqa E402


class MMM50Thermostat(tc.ThermostatCommonZone):
    """3m50 thermostat functions."""

    system_switch_position = {
        tc.ThermostatCommonZone.COOL_MODE: 2,
        tc.ThermostatCommonZone.HEAT_MODE: 1,
        tc.ThermostatCommonZone.OFF_MODE: 0,
        tc.ThermostatCommonZone.AUTO_MODE: 3,
        }

    # 3m50 thermostat IP addresses (local net)
    MAIN_3M50 = 0  # zone 0
    BASEMENT_3M50 = 1  # zone 1
    mmm_ip = {
        MAIN_3M50: "192.168.86.82",  # local IP
        BASEMENT_3M50: "192.168.86.83",  # local IP
    }

    def __init__(self, ip_address, *_, **__):
        """
        Constructor, connect to thermostat.

        inputs:
            ip_address(str):  ip address of thermostat on local net
        """
        super(MMM50Thermostat, self).__init__(*_, **__)
        self.zone_constructor = MMM50Thermostat
        try:
            self.device_id = radiotherm.get_thermostat(ip_address)
        except urllib.error.URLError as e:
            raise Exception("FATAL ERROR: 3m thermostat not found at "
                            "ip address: %s" % ip_address) from e
        self.ip_address = ip_address
        self.zone_number = list(self.mmm_ip.keys())[
            list(self.mmm_ip.values()).index(ip_address)]

        # runtime parameter defaults
        self.poll_time_sec = 10 * 60  # default to 10 minutes
        self.connection_time_sec = 8 * 60 * 60  # default to 8 hours

    def get_target_zone_id(self):
        """
        Return the target zone ID.

        inputs:
            None
        returns:
            (str):  IP address of target zone.
        """
        return self.ip_address

    def get_all_thermostat_metadata(self):
        """
        Return initial meta data queried from thermostat.

        inputs:
            None
        returns:
            None
        """
        # dump all meta data
        self.get_all_metadata()

        # dump uiData in a readable format
        return_data = self.get_latestdata()
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(return_data)

    def get_meta_data_dict(self):
        """Build meta data dictionary from list of object attributes.

        inputs:
            None
        returns:
            (dict) of meta data
        """
        print("querying thermostat for meta data...")
        attr_dict = {}
        ignore_fields = ['get', 'post', 'reboot', 'set_day_program']
        for attr in dir(self.device_id):
            if attr[0] != "_" and attr not in ignore_fields:
                key = attr
                try:
                    val = self.device_id.__getattribute__(key)
                except TypeError:
                    val = "<attribute is not readable>"
                except AttributeError as e:
                    val = e
                except socket.timeout:
                    val = "<socket timeout>"
                attr_dict[key] = val
        return attr_dict

    def get_all_metadata(self):
        """
        Get all the current thermostat metadata.

        inputs:
            None
        returns:
            (list) of thermostat attributes.
        """
        return self.get_meta_data_dict()

    def get_metadata(self, parameter=None):
        """
        Get the current thermostat metadata settings.

        inputs:
          parameter(str): target parameter, None = all settings
        returns:
          dict if parameter=None
          str if parameter != None
        """
        if parameter is None:
            return self.get_meta_data_dict()
        else:
            return self.device_id[parameter]['raw']

    def get_latestdata(self):
        """
        Get the current thermostat latest data.

        inputs:
          None
        returns:
          dict if parameter=None
          str if parameter != None
        """
        return self.get_meta_data_dict()

    def get_uiData(self):
        """
        Get the latest thermostat ui data

        inputs:
          None
        returns:
          (dict) empty dict.
        """
        return self.get_meta_data_dict()

    def get_uiData_param(self, parameter):
        """
        Get the latest thermostat ui data for one specific parameter.

        inputs:
          parameter(str): UI parameter
        returns:
          (dict) empty dict.
        """
        return self.device_id[parameter]['raw']

    def get_display_temp(self) -> float:
        """
        Return DispTemperature.

        inputs:
            None
        returns:
            (float): display temp in degrees.
        """
        return float(self.device_id.temp['raw'])

    def get_display_humidity(self) -> float:
        """
        Return Humidity.

        inputs:
            None
        returns:
            (float): humidity in %RH.
        """
        return util.bogus_int  # not available

    def get_is_humidity_supported(self) -> bool:
        """Return humidity sensor status."""
        return False  # not supported

    def get_heat_mode(self) -> int:
        """
        Return the heat mode.

        inputs:
            None
        returns:
            (int): heat mode.
        """
        return int(self.device_id.tmode['raw'] ==
                   self.system_switch_position[self.HEAT_MODE])

    def get_cool_mode(self) -> int:
        """
        Return the cool mode.

        inputs:
            None
        returns:
            (int): cool mode.
        """
        return int(self.device_id.tmode['raw'] ==
                   self.system_switch_position[self.COOL_MODE])

    def get_setpoint_list(self, sp_dict, day) -> int:
        """
        Return list of 4 setpoints for the day.

        inputs:
            sp_dict(dict): setpoint dictionary
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
            sp_dict(dict): setpoint dictionary
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
            sp_dict(dict): setpoint dictionary
        returns:
            (int) last temperature set the day before.
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
        return current_sp

    def get_heat_setpoint(self) -> float:
        """
        Return the current heat setpoint.

        t_heat field is only present if in heat mode.
        inputs:
            None
        returns:
            (float): current heat set point in degrees.
        """
        result = self.device_id.t_heat['raw']
        if not isinstance(result, float):
            raise Exception("heat set point is type %s, "
                            "should be float" % type(result))
        return result

    def get_heat_setpoint_raw(self) -> float:
        """
        Return the current raw heat setpoint.

        t_heat field is only present if in heat mode.
        inputs:
            None
        returns:
            (float): current raw heat set point in degrees.
        """
        result = self.get_heat_setpoint()
        if not isinstance(result, float):
            raise Exception("heat set point raw is type %s, "
                            "should be float" % type(result))
        return result

    def get_cool_setpoint(self) -> int:
        """
        Return the current cool setpoint.

        t_cool field is only present if in cool mode.
        inputs:
            None
        returns:
            (int): current cool set point in degrees.
        """
        result = self.device_id.t_cool['raw']
        if not isinstance(result, (int, float)):
            raise Exception("cool set point is type %s, "
                            "should be (int, float)" % type(result))
        return result

    def get_cool_setpoint_raw(self) -> int:
        """
        Return the current raw cool setpoint.

        t_cool field is only present if in cool mode.
        inputs:
            None
        returns:
            (int): current raw cool set point in degrees.
        """
        result = self.get_cool_setpoint()
        if not isinstance(result, (int, float)):
            raise Exception("cool setpoint raw is type %s, "
                            "should be (int, float)" % type(result))
        return result

    def get_schedule_program_heat(self) -> int:
        """
        Return the scheduled heat setpoint.

        inputs:
            None
        returns:
            (int): scheduled heat set point in degrees.
        """
        result = self.device_id.program_heat['raw']
        if not isinstance(result, int):
            raise Exception("heat program schedule set point is type %s, "
                            "should be int" % type(result))
        return result

    def get_schedule_heat_sp(self) -> int:
        """
        Return the scheduled heat setpoint.

        inputs:
            None
        returns:
            (int): current scheduled heat set point in degrees.
        """
        result = self.get_schedule_setpoint(self.device_id.program_heat)
        if not isinstance(result, int):
            raise Exception("schedule heat set point is type %s, "
                            "should be int" % type(result))
        return result

    def get_schedule_program_cool(self) -> int:
        """
        Return the sechduled cool setpoint.

        inputs:
            None
        returns:
            (int): current scheduled cool set point in degrees.
        """
        result = self.device_id.program_cool['raw']
        if not isinstance(result, int):
            raise Exception("schedule program cool set point is type %s, "
                            "should be int" % type(result))
        return result

    def get_schedule_cool_sp(self) -> int:
        """
        Return the sechduled cool setpoint.

        inputs:
            None
        returns:
            (int): current schedule cool set point in degrees.
        """
        result = self.get_schedule_setpoint(self.device_id.program_cool)
        if not isinstance(result, int):
            raise Exception("schedule cool set point is type %s, "
                            "should be int" % type(result))
        return result

    def get_is_invacation_hold_mode(self) -> bool:
        """
        Return the in vacation hold status.

        inputs:
            None
        returns:
            (int): 0=Disabled, 1=Enabled
        """
        result = bool(self.device_id.hold['raw'])
        if not isinstance(result, bool):
            raise Exception("is_invacation_hold_mode is type %s, "
                            "should be bool" % type(result))
        return result

    def get_vacation_hold(self) -> bool:
        """
        Return the Hold setting.

        inputs:
            None
        returns:
            (int): 0=Disabled, 1=Enabled
        """
        result = self.device_id.override['raw']
        if not isinstance(result, bool):
            raise Exception("get_vacation_hold_mode is type %s, "
                            "should be bool" % type(result))
        return result

    def get_vacation_hold_until_time(self) -> int:
        """
        Return the 'VacationHoldUntilTime'.

        inputs:
            None
        returns:
            (int): vacation hold time in minutes.
         """
        return -1  # not implemented

    def get_temporary_hold_until_time(self) -> int:
        """
        Return the 'TemporaryHoldUntilTime'.

        inputs:
            None
        returns:
            (int): temporary hold time in minutes.
         """
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
        """
        Return the 'SetpointChangeAllowed' setting.

        inputs:
            None
        returns:
            (bool): 'SetpointChangeAllowed' will be True in heating mode,
            False in OFF mode (assume True in cooling mode too)
        """
        return False  # not implemented

    def get_system_switch_position(self) -> int:
        """ Return the thermostat mode.

        inputs:
            None
        returns:
            (int): thermostat mode, refer to tc.system_swtich position
            for details.
        """
        result = self.device_id.tmode['raw']
        if not isinstance(result, int):
            raise Exception("get_system_switch_position is type %s, "
                            "should be int" % type(result))
        return result

    def set_heat_setpoint(self, temp: int) -> None:
        """
        Set a new heat setpoint.

        This will also attempt to turn the thermostat to 'Heat'
        inputs:
            temp(int): desired temperature in degrees.
        returns:
            None
        """
        print("setting heat to %s" % temp)
        self.device_id.t_heat = temp

    def set_cool_setpoint(self, temp: int) -> None:
        """
        Set a new cool setpoint.

        This will also attempt to turn the thermostat to 'Cool'
        inputs:
            temp(int): desired temperature in degrees.
        returns:
            None
        """
        self.device_id.t_cool = temp

    def report_heating_parameters(self):
        """
        Display critical thermostat settings and reading to the screen.

        inputs:
            None
        returns:
            None
        """
        return  # not yet implemented


if __name__ == "__main__":

    util.log_msg.debug = True  # debug mode set

    ip_main_3m50 = "192.168.86.82"
    ip_basement_3m50 = "192.168.86.83"

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
