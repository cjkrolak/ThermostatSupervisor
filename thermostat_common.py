"""
Common Thermostat Class
"""
# built-ins
import datetime
import operator

# local imports
import email_notification
import utilities as util

# bogus values to identify uninitialized data
bogus_int = -13
bogus_bool = None

degree_sign = u"\N{DEGREE SIGN}"


class ThermostatCommonZone():
    """Class methods common to all thermostat zones."""

    OFF_MODE = "OFF_MODE"
    HEAT_MODE = "HEAT_MODE"
    COOL_MODE = "COOL_MODE"
    AUTO_MODE = "AUTO_MODE"
    system_switch_position = {
        # placeholder, will be tstat-specific
        HEAT_MODE: bogus_int,
        OFF_MODE: bogus_int,
        COOL_MODE: bogus_int,
        AUTO_MODE: bogus_int,
        }
    max_scheduled_heat_allowed = 74  # warn if scheduled heat value exceeds.
    min_scheduled_cool_allowed = 68  # warn if scheduled cool value exceeds.

    def get_current_mode(self, session_count, poll_count, print_status=True,
                         flag_all_deviations=False):
        """
        Determine whether thermostat is following schedule or if it has been
        deviated from schedule.

        inputs:
            zone(obj):  TCC Zone object
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
        #                              schedule event

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

        print("DEBUG: %s entrypoint (switch position=%s)" %
              (util.get_function_name(),
               self.get_system_switch_position()))
        # current temperature
        display_temp = self.get_display_temp()

        # current humidity
        display_humidity = self.get_display_humidity()
        humidity_is_available = self.get_is_humidity_supported()

        # check for heat deviation
        heat_mode = (self.get_system_switch_position() ==
                     self.system_switch_position[self.HEAT_MODE])
        if heat_mode:
            mode = "HEAT MODE"
            # cast integers just in case a set point returns a float
            heat_set_point = int(self.get_heat_setpoint_raw())
            heat_schedule_point = int(self.get_schedule_heat_sp())
            if heat_operator(heat_set_point, heat_schedule_point):
                status_msg = ("[heat deviation] act temp=%.1f%sF" %
                              (display_temp, degree_sign))
                # add humidity if available
                if humidity_is_available:
                    status_msg += ", act humidity=%.1f%% RH" % display_humidity
                # add setpoint and override point
                status_msg += (", set point=%s, override=%s" %
                               (heat_schedule_point, heat_set_point))
                heat_deviation = True

            # warning email if heat set point is above global max value
            if heat_set_point > self.max_scheduled_heat_allowed:
                msg = ("scheduled heat set point (%s) is above "
                       "max limit (%s)" % (
                           heat_set_point, self.max_scheduled_heat_allowed))
                email_notification.send_email_alert(
                        subject=msg,
                        body="%s: %s" % (util.get_function_name(), msg))

        # check for cool deviation
        cool_mode = (self.get_system_switch_position() ==
                     self.system_switch_position[self.COOL_MODE])

        if cool_mode:
            mode = "COOL MODE"
            # cast integers just in case a set point returns a float
            cool_set_point = int(self.get_cool_setpoint_raw())
            cool_schedule_point = int(self.get_schedule_cool_sp())
            if cool_operator(cool_set_point, cool_schedule_point):
                status_msg = ("[cool deviation] act temp=%.1f%sF" %
                              (display_temp, degree_sign))
                # add humidity if available
                if humidity_is_available:
                    status_msg += ", act humidity=%.1f%% RH" % display_humidity
                # add setpoint and override point
                status_msg += (", set point=%s, override=%s" %
                               (cool_schedule_point, cool_set_point))
                cool_deviation = True

            # warning email if cool set point is below global min value
            if cool_set_point < self.min_scheduled_cool_allowed:
                msg = ("scheduled cool set point (%s) is below "
                       "min limit (%s)" % (
                           cool_set_point, self.min_scheduled_cool_allowed))
                email_notification.send_email_alert(
                        subject=msg,
                        body="%s: %s" % (util.get_function_name(), msg))

        # hold cooling
        if heat_deviation or cool_deviation:
            print("DEBUG: in vacation hold=%s" %
                  self.get_is_invacation_hold_mode())
            print("DEBUG: hold time=%s" %
                  self.get_temporary_hold_until_time())
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
            if heat_mode:
                status_msg += (", set point=%s, override=%s" %
                               (heat_schedule_point, heat_set_point))
            elif cool_mode:
                status_msg += (", set point=%s, override=%s" %
                               (cool_schedule_point, cool_set_point))

        full_status_msg = ("%s: (session:%s, poll:%s) %s %s" %
                           (datetime.datetime.now().
                            strftime("%Y-%m-%d %H:%M:%S"),
                            session_count, poll_count, mode, status_msg))
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
    def get_display_temp(self) -> float:
        """Return the displayed temperature."""
        return float(bogus_int)  # placeholder

    def get_display_humidity(self) -> float:
        """Return the displayed humidity."""
        return float(bogus_int)  # placeholder

    def get_is_humidity_supported(self) -> bool:
        """Return humidity sensor status."""
        return bogus_bool  # placeholder

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
        return  # placeholder

    def report_heating_parameters(self):
        """Display critical thermostat settings and reading to the screen."""
        return  # placeholder
