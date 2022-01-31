"""
Connection to Honeywell thermoststat via TotalConnectComfort web site
using pyhtcc library.

https://pypi.org/project/pyhtcc/
"""
# built-in imports
import datetime
import os
import pprint
import time
import traceback

# local imports
from thermostatsupervisor import email_notification
from thermostatsupervisor import honeywell_config
from thermostatsupervisor import thermostat_api as api
from thermostatsupervisor import thermostat_common as tc
from thermostatsupervisor import utilities as util

# honeywell import
HONEYWELL_DEBUG = False  # debug uses local pyhtcc repo instead of pkg
if HONEYWELL_DEBUG and not util.is_azure_environment():
    pyhtcc = util.dynamic_module_import("pyhtcc",
                                        "..\\..\\pyhtcc\\pyhtcc")
else:
    import pyhtcc  # noqa E402, from path / site packages


class ThermostatClass(pyhtcc.PyHTCC, tc.ThermostatCommon):
    """Extend the PyHTCC class with additional methods."""

    def __init__(self, zone):
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

        # call both parent class __init__
        self.args = [self.tcc_uname, self.tcc_pwd]
        pyhtcc.PyHTCC.__init__(self, *self.args)
        tc.ThermostatCommon.__init__(self)

        # configure zone info
        self.thermostat_type = honeywell_config.ALIAS
        self.zone_number = int(zone)
        self.device_id = self.get_target_zone_id(self.zone_number)

    def __del__(self):
        """Clean-up session created in pyhtcc."""
        self.session.close()

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

    def get_target_zone_id(self, zone=honeywell_config.default_zone) -> int:
        """
        Return the target zone ID.

        inputs:
            zone(int):  zone number.
        returns:
            (int): zone device id number
        """
        return self._get_zone_device_ids()[zone]

    def print_all_thermostat_metadata(self, zone, debug=False):
        """
        Return initial meta data queried from thermostat.

        inputs:
            zone(int): zone number
            debug(bool): debug flag
        returns:
            None, prints data to the stdout.
        """
        # dump all meta data
        self.get_all_metadata(zone)

        # dump uiData in a readable format
        self.exec_print_all_thermostat_metadata(
            self.get_latestdata, [zone, debug])

    def get_all_metadata(self, zone=honeywell_config.default_zone) -> dict:
        """
        Return all the current thermostat metadata.

        inputs:
          zone(int): zone number, default=honeywell_config.default_zone
        returns:
          (dict) thermostat meta data.
        """
        return_data = self.get_metadata(zone, parameter=None)
        util.log_msg(f"all meta data: {return_data}",
                     mode=util.DEBUG_LOG + util.CONSOLE_LOG, func_name=1)
        return return_data

    def get_metadata(self, zone=honeywell_config.default_zone,
                     parameter=None) -> (dict, str):
        """
        Return the current thermostat metadata settings.

        inputs:
          zone(int): zone number, default=honeywell_config.default_zone
          parameter(str): target parameter, None = all settings
        returns:
          dict if parameter=None
          str if parameter != None
        """
        zone_info_list = self.get_zones_info()
        if parameter is None:
            return_data = zone_info_list[zone]
            util.log_msg(f"zone{zone} info: {return_data}",
                         mode=util.DEBUG_LOG + util.CONSOLE_LOG, func_name=1)
            return return_data
        else:
            return_data = zone_info_list[zone].get(parameter)
            util.log_msg(f"zone{zone} parameter '{parameter}': {return_data}",
                         mode=util.DEBUG_LOG + util.CONSOLE_LOG, func_name=1)
            return return_data

    def get_latestdata(self, zone=honeywell_config.default_zone,
                       debug=False) -> dict:
        """
        Return the current thermostat latest data.

        inputs:
          zone(int): zone number, default=honeywell_config.default_zone
          debug(bool): debug flag
        returns:
          (dict) latest data from thermostat.
        """
        latest_data_dict = self.get_metadata(zone).get('latestData')
        if debug:
            util.log_msg(f"zone{zone} latestData: {latest_data_dict}",
                         mode=util.BOTH_LOG, func_name=1)
        return latest_data_dict

    def get_ui_data(self, zone=honeywell_config.default_zone) -> dict:
        """
        Return the latest thermostat ui data.

        inputs:
          zone(int): zone, default=honeywell_config.default_zone
        returns:
          (dict) ui data from thermostat.
        """
        ui_data_dict = self.get_latestdata(zone).get('uiData')
        util.log_msg(f"zone{zone} latestData: {ui_data_dict}",
                     mode=util.DEBUG_LOG + util.CONSOLE_LOG, func_name=1)
        return ui_data_dict

    def get_ui_data_param(self, zone=honeywell_config.default_zone,
                          parameter=None) -> dict:
        """
        Return the latest thermostat ui data for one specific parameter.

        inputs:
          zone(int): zone, default=honeywell_config.default_zone
          parameter(str): paramenter name
        returns:
          (dict)  # need to verify return data type.
        """
        parameter_data = self.get_ui_data(
            zone=honeywell_config.default_zone).get(parameter)
        util.log_msg(f"zone{zone} uiData parameter {parameter}: "
                     f"{parameter_data}",
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
            except Exception:  # noqa w0703 too general exception
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


class ThermostatZone(pyhtcc.Zone, tc.ThermostatCommonZone):
    """Extend the Zone class with additional methods to get and set
       uiData parameters."""

    def __init__(self, Thermostat_obj):
        """
        Zone constructor.

        inputs:
            Thermostat_obj(obj): Thermostat class object instance.
        returns:
            None
        """
        if not isinstance(Thermostat_obj.device_id, int):
            raise TypeError("device_id is type %s, "
                            "expected type 'int'" %
                            type(Thermostat_obj.device_id))

        # call both parent class __init__
        self.args = [Thermostat_obj.device_id, Thermostat_obj]
        pyhtcc.Zone.__init__(self, *self.args)
        tc.ThermostatCommonZone.__init__(self)

        # switch config for this thermostat
        self.system_switch_position[tc.ThermostatCommonZone.COOL_MODE] = 3
        self.system_switch_position[tc.ThermostatCommonZone.HEAT_MODE] = 1
        self.system_switch_position[tc.ThermostatCommonZone.OFF_MODE] = 2
        # TODO: what mode is 0 on Honeywell?

        # zone info
        self.thermostat_type = honeywell_config.ALIAS
        self.device_id = Thermostat_obj.device_id
        self.zone_number = Thermostat_obj.zone_number
        self.zone_name = self.get_zone_name()

        # runtime parameter defaults
        self.poll_time_sec = 10 * 60  # default to 10 minutes
        # min practical value is 2 minutes based on empirical test
        # max value was 3, higher settings will cause HTTP errors, why?
        # not showing error on Pi at 10 minutes, so changed default to 10 min.
        self.connection_time_sec = 8 * 60 * 60  # default to 8 hours

    def get_zone_name(self) -> str:  # used
        """
        Refresh the cached zone information then return Name.

        inputs:
            None
        returns:
            (str): zone name
        """
        self.refresh_zone_info()
        return self.zone_info['Name']

    def get_display_temp(self) -> float:  # used
        """
        Refresh the cached zone information then return DispTemperature.

        inputs:
            None
        returns:
            (float): display temperature in degrees F.
        """
        self.refresh_zone_info()
        return float(self.zone_info['latestData']['uiData']['DispTemperature'])

    def get_display_humidity(self) -> (float, None):
        """
        Refresh the cached zone information then return IndoorHumidity.

        inputs:
            None
        returns:
            (float, None): indoor humidity in %RH, None if not supported.
        """
        self.refresh_zone_info()
        raw_humidity = self.zone_info['latestData']['uiData']['IndoorHumidity']
        if raw_humidity is not None:
            return float(raw_humidity)
        else:
            return raw_humidity

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

    def is_heat_mode(self) -> int:
        """
        Refresh the cached zone information and return heat mode.

        inputs:
            None
        returns:
            (int): 1 heat mode, else 0
        """
        return int(self.get_system_switch_position() ==
                   self.system_switch_position[
                       tc.ThermostatCommonZone.HEAT_MODE])

    def is_cool_mode(self) -> int:
        """
        Refresh the cached zone information and return the cool mode.

        inputs:
            None
        returns:
            (int): 1 if cool mode, else 0
        """
        return int(self.get_system_switch_position() ==
                   self.system_switch_position[
                       tc.ThermostatCommonZone.COOL_MODE])

    def is_dry_mode(self) -> int:
        """
        Return the dry mode.

        inputs:
            None
        returns:
            (int): 1 if dry mode, else 0
        """
        return int(self.get_system_switch_position() ==
                   self.system_switch_position[
                       tc.ThermostatCommonZone.DRY_MODE])

    def is_fan_mode(self) -> int:
        """
        Refresh the cached zone information and return the fan mode.

        Fan mode on Honeywell is defined as in off mode with fan set to
        on or circulate modes.
        inputs:
            None
        returns:
            (int): fan mode, 1=enabled, 0=disabled.
        """
        return int(self.get_system_switch_position() ==
                   self.system_switch_position[
                       tc.ThermostatCommonZone.OFF_MODE] and
                   (self.is_fan_on_mode() or self.is_fan_circulate_mode()))

    def is_auto_mode(self) -> int:
        """
        Return the auto mode.

        inputs:
            None
        returns:
            (int): 1 if auto mode, else 0
        """
        return int(self.get_system_switch_position() ==
                   self.system_switch_position[
                       tc.ThermostatCommonZone.AUTO_MODE])

    def is_heating(self) -> int:
        """
        Refresh the cached zone information and return the heat active mode.
        inputs:
            None
        returns:
            (int) 1 if heating is active, else 0.
        """
        self.refresh_zone_info()
        return int(self.is_heat_mode() and
                   self.get_display_temp() < self.get_heat_setpoint_raw())

    def is_cooling(self) -> int:
        """
        Refresh the cached zone information and return the cool active mode.
        inputs:
            None
        returns:
            (int): 1 if cooling is active, else 0.
        """
        self.refresh_zone_info()
        return int(self.is_cool_mode() and
                   self.get_display_temp() > self.get_cool_setpoint_raw())

    def is_drying(self):
        """Return 1 if drying relay is active, else 0."""
        return int(self.is_dry_mode() and self.is_power_on() and
                   self.get_cool_setpoint_raw() < self.get_display_temp())

    def is_auto(self):
        """Return 1 if auto relay is active, else 0."""
        return int(self.is_auto_mode() and self.is_power_on() and
                   (self.get_cool_setpoint_raw() < self.get_display_temp() or
                    self.get_heat_setpoint_raw() > self.get_display_temp()))

    def is_fanning(self):
        """Return 1 if fan relay is active, else 0."""
        return int((self.is_fan_on() or self.is_fan_circulate_mode())
                   and self.is_power_on())

    def is_fan_circulate_mode(self):
        """Return 1 if fan is in circulate mode, else 0."""
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['fanData'][
            'fanMode'] == 2)

    def is_fan_auto_mode(self):
        """Return 1 if fan is in auto mode, else 0."""
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['fanData'][
            'fanMode'] == 0)

    def is_fan_on_mode(self):
        """Return 1 if fan is in always on mode, else 0."""
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['fanData'][
            'fanMode'] == 1)

    def is_power_on(self):
        """Return 1 if power relay is active, else 0."""
        self.refresh_zone_info()
        # just a guess, not sure what position 0 is yet.
        return int(self.zone_info['latestData']['uiData'][
            'SystemSwitchPosition'] > 0)

    def is_fan_on(self):
        """Return 1 if fan relay is active, else 0."""
        self.refresh_zone_info()
        return int(self.zone_info['latestData']['fanData']['fanIsRunning'])

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
            (int) current mode for unit, should match value
                  in self.system_switch_position
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
            util.log_msg(f"heat mode={self.is_heat_mode()}",
                         mode=util.BOTH_LOG)
            util.log_msg("heat setpoint=%s" %
                         self.get_heat_setpoint(), mode=util.BOTH_LOG)
            # util.log_msg("heat setpoint raw=%s" %
            #              zone.get_heat_setpoint_raw())
            util.log_msg("schedule heat sp=%s" %
                         self.get_schedule_heat_sp(), mode=util.BOTH_LOG)
            util.log_msg("\n", mode=util.BOTH_LOG)

        # cooling status
        if switch_position == \
                self.system_switch_position[self.COOL_MODE]:
            util.log_msg(f"cool mode={self.is_cool_mode()}",
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
        util.log_msg(f"vacation hold={self.get_vacation_hold()}",
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
            None, populates self.zone_info dict.
        """
        number_of_retries = 3
        trial_number = 1
        retry_delay_sec = 60
        while trial_number < number_of_retries:
            try:
                time_now = (datetime.datetime.now().
                            strftime("%Y-%m-%d %H:%M:%S"))
                all_zones_info = self.pyhtcc.get_zones_info()
            except Exception:  # noqa w0703 too general exception
                # catching simplejson.errors.JSONDecodeError
                # using Exception since simplejson is not imported
                util.log_msg(traceback.format_exc(),
                             mode=util.BOTH_LOG,
                             func_name=1)
                util.log_msg("%s: exception during refresh_zone_info, "
                             "on trial %s of %s, probably a"
                             " connection issue%s" %
                             (time_now, trial_number, number_of_retries,
                              ["",
                               ", waiting %s seconds and then retrying..." %
                               retry_delay_sec]
                              [trial_number < number_of_retries]),
                             mode=util.BOTH_LOG, func_name=1)
                if trial_number < number_of_retries:
                    time.sleep(retry_delay_sec)
                trial_number += 1
            else:
                # log the mitigated failure
                if trial_number > 1:
                    email_notification.send_email_alert(
                        subject=("intermittent JSON decode error "
                                 "during refresh zone"),
                        body="%s: trial %s of %s at %s" %
                        (util.get_function_name(), trial_number,
                         number_of_retries, time_now))
                for zone_data in all_zones_info:
                    if zone_data['DeviceID'] == self.device_id:
                        pyhtcc.logger.debug(f"Refreshed zone info for \
                                           {self.device_id}")
                        self.zone_info = zone_data
                        self.last_fetch_time = time.time()
                        return

        # log fatal failure
        email_notification.send_email_alert(
            subject=("fatal JSON decode error during refresh zone"),
            body="{}: trial {} of {} at {}".format(util.get_function_name(),
                                                   trial_number,
                                                   number_of_retries,
                                                   time_now))
        raise pyhtcc.ZoneNotFoundError(f"Missing device: {self.device_id}")


# add default requests session default timeout to prevent TimeoutExceptions
# see ticket #93 for details
# pylint: disable=wrong-import-order,wrong-import-position
from requests.adapters import HTTPAdapter  # noqa E402

# network timeout limit
# 6s upper is 1.9 on pi4 and laptop
# 6s upper is 2.17 on Azure pipeline
HTTP_TIMEOUT = 2.5  # 6 sigma limit in seconds


class TimeoutHTTPAdapter(HTTPAdapter):
    """Override TimeoutHTTPAdapter to include timeout parameter.
    """
    def __init__(self, *args, **kwargs):
        self.timeout = HTTP_TIMEOUT
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):  # pylint: disable=arguments-differ
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)


if __name__ == "__main__":

    # verify environment
    util.get_python_version()

    # get zone override
    zone_number = api.parse_all_runtime_parameters()["zone"]

    _, Zone = tc.thermostat_basic_checkout(
        api, honeywell_config.ALIAS,
        zone_number,
        ThermostatClass, ThermostatZone)

    # measure thermostat response time
    MEASUREMENTS = 30
    print(f"Thermostat response times for {MEASUREMENTS} measurements...")
    meas_data = Zone.measure_thermostat_response_time(
        MEASUREMENTS, func=Zone.pyhtcc.get_zones_info)
    ppp = pprint.PrettyPrinter(indent=4)
    ppp.pprint(meas_data)