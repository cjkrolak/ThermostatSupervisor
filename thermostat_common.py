"""
Common Thermostat Class
"""
# built-ins
import datetime
import operator
import time
import statistics

# local imports
import email_notification
import utilities as util


degree_sign = u"\N{DEGREE SIGN}"


class ThermostatCommon():
    """Class methods common to all thermostat objects."""

    def __init__(self, *_, **__):
        self.thermostat_type = "unknown"  # placeholder
        self.zone_number = util.bogus_int  # placeholder
        self.device_id = util.bogus_int  # placeholder
        self.ip_address = None  # placeholder

    def print_all_thermostat_metadata(self):
        """
        Print initial meta data queried from thermostat.

        inputs:
            None
        returns:
            None
        """
        util.log_msg("WARNING: print_all_thermostat_metatdata() not yet "
                     "implemented for this thermostat type\n",
                     mode=util.BOTH_LOG, func_name=1)


class ThermostatCommonZone():
    """Class methods common to all thermostat zones."""

    OFF_MODE = "OFF_MODE"
    HEAT_MODE = "HEAT_MODE"
    COOL_MODE = "COOL_MODE"
    AUTO_MODE = "AUTO_MODE"
    DRY_MODE = "DRY_MODE"
    UNKNOWN_MODE = "UNKNOWN_MODE"

    system_switch_position = {
        # placeholder, will be tstat-specific
        HEAT_MODE: util.bogus_int - 1,
        OFF_MODE: util.bogus_int - 2,
        COOL_MODE: util.bogus_int - 3,
        AUTO_MODE: util.bogus_int - 4,
        DRY_MODE: util.bogus_int - 5,
        UNKNOWN_MODE: util.bogus_int - 6,
        }
    max_scheduled_heat_allowed = 74  # warn if scheduled heat value exceeds.
    min_scheduled_cool_allowed = 68  # warn if scheduled cool value exceeds.
    tolerance_degrees_default = 2  # allowed override vs. the scheduled value.

    def __init__(self, *_, **__):
        self.thermostat_type = "unknown"  # placeholder
        self.zone_number = util.bogus_int  # placeholder
        self.device_id = util.bogus_int  # placeholder
        self.poll_time_sec = util.bogus_int  # placeholder
        self.connection_time_sec = util.bogus_int  # placeholder
        self.tolerance_degrees = self.tolerance_degrees_default
        self.current_mode = None  # placeholder

    def get_current_mode(self, session_count, poll_count, print_status=True,
                         flag_all_deviations=False):
        """
        Determine whether thermostat is following schedule or if it has been
        deviated from schedule.

        inputs:
            session_count(int): session number (connection #) for reporting
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
        cool_deviation = util.bogus_bool  # cool set point deviates from sched
        heat_deviation = util.bogus_bool  # heat set point deviates from sched
        hold_mode = util.bogus_bool  # True if not following schedule
        heat_schedule_point = util.bogus_int  # heating schedule set point
        heat_set_point = util.bogus_int  # heating current set point
        cool_schedule_point = util.bogus_int  # cooling schedule set point
        cool_set_point = util.bogus_int  # cooling current set point
        mode = "OFF MODE"  # mode for display, "OFF MODE", "HEAT MODE",
        #                    "COOL MODE"
        hold_temporary = util.bogus_bool  # True if hold will revert on next
        #                              schedule event

        if flag_all_deviations:
            cool_operator = operator.ne
            heat_operator = operator.ne
            self.tolerance_degrees = 0  # disable tolerance
        else:
            cool_operator = operator.lt
            heat_operator = operator.gt

        return_buffer = {
            "heat_mode": util.bogus_bool,  # in heating mode
            "cool_mode": util.bogus_bool,  # in cooling mode
            "heat_deviation": util.bogus_bool,  # True: heat is deviated above
            "cool_deviation": util.bogus_bool,  # True: cool is deviated below
            "hold_mode": util.bogus_bool,  # True if hold is enabled
            "status_msg": "",  # status message
            }

        print("DEBUG: %s entrypoint (switch position=%s)" %
              (util.get_function_name(),
               self.get_system_switch_position()))
        # current temperature
        display_temp = self.validate_numeric(self.get_display_temp(),
                                             "get_display_temp")

        # current humidity
        display_humidity = self.get_display_humidity()
        humidity_is_available = self.get_is_humidity_supported()

        # check for heat deviation
        if self.is_heat_mode():
            mode = "HEAT MODE"
            # cast integers just in case a set point returns a float
            heat_set_point = int(self.get_heat_setpoint_raw())
            heat_schedule_point = int(self.get_schedule_heat_sp())
            if heat_operator(heat_set_point, heat_schedule_point +
                             self.tolerance_degrees):
                status_msg = ("[heat deviation] act temp=%.1f%sF" %
                              (display_temp, degree_sign))
                # add humidity if available
                if humidity_is_available:
                    status_msg += ", act humidity=%.1f%% RH" % display_humidity
                # add setpoint and override point
                status_msg += (", set point=%s, tolerance=%s, override=%s" %
                               (heat_schedule_point,
                                self.tolerance_degrees, heat_set_point))
                heat_deviation = True

            # warning email if heat set point is above global max value
            self.warn_if_outside_global_limit(heat_schedule_point,
                                              self.max_scheduled_heat_allowed,
                                              operator.gt, "heat")

        # check for cool deviation
        if self.is_cool_mode():
            mode = "COOL MODE"
            # cast integers just in case a set point returns a float
            cool_set_point = int(self.get_cool_setpoint_raw())
            cool_schedule_point = int(self.get_schedule_cool_sp())
            if cool_operator(cool_set_point, cool_schedule_point -
                             self.tolerance_degrees):
                status_msg = ("[cool deviation] act temp=%.1f%sF" %
                              (display_temp, degree_sign))
                # add humidity if available
                if humidity_is_available:
                    status_msg += ", act humidity=%.1f%% RH" % display_humidity
                # add setpoint and override point
                status_msg += (", set point=%s, tolerance=%s, override=%s" %
                               (cool_schedule_point,
                                self.tolerance_degrees, cool_set_point))
                cool_deviation = True

            # warning email if cool set point is below global min value
            self.warn_if_outside_global_limit(cool_schedule_point,
                                              self.min_scheduled_cool_allowed,
                                              operator.lt, "cool")

        # persistent or temporary deviation detected.
        if heat_deviation or cool_deviation:
            # print("DEBUG: in vacation hold=%s" %
            #       self.get_is_invacation_hold_mode())
            # print("DEBUG: hold time=%s" %
            #       self.get_temporary_hold_until_time())
            hold_mode = True  # True = not following schedule
            # TCC:
            #   get_is_in_vacation_hold_mode(): always 0 for TCC
            #   get_temporary_hold_until_time(): > 0 for temp hold
            #                                   == 0 for perm hold
            # 3m50:
            #   get_is_in_vacation_hold_mode(): need to verify
            #   get_temporary_hold_until_time(): need to verify
            hold_temporary = (self.get_temporary_hold_until_time() > 0)
            # or not self.get_is_invacation_hold_mode())
            status_msg += (" (%s)" % ["persistent",
                                      "temporary"][hold_temporary])
        else:
            status_msg = ("[following schedule] act temp=%.1f%sF" %
                          (display_temp, degree_sign))
            # add humidity if available
            if humidity_is_available:
                status_msg += ", act humidity=%.1f%% RH" % display_humidity
            # add setpoints if in heat or cool mode
            if self.is_heat_mode():
                status_msg += (", set point=%s, tolerance=%s, override=%s" %
                               (heat_schedule_point,
                                self.tolerance_degrees, heat_set_point))
            elif self.is_cool_mode():
                status_msg += (", set point=%s, tolerance=%s, override=%s" %
                               (cool_schedule_point,
                                self.tolerance_degrees, cool_set_point))

        full_status_msg = ("%s: (session:%s, poll:%s) %s %s" %
                           (datetime.datetime.now().
                            strftime("%Y-%m-%d %H:%M:%S"),
                            session_count, poll_count, mode, status_msg))
        if print_status:
            util.log_msg(full_status_msg, mode=util.BOTH_LOG)

        self.store_current_mode()

        # return status
        return_buffer["heat_mode"] = self.is_heat_mode()
        return_buffer["cool_mode"] = self.is_cool_mode()
        return_buffer["heat_deviation"] = heat_deviation
        return_buffer["cool_deviation"] = cool_deviation
        return_buffer["hold_mode"] = hold_mode
        return_buffer["status_msg"] = full_status_msg
        return return_buffer

    def set_mode(self, target_mode):
        """
        Set the thermostat mode.

        inputs:
            target_mode(str):  target mode
        returns:
            True if successful, else False
        """
        print("DEBUG in set_mode, target_mode=%s, doing nothing" % target_mode)
        return False

    def store_current_mode(self):
        """Save the current mode to cache."""
        if self.is_heat_mode():
            self.current_mode = self.HEAT_MODE
        elif self.is_cool_mode():
            self.current_mode = self.COOL_MODE
        elif self.is_dry_mode():
            self.current_mode = self.DRY_MODE
        elif self.is_auto_mode():
            self.current_mode = self.AUTO_MODE
        else:
            self.current_mode = self.OFF_MODE

    def validate_numeric(self, input_val, parameter_name):
        """
        Validate value returned is numeric, otherwise raise exception.

        inputs:
            input_val: input value of unknown type.
            parameter_name(str): parameter name.
        returns:
            (int, float): pass thru value if numeric, else raise exception.
        """
        if not isinstance(input_val, (int, float)):
            raise TypeError("value returned for parameter '%s' is type %s, "
                            "expected int or float" %
                            (parameter_name, type(input_val)))
        return input_val

    def warn_if_outside_global_limit(self, setpoint, limit_value, oper, label):
        """
        Send warning email if setpoint is outside of global limits.

        inputs:
            setpoint(int): setpoint value.
            limit_value(int): the limit value
            oper(operator):  the operator, either operator.gt or operator.lt
            label(str): label for warning message denoting the mode
        returns:
            (bool): result of check
        """
        if oper == operator.gt:  # pylint: disable=W0143
            level = "above max"
        else:
            level = "below min"
        if oper(setpoint, limit_value):
            msg = ("%s zone %s: scheduled %s set point (%s) is "
                   "%s limit (%s)" % (
                       self.thermostat_type, self.zone_number, label,
                       setpoint, level, limit_value))
            util.log_msg("WARNING: %s" % msg, mode=util.BOTH_LOG)
            email_notification.send_email_alert(
                    subject=msg,
                    body="%s: %s" % (util.get_function_name(), msg))
            return True
        else:
            return False

    def get_heat_mode(self):
        """Return 1 if heat mode enabled, else 0."""
        return util.bogus_int

    def get_cool_mode(self):
        """Return 1 if cool mode enabled, else 0."""
        return util.bogus_int

    def get_dry_mode(self):
        """Return 1 if dry mode enabled, else 0."""
        return util.bogus_int

    def is_heat_mode(self):
        """Return True if in heat mode."""
        return (self.get_system_switch_position() ==
                self.system_switch_position[self.HEAT_MODE])

    def is_cool_mode(self):
        """Return True if in cool mode."""
        return (self.get_system_switch_position() ==
                self.system_switch_position[self.COOL_MODE])

    def is_dry_mode(self):
        """Return True if in dry mode."""
        return (self.get_system_switch_position() ==
                self.system_switch_position[self.DRY_MODE])

    def is_auto_mode(self):
        """Return True if in auto mode."""
        return (self.get_system_switch_position() ==
                self.system_switch_position[self.AUTO_MODE])

    # Thermostat-specific methods will be overloaded
    def get_display_temp(self) -> float:
        """Return the displayed temperature."""
        return float(util.bogus_int)  # placeholder

    def get_display_humidity(self) -> float:
        """Return the displayed humidity."""
        return float(util.bogus_int)  # placeholder

    def get_is_humidity_supported(self) -> bool:
        """Return humidity sensor status."""
        return util.bogus_bool  # placeholder

    def get_system_switch_position(self) -> int:
        """Return the 'SystemSwitchPosition'
            'SystemSwitchPosition' = 1 for heat, 2 for off
        """
        return util.bogus_int  # placeholder

    def get_heat_setpoint_raw(self) -> int:
        """Return raw heat set point(number only, no units)."""
        return util.bogus_int  # placeholder

    def get_heat_setpoint(self) -> int:
        """Return raw heat set point(number and units)."""
        return util.bogus_int  # placeholder

    def get_schedule_program_heat(self) -> dict:
        """
        Return the heat setpoint schedule.

        inputs:
            None
        returns:
            (dict): scheduled heat set points and times in degrees.
        """
        return util.bogus_dict  # placeholder

    def get_schedule_heat_sp(self) -> int:
        """Return the heat setpoint."""
        if self.thermostat_type == "UNITTEST":
            # unit test mode, return global min
            return self.max_scheduled_heat_allowed
        else:
            return util.bogus_int  # placeholder

    def get_cool_setpoint_raw(self) -> int:
        """Return raw cool set point (number only, no units)."""
        return util.bogus_int  # placeholder

    def get_cool_setpoint(self) -> int:
        """Return raw cool set point (number and units)."""
        return util.bogus_int  # placeholder

    def get_schedule_program_cool(self) -> dict:
        """
        Return the cool setpoint schedule.

        inputs:
            None
        returns:
            (dict): scheduled cool set points and times in degrees.
        """
        return util.bogus_dict  # placeholder

    def get_schedule_cool_sp(self) -> int:
        """Return the cool setpoint."""
        if self.thermostat_type == "UNITTEST":
            # unit test mode, return global min
            return self.min_scheduled_cool_allowed
        else:
            return util.bogus_int  # placeholder

    def get_vacation_hold(self) -> bool:
        """Return True if thermostat is in vacation hold mode."""
        return util.bogus_bool  # placeholder

    def get_is_invacation_hold_mode(self) -> bool:
        """Return the 'IsInVacationHoldMode' setting."""
        return util.bogus_bool  # placeholder

    def get_temporary_hold_until_time(self) -> int:
        """Return the 'TemporaryHoldUntilTime' """
        return util.bogus_int  # placeholder

    def refresh_zone_info(self, force_refresh=False) -> None:
        """
        Refresh zone info.

        inputs:
            force_refresh(bool): if True, ignore expiration timer.
        returns:
            None, cached data is refreshed.
        """
        del force_refresh  # not used in this template.
        return  # placeholder

    def report_heating_parameters(self):
        """Display critical thermostat settings and reading to the screen."""
        return  # placeholder

    def get_vacation_hold_until_time(self) -> int:
        """
        Return the 'VacationHoldUntilTime'.

        inputs:
            None
        returns:
            (int): vacation hold time in minutes.
         """
        return util.bogus_int  # not implemented

    def update_runtime_parameters(self, user_inputs):
        """use runtime parameter overrides.

        inputs:
            user_inputs(dict): runtime overrides.
        returns:
            None, updates class variables.
        """
        # map user input keys to class methods
        # "thermostat_type is not overwritten
        user_input_to_class_mapping = {
            "thermostat_type": "thermostat_type",
            "zone": "zone_number",
            "poll_time_sec": "poll_time_sec",
            "connection_time_sec": "connection_time_sec",
            "tolerance_degrees": "tolerance_degrees",
            "target_mode": "target_mode",
            }

        for inp, cls_method in user_input_to_class_mapping.items():
            user_input = user_inputs.get(inp)
            if user_input is not None:
                setattr(self, cls_method, user_input)
                util.log_msg("%s=%s" % (inp, user_input),
                             mode=util.BOTH_LOG, func_name=1)

    def verify_current_mode(self, target_mode):
        """
        Verify current mode matches target mode.

        inputs:
            target_mode(str): target mode override
        returns:
            (bool): True if current mode matches target mode,
                    or target mode is not specified.
        """
        if target_mode is None:
            return True
        else:
            if self.current_mode == target_mode:
                return True
            else:
                return False

    def revert_thermostat_mode(self, target_mode):
        """
        Revert thermostat mode to target mode.

        inputs:
            target_mode(str): target mode override
        returns:
            target_mode(str) target_mode, which may get updated by
            this function.
        """
        heat_modes = [self.HEAT_MODE, self.AUTO_MODE]
        cool_modes = [self.COOL_MODE, self.DRY_MODE, self.AUTO_MODE]
        # do not switch directly from hot to cold
        if (self.current_mode in heat_modes and target_mode in cool_modes):
            util.log_msg("WARNING: target mode=%s, switching from %s mode to "
                         "OFF_MODE to prevent damage to HVAC" %
                         (target_mode, self.current_mode),
                         mode=util.BOTH_LOG, func_name=1)
            target_mode = self.OFF_MODE

        # do not switch directly from cold to hot
        elif (self.current_mode in cool_modes and target_mode in heat_modes):
            util.log_msg("WARNING: target mode=%s, switching from %s mode to "
                         "OFF_MODE to prevent damage to HVAC" %
                         (target_mode, self.current_mode),
                         mode=util.BOTH_LOG, func_name=1)
            target_mode = self.OFF_MODE

        # revert the mode to target
        self.set_mode(target_mode)

        return target_mode

    def measure_thermostat_response_time(self, measurements=30):
        """
        Measure Thermostat response time and report statistics.

        inputs:
            measurements(int): number of measurements
        returns:
            (dict): measurement statistics.
        """
        delta_lst = []
        stats = {}
        for n in range(measurements):
            t0 = time.time()
            self.get_schedule_heat_sp()  # arbitrary command
            t1 = time.time()

            # accumulate stats
            tdelta = t1 - t0
            delta_lst.append(tdelta)
            util.log_msg("measurement %s=%.1f seconds" % (n, tdelta),
                         mode=util.BOTH_LOG, func_name=1)

        # calc stats
        stats["measurements"] = measurements
        stats["mean"] = round(statistics.mean(delta_lst), 1)
        stats["stdev"] = round(statistics.stdev(delta_lst), 1)
        stats["min"] = round(min(delta_lst), 1)
        stats["max"] = round(max(delta_lst), 1)
        stats["3sigma_upper"] = round((3.0 * stats["stdev"] +
                                      stats["mean"]), 1)
        stats["6sigma_upper"] = round((6.0 * stats["stdev"] +
                                       stats["mean"]), 1)
        return stats

    def _c_to_f(self, tempc) -> float:
        """
        Convert from Celsius to Fahrenheit.

        inputs:
            tempc(int, float): temp in deg c.
        returns:
            (float): temp in deg f.
        """
        if isinstance(tempc, (int, float)):
            return tempc * 9.0 / 5 + 32
        else:
            return tempc  # pass-thru

    def _f_to_c(self, tempf) -> float:
        """
        Convert from Fahrenheit to Celsius.

        inputs:
            tempc(int, float): temp in deg f.
        returns:
            (float): temp in deg c.
        """
        if isinstance(tempf, (int, float)):
            return (tempf - 32) * 5 / 9.0
        else:
            return tempf  # pass-thru

    def display_basic_thermostat_summary(self, mode=util.CONSOLE_LOG):
        """
        Display basic thermostat summary.

        inputs:
            mode(int): target log for data.
        returns:
            None, prints data to log and/or console.
        """
        util.log_msg("current thermostat settings...",
                     mode=mode, func_name=1)
        util.log_msg("system switch position: %s (%s)" %
                     (self.get_system_switch_position(),
                      util.get_key_from_value(
                          self.system_switch_position,
                          self.get_system_switch_position())),
                     mode=mode, func_name=1)
        util.log_msg("thermostat display temp=%s" %
                     util.temp_value_with_units(self.get_display_temp()),
                     mode=mode, func_name=1)
        util.log_msg("thermostat display humidity=%s RH" %
                     self.get_display_humidity(),
                     mode=mode, func_name=1)
        util.log_msg("heat set point=%s" % self.get_heat_setpoint(),
                     mode=mode, func_name=1)
        util.log_msg("cool set point=%s" % self.get_cool_setpoint(),
                     mode=mode, func_name=1)
        util.log_msg("heat schedule set point=%s" %
                     self.get_schedule_heat_sp(), mode=mode, func_name=1)
        util.log_msg("cool schedule set point=%s" %
                     self.get_schedule_cool_sp(), mode=mode, func_name=1)
        util.log_msg("(schedule) heat program=%s" %
                     self.get_schedule_program_heat(),
                     mode=mode, func_name=1)
        util.log_msg("(schedule) cool program=%s" %
                     self.get_schedule_program_cool(),
                     mode=mode, func_name=1)
        util.log_msg("heat mode=%s" % self.get_heat_mode(),
                     mode=mode, func_name=1)
        util.log_msg("cool mode=%s" % self.get_cool_mode(),
                     mode=mode, func_name=1)
        util.log_msg("dry mode=%s" % self.get_dry_mode(),
                     mode=mode, func_name=1)
        util.log_msg("hold=%s" % self.get_vacation_hold(),
                     mode=mode, func_name=1)
        util.log_msg("temporary hold minutes=%s" %
                     self.get_temporary_hold_until_time(),
                     mode=mode, func_name=1)
