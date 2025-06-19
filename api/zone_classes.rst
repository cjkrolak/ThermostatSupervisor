Zone Classes
=============

Zone classes represent individual zones or rooms controlled by thermostats. Each zone 
has its own temperature settings, schedules, and operational modes.

Required API Methods
-------------------

All zone classes must implement the following methods as specified in the 
ThermostatSupervisor API contract:

get_current_mode()
~~~~~~~~~~~~~~~~~

**Purpose:** Determine whether the thermostat is following its schedule or has been 
deviated from the schedule.

**Signature:** ``get_current_mode() -> str``

**Returns:** 
  - ``str``: Current operational mode (e.g., 'HEAT_MODE', 'COOL_MODE', 'AUTO_MODE', 'OFF_MODE')

**Description:** This method returns the current operational mode of the zone. It 
distinguishes between scheduled operation and manual overrides.

report_heating_parameters()
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Display critical thermostat settings and readings to the screen.

**Signature:** ``report_heating_parameters() -> None``

**Returns:** None (prints to stdout)

**Description:** Provides a comprehensive report of the zone's current heating/cooling 
parameters including temperatures, setpoints, and operational status.

get_schedule_heat_sp()
~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Retrieve the scheduled heat setpoint for the current time.

**Signature:** ``get_schedule_heat_sp() -> float``

**Returns:** 
  - ``float``: Scheduled heating setpoint in degrees Fahrenheit

**Description:** Returns the temperature that the zone should be heated to according 
to the programmed schedule.

set_heat_setpoint()
~~~~~~~~~~~~~~~~~~

**Purpose:** Set a new heat setpoint for the zone.

**Signature:** ``set_heat_setpoint(temp: int) -> None``

**Parameters:**
  - ``temp`` (int): Desired heating temperature in degrees Fahrenheit

**Returns:** None

**Description:** Changes the heating setpoint for the zone. This typically creates 
a temporary override of the programmed schedule.

get_schedule_cool_sp()
~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Retrieve the scheduled cool setpoint for the current time.

**Signature:** ``get_schedule_cool_sp() -> float``

**Returns:** 
  - ``float``: Scheduled cooling setpoint in degrees Fahrenheit

**Description:** Returns the temperature that the zone should be cooled to according 
to the programmed schedule.

set_cool_setpoint()
~~~~~~~~~~~~~~~~~~

**Purpose:** Set a new cool setpoint for the zone.

**Signature:** ``set_cool_setpoint(temp: int) -> None``

**Parameters:**
  - ``temp`` (int): Desired cooling temperature in degrees Fahrenheit

**Returns:** None

**Description:** Changes the cooling setpoint for the zone. This typically creates 
a temporary override of the programmed schedule.

refresh_zone_info()
~~~~~~~~~~~~~~~~~~

**Purpose:** Refresh the zone_info attribute with current data from the thermostat.

**Signature:** ``refresh_zone_info(force_refresh: bool = False) -> None``

**Parameters:**
  - ``force_refresh`` (bool): If True, forces a refresh regardless of cache age

**Returns:** None

**Description:** Updates the cached zone information by querying the thermostat device. 
This method implements intelligent caching to avoid excessive network requests.

Common Base Class
-----------------

ThermostatCommonZone
~~~~~~~~~~~~~~~~~~~

.. autoclass:: thermostatsupervisor.thermostat_common.ThermostatCommonZone
   :members:
   :undoc-members:
   :show-inheritance:

Base class providing common functionality for all zone implementations.

Operational Modes
~~~~~~~~~~~~~~~~

The following operational modes are supported:

.. code-block:: python

   OFF_MODE = "OFF_MODE"           # Thermostat is off
   HEAT_MODE = "HEAT_MODE"         # Heating only
   COOL_MODE = "COOL_MODE"         # Cooling only  
   AUTO_MODE = "AUTO_MODE"         # Automatic heating/cooling
   DRY_MODE = "DRY_MODE"           # Dehumidification
   FAN_MODE = "FAN_MODE"           # Fan only
   ECO_MODE = "MANUAL_ECO"         # Energy saving mode
   UNKNOWN_MODE = "UNKNOWN_MODE"   # Unable to determine mode

Key Properties
~~~~~~~~~~~~~

- ``heat_modes``: List of modes that provide heating
- ``cool_modes``: List of modes that provide cooling  
- ``controlled_modes``: List of modes where setpoints apply

Implementation Examples
----------------------

Honeywell Zone
~~~~~~~~~~~~~

.. autoclass:: thermostatsupervisor.honeywell.ThermostatZone
   :members: get_current_mode, report_heating_parameters, get_schedule_heat_sp, set_heat_setpoint, get_schedule_cool_sp, set_cool_setpoint, refresh_zone_info
   :show-inheritance:

Full implementation for Honeywell TCC-compatible thermostats.

Emulator Zone
~~~~~~~~~~~~

.. autoclass:: thermostatsupervisor.emulator.ThermostatZone
   :members: get_current_mode, report_heating_parameters, get_schedule_heat_sp, set_heat_setpoint, get_schedule_cool_sp, set_cool_setpoint, refresh_zone_info
   :show-inheritance:

Testing implementation that simulates zone behavior.

Optional Methods
---------------

Many zone classes implement additional methods for extended functionality:

Temperature Monitoring
~~~~~~~~~~~~~~~~~~~~~

- ``get_display_temp()``: Current temperature reading
- ``get_display_humidity()``: Current humidity reading (if supported)
- ``get_is_humidity_supported()``: Check if humidity sensing is available

Schedule Management
~~~~~~~~~~~~~~~~~~

- ``get_hold_mode()``: Check if schedule is being overridden
- ``get_temporary_hold_until_time()``: Get temporary override expiration
- ``get_vacation_hold_until_time()``: Get vacation mode expiration

Setpoint Queries
~~~~~~~~~~~~~~~

- ``get_heat_setpoint()``: Current heating setpoint
- ``get_cool_setpoint()``: Current cooling setpoint
- ``get_heat_setpoint_raw()``: Raw heating setpoint data
- ``get_cool_setpoint_raw()``: Raw cooling setpoint data

System Status
~~~~~~~~~~~~

- ``get_system_switch_position()``: Current system mode setting
- ``get_setpoint_change_allowed()``: Check if setpoint changes are permitted
- ``is_heat_mode()``: Check if currently in heating mode
- ``is_cool_mode()``: Check if currently in cooling mode

Data Validation
--------------

Zone classes include built-in validation for:

- Temperature range limits
- Setpoint change permissions
- Schedule override conflicts
- Network connectivity status

Error Handling
--------------

Proper error handling is implemented for:

- Network communication failures
- Invalid temperature requests
- Schedule conflicts
- Hardware limitations

Caching Strategy
---------------

Zone classes implement intelligent caching to:

- Minimize network requests
- Improve response times
- Handle temporary network outages
- Maintain data consistency

The default cache expiration is 10 seconds, but can be configured per thermostat type.