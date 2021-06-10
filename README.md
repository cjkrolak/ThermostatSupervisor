# ThermostatSupervisor:
supervisor to detect and correct thermostat deviations<br/>

# dependencies:
pyhtcc (pip3 install pyhtcc)<br/>
radiotherm repository (mhrivnak/radiotherm or pip3 install radiotherm)<br/>

# Docker Image:
docker run --rm --env-file supervisor-env.txt cjkrolak/thermostatsupervisor "thermostat type" "zone"<br/>
supervisor-env.txt is your environment variables passed in (see below)<br/>
"thermostat type" is the thermostat type (default=honeywell)<br/>
"zone" is the thermostat zone (default=0)<br/>

# supervise.py:
This is the main entry point script.<br/>
runtime parameters can be specified to override defaults:<br/>
argv[1] = Thermostat type, currently support "honeywell" and "mmm50".  Default is "honeywell".<br/>
argv[2] = zone, currently support zone 0 on honeywell and zones [0,1] on 3m50.<br/>
supervise script will call honeywell or mmm50 scripts, detailed below.<br/>
command line usage:  "*python supervise.py \<thermostat type\> \<zone\>*"
  
# flaskserver.py:
This module will render supervise.py output on an HTML page using Flask.<br/>
Same runtime parameters as supervise.py can be specified to override defaults:<br/>
Flask server rendering currently works through IDE, but not yet through command line.<br/>
port is currently hard-coded to 80, access at loopback.<br/>
command line usage:  "*python flaskserver.py \<thermostat type\> \<zone\>*"

# honeywell.py:
1. Script will logon to TCC web site and infinitely poll server at configurable poll interval for current thermostat settings.
2. polling is currently set to 3 minutes, longer poll times experience connection errors, shorter poll times are impractical based on emperical data.
3. If schedule deviation detected, script will revert thermostat back to scheduled settings.
Script can be configured to customize polling interval, force re-logon after period of time, and either just alert or alert and revert to schedule.

# mmm50.py:
1. Script will connect to 3m50 thermostat on local network, IP address stored in thermostat_api.mmm_ip
2. polling is currently set to 10 minutes.
3. If schedule deviation detected, script will revert thermostat back to scheduled settings.
Script can be configured to customize polling interval, force re-logon after period of time, and either just alert or alert and revert to schedule.<br/>
command line usage:  "*python mmm.py \<zone\>*"

# errata:
1. code currently only supports Honeywell thermostat connected to MyTotalControl web site and 3m50 thermostat connected to local network.
2. code only reliably runs with 3 minute poll time on Honeywell.
3. a few other low frequency intermittent issues exist, refer to issues in github repo for details.

# debug / diagnostics:
1. Honeywell pyhtcc.txt file in /home/pi/log/pyhtcc/ shows logging specific to pyhtcc class
2. ./data/ folder contains supervisor logs

# environment variables required:<br/>
in Linux, define and then export variables in ~/.profile<br/>
in Windows, define env variables in control panel and then re-start IDE<br/>
* 'TCC_USERNAME':  username to Honeywell TCC website
* 'TCC_PASSWORD':  password for TCC_USERNAME
* 'GMAIL_USERNAME': email account to send notifications from
* 'GMAIL_PASSWORD': password for GMAIL_USERNAME

# Supervisor API required methods:<br/>
**thermostat class:**<br/>
* get_all_thermostat_metadata(): Return intial thermostat meta data.
* get_target_zone_id(): Return the target zone ID.

**zone class:**<br/>
* get_current_mode(): Determine whether thermostat is following schedule or if it has been deviated from schedule.
* report_heating_parameters(): Display critical thermostat settings and reading to the screen.
* set_heat_setpoint():  Sets a new heat setpoint.
* set_cool_setpoint():  Set a new cool setpoint.
* refresh_zone_info():  Refresh the zone_info attribute.



