"""
Common Thermostat Class
"""
# built-ins
import datetime
import operator
import pprint
import statistics
import time
import traceback

# local imports
from thermostatsupervisor import email_notification as eml
from thermostatsupervisor import thermostat_api as api
from thermostatsupervisor import utilities as util


DEGREE_SIGN = "\N{DEGREE SIGN}"

connection_ok = True  # global flag for connection OK.
connection_fail_cnt = 0  # count number of connection failures
max_connection_fail_cnt = 9  # max number of connection failures


class ThermostatCommon():
    """Class methods common to all thermostat objects."""

    def __init__(self, *_, **__):
        self.verbose = True
        self.thermostat_type = "unknown"  # placeholder
        self.zone_number = util.BOGUS_INT  # placeholder
        self.device_id = util.BOGUS_INT  # placeholder
        self.ip_address = None  # placeholder
        global connection_ok  # noqa W603
        connection_ok = True

    def print_all_thermostat_metadata(self, zone, debug=False):  # noqa R0201
        """
        Print initial meta data queried from thermostat for specified zone.

        inputs:
            zone(int): zone number
            debug(bool): debug flag
        returns:
            None
        """
        del debug  # placeholder function
        util.log_msg(
            f"WARNING: print_all_thermostat_metatdata({zone}) not yet "
            f"implemented for this thermostat type\n",
            mode=util.BOTH_LOG,
            func_name=1)

    def exec_print_all_thermostat_metadata(self, func, args):
        """
        Print all metadata to screen.

        inputs:
            func(obj): function get metadata.
            args(list): argument list
        returns:
            (dict): return data
        """
        # dump metadata in a readable format
        return_data = func(*args)
        pprint_obj = pprint.PrettyPrinter(indent=4)
        print("\n")
        util.log_msg("raw thermostat meta data:",
                     mode=util.BOTH_LOG, func_name=1)
        pprint_obj.pprint(return_data)
        return return_data


