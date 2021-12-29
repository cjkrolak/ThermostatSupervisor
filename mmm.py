"""
connection to 3m50 thermoststat on local net.
"""
# built-in imports
import datetime
import os
import pprint
import socket
import sys

# add github version of radiotherm to path
sys.path.append(os.path.abspath('../radiotherm'))
# insert gitub version of radiotherm to front of path for debugging
# sys.path.insert(0, os.path.abspath('../radiotherm'))  # front of path list
import radiotherm  # noqa F405
# print("path=%s" % sys.path)
# print("radiotherm=%s" % radiotherm)  # show imported object

import urllib  # noqa E402

# local imports
import mmm_config  # noqa E402
import thermostat_api as api  # noqa E402
import thermostat_common as tc  # noqa E402
import utilities as util  # noqa E402


socket_timeout = 30  # http socket timeout override


class ThermostatClass(tc.ThermostatCommon):
    """3m50 thermostat zone functions."""

    def __init__(self, zone):
        """
        Constructor, connect to thermostat.

        inputs:
            zone(str):  zone of thermostat on local net.
            mmm_metadata dict above must have correct local IP address for each
            zone.
        """
        # construct the superclass
        # tc.ThermostatCommonZone.__init__(self)
        # tc.ThermostatCommon.__init__(self)
        super().__init__()
        self.thermostat_type = mmm_config.ALIAS

        # configure zone info
        self.zone_number = int(zone)
        self.ip_address = mmm_config.mmm_metadata[
            self.zone_number]["ip_address"]
        self.device_id = self.get_target_zone_id()

    def get_target_zone_id(self) -> object:
        """
        Return the target zone ID from the
        zone number provided.

        inputs:
            None
        returns:
            (obj):  device object.
        """
        # verify thermostat exists on network
        try:
            self.device_id = radiotherm.get_thermostat(self.ip_address)
        except urllib.error.URLError as e:
            raise Exception("FATAL ERROR: 3m thermostat not found at "
                            "ip address: %s" % self.ip_address) from e
        return self.device_id

    def print_all_thermostat_metadata(self, zone, debug=False):
        """
        Return initial meta data queried from thermostat.

        inputs:
            zone(int) zone number
            debug(bool): debug flag
        returns:
            None
        """
        # dump all meta data
        self.get_all_metadata(zone)

        # dump uiData in a readable format
        self.exec_print_all_thermostat_metadata(
            self.get_latestdata, [zone, debug])

    def get_meta_data_dict(self, zone) -> dict:
        """Build meta data dictionary from list of object attributes.

        inputs:
            zone(int): zone number
        returns:
            (dict) of meta data
        """
        util.log_msg("querying thermostat zone %s for meta data..." % zone,
                     mode=util.BOTH_LOG, func_name=1)
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

    def get_all_metadata(self, zone) -> list:
        """
        Get all the current thermostat metadata.

        inputs:
            zone(int): zone number
        returns:
            (list) of thermostat attributes.
        """
        return self.get_meta_data_dict(zone)

    def get_metadata(self, zone, parameter=None) -> (dict, str):
        """
        Get the current thermostat metadata settings.

        inputs:
          parameter(str): target parameter, None = all settings
        returns:
          dict if parameter=None
          str if parameter != None
        """
        if parameter is None:
            return self.get_meta_data_dict(zone)
        else:
            return self.device_id[parameter]['raw']

    def get_latestdata(self, zone, debug=False) -> (dict, str):
        """
        Get the current thermostat latest data.

        inputs:
          zone(int): target zone
          debug(bool): debug flag
        returns:
          dict if parameter=None
          str if parameter != None
        """
        latest_data_dict = self.get_meta_data_dict(zone)
        if debug:
            util.log_msg("zone%s latestData: %s" % (zone, latest_data_dict),
                         mode=util.BOTH_LOG, func_name=1)
        return latest_data_dict

    def get_uiData(self, zone) -> dict:
        """
        Get the latest thermostat ui data

        inputs:
          zone(int): target zone.
        returns:
          (dict)
        """
        return self.get_meta_data_dict(zone)

    def get_uiData_param(self, parameter) -> dict:
        """
        Get the latest thermostat ui data for one specific parameter.

        inputs:
          parameter(str): UI parameter
        returns:
          (dict)
        """
        return self.device_id[parameter]['raw']


