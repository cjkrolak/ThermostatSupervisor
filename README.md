# ThermostatSupervisor:
supervisor to detect and correct thermostat deviations

# dependencies
pyhtcc (pip3 install pyhtcc)


# honeywell.py:
1. Script will logon to TCC web site and infinitely poll server at configurable poll interval for current thermostat settings.
2. If schedule deviation detected, script will revert thermostat back to scheduled settings.
Script can be configured to customize polling interval, force re-logon after period of time, and either just alert or alert and revert to schedule.

# errata:
1. code currently only supports Honeywell thermostat connected to MyTotalControl web site.
2. code only reliably runs with 3 minute poll time

# environment variables required
# in Linux, define and then export variables in ~/.profile
# in Windows, define env variables in control panel and then re-start IDE
'TCC_USERNAME':  username to Honeywell TCC website

'TCC_PASSWORD':  password for TCC_USERNAME

'GMAIL_USERNAME': email account to send notifications from

'GMAIL_PASSWORD': password for GMAIL_USERNAME


Supervisor API required methods:
**thermostat class:**
* get_all_thermostat_metadata(): Return intial thermostat meta data.
* get_target_zone_id(): Return the target zone ID.

**zone class:**
* get_current_mode(): Determine whether thermostat is following schedule or if it has been deviated from schedule.
* report_heating_parameters(): Display critical thermostat settings and reading to the screen.
* set_heat_setpoint():  Sets a new heat setpoint.
* set_cool_setpoint():  Set a new cool setpoint.
* refresh_zone_info():  Refresh the zone_info attribute.



