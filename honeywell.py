"""
connection to Honeywell thermoststat using pyhtcc

https://pypi.org/project/pyhtcc/
"""
# built-in imports
import os
import pprint
import pyhtcc
import time
import traceback

# local imports
import email_notification
import thermostat_common as tc
import utilities as util


class HoneywellThermostat(pyhtcc.PyHTCC):
    """Extend the PyHTCC class with additional methods."""

    def __init__(self, zone, *_, **__):
        """
        inputs:
            zone(str):  zone number
        """
        # TCC server auth credentials from env vars
        self.TCC_UNAME_KEY = 'TCC_USERNAME'
        self.TCC_PASSWORD_KEY = 'TCC_PASSWORD'
        self.tcc_uname = (os.environ.get(self.TCC_UNAME_KEY, "<" +
                          self.TCC_UNAME_KEY + "_KEY_MISSING>"))
        self.tcc_pwd = (os.environ.get(
            self.TCC_PASSWORD_KEY, "<" +
            self.TCC_PASSWORD_KEY + "_KEY_MISSING>"))
        self.args = [self.tcc_uname, self.tcc_pwd]

        # construct the superclass, requires auth setup first
        super(HoneywellThermostat, self).__init__(*self.args)

        # configure zone info
        self.zone_number = int(zone)
        self.zone_constructor = HoneywellZone
        self.device_id = self.get_target_zone_id()

    def _get_zone_device_ids(self) -> list:
        """
        Return a list of zone Device IDs.

        inputs:
            None
        returns:
            (list): all zone device ids supported.
        """
        zone_id_lst = []
        for _, zone in enumerate(self.get_zones_info()):
            zone_id_lst.append(zone['DeviceID'])
        return zone_id_lst

    def get_target_zone_id(self, zone_number=0):
        """
        Return the target zone ID.

        inputs:
            zone_number(int):  zone number.
        returns:
            (int): zone device id number
        """
        return self._get_zone_device_ids()[zone_number]

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

    def get_all_metadata(self, zone_number=0):
        """
        Return all the current thermostat metadata.

        inputs:
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

    def get_zones_info(self) -> list:
        """
        Return a list of dicts corresponding with each one corresponding to a
        particular zone.

        Method overridden from base class to add additional debug info.
        inputs:
            None
        returns:
            list of zone info.
        """
        zones = []
        for page_num in range(1, 6):
            pyhtcc.logger.debug("Attempting to get zones for location id, "
                                f"page: {self._locationId}, {page_num}")
            result = self._post_zone_list_data(page_num)
            pyhtcc.logger.debug("finished get zones for location id, "
                                f"page: {self._locationId}, {page_num}")
            try:
                data = result.json()
            except Exception:
                # we can get a 200 with non-json data if pages aren't needed.
                # Though the 1st page shouldn't give non-json.
                if page_num == 1:
                    pyhtcc.logger.exception("Unable to decode json data "
                                            "returned by GetZoneList. Data "
                                            f"was:\n {result.text}")
                    raise
                else:
                    # custom debug code here
                    pyhtcc.logger.debug("Unable to decode json data returned "
                                        "by GetZoneList on page {page_num}. "
                                        f"Data was:\n {result.text}")
                    data = {}

            # once we go to an empty page, we're done.
            # Luckily it returns empty json instead of erroring
            if not data:
                pyhtcc.logger.debug(f"page {page_num} is empty")
                break

            zones.extend(data)

        # add name (and additional info) to zone info
        for idx, zone in enumerate(zones):
            device_id = zone['DeviceID']
            name = self._get_name_for_device_id(device_id)
            zone['Name'] = name

            device_id = zone['DeviceID']
            result = self._get_check_data_session(device_id)

            try:
                more_data = result.json()
            except Exception:
                pyhtcc.logger.exception("Unable to decode json data returned "
                                        "by CheckDataSession. Data was:\n "
                                        f"{result.text}")
                raise

            zones[idx] = {**zone, **more_data,
                          **self._get_outdoor_weather_info_for_zone(device_id)}

        return zones


class HoneywellZone(pyhtcc.Zone, tc.ThermostatCommonZone):
    """Extend the Zone class with additional methods to get and set
       uiData parameters."""

    system_switch_position = {
        tc.ThermostatCommonZone.COOL_MODE: 3,
        tc.ThermostatCommonZone.HEAT_MODE: 1,
        tc.ThermostatCommonZone.OFF_MODE: 2,
        tc.ThermostatCommonZone.AUTO_MODE: util.bogus_int,
        # what mode is 0 on Honeywell?
        }

    def __init__(self, *_, **__):
        # runtime parameter defaults
        self.poll_time_sec = 10 * 60  # default to 10 minutes
        # min practical value is 2 minutes based on empirical test
        # max value was 3, higher settings will cause HTTP errors, why?
        # not showing error on Pi at 10 minutes, so changed default to 10 min.
        self.connection_time_sec = 8 * 60 * 60  # default to 8 hours

        super(HoneywellZone, self).__init__(*_, **__)

    def get_display_temp(self) -> float:  # used
        """
        Refresh the cached zone information then return DispTemperature.

        inputs:
            None
        returns:
            (float): display temperature in degrees.
        """
        self.refresh_zone_info()
        return float(self.zone_info['latestData']['uiData']['DispTemperature'])

    def get_display_humidity(self) -> float:
        """
        Refresh the cached zone information then return IndoorHumidity.

        inputs:
            None
        returns:
            (float): indoor humidity in %RH.
        """
        self.refresh_zone_info()
        return float(self.zone_info['latestData']['uiData']['IndoorHumidity'])

    def get_is_humidity_supported(self) -> bool:  # used
        """
        Refresh the cached zone information and return the
          True if humidity sensor data is trustworthy.

        inputs:
            None
        returns:
            (booL): True if is in humidity sensor is available and not faulted.
        """
        self.refresh_zone_info()
        available = (self.zone_info['latestData']['uiData']
                     ['IndoorHumiditySensorAvailable'])
        not_fault = (self.zone_info['latestData']['uiData']
                     ['IndoorHumiditySensorNotFault'])
        return available and not_fault

    def get_heat_mode(self) -> int:
        """
        Refresh the cached zone information and return the heat mode.

        inputs:
            None
        returns:
            (int) heat mode.
        """
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']['StatusHeat'])

    def get_cool_mode(self) -> int:
        """
        Refresh the cached zone information and return the cool mode.

        inputs:
            None
        returns:
            (int): cool mode.
        """
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']['StatusCool'])

    def get_schedule_heat_sp(self) -> int:  # used
        """
        Refresh the cached zone information and return the
        schedule heat setpoint.

        inputs:
            None
        returns:
            (int): heating set point in degrees.
        """
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']['ScheduleHeatSp'])

    def get_schedule_cool_sp(self) -> int:
        """
        Refresh the cached zone information and return the
        schedule cool setpoint.

        inputs:
            None
        returns:
            (int): cooling set point in degrees.
        """
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']['ScheduleCoolSp'])

    def get_is_invacation_hold_mode(self) -> bool:  # used
        """
        Refresh the cached zone information and return the
          'IsInVacationHoldMode' setting.

        inputs:
            None
        returns:
            (booL): True if is in vacation hold mode.
        """
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']
                   ['IsInVacationHoldMode'])

    def get_vacation_hold(self) -> bool:
        """
        Refresh the cached zone information and return the
        VacationHold setting.

        inputs:
            None
        returns:
            (bool): True if vacation hold is set.
        """
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']['VacationHold'])

    def get_vacation_hold_until_time(self) -> int:
        """
        Refresh the cached zone information and return
        the 'VacationHoldUntilTime'.
        inputs:
            None
        returns:
            (int) vacation hold time until in minutes
        """
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']
                   ['VacationHoldUntilTime'])

    def get_temporary_hold_until_time(self) -> int:  # used
        """
        Refresh the cached zone information and return the
        'TemporaryHoldUntilTime'.

        inputs:
            None
        returns:
            (int) temporary hold time until in minutes.
        """
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']
                   ['TemporaryHoldUntilTime'])

    def get_setpoint_change_allowed(self) -> bool:
        """
        Refresh the cached zone information and return the
        'SetpointChangeAllowed' setting.

        'SetpointChangeAllowed' will be True in heating mode,
        False in OFF mode (assume True in cooling mode too)
        inputs:
            None
        returns:
            (bool): True if set point changes are allowed.
        """
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']
                   ['SetpointChangeAllowed'])

    def get_system_switch_position(self) -> int:  # used
        """
        Refresh the cached zone information and return the
        'SystemSwitchPosition'.

        'SystemSwitchPosition' = 1 for heat, 2 for off
        inputs:
            None
        returns:
            None
        """
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['uiData']
                   ['SystemSwitchPosition'])

    def set_heat_setpoint(self, temp: int) -> None:
        """
        Set a new heat setpoint.

        This will also attempt to turn the thermostat to 'Heat'
        inputs:
            temp(int): desired temperature.
        returns:
            None
        """
        # logger.info(f"setting heat on with a target temp of: {temp}")
        return self.submit_control_changes({
            'HeatSetpoint': temp,
            'StatusHeat': 0,  # follow schedule
            'StatusCool': 0,  # follow schedule
            'SystemSwitch': self.system_switch_position[self.HEAT_MODE],
        })

    def set_cool_setpoint(self, temp: int) -> None:
        """
        Set a new cool setpoint.

        This will also attempt to turn the thermostat to 'Cool'
        inputs:
            temp(int): desired temperature.
        returns:
            None
        """
        # logger.info(f"setting heat on with a target temp of: {temp}")
        return self.submit_control_changes({
            'CoolSetpoint': temp,
            'StatusHeat': 0,  # follow schedule
            'StatusCool': 0,  # follow schedule
            'SystemSwitch': self.system_switch_position[self.COOL_MODE],
        })

    def report_heating_parameters(self):
        """
        Display critical thermostat settings and reading to the screen.

        inputs:
            None
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

    def refresh_zone_info(self) -> None:
        """
        Refresh the zone_info attribute.

        Method overridden from base class to add retry on connection errors.
        inputs:
            None
        returns:
            None
        """
        number_of_retries = 3
        trial_number = 1
        while trial_number < number_of_retries:
            try:
                all_zones_info = self.pyhtcc.get_zones_info()
            except Exception:
                # catching simplejson.errors.JSONDecodeError
                # using Exception since simplejson is not imported
                util.log_msg(traceback.format_exc(),
                             mode=util.DEBUG_LOG + util.CONSOLE_LOG,
                             func_name=1)
                util.log_msg("exception during refresh_zone_info, on trial "
                             "%s of %s, probably a"
                             " connection issue%s" %
                             (trial_number, number_of_retries,
                              ["", ", waiting 30 seconds and then retrying..."]
                              [trial_number < number_of_retries]),
                             mode=util.BOTH_LOG, func_name=1)
                if trial_number < number_of_retries:
                    time.sleep(30)
                trial_number += 1
            else:
                # log the mitigated failure
                if trial_number > 1:
                    email_notification.send_email_alert(
                        subject=("intermittent JSON decode error "
                                 "during refresh zone"),
                        body="%s: trial %s of %s" % (util.get_function_name(),
                                                     trial_number,
                                                     number_of_retries))
                for z in all_zones_info:
                    if z['DeviceID'] == self.device_id:
                        pyhtcc.logger.debug(f"Refreshed zone info for \
                                           {self.device_id}")
                        self.zone_info = z
                        return

        # log fatal failure
        email_notification.send_email_alert(
            subject=("intermittent JSON decode error during refresh zone"),
            body="%s: trial %s of %s" % (util.get_function_name(),
                                         trial_number, number_of_retries))
        raise pyhtcc.ZoneNotFoundError(f"Missing device: {self.device_id}")