class ThermostatZone(tc.ThermostatCommonZone):
    """3m50 thermostat zone functions."""

    def __init__(self, Thermostat_obj):
        """
        Constructor, connect to thermostat.

        mmm_metadata dict above must have correct local IP address for each
            zone.

        inputs:
            Thermostat_obj(obj):  Thermostat class instance.
        """
        # construct the superclass
        super().__init__()

        # switch config for this thermostat
        self.system_switch_position[tc.ThermostatCommonZone.COOL_MODE] = 2
        self.system_switch_position[tc.ThermostatCommonZone.HEAT_MODE] = 1
        self.system_switch_position[tc.ThermostatCommonZone.OFF_MODE] = 0
        self.system_switch_position[tc.ThermostatCommonZone.AUTO_MODE] = 3

        # need verification
        self.system_switch_position[
            tc.ThermostatCommonZone.DRY_MODE] = util.bogus_int
        self.system_switch_position[
            tc.ThermostatCommonZone.FAN_MODE] = util.bogus_int

        # zone info
        self.thermostat_type = mmm_config.ALIAS
        self.device_id = Thermostat_obj.device_id
        self.zone_number = Thermostat_obj.zone_number
        self.zone_name = self.get_zone_name()

        # runtime parameter defaults
        self.poll_time_sec = 10 * 60  # default to 10 minutes
        self.connection_time_sec = 8 * 60 * 60  # default to 8 hours

    def get_zone_name(self, zone=None):
        """
        Return the name associated with the zone number.

        inputs:
            zone(int): Zone number
        returns:
            (str) zone name
        """
        if zone is None:
            # pull from thermostat
            return self.device_id.name['raw']
        else:
            # override from config file
            return mmm_config.mmm_metadata[zone]["zone_name"]

    def get_display_temp(self) -> float:
        """
        Return DispTemperature.

        inputs:
            None
        returns:
            (float): display temp in degrees.
        """
        return float(self.device_id.temp['raw'])

    def get_display_humidity(self) -> (float, None):
        """
        Return Humidity.

        inputs:
            None
        returns:
            (float, None): humidity in %RH, return None if not supported.
        """
        return None  # not available

    def get_is_humidity_supported(self) -> bool:
        """
        Return humidity sensor status.

        inputs:
            None
        returns:
            (bool): True if humidity is supported.
        """
        return self.get_display_humidity() is not None

    def is_heat_mode(self) -> int:
        """
        Return the heat mode.

        inputs:
            None
        returns:
            (int): heat mode.
        """
        return int(self.device_id.tmode['raw'] ==
                   self.system_switch_position[self.HEAT_MODE])

    def is_cool_mode(self) -> int:
        """
        Return the cool mode.

        inputs:
            None
        returns:
            (int): 1=cool mode enabled, 0=disabled.
        """
        return int(self.device_id.tmode['raw'] ==
                   self.system_switch_position[self.COOL_MODE])

    def is_dry_mode(self) -> int:
        """
        Return the dry mode.

        inputs:
            None
        returns:
            (int): 1=dry mode enabled, 0=disabled.
        """
        return int(self.device_id.tmode['raw'] ==
                   self.system_switch_position[self.DRY_MODE])

    def is_auto_mode(self) -> int:
        """
        Return the auto mode.

        inputs:
            None
        returns:
            (int): 1=auto mode enabled, 0=disabled.
        """
        return int(self.device_id.tmode['raw'] ==
                   self.system_switch_position[self.AUTO_MODE])

    def is_fan_mode(self) -> int:
        """
        Return the fan mode.

        Fan mode is fan on for circulation but not applying heat or cooling.
        inputs:
            None
        returns:
            (int): 1=fan mode enabled, 0=disabled.
        """
        return int(self.device_id.fmode['raw'] == 2 and self.is_off_mode())

    def is_off_mode(self) -> int:
        """
        Refresh the cached zone information and return the off mode.

        inputs:
            None
        returns:
            (int): off mode, 1=enabled, 0=disabled.
        """
        return int(self.device_id.tmode['raw'] ==
                   self.system_switch_position[self.OFF_MODE] and
                   not self.device_id.fmode['raw'] == 2)

    def is_heating(self):
        """Return 1 if heating relay is active, else 0."""
        return int(self.is_heat_mode() and self.is_power_on() and
                   self.get_heat_setpoint_raw() > self.get_display_temp())

    def is_cooling(self):
        """Return 1 if cooling relay is active, else 0."""
        return int(self.is_cool_mode() and self.is_power_on() and
                   self.get_cool_setpoint_raw() < self.get_display_temp())

    def is_drying(self):
        """Return 1 if drying relay is active, else 0."""
        return 0  # not applicable

    def is_auto(self):
        """Return 1 if auto relay is active, else 0."""
        return 0  # not applicable

    def is_fanning(self):
        """Return 1 if fan relay is active, else 0."""
        return int(self.is_fan_on() and self.is_power_on())

    def is_power_on(self):
        """Return 1 if power relay is active, else 0."""
        return int(self.device_id.power['raw'] > 0)

    def is_fan_on(self):
        """Return 1 if fan relay is active, else 0."""
        return self.device_id.fstate['raw']

    def is_defrosting(self):
        """Return 1 if defrosting is active, else 0."""
        return 0  # not applicable

    def is_standby(self):
        """Return 1 if standby is active, else 0."""
        return 0  # not applicable

    def get_setpoint_list(self, sp_dict, day) -> list:
        """
        Return list of 4 setpoints for the day.

        inputs:
            sp_dict(dict): setpoint dictionary
            day(int): day of the week, 0=Monday
        returns:
            list of 8 elements, representing 4 pairs of elapsed minutes
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

    def get_schedule_program_heat(self) -> dict:
        """
        Return the scheduled heat program, times and settings.

        inputs:
            None
        returns:
            (dict): scheduled heat set points and times in degrees.
        """
        result = self.device_id.program_heat['raw']
        if not isinstance(result, dict):
            raise Exception("heat program schedule set point is type %s, "
                            "should be dict" % type(result))
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

    def get_schedule_program_cool(self) -> dict:
        """
        Return the sechduled cool setpoint.

        inputs:
            None
        returns:
            (dict): current scheduled cool set point in degrees.
        """
        result = self.device_id.program_cool['raw']
        if not isinstance(result, dict):
            raise Exception("schedule program cool set point is type %s, "
                            "should be dict" % type(result))
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
        result = bool(self.device_id.override['raw'])
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
        if self.is_heat_mode() == 1:
            sp_dict = self.device_id.program_heat
        elif self.is_cool_mode() == 1:
            sp_dict = self.device_id.program_cool
        else:
            # off mode, use dummy dict.
            sp_dict = {'raw': {'0': [0] * 8, '1': [0] * 8, '2': [0] * 8,
                               '3': [0] * 8, '4': [0] * 8, '5': [0] * 8,
                               '6': [0] * 8}}
            # raise Exception("unknown heat/cool mode")
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

    def report_heating_parameters(self, switch_position=None):
        """
        Display critical thermostat settings and reading to the screen.

        inputs:
            switch_position(int): switch position override, used for testing.
        returns:
            None
        """
        # current temp as measured by thermostat
        util.log_msg("display temp=%s" %
                     util.temp_value_with_units(self.get_display_temp()),
                     mode=util.BOTH_LOG, func_name=1)

        # get switch position
        if switch_position is None:
            switch_position = self.get_system_switch_position()

        # heating status
        if switch_position == \
                self.system_switch_position[self.HEAT_MODE]:
            util.log_msg("heat mode=%s" % self.is_heat_mode(),
                         mode=util.BOTH_LOG)
            util.log_msg("heat setpoint=%s" %
                         self.get_heat_setpoint_raw(), mode=util.BOTH_LOG)
            util.log_msg("schedule heat sp=%s" %
                         self.get_schedule_heat_sp(), mode=util.BOTH_LOG)
            util.log_msg("\n", mode=util.BOTH_LOG)

        # cooling status
        if switch_position == \
                self.system_switch_position[self.COOL_MODE]:
            util.log_msg("cool mode=%s" % self.is_cool_mode(),
                         mode=util.BOTH_LOG)
            util.log_msg("cool setpoint=%s" %
                         self.get_cool_setpoint_raw(), mode=util.BOTH_LOG)
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


# monkeypatch radiotherm.thermostat.Thermostat __init__ method with longer
# socket.timeout delay, based on radiotherm version 2.1
def __init__(self, host, timeout=socket_timeout):  # changed from 4 (default)
    self.host = host
    self.timeout = timeout


radiotherm.thermostat.Thermostat.__init__ = __init__
# end of monkeypatch radiotherm.thermostat.Thermostst __init__

if __name__ == "__main__":

    # get zone override
    zone_number = api.parse_all_runtime_parameters()["zone"]

    _, Zone = tc.thermostat_basic_checkout(
        api, mmm_config.ALIAS,
        zone_number,
        ThermostatClass, ThermostatZone)

    # measure thermostat response time
    measurements = 30
    print("Thermostat response times for %s measurements..." % measurements)
    meas_data = Zone.measure_thermostat_response_time(measurements)
    ppp = pprint.PrettyPrinter(indent=4)
    ppp.pprint(meas_data)
