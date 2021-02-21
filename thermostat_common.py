"""
Common Thermostat Class
"""
# built-ins
import datetime
import operator

# local imports
import utilities as util

# bogus values to identify uninitialized data
bogus_int = -13
bogus_bool = None


class ThermostatCommonZone():
    """Class methods common to all thermostat zones."""

    OFF_MODE = "OFF_MODE"
    HEAT_MODE = "HEAT_MODE"
    COOL_MODE = "COOL_MODE"
    system_switch_position = {
        COOL_MODE: 0,  # assumed, need to verify
        HEAT_MODE: 1,
        OFF_MODE: 2,
        }

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
        cool_deviation = bogus_bool  # cooling set point deviates from schedule
        heat_deviation = bogus_bool  # heating set point deviates from schedule
        hold_mode = bogus_bool  # True if not following schedule
        heat_schedule_point = bogus_int  # heating schedule set point
        heat_set_point = bogus_int  # heating current set point
        cool_schedule_point = bogus_int  # cooling schedule set point
        cool_set_point = bogus_int  # cooling current set point
        mode = "OFF MODE"  # mode for display, "OFF MODE", "HEAT MODE",
        #                    "COOL MODE"
        hold_temporary = bogus_bool  # True if hold will revert on next
        #                         schedule event

        if flag_all_deviations:
            cool_operator = operator.ne
            heat_operator = operator.ne
        else:
            cool_operator = operator.lt
            heat_operator = operator.gt

        return_buffer = {
            "heat_mode": bogus_bool,  # in heating mode
            "cool_mode": bogus_bool,  # in cooling mode
            "heat_deviation": bogus_bool,  # True if heat is deviated above
            "cool_deviation": bogus_bool,  # True if cool is deviated below
            "hold_mode": bogus_bool,  # True if hold is enabled
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

    # Thermostat-specific methods will be overloaded
    def get_display_temp(self) -> int:
        """Return the displayed temperature."""
        return bogus_int  # placeholder

    def get_system_switch_position(self) -> int:
        """Return the 'SystemSwitchPosition'
            'SystemSwitchPosition' = 1 for heat, 2 for off
        """
        return bogus_int  # placeholder

    def get_heat_setpoint_raw(self) -> int:
        """Return raw heat set point."""
        return bogus_int  # placeholder

    def get_schedule_heat_sp(self) -> int:
        """Return the heat setpoint."""
        return bogus_int  # placeholder

    def get_cool_setpoint_raw(self) -> int:
        """Return raw cool set point."""
        return bogus_int  # placeholder

    def get_schedule_cool_sp(self) -> int:
        """Return the cool setpoint."""
        return bogus_int  # placeholder

    def get_is_invacation_hold_mode(self) -> bool:
        """Return the 'IsInVacationHoldMode' setting."""
        return bogus_bool  # placeholder

    def get_temporary_hold_until_time(self) -> int:
        """Return the 'TemporaryHoldUntilTime' """
        return bogus_int  # placeholder

    def refresh_zone_info(self) -> None:
        """Refreshes zone info."""
        return
