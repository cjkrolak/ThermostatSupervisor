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
'TCC_USERNAME':  username to Honeywell TCC website

'TCC_PASSWORD':  password for TCC_USERNAME

'GMAIL_TO_USERNAME':  email accounts to send alerts

'GMAIL_USERNAME': email account to send notifications from

'GMAIL_PASSWORD': password for GMAIL_USERNAME