class ThermostatCommonZone():
    """Class methods common to all thermostat zones."""

    # supported thermostat modes and label text
    OFF_MODE = "OFF_MODE"
    HEAT_MODE = "HEAT_MODE"
    COOL_MODE = "COOL_MODE"
    AUTO_MODE = "AUTO_MODE"
    DRY_MODE = "DRY_MODE"
    FAN_MODE = "FAN_MODE"
    UNKNOWN_MODE = "UNKNOWN_MODE"  # bypass set mode or unable to detect

    # modes where heat is applied
    heat_modes = [HEAT_MODE, AUTO_MODE]

    # modes where cooling is applied
    cool_modes = [COOL_MODE, DRY_MODE, AUTO_MODE]

    # modes in which setpoints apply
    controlled_modes = [HEAT_MODE, AUTO_MODE, COOL_MODE]

    system_switch_position = {
        # placeholder, will be tstat-specific
        UNKNOWN_MODE: util.BOGUS_INT,
        HEAT_MODE: util.BOGUS_INT - 1,
        COOL_MODE: util.BOGUS_INT - 2,
        AUTO_MODE: util.BOGUS_INT - 3,
        DRY_MODE: util.BOGUS_INT - 4,
        FAN_MODE: util.BOGUS_INT - 5,
        OFF_MODE: util.BOGUS_INT - 6,
    }
    max_scheduled_heat_allowed = 74  # warn if scheduled heat value exceeds.
    min_scheduled_cool_allowed = 68  # warn if scheduled cool value exceeds.
    tolerance_degrees_default = 2  # allowed override vs. the scheduled value.

    def __init__(self, *_, **__):
        self.verbose = True
        self.thermostat_type = "unknown"  # placeholder
        self.zone_number = util.BOGUS_INT  # placeholder
        self.zone_name = None  # placeholder
        self.device_id = util.BOGUS_INT  # placeholder
        self.poll_time_sec = util.BOGUS_INT  # placeholder
        self.session_start_time_sec = util.BOGUS_INT  # placeholder
        self.connection_time_sec = util.BOGUS_INT  # placeholder
        self.target_mode = "OFF_MODE"  # placeholder
        self.flag_all_deviations = False  #
        self.revert_deviations = True  # Revert deviation
        self.revert_all_deviations = False  # Revert only energy-wasting events
        self.temperature_is_deviated = False  # temp deviated from schedule
        self.display_temp = None  # current temperature in deg F
        self.display_humidity = None  # current humidity in %RH
        self.humidity_is_available = False  # humidity supported flag
        self.hold_mode = False  # True = not following schedule
        self.hold_temporary = False
        self.zone_info = {}  # dict containing zone data
        self.last_fetch_time = None  # last fetch of zone_info

        # abstraction vars and funcs, defined in query_thermostat_zone
        self.current_mode = None  # str representing mode
        self.current_setpoint = util.BOGUS_INT  # current setpoint
        self.schedule_setpoint = util.BOGUS_INT  # current scheduled setpoint
        self.tolerance_sign = 1  # +1 for heat, -1 for cool
        self.operator = operator.ne  # operator for deviation check
        self.tolerance_degrees = self.tolerance_degrees_default
        self.global_limit = util.BOGUS_INT  # global temp limit
        self.global_operator = operator.ne  # oper for global temp deviation
        self.revert_setpoint_func = self.function_not_supported
        self.get_setpoint_func = self.function_not_supported

    def query_thermostat_zone(self):
        """Return the current mode and set mode-specific parameters."""

        # current temperature
        try:
            self.display_temp = self.validate_numeric(self.get_display_temp(),
                                                      "get_display_temp")
        except TypeError:
            util.log_msg(traceback.format_exc(),
                         mode=util.BOTH_LOG, func_name=1)
            self.display_temp = None

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
            self.current_setpoint = util.BOGUS_INT
            self.schedule_setpoint = util.BOGUS_INT
            self.tolerance_sign = 1
            self.operator = operator.ne
            self.global_limit = util.BOGUS_INT
            self.global_operator = operator.ne
            self.revert_setpoint_func = self.function_not_supported
            self.get_setpoint_func = self.function_not_supported
        elif self.is_fan_mode():
            self.current_mode = self.FAN_MODE
            self.current_setpoint = util.BOGUS_INT
            self.schedule_setpoint = util.BOGUS_INT
            self.tolerance_sign = 1
            self.operator = operator.ne
            self.global_limit = util.BOGUS_INT
            self.global_operator = operator.ne
            self.revert_setpoint_func = self.function_not_supported
            self.get_setpoint_func = self.function_not_supported
        elif self.is_off_mode():
            self.current_mode = self.OFF_MODE
            self.current_setpoint = util.BOGUS_INT
            self.schedule_setpoint = util.BOGUS_INT
            self.tolerance_sign = 1
            self.operator = operator.ne
            self.global_limit = util.BOGUS_INT
            self.global_operator = operator.ne
            self.revert_setpoint_func = self.function_not_supported
            self.get_setpoint_func = self.function_not_supported
        else:
            print(f"DEBUG: zone info: {self.zone_info}")
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
            "heat_mode": util.BOGUS_BOOL,  # in heating mode
            "cool_mode": util.BOGUS_BOOL,  # in cooling mode
            "heat_deviation": util.BOGUS_BOOL,  # True: heat is deviated above
            "cool_deviation": util.BOGUS_BOOL,  # True: cool is deviated below
            "hold_mode": util.BOGUS_BOOL,  # True if hold is enabled
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
            status_msg = (f"[{self.current_mode.upper()} deviation] act temp="
                          f"{util.temp_value_with_units(self.display_temp)}")
        else:
            status_msg = (f"[following schedule] act temp="
                          f"{util.temp_value_with_units(self.display_temp)}")

        # add humidity if available
        if self.humidity_is_available:
            status_msg += \
                (f", act humidity="
                 f"{util.humidity_value_with_units(self.display_humidity)}")

        # add hold information
        if self.is_temp_deviated_from_schedule() and self.is_controlled_mode():
            self.hold_mode = True  # True = not following schedule
            self.hold_temporary = self.get_temporary_hold_until_time() > 0
            status_msg += (
                f" ({['persistent', 'temporary'][self.hold_temporary]})")
        else:
            self.hold_mode = False
            self.hold_temporary = False

        # add setpoints if in heat or cool mode
        if self.is_heat_mode() or self.is_cool_mode():
            status_msg += (
                f", set point="
                f"{util.temp_value_with_units(self.schedule_setpoint)}, "
                f"tolerance="
                f"{util.temp_value_with_units(self.tolerance_degrees)}, "
                f"override="
                f"{util.temp_value_with_units(self.current_setpoint)}")

        date_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        full_status_msg = (
            f"{date_str}: "
            f"(tstat:{self.thermostat_type}, zone:{self.zone_name}, "
            f"session:{session_count}, poll:{poll_count}) "
            f"{self.current_mode.upper()} {status_msg}")
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
            target_mode(str): target mode, refer to supported_configs["modes"]
        returns:
            True if successful, else False
        """
        print(f"DEBUG in set_mode, target_mode={target_mode}, doing nothing")
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
            raise TypeError(
                f"value returned for parameter '{parameter_name}' is "
                f"type {type(input_val)}, expected int or float")
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
            msg = (f"{self.thermostat_type} zone {self.zone_name}: "
                   f"scheduled {label.upper()} set point "
                   f"({util.temp_value_with_units(setpoint)}) is {level} "
                   f"limit ({util.temp_value_with_units(limit_value)})")
            util.log_msg(f"WARNING: {msg}", mode=util.BOTH_LOG)
            eml.send_email_alert(
                subject=msg,
                body=f"{util.get_function_name()}: {msg}")
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

    def is_heating(self):  # noqa R0201
        """Return 1 if heating relay is active, else 0."""
        return util.BOGUS_INT

    def is_cooling(self):  # noqa R0201
        """Return 1 if cooling relay is active, else 0."""
        return util.BOGUS_INT

    def is_drying(self):  # noqa R0201
        """Return 1 if drying relay is active, else 0."""
        return util.BOGUS_INT

    def is_auto(self):  # noqa R0201
        """Return 1 if auto relay is active, else 0."""
        return util.BOGUS_INT

    def is_fanning(self):  # noqa R0201
        """Return 1 if fan relay is active, else 0."""
        return util.BOGUS_INT

    def set_heat_setpoint(self, temp: int) -> None:  # noqa R0201
        """
        Set a new heat setpoint.

        This will also attempt to turn the thermostat to 'Cool'
        inputs:
            temp(int): desired temperature in deg F.
        returns:
            None
        """
        del temp
        util.log_msg(
            f"WARNING: {util.get_function_name()}: function is not yet "
            f"implemented on this thermostat, doing nothing",
            mode=util.BOTH_LOG,
            func_name=1)

    def set_cool_setpoint(self, temp: int) -> None:  # noqa R0201
        """
        Set a new cool setpoint.

        This will also attempt to turn the thermostat to 'Cool'
        inputs:
            temp(int): desired temperature in deg F.
        returns:
            None
        """
        del temp
        util.log_msg(
            f"WARNING: {util.get_function_name()}: function is not yet "
            f"implemented on this thermostat, doing nothing",
            mode=util.BOTH_LOG,
            func_name=1)

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
    def get_display_temp(self) -> float:  # noqa R0201
        """Return the displayed temperature."""
        return float(util.BOGUS_INT)  # placeholder

    def get_display_humidity(self) -> float:  # noqa R0201
        """Return the displayed humidity."""
        return float(util.BOGUS_INT)  # placeholder

    def get_is_humidity_supported(self) -> bool:  # noqa R0201
        """Return humidity sensor status."""
        return util.BOGUS_BOOL  # placeholder

    def get_system_switch_position(self) -> int:  # noqa R0201
        """Return the 'SystemSwitchPosition'
            'SystemSwitchPosition' = 1 for heat, 2 for off
        """
        return util.BOGUS_INT  # placeholder

    def get_heat_setpoint_raw(self) -> int:  # noqa R0201
        """Return raw heat set point(number only, no units)."""
        return util.BOGUS_INT  # placeholder

    def get_heat_setpoint(self) -> int:  # noqa R0201
        """Return raw heat set point(number and units)."""
        return util.BOGUS_INT  # placeholder

    def get_schedule_program_heat(self) -> dict:  # noqa R0201
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
        return util.BOGUS_INT  # placeholder

    def get_cool_setpoint_raw(self) -> int:  # noqa R0201
        """Return raw cool set point (number only, no units)."""
        return util.BOGUS_INT  # placeholder

    def get_cool_setpoint(self) -> int:  # noqa R0201
        """Return raw cool set point (number and units)."""
        return util.BOGUS_INT  # placeholder

    def get_schedule_program_cool(self) -> dict:  # noqa R0201
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
        return util.BOGUS_INT  # placeholder

    def get_vacation_hold(self) -> bool:  # noqa R0201
        """Return True if thermostat is in vacation hold mode."""
        return util.BOGUS_BOOL  # placeholder

    def get_is_invacation_hold_mode(self) -> bool:  # noqa R0201
        """Return the 'IsInVacationHoldMode' setting."""
        return util.BOGUS_BOOL  # placeholder

    def get_temporary_hold_until_time(self) -> int:  # noqa R0201
        """Return the 'TemporaryHoldUntilTime' """
        return util.BOGUS_INT  # placeholder

    def refresh_zone_info(self, force_refresh=False) -> None:
        """
        Refresh zone info.

        inputs:
            force_refresh(bool): if True, ignore expiration timer.
        returns:
            None, cached data is refreshed.
        """
        del force_refresh  # not used in this template.
        self.zone_info = {}
        self.last_fetch_time = time.time()

    def report_heating_parameters(self, switch_position=None):  # noqa R0201
        """
        Display critical thermostat settings and reading to the screen.

        inputs:
            switch_position(int): switch position override for testing.
        returns:
            None
        """
        del switch_position  # placeholder

    def get_vacation_hold_until_time(self) -> int:  # noqa R0201
        """
        Return the 'VacationHoldUntilTime'.

        inputs:
            None
        returns:
            (int): vacation hold time in minutes.
         """
        return util.BOGUS_INT  # not implemented

    def update_runtime_parameters(self):
        """use runtime parameter overrides.

        inputs:
            None
        returns:
            None, updates class variables.
        """
        # map user input keys to class members.
        # "thermostat_type is not overwritten
        user_input_to_class_mapping = {
            api.input_flds.thermostat_type: "thermostat_type",
            api.input_flds.zone: "zone_name",
            api.input_flds.poll_time: "poll_time_sec",
            api.input_flds.connection_time: "connection_time_sec",
            api.input_flds.tolerance: "tolerance_degrees",
            api.input_flds.target_mode: "target_mode",
            api.input_flds.measurements: "measurements",
        }

        if self.verbose:
            print("\n")
            util.log_msg("supervisor runtime parameters:",
                         mode=util.BOTH_LOG, func_name=1)
        for inp, cls_method in user_input_to_class_mapping.items():
            user_input = api.uip.get_user_inputs(api.uip.zone_name, inp)
            if user_input is not None:
                setattr(self, cls_method, user_input)
                if self.verbose:
                    util.log_msg(f"{inp}={user_input}",
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
            return bool(self.current_mode == target_mode)

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
            util.log_msg(
                f"WARNING: target mode={target_mode}, switching from "
                f"{self.current_mode} to OFF_MODE to prevent damage to HVAC",
                mode=util.BOTH_LOG,
                func_name=1)
            target_mode = self.OFF_MODE

        # do not switch directly from cold to hot
        elif (self.current_mode in self.cool_modes and
              target_mode in self.heat_modes):
            util.log_msg(
                f"WARNING: target mode={target_mode}, switching from "
                f"{self.current_mode} to OFF_MODE to prevent damage to HVAC",
                mode=util.BOTH_LOG,
                func_name=1)
            target_mode = self.OFF_MODE

        # revert the mode to target
        # UNKNOWN mode is bypassed
        if target_mode == self.UNKNOWN_MODE:
            print(f"{util.get_function_name()}: target_mode='{target_mode}', "
                  "doing nothing.")
        else:
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
            func = self.get_display_temp

        # measurement loop
        for measurement in range(measurements):
            time0 = time.time()
            func()  # target command
            time1 = time.time()

            # accumulate stats
            tdelta = time1 - time0
            delta_lst.append(tdelta)
            util.log_msg(f"measurement {measurement}={tdelta:.2f} seconds",
                         mode=util.BOTH_LOG, func_name=1)

        # calc stats
        stats["measurements"] = measurements
        stats["mean"] = round(statistics.mean(delta_lst), 2)
        stats["stdev"] = round(statistics.stdev(delta_lst), 2)
        stats["min"] = round(min(delta_lst), 2)
        stats["max"] = round(max(delta_lst), 2)
        stats["3sigma_upper"] = round((3.0 * stats["stdev"] +
                                      stats["mean"]), 2)
        stats["6sigma_upper"] = round((6.0 * stats["stdev"] +
                                       stats["mean"]), 2)
        return stats

    def measure_thermostat_repeatability(self, measurements=30,
                                         poll_interval_sec=0,
                                         func=None):
        """
        Measure Thermostat repeatability and report statistics.

        inputs:
            measurements(int): number of measurements
            poll_interval_sec(int): delay between measurements
            func(obj): target function to run during repeatabilty measurement.
        returns:
            (dict): measurement statistics.
        """
        data_lst = []
        stats = {}
        # set default measurement method if not provided.
        if func is None:
            func = self.get_display_temp

        # measurement loop
        for measurement in range(measurements):
            t_start = time.time()
            data = func()  # target command
            t_end = time.time()

            # accumulate stats
            tdelta = t_end - t_start
            data_lst.append(data)
            util.log_msg(
                f"measurement {measurement}={data} (deltaTime={tdelta:.2f} "
                f"sec, delay={poll_interval_sec} sec)",
                mode=util.BOTH_LOG,
                func_name=1)
            time.sleep(poll_interval_sec)
            self.refresh_zone_info()

        # calc stats
        stats["measurements"] = measurements
        stats["mean"] = round(statistics.mean(data_lst), 2)
        stats["stdev"] = round(statistics.stdev(data_lst), 2)
        stats["min"] = round(min(data_lst), 2)
        stats["max"] = round(max(data_lst), 2)
        stats["3sigma_upper"] = round((3.0 * stats["stdev"] +
                                      stats["mean"]), 2)
        stats["6sigma_upper"] = round((6.0 * stats["stdev"] +
                                       stats["mean"]), 2)
        return stats

    def display_basic_thermostat_summary(self, mode=util.CONSOLE_LOG):
        """
        Display basic thermostat summary.

        inputs:
            mode(int): target log for data.
        returns:
            None, prints data to log and/or console.
        """
        print("\n")
        util.log_msg("current thermostat settings...",
                     mode=mode, func_name=1)
        util.log_msg(f"zone name='{self.zone_name}'",
                     mode=mode, func_name=1)
        sw_pos = util.get_key_from_value(self.system_switch_position,
                                         self.get_system_switch_position())
        util.log_msg(
            f"system switch position: {self.get_system_switch_position()} "
            f"({sw_pos})",
            mode=mode,
            func_name=1)
        util.log_msg(
            f"thermostat display temp="
            f"{util.temp_value_with_units(self.get_display_temp())}",
            mode=mode,
            func_name=1)
        util.log_msg(
            f"thermostat display humidity="
            f"{util.humidity_value_with_units(self.get_display_humidity())}",
            mode=mode,
            func_name=1)
        util.log_msg(
            f"heat set point="
            f"{util.temp_value_with_units(self.get_heat_setpoint())}",
            mode=mode,
            func_name=1)
        util.log_msg(
            f"cool set point="
            f"{util.temp_value_with_units(self.get_cool_setpoint())}",
            mode=mode,
            func_name=1)
        util.log_msg(
            f"heat schedule set point="
            f"{util.temp_value_with_units(self.get_schedule_heat_sp())}",
            mode=mode,
            func_name=1)
        util.log_msg(
            f"cool schedule set point="
            f"{util.temp_value_with_units(self.get_schedule_cool_sp())}",
            mode=mode,
            func_name=1)
        util.log_msg(
            f"(schedule) heat program={self.get_schedule_program_heat()}",
            mode=mode, func_name=1)
        util.log_msg(
            f"(schedule) cool program={self.get_schedule_program_cool()}",
            mode=mode, func_name=1)
        util.log_msg(
            f"heat mode={self.is_heat_mode()} "
            f"(actively heating={self.is_heating()})",
            mode=mode,
            func_name=1)
        util.log_msg(
            f"cool mode={self.is_cool_mode()} "
            f"(actively cooling={self.is_cooling()})",
            mode=mode,
            func_name=1)
        util.log_msg(
            f"dry mode={self.is_dry_mode()} "
            f"(actively drying={self.is_drying()})",
            mode=mode,
            func_name=1)
        util.log_msg(
            f"auto mode={self.is_auto_mode()} "
            f"(actively auto={self.is_auto()})",
            mode=mode,
            func_name=1)
        util.log_msg(
            f"fan mode={self.is_fan_mode()} "
            f"(actively fanning={self.is_fanning()})",
            mode=mode,
            func_name=1)
        util.log_msg(f"off mode={self.is_off_mode()}",
                     mode=mode, func_name=1)
        util.log_msg(f"hold={self.get_vacation_hold()}",
                     mode=mode, func_name=1)
        util.log_msg(
            f"temporary hold minutes={self.get_temporary_hold_until_time()}",
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
            subject=f"{self.thermostat_type} {self.current_mode.upper()} "
            f"deviation alert on zone {self.zone_name}",
            body=msg)
        util.log_msg(
            f"\n*** {self.thermostat_type} {self.current_mode.upper()} "
            f"deviation detected on zone {self.zone_name}, "
            f"reverting thermostat to heat schedule ***\n",
            mode=util.BOTH_LOG)
        self.revert_setpoint_func(setpoint)

    def function_not_supported(self, *_, **__):
        """Function for unsupported activities."""
        util.log_msg(
            f"WARNING (in {util.get_function_name(2)}): function call is "
            f"not supported on this thermostat type",
            mode=util.BOTH_LOG)

    def display_runtime_settings(self):
        """
        Display runtime settings to console.

        inputs:
            None
        returns:
            None
        """
        # poll time setting:
        util.log_msg(
            f"polling time set to {self.poll_time_sec / 60.0:.1f} minutes",
            mode=util.BOTH_LOG)

        # reconnection time to thermostat server:
        util.log_msg(
            f"server re-connect time set to "
            f"{self.connection_time_sec / 60.0:.1f}"
            f" minutes",
            mode=util.BOTH_LOG)

        # tolerance to set point:
        util.log_msg(
            f"tolerance to set point is set to "
            f"{util.temp_value_with_units(self.tolerance_degrees)}",
            mode=util.BOTH_LOG)

    def display_session_settings(self):
        """
        Display session settings to console.

        inputs:
            None
        returns:
            None
        """
        # set log file name
        util.log_msg.file_name = (self.thermostat_type + "_" +
                                  str(self.zone_name) + ".txt")

        util.log_msg(
            f"{self.thermostat_type} thermostat zone {self.zone_name} "
            f"monitoring service\n",
            mode=util.BOTH_LOG)

        util.log_msg("session settings:", mode=util.BOTH_LOG)

        util.log_msg("thermostat %s for %s\n" %
                     (["is being monitored", "will be reverted"]
                      [self.revert_deviations],
                      ["energy consuming deviations\n("
                       "e.g. heat setpoint above schedule "
                       "setpoint, cool setpoint below schedule"
                       " setpoint)",
                       "all schedule deviations"]
                      [self.revert_all_deviations]), mode=util.BOTH_LOG)

    def supervisor_loop(self, Thermostat, session_count, measurement,
                        debug):
        """
        Loop through supervisor algorithm.

        inputs:
            Thermostat(obj):  Thermostat instance object
            session_count(int):  current session
            measurement(int):  current measurement index
            debug(bool): debug flag
        returns:
            measurement(int): current measurement count
        """
        global connection_ok  # noqa W603

        # initialize poll counter
        poll_count = 1
        previous_mode_dict = {}

        # poll thermostat settings
        while not api.uip.max_measurement_count_exceeded(measurement):
            # query thermostat for current settings and set points
            current_mode_dict = self.get_current_mode(
                session_count, poll_count,
                flag_all_deviations=self.revert_all_deviations)

            # debug data on change from previous poll
            # note this check is probably hyper-sensitive, since status msg
            # change could trigger this extra report.
            if current_mode_dict != previous_mode_dict:
                if debug:
                    self.report_heating_parameters()
                previous_mode_dict = current_mode_dict  # latch

            # revert thermostat mode if not matching target
            if not self.verify_current_mode(api.uip.get_user_inputs(
                    api.uip.zone_name, api.input_flds.target_mode)):
                api.uip.set_user_inputs(api.uip.zone_name,
                                        api.input_flds.target_mode,
                                        self.revert_thermostat_mode(
                                            api.uip.get_user_inputs(
                                                api.uip.zone_name,
                                                api.input_flds.target_mode)
                                            ))

            # revert thermostat to schedule if heat override is detected
            if (self.revert_deviations and self.is_controlled_mode() and
                    self.is_temp_deviated_from_schedule()):
                self.revert_temperature_deviation(
                    self.schedule_setpoint, current_mode_dict["status_msg"])

            # increment poll count
            poll_count += 1
            measurement += 1

            # polling delay
            time.sleep(self.poll_time_sec)

            # refresh zone info
            connection_ok = True
            self.refresh_zone_info()

            # reconnect
            if ((time.time() - self.session_start_time_sec)
                    > self.connection_time_sec) or not connection_ok:
                util.log_msg("forcing re-connection to thermostat...",
                             mode=util.BOTH_LOG)
                del Thermostat
                break  # force reconnection

        # return measurement count
        return measurement


def create_thermostat_instance(thermostat_type, zone,
                               ThermostatClass, ThermostatZone,
                               verbose=True):
    """
    Create Thermostat and Zone instances.

    inputs:
        tstat(int):  thermostat_type
        zone(int): zone number
        zone_name(str): name of zone
        ThermostatClass(cls): Thermostat class
        ThermostatZone(cls): ThermostatZone class
        verbose(bool): debug flag
    returns:
        Thermostat(obj): Thermostat object
        Zone(obj):  Zone object
    """
    util.log_msg.debug = verbose  # debug mode set

    # verify required env vars
    api.verify_required_env_variables(thermostat_type, str(zone),
                                      verbose=verbose)

    # import hardware module
    api.load_hardware_library(thermostat_type)

    # create Thermostat object
    Thermostat = ThermostatClass(zone, verbose=verbose)
    if verbose:
        Thermostat.print_all_thermostat_metadata(zone)

    # create Zone object
    Zone = ThermostatZone(Thermostat, verbose=verbose)

    # update runtime overrides
    # thermostat_type
    api.uip.set_user_inputs(api.uip.zone_name,
                            api.input_flds.thermostat_type,
                            thermostat_type)
    # zone
    api.uip.set_user_inputs(api.uip.zone_name, api.input_flds.zone,
                            zone)
    Zone.update_runtime_parameters()

    return Thermostat, Zone


def thermostat_basic_checkout(thermostat_type, zone,
                              ThermostatClass, ThermostatZone):
    """
    Perform basic Thermostat checkout.

    inputs:
        tstat(int):  thermostat_type
        zone(int): zone number
        ThermostatClass(cls): Thermostat class
        ThermostatZone(cls): ThermostatZone class
    returns:
        Thermostat(obj): Thermostat object
        Zone(obj):  Zone object
    """
    util.log_msg.debug = True  # debug mode set

    # create class instances
    Thermostat, Zone = create_thermostat_instance(thermostat_type, zone,
                                                  ThermostatClass,
                                                  ThermostatZone)

    Zone.display_basic_thermostat_summary()

    return Thermostat, Zone


def thermostat_get_all_zone_temps(thermostat_type, zone_lst,
                                  ThermostatClass, ThermostatZone):
    """
    Perform basic Thermostat checkout.

    inputs:
        tstat(int):  thermostat_type
        zone_lst(list): list of zones
        ThermostatClass(cls): Thermostat class
        ThermostatZone(cls): ThermostatZone class
    returns:
        Thermostat(obj): Thermostat object
        Zone(obj):  Zone object
    """
    util.log_msg.debug = False  # debug mode unset
    print("\nquerying all zone temps:")

    for zone in zone_lst:
        # create class instances
        Thermostat, Zone = create_thermostat_instance(thermostat_type, zone,
                                                      ThermostatClass,
                                                      ThermostatZone,
                                                      verbose=False)

        display_temp = Zone.get_display_temp()
        zone_name = Zone.zone_name
        print(f"zone: {zone}, name: {zone_name}, temp: {display_temp}")

    return Thermostat, Zone
