Thermostat Classes
==================

Thermostat classes represent the physical thermostat devices and provide methods for 
device-level operations such as retrieving metadata and managing device connections.

Required API Methods
-------------------

All thermostat classes must implement the following methods as specified in the 
ThermostatSupervisor API contract:

print_all_thermostat_metadata()
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Print all thermostat metadata to the console for debugging and inspection.

**Signature:** ``print_all_thermostat_metadata(zone: int) -> None``

**Parameters:**
  - ``zone`` (int): Target zone number

**Returns:** None (prints to stdout)

**Description:** This method retrieves and displays comprehensive metadata about the 
thermostat device, including current settings, capabilities, and status information.

get_target_zone_id()
~~~~~~~~~~~~~~~~~~~

**Purpose:** Return the target zone ID for the specified zone.

**Signature:** ``get_target_zone_id(zone: int) -> int``

**Parameters:**
  - ``zone`` (int): Zone number to look up

**Returns:** 
  - ``int``: Device-specific zone identifier

**Description:** Maps logical zone numbers to device-specific zone identifiers. This 
is necessary because different thermostat brands use different zone numbering schemes.

**Raises:**
  - ``ValueError``: If the specified zone is not valid for this thermostat

Common Base Class
-----------------

ThermostatCommon
~~~~~~~~~~~~~~~

.. autoclass:: src.thermostat_common.ThermostatCommon
   :members:
   :undoc-members:
   :show-inheritance:

Base class providing common functionality for all thermostat implementations.

Key Methods:

get_all_metadata()
******************

.. automethod:: src.thermostat_common.ThermostatCommon.get_all_metadata

Retrieves complete metadata for the specified zone.

get_metadata()
*************

.. automethod:: src.thermostat_common.ThermostatCommon.get_metadata

Retrieves specific metadata parameters for a zone.

Implementation Examples
----------------------

Honeywell Thermostat
~~~~~~~~~~~~~~~~~~~

.. autoclass:: src.honeywell.ThermostatClass
   :members: print_all_thermostat_metadata, get_target_zone_id, get_all_metadata, get_metadata
   :show-inheritance:

The Honeywell implementation provides full support for TCC-compatible thermostats.

Emulator Thermostat
~~~~~~~~~~~~~~~~~~

.. autoclass:: src.emulator.ThermostatClass
   :members: print_all_thermostat_metadata, get_target_zone_id, get_all_metadata, get_metadata
   :show-inheritance:

The emulator provides a testing implementation that simulates thermostat behavior 
without requiring actual hardware.

Optional Methods
---------------

While not required, many thermostat classes implement additional methods for 
extended functionality:

Connection Management
~~~~~~~~~~~~~~~~~~~~

- ``close()``: Explicitly close network connections
- ``__del__()``: Cleanup method for proper resource deallocation

Data Retrieval
~~~~~~~~~~~~~~

- ``get_latestdata()``: Retrieve the most recent thermostat data
- ``get_zones_info()``: Get information about all zones
- ``get_zone_device_ids()``: Get device IDs for all zones

Configuration Access
~~~~~~~~~~~~~~~~~~~

- ``get_system_info()``: Retrieve system-level configuration
- ``get_device_info()``: Get device-specific information
- ``get_capabilities()``: Query supported features

Error Handling
--------------

All thermostat classes should implement proper error handling:

- Network connectivity issues
- Authentication failures  
- Invalid zone/parameter requests
- Hardware communication errors

Connection timeouts and retries are handled automatically by the base classes.