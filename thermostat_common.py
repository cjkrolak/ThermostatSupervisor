"""
Common Thermostat Class
"""
# built-ins
import datetime
import operator
import time
import statistics

# local imports
import email_notification as eml
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

    # supported thermostat modes
    OFF_MODE = "off"
    HEAT_MODE = "heat"
    COOL_MODE = "cool"
    AUTO_MODE = "auto"
    DRY_MODE = "dry"
    FAN_MODE = "fan"
    UNKNOWN_MODE = "unknown"

    # modes where heat is applied
    heat_modes = [HEAT_MODE, AUTO_MODE]

    # modes where cooling is applied
    cool_modes = [COOL_MODE, DRY_MODE, AUTO_MODE]

    # modes in which setpoints apply
    controlled_modes = [HEAT_MODE, AUTO_MODE, COOL_MODE]

    system_switch_position = {
        # placeholder, will be tstat-specific
        UNKNOWN_MODE: util.bogus_int,
        HEAT_MODE: util.bogus_int - 1,
        COOL_MODE: util.bogus_int - 2,
        AUTO_MODE: util.bogus_int - 3,
        DRY_MODE: util.bogus_int - 4,
        FAN_MODE: util.bogus_int - 5,
        OFF_MODE: util.bogus_int - 6,
        }
    max_scheduled_heat_allowed = 74  # warn if scheduled heat value exceeds.
    min_scheduled_cool_allowed = 68  # warn if scheduled cool value exceeds.
    tolerance_degrees_default = 2  # allowed override vs. the scheduled value.

    def __init__(self, *_, **__):
        self.thermostat_type = "unknown"  # placeholder
        self.zone_number = util.bogus_int  # placeholder
        self.zone_name = None  # placeholder
        self.device_id = util.bogus_int  # placeholder
        self.poll_time_sec = util.bogus_int  # placeholder
        self.connection_time_sec = util.bogus_int  # placeholder
        self.flag_all_deviations = False  #
        self.temperature_is_deviated = False  # temp deviated from schedule
        self.display_temp = None  # current temperature in deg F
        self.display_humidity = None  # current humidity in %RH
        self.humidity_is_available = False  # humidity supported flag
        self.hold_mode = False  # True = not following schedule
        self.hold_temporary = False

        # abstraction vars and funcs, defined in query_thermostat_zone
        self.current_mode = None  # integer representing mode
        self.current_setpoint = util.bogus_int  # current setpoint
        self.schedule_setpoint = util.bogus_int  # current scheduled setpoint
        self.tolerance_sign = 1  # +1 for heat, -1 for cool
        self.operator = operator.ne  # operator for deviation check
        self.tolerance_degrees = self.tolerance_degrees_default
        self.global_limit = util.bogus_int  # global temp limit
        self.global_operator = operator.ne  # oper for global temp deviation
        self.revert_setpoint_func = self.function_not_supported
        self.get_setpoint_func = self.function_not_supported

    def query_thermostat_zone(self):
        """Return the current mode and set mode-specific parameters."""

        # current temperature
        self.display_temp = self.validate_numeric(self.get_display_temp(),
                                                  "get_display_temp")

        # current humidity
        self.display_humidity = self.get_display_humidity()
        self.humidity_is_available = self.get_is_humidity_supported()

        # mode-specific parameters
        if self.is_heat_mode():
            self.current_mode = self.HEAT_MODE
            self.current_setpoint = int(self.get_heat_setpoint_raw())
            self.schedule_setpoint = int(self.get_schedule_heat_sp())
            self.tolerance_sign = 1
            if self.flag_all_deviations:
                self.operator = operator.ne
                self.tolerance_degrees = 0  # disable tolerance
            else:
                self.operator = operator.gt
            self.global_limit = self.max_scheduled_heat_allowed
            self.global_operator = operator.gt
            self.revert_setpoint_func = self.set_heat_setpoint
            self.get_setpoint_func = self.get_heat_setpoint_raw
        elif self.is_cool_mode():
            self.current_mode = self.COOL_MODE
            self.current_setpoint = int(self.get_cool_setpoint_raw())
            self.schedule_setpoint = int(self.get_schedule_cool_sp())
            self.tolerance_sign = -1
            if self.flag_all_deviations:
                self.operator = operator.ne
                self.tolerance_degrees = 0  # disable tolerance
            else:
                self.operator = operator.lt
            self.global_limit = self.min_scheduled_cool_allowed
            self.global_operator = operator.lt
            self.revert_setpoint_func = self.set_cool_setpoint
            self.get_setpoint_func = self.get_cool_setpoint_raw
        elif self.is_dry_mode():
            self.current_mode = self.DRY_MODE
            self.current_setpoint = int(self.get_cool_setpoint_raw())
            self.schedule_setpoint = int(self.get_schedule_cool_sp())
            self.tolerance_sign = -1
            if self.flag_all_deviations:
                self.operator = operator.ne
                self.tolerance_degrees = 0  # disable tolerance
            else:
                self.operator = operator.lt
            self.global_limit = self.min_scheduled_cool_allowed
            self.global_operator = operator.lt
            self.revert_setpoint_func = self.function_not_supported
            self.get_setpoint_func = self.function_not_supported
        elif self.is_auto_mode():
            self.current_mode = self.AUTO_MODE
            self.current_setpoint = util.bogus_int
            self.schedule_setpoint = util.bogus_int
            self.tolerance_sign = 1
            self.operator = operator.ne
            self.global_limit = util.bogus_int
            self.global_operator = operator.ne
            self.revert_setpoint_func = self.function_not_supported
            self.get_setpoint_func = self.function_not_supported
        elif self.is_fan_mode():
            self.current_mode = self.FAN_MODE
            self.current_setpoint = util.bogus_int
            self.schedule_setpoint = util.bogus_int
            self.tolerance_sign = 1
            self.operator = operator.ne
            self.global_limit = util.bogus_int
            self.global_operator = operator.ne
            self.revert_setpoint_func = self.function_not_supported
            self.get_setpoint_func = self.function_not_supported
        elif self.is_off_mode():
            self.current_mode = self.OFF_MODE
            self.current_setpoint = util.bogus_int
            self.schedule_setpoint = util.bogus_int
            self.tolerance_sign = 1
            self.operator = operator.ne
            self.global_limit = util.bogus_int
            self.global_operator = operator.ne
            self.revert_setpoint_func = self.function_not_supported
            self.get_setpoint_func = self.function_not_supported
        else:
            raise ValueError("unknown thermostat mode")

        self.temperature_is_deviated = self.is_temp_deviated_from_schedule()

    def is_temp_deviated_from_schedule(self):
        """
        Return True if temperature is deviated from current schedule.

        inputs:
            None:
        returns:
            (bool): True if temp is deviated from schedule.
        """
        return self.operator(self.current_setpoint, self.schedule_setpoint
                             + self.tolerance_sign
                             * self.tolerance_degrees)

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

        return_buffer = {
            "heat_mode": util.bogus_bool,  # in heating mode
            "cool_mode": util.bogus_bool,  # in cooling mode
            "heat_deviation": util.bogus_bool,  # True: heat is deviated above
            "cool_deviation": util.bogus_bool,  # True: cool is deviated below
            "hold_mode": util.bogus_bool,  # True if hold is enabled
            "status_msg": "",  # status message
            }

        self.flag_all_deviations = flag_all_deviations
        self.query_thermostat_zone()

        # warning email if set point is outside global limit
        self.warn_if_outside_global_limit(self.current_setpoint,
                                          self.global_limit,
                                          self.global_operator,
                                          self.current_mode)

        if self.is_temp_deviated_from_schedule() and self.is_controlled_mode():
            status_msg = ("[%s_MODE deviation] act temp=%s" %
                          (self.current_mode.upper(),
                           util.temp_value_with_units(self.display_temp)))
        else:
            status_msg = ("[following schedule] act temp=%s" %
                          util.temp_value_with_units(
                              self.display_temp))

        # add humidity if available
        if self.humidity_is_available:
            status_msg += (", act humidity=%s" %
                           util.humidity_value_with_units(
                               self.display_humidity))

        # add hold information
        if self.is_temp_deviated_from_schedule() and self.is_controlled_mode():
            self.hold_mode = True  # True = not following schedule
            self.hold_temporary = (self.get_temporary_hold_until_time() > 0)
            status_msg += (" (%s)" % ["persistent",
                                      "temporary"][self.hold_temporary])
        else:
            self.hold_mode = False
            self.hold_temporary = False

        # add setpoints if in heat or cool mode
        if self.is_heat_mode() or self.is_cool_mode():
            status_msg += (", set point=%s, tolerance=%s, override=%s" %
                           (util.temp_value_with_units(self.schedule_setpoint),
                            util.temp_value_with_units(self.tolerance_degrees),
                            util.temp_value_with_units(self.current_setpoint)))

        full_status_msg = ("%s: (session:%s, poll:%s) %s_MODE %s" %
                           (datetime.datetime.now().
                            strftime("%Y-%m-%d %H:%M:%S"),
                            session_count, poll_count,
                            self.current_mode.upper(),
                            status_msg))
        if print_status:
            util.log_msg(full_status_msg, mode=util.BOTH_LOG)

        self.store_current_mode()

        # return status
        return_buffer["heat_mode"] = self.is_heat_mode()
        return_buffer["cool_mode"] = self.is_cool_mode()
        return_buffer["heat_deviation"] = self.is_heat_deviation()
        return_buffer["cool_deviation"] = self.is_cool_deviation()
        return_buffer["hold_mode"] = self.hold_mode
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
        elif self.is_fan_mode():
            self.current_mode = self.FAN_MODE
        elif self.is_off_mode():
            self.current_mode = self.OFF_MODE
        else:
            raise ValueError("unknown thermostat mode")
        print("DEBUG: self.current_mode=%s" % self.current_mode)

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
            msg = ("%s zone %s: scheduled %s_MODE set point (%s) is "
                   "%s limit (%s)" % (
                       self.thermostat_type, self.zone_number, label.upper(),
                       util.temp_value_with_units(setpoint), level,
                       util.temp_value_with_units(limit_value)))
            util.log_msg("WARNING: %s" % msg, mode=util.BOTH_LOG)
            eml.send_email_alert(
                    subject=msg,
                    body="%s: %s" % (util.get_function_name(), msg))
            return True
        else:
            return False

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

    def is_fan_mode(self):
        """Return 1 if fan mode enabled, else 0."""
        return (self.get_system_switch_position() ==
                self.system_switch_position[self.FAN_MODE])

    def is_off_mode(self):
        """Return 1 if fan mode enabled, else 0."""
        return (self.get_system_switch_position() ==
                self.system_switch_position[self.OFF_MODE])

    def is_controlled_mode(self):
        """Return True if mode is being controlled."""
        return self.current_mode in self.controlled_modes

    def is_heating(self):
        """Return 1 if heating relay is active, else 0."""
        return util.bogus_int

    def is_cooling(self):
        """Return 1 if cooling relay is active, else 0."""
        return util.bogus_int

    def is_drying(self):
        """Return 1 if drying relay is active, else 0."""
        return util.bogus_int

    def is_auto(self):
        """Return 1 if auto relay is active, else 0."""
        return util.bogus_int

    def is_fanning(self):
        """Return 1 if fan relay is active, else 0."""
        return util.bogus_int

    def set_heat_setpoint(self, temp: int) -> None:
        """
        Set a new heat setpoint.

        This will also attempt to turn the thermostat to 'Cool'
        inputs:
            temp(int): desired temperature in deg F.
        returns:
            None
        """
        del temp
        util.log_msg("WARNING: %s: function is not yet implemented on this "
                     "thermostat, doing nothing" %
                     util.get_function_name(), mode=util.BOTH_LOG,
                     func_name=1)
        return

    def set_cool_setpoint(self, temp: int) -> None:
        """
        Set a new cool setpoint.

        This will also attempt to turn the thermostat to 'Cool'
        inputs:
            temp(int): desired temperature in deg F.
        returns:
            None
        """
        del temp
        util.log_msg("WARNING: %s: function is not yet implemented on this "
                     "thermostat, doing nothing" %
                     util.get_function_name(), mode=util.BOTH_LOG,
                     func_name=1)
        return

    def is_heat_deviation(self):
        """
        Return True if heat is deviated.

        inputs:
            None
        returns:
            (bool): True if deviation exists.
        """
        return self.is_heat_mode() and self.is_temp_deviated_from_schedule()

    def is_cool_deviation(self):
        """
        Return True if cool is deviated.

        inputs:
            None
        returns:
            (bool): True if deviation exists.
        """
        return self.is_cool_mode() and self.is_temp_deviated_from_schedule()

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

    def report_heating_parameters(self, switch_position=None):
        """
        Display critical thermostat settings and reading to the screen.

        inputs:
            switch_position(int): switch position override for testing.
        returns:
            None
        """
        del switch_position
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
            "measurements": "measurements",
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
        # do not switch directly from hot to cold
        if (self.current_mode in self.heat_modes and
                target_mode in self.cool_modes):
            util.log_msg("WARNING: target mode=%s, switching from %s mode to "
                         "OFF_MODE to prevent damage to HVAC" %
                         (target_mode, self.current_mode),
                         mode=util.BOTH_LOG, func_name=1)
            target_mode = self.OFF_MODE

        # do not switch directly from cold to hot
        elif (self.current_mode in self.cool_modes and
              target_mode in self.heat_modes):
            util.log_msg("WARNING: target mode=%s, switching from %s mode to "
                         "OFF_MODE to prevent damage to HVAC" %
                         (target_mode, self.current_mode),
                         mode=util.BOTH_LOG, func_name=1)
            target_mode = self.OFF_MODE

        # revert the mode to target
        self.set_mode(target_mode)

        return target_mode

    def measure_thermostat_response_time(self, measurements=30,
                                         func=None):
        """
        Measure Thermostat response time and report statistics.

        inputs:
            measurements(int): number of measurements
            func(obj): target function to run during timing measurement.
        returns:
            (dict): measurement statistics.
        """
        delta_lst = []
        stats = {}
        # set default measurement method if not provided.
        if func is None:
            func = self.get_schedule_heat_sp

        # measurement loop
        for n in range(measurements):
            t0 = time.time()
            func()  # target command
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
        util.log_msg("zone name='%s'" % self.zone_name,
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
        util.log_msg("heat mode=%s (actively heating=%s)" %
                     (self.is_heat_mode(), self.is_heating()),
                     mode=mode, func_name=1)
        util.log_msg("cool mode=%s (actively cooling=%s)" %
                     (self.is_cool_mode(), self.is_cooling()),
                     mode=mode, func_name=1)
        util.log_msg("dry mode=%s (actively drying=%s)" %
                     (self.is_dry_mode(), self.is_drying()),
                     mode=mode, func_name=1)
        util.log_msg("auto mode=%s (actively auto=%s)" %
                     (self.is_auto_mode(), self.is_auto()),
                     mode=mode, func_name=1)
        util.log_msg("fan mode=%s (actively fanning=%s)" %
                     (self.is_fan_mode(), self.is_fanning()),
                     mode=mode, func_name=1)
        util.log_msg("off mode=%s" % self.is_off_mode(),
                     mode=mode, func_name=1)
        util.log_msg("hold=%s" % self.get_vacation_hold(),
                     mode=mode, func_name=1)
        util.log_msg("temporary hold minutes=%s" %
                     self.get_temporary_hold_until_time(),
                     mode=mode, func_name=1)

    def revert_temperature_deviation(self, setpoint=None, msg=""):
        """
        Revert the temperature deviation.

        inputs:
            setpoint(int or float): setpoint in deg F
            msg(str): status message to display.
        returns:
            None
        """
        if setpoint is None:
            setpoint = self.current_setpoint

        eml.send_email_alert(
            subject=("%s %s_MODE deviation alert on zone %s" %
                     (self.thermostat_type, self.current_mode.upper(),
                      self.zone_number)),
            body=msg)
        util.log_msg("\n*** %s %s_MODE deviation detected on zone %s,"
                     " reverting thermostat to heat schedule ***\n" %
                     (self.thermostat_type, self.current_mode.upper(),
                      self.zone_number), mode=util.BOTH_LOG)
        self.revert_setpoint_func(setpoint)

    def function_not_supported(self, *_, **__):
        """Function for unsupported activities."""
        util.log_msg("WARNING (in %s): function call is not supported "
                     "on this thermostat type" %
                     (util.get_function_name(2)), mode=util.BOTH_LOG)


def thermostat_basic_checkout(api, thermostat_type, zone,
                              ThermostatClass, ThermostatZone):
    """
    Perform basic Thermostat checkout.

    inputs:
        api(module): thermostat_api module.
        tstat(int):  thermostat_type
        zone(int): zone number
        ThermostatClass(cls): Thermostat class
        ThermostatZone(cls): ThermostatZone class
    returns:
        Thermostat(obj): Thermostat object
        Zone(obj):  Zone object
    """
    util.log_msg.debug = True  # debug mode set

    # verify required env vars
    api.verify_required_env_variables(thermostat_type, zone)

    # import hardware module
    api.load_hardware_library(thermostat_type)

    # create Thermostat object
    Thermostat = ThermostatClass(zone)
    Thermostat.print_all_thermostat_metadata()

    # create Zone object
    Zone = ThermostatZone(Thermostat)

    # update runtime overrides
    api.user_inputs["thermostat_type"] = thermostat_type
    api.user_inputs["zone"] = zone
    Zone.update_runtime_parameters(api.user_inputs)

    # print("thermostat meta data=%s\n" % Thermostat.get_all_metadata())
    Zone.display_basic_thermostat_summary()

    return Thermostat, Zone
