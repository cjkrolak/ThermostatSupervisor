Thermostat API Module
=====================

The ``thermostat_api`` module provides the core API functionality for ThermostatSupervisor.
This module handles thermostat type discovery, configuration loading, and user input processing.

.. automodule:: src.thermostat_api
   :members:
   :undoc-members:
   :show-inheritance:

Key Functions
-------------

verify_required_env_variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: src.thermostat_api.verify_required_env_variables

Verifies that all required environment variables are present for the specified thermostat type.
This function is critical for ensuring proper thermostat connectivity.

**Parameters:**
  - ``tstat`` (str): Thermostat type alias
  - ``zone_str`` (str): Zone identifier as string
  - ``verbose`` (bool): Enable debug output

**Returns:**
  - ``bool``: True if all required environment variables are present

**Raises:**
  - ``KeyError``: If required environment variables are missing

load_hardware_library
~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: src.thermostat_api.load_hardware_library

Dynamically loads the appropriate hardware library for the specified thermostat type.

**Parameters:**
  - ``thermostat_type`` (str): Thermostat type alias

**Returns:**
  - ``module``: Loaded Python module for the thermostat type

load_user_inputs
~~~~~~~~~~~~~~~~

.. autofunction:: src.thermostat_api.load_user_inputs

Loads and processes user input configurations for the specified thermostat.

**Parameters:**
  - ``config_mod`` (module): Configuration module for the thermostat type

Classes
-------

UserInputs
~~~~~~~~~~

.. autoclass:: src.thermostat_api.UserInputs
   :members:
   :undoc-members:
   :show-inheritance:

Manages runtime arguments and configuration for thermostat operations.

Key Methods:

- ``initialize_user_inputs()``: Set up input parameter parsing
- ``dynamic_update_user_inputs()``: Update inputs based on thermostat configuration
- ``max_measurement_count_exceeded()``: Check if measurement limits are exceeded

Configuration Data
------------------

SUPPORTED_THERMOSTATS
~~~~~~~~~~~~~~~~~~~~~

Dictionary containing configuration information for all supported thermostat types:

.. code-block:: python

   SUPPORTED_THERMOSTATS = {
       'emulator': {
           'module': 'emulator',
           'type': 0,
           'zones': [0, 1, 2],
           'modes': ['HEAT_MODE', 'COOL_MODE', 'AUTO_MODE']
       },
       # ... additional thermostat configurations
   }

thermostats
~~~~~~~~~~~

Dictionary mapping thermostat types to their required environment variables:

.. code-block:: python

   thermostats = {
       'honeywell': {
           'required_env_variables': [
               'HONEYWELL_USERNAME',
               'HONEYWELL_PASSWORD'
           ]
       },
       # ... additional thermostat configurations
   }

Input Field Definitions
-----------------------

The module defines standard input field names used throughout the application:

.. code-block:: python

   input_flds.thermostat_type = "thermostat_type"
   input_flds.zone = "zone"
   input_flds.poll_time = "poll_time"
   input_flds.connection_time = "connection_time"
   input_flds.tolerance = "tolerance"
   input_flds.target_mode = "target_mode"
   input_flds.measurements = "measurements"
   input_flds.input_file = "input_file"