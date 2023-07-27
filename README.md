[![Codacy Security Scan](https://github.com/cjkrolak/ThermostatSupervisor/actions/workflows/codacy-analysis.yml/badge.svg)](https://github.com/cjkrolak/ThermostatSupervisor/actions/workflows/codacy-analysis.yml)
[![CodeQL](https://github.com/cjkrolak/ThermostatSupervisor/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/cjkrolak/ThermostatSupervisor/actions/workflows/codeql-analysis.yml)
[![Build Status](https://dev.azure.com/cjkrolak/cjkrolak/_apis/build/status/cjkrolak.ThermostatSupervisor?branchName=develop)](https://dev.azure.com/cjkrolak/cjkrolak/_build/latest?definitionId=1&branchName=develop)
[![Docker Image CI](https://github.com/cjkrolak/ThermostatSupervisor/actions/workflows/docker-image.yml/badge.svg)](https://github.com/cjkrolak/ThermostatSupervisor/actions/workflows/docker-image.yml)
[![OSSAR](https://github.com/cjkrolak/ThermostatSupervisor/actions/workflows/ossar-analysis.yml/badge.svg)](https://github.com/cjkrolak/ThermostatSupervisor/actions/workflows/ossar-analysis.yml)
[![Pylint](https://github.com/cjkrolak/ThermostatSupervisor/actions/workflows/pylint.yml/badge.svg)](https://github.com/cjkrolak/ThermostatSupervisor/actions/workflows/pylint.yml)

# ThermostatSupervisor:
supervisor to detect and correct thermostat deviations<br/>

# Thermostat & Temperature Monitor Support:
1. Honeywell thermostat through TCC web site (user must configure TCC web site credentials as environment variables).
2. 3M50 thermostat on local net (user must provide local IP address of each 3m50 thermostat zone).
3. SHT31 temperature sensor either locally or remote (user must provide local/remote IP address in environment variables and setup firewall port routing if remote).
4. Mitsubishi ductless thermostat through Kumocloud on remote network (monitoring) or local network (monitoring and control).
5. Blink camera temperature sensors.

# errata:
1. Honeywell thermostat support through TCC web site requires 3 minute poll time (or longer).  Default for this thermostat is set to 10 minutes.
2. a few other low frequency intermittent issues exist, refer to issues in github repo for details.
3. KumoCloud remote connection currently only supports monitoring, cannot set or revert settings.
4. supervisor_flask_server not currently working on Linux server.

# Build Information:
## dependencies:
pyhtcc for Honeywell thermostats (pip3 install pyhtcc)<br/>
radiotherm for 3m50 thermostats (mhrivnak/radiotherm or pip3 install radiotherm)<br/>
flask, flask-resful, and fask-wtf for sht31 flask server<br/>
flask and flask-wtf for supervisor flask server<br/>
pykumo for kumocloud<br/>
blinkpy for blink camera temp sensor support<br/>
coverage for code coverage analysis<br/>
psutil for all thermostat types<br/>
refer to requirements.txt for full list of package dependencies.<br/>

## Run the Docker Image:
docker run --rm -it --privileged --env-file 'envfile' 'username'/thermostatsupervisor:'tag' thermostatsupervisor.'module' 'runtime parameters'<br/>
* '--rm' removes the docker container when done<br/>
* '-it' runs in interactive mode so that output is displayed in the console<br/>
* '--env-file' specifies your env variables from file 'envfile', see below for required env variables<br/>
* '--privileged' runs in privileged mode, this may be required to avoid PermissionErrors with device objects<br/>
* 'username' is your DockerHub username<br/>
* 'tag' is the Docker image tag (e.g. 'develop', 'main', etc.)<br/>
* 'module' is the module to run, (e.g. 'supervise', 'honeywell', 'kumocloud', etc.).<br/>
* 'runtime parameters' are supervise runtime parameters as specified below.<br/>

## GitHub repository environment variables required for docker image build (settings / secrets):
* 'DOCKER_USERNAME' is your DockerHub username<br/>
* 'DOCKER_PASSWORD' is your DockerHub password<br/>

# Execution Information:
## debug / diagnostics:
1. Honeywell pyhtcc.txt file in /home/pi/log/pyhtcc/ shows logging specific to pyhtcc class
2. ./data/ folder contains supervisor logs

## required environment variables:<br/>
Environment variables required depend on the thermostat being used.<br/>
* All configurations require the GMAIL env vars:
  * 'GMAIL_USERNAME': email account to send notifications from (source) and to (destination)
  * 'GMAIL_PASSWORD': password for GMAIL_USERNAME
* Honeywell thermostat requires the 'TCC' env vars:
  * 'TCC_USERNAME':  username to Honeywell TCC website
  * 'TCC_PASSWORD':  password for TCC_USERNAME
* SHT31 temp sensor requires the 'SHT31' env vars:
  * 'SHT31_REMOTE_IP_ADDRESS_'zone'': remote IP address / URL for SHT31 thermal sensor, 'zone' is the zone number.
* Mitsubishi ductless requires the 'KUMOCLOUD' env vars:
  * 'KUMO_USERNAME': username for Kumocloud account
  * 'KUMO_PASSWORD': password for Kumocloud account
* Blink camera temp sensor requires the 'BLINK' env vars:
  * 'BLINK_USERNAME': username for Blink account
  * 'BLINK_PASSWORD': password for Blink account
  * 'BLINK_2FA': 2 factor auth string for Blink account

## updating environment variables:<br/>
* Linux: update file ~/.profile and then "source ~/.profile" to load the file<br/>
* Windows: define env variables in control panel and then re-start IDE<br/>
* docker image: export the env files to a text file and specify during the docker run command<br/>

# Source Code Information:
## supervise.py:
This is the main entry point script.<br/>
runtime parameters can be specified to override defaults either via single dash named parameters or values in order:<br/>
* '-h'= help screen
* argv[1] or '-t'= Thermostat type, currently support "honeywell", "mmm50", "sht31", "kumocloud", "kumolocal" and "blink".  Default is "honeywell".
* argv[2] or '-z'= zone, currently support:
  * honeywell = zone 0 only
  * 3m50 = zones [0,1] on local net
  * sht31: 0 = local net, 1 = remote URL
  * kumocloud, kumolocal: [0,1]
  * blink = [0,1,2,3,4,5,6,7,8]
  * emulator = zone 0 only
* argv[3] or '-p'= poll time in seconds (default is thermostat-specific)
* argv[4] or '-c'= re-connect time in seconds (default is thermostat-specific)
* argv[5] or '-d'= tolerance from setpoint allowed in degrees (default is 2 degrees)
* argv[6] or '-m'= target thermostat mode (e.g. OFF_MODE, COOL_MODE, HEAT_MODE, DRY_MODE, etc.), not yet fully functional.
* argv[7] or '-n'= number of measurements (default is infinitity).<br/><br/>
command line usage (unnamed):  "*python -m thermostatsupervisor.supervise \<thermostat type\> \<zone\> \<poll time\> \<connection time\> \<tolerance\> \<target mode\> \<measurements\>*".<br/>
command line usage (named):  "*python -m thermostatsupervisor.supervise -t \<thermostat type\> -z \<zone\> -p \<poll time\> -c \<connection time\> -d \<tolerance\> -m \<target mode\> -n \<measurements\>*"
  
## supervisor_flask_server.py:
This module will render supervise.py output on an HTML page using Flask.<br/>
Same runtime parameters as supervise.py can be specified to override defaults:<br/>
Port is currently hard-coded to 5001, access at server's local IP address<br/><br/>
command line usage:  "*python -m thermostatsupervisor.supervisor_flask_server \<runtime parameters\>*"

## emulator.py:
Script will run an emulator with fabribated thermostat meta data.<br/><br/>
command line usage:  "*python -m thermostatsupervisor.emulator \<thermostat type\> \<zone\>*"

## honeywell.py:
Script will logon to TCC web site and query thermostat meta data.<br/>
Default poll time is currently set to 3 minutes, longer poll times experience connection errors, shorter poll times are impractical based on emperical data.<br/><br/>
command line usage:  "*python -m thermostatsupervisor.honeywell \<thermostat type\> \<zone\>*"

## mmm50.py:
Script will connect to 3m50 thermostat on local network, IP address stored in mmm_config.mmm_metadata.<br/>
Default poll time is currently set to 10 minutes.<br/><br/>
command line usage:  "*python -m thermostatsupervisor.mmm \<thermostat type\> \<zone\>*"

## sht31.py:
Script will connect to sht31 thermometer at URL specified (can be local IP or remote URL).<br/>
Default poll time is currently set to 1 minute.<br/><br/>
command line usage:  "*python -m thermostatsupervisor.sht31 \<thermostat type\> \<zone\>*"

## sht31_flask_server.py:
This module will render sht31 sensor output on an HTML page using Flask.<br/>
Port is currently hard-coded to 5000.<br/>
Production data is at root, subfolders provide additional commands:<br/>
* /unit: unit test (fabricated) data
* /diag: fault register data
* /clear_diag: clear the fault register
* /enable_heater: enable the internal heater
* /disable_heater: disable the internal heater
* /soft_reset: perform soft reset
* /reset: perform hard reset<br/>

### server command line usage:<br/>
"*python -m thermostatsupervisor.sht31_flask_server \<debug\>*"<br/>
argv[1] = debug (bool): True to enable Flask debug mode, False is default.<br/>

### client URL usage:<br/>
production: "*\<ip\>:\<port\>?measurements=\<measurements\>*"<br/>
unit test: "*\<ip\>:\<port\>/unit?measurements=\<measurements\>&seed=\<seed\>*"<br/>
diag: "*\<ip\>:\<port\>/diag*"<br/>
measurements=number of measurements to average (default=10)<br/>
seed=seed value for fabricated data in unit test mode (default=0x7F)<br/>

## kumocloud.py:
Script will connect to Mitsubishi ductless thermostat through kumocloud account only.<br/>
Default poll time is currently set to 10 minutes.<br/>
Zone number refers to the thermostat order in kumocloud, 0=first thermostat data returned, 1=second thermostat, etc.<br/><br/>
command line usage:  "*python -m thermostatsupervisor.kumocloud \<thermostat type\> \<zone\>*"

## kumolocal.py:
Script will connect to Mitsubishi ductless thermostat through kumocloud account and local network.<br/>
Default poll time is currently set to 10 minutes.<br/>
Zone number refers to the thermostat order in kumocloud, 0=first thermostat data returned, 1=second thermostat, etc.<br/><br/>
command line usage:  "*python -m thermostatsupervisor.kumolocal \<thermostat type\> \<zone\>*"

## blink.py:
Script will connect to Blink camera through Blink account.<br/>
Default poll time is currently set to 10 minutes.<br/>
Zone number refers to the thermostat order in Blink server, 0=first thermostat data returned, 1=second thermostat, etc.<br/><br/>
command line usage:  "*python -m thermostatsupervisor.blink \<thermostat type\> \<zone\>*"

## Supervisor API required methods:<br/>
**Thermostat class:**<br/>
* print_all_thermostat_metadata(): Print all thermostat meta data.
* get_target_zone_id(): Return the target zone ID.

**Zone class:**<br/>
* get_current_mode(): Determine whether thermostat is following schedule or if it has been deviated from schedule.
* report_heating_parameters(): Display critical thermostat settings and reading to the screen.
* get_schedule_heat_sp(): Retrieve the scheduled heat setpoint.
* set_heat_setpoint():  Sets a new heat setpoint.
* get_schedule_cool_sp(): Retrieve the scheduled cool setpoint.
* set_cool_setpoint():  Set a new cool setpoint.
* refresh_zone_info():  Refresh the zone_info attribute.
