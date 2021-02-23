# ThermostatSupervisor:<br/>
supervisor to detect and correct thermostat deviations<br/>

# dependencies<br/>
pyhtcc (pip3 install pyhtcc)<br/>
radiotherm repository (mhrivnak/radiotherm)<br/>

# honeywell.py:
1. Script will logon to TCC web site and infinitely poll server at configurable poll interval for current thermostat settings.
2. If schedule deviation detected, script will revert thermostat back to scheduled settings.
Script can be configured to customize polling interval, force re-logon after period of time, and either just alert or alert and revert to schedule.

# errata:
1. code currently only supports Honeywell thermostat connected to MyTotalControl web site.
2. code only reliably runs with 3 minute poll time

# environment variables required<br/>
# in Linux, define and then export variables in ~/.profile<br/>
# in Windows, define env variables in control panel and then re-start IDE<br/>
'TCC_USERNAME':  username to Honeywell TCC website<br/>
'TCC_PASSWORD':  password for TCC_USERNAME<br/>
'GMAIL_USERNAME': email account to send notifications from<br/>
'GMAIL_PASSWORD': password for GMAIL_USERNAME<br/>

Supervisor API required methods:<br/>
**thermostat class:**<br/>
* get_all_thermostat_metadata(): Return intial thermostat meta data.
* get_target_zone_id(): Return the target zone ID.

**zone class:**<br/>
* get_current_mode(): Determine whether thermostat is following schedule or if it has been deviated from schedule.
* report_heating_parameters(): Display critical thermostat settings and reading to the screen.
* set_heat_setpoint():  Sets a new heat setpoint.
* set_cool_setpoint():  Set a new cool setpoint.
* refresh_zone_info():  Refresh the zone_info attribute.



