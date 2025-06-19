API Overview
============

ThermostatSupervisor provides a unified API for interfacing with multiple thermostat types.
The API is designed with a consistent interface across all supported thermostat brands.

Core API Structure
------------------

The API is organized around two main class hierarchies:

1. **Thermostat Classes** - Represent the physical thermostat device
2. **Zone Classes** - Represent individual zones or rooms controlled by thermostats

Supported Thermostat Types
-------------------------

The following thermostat types are currently supported:

.. list-table:: Supported Thermostats
   :widths: 25 25 50
   :header-rows: 1

   * - Type
     - Module
     - Description
   * - Emulator
     - emulator
     - Testing/development emulator
   * - Honeywell
     - honeywell
     - Honeywell TCC-compatible thermostats
   * - 3M-50
     - mmm
     - 3M Filtrete 3M-50 radio thermostats
   * - KumoCloud
     - kumocloud
     - Mitsubishi KumoCloud service
   * - KumoLocal
     - kumolocal
     - Local Mitsubishi Kumo interface
   * - Nest
     - nest
     - Google Nest thermostats
   * - Blink
     - blink
     - Blink cameras (temperature sensors)
   * - SHT31
     - sht31
     - SHT31 temperature/humidity sensors

Environment Variables
--------------------

Each thermostat type requires specific environment variables to be configured:

- Username/password credentials for cloud services
- IP addresses for local network devices
- API keys for cloud services
- Zone identifiers

Refer to the specific thermostat configuration modules for detailed requirements.

Common API Patterns
------------------

All thermostat implementations follow these common patterns:

**Initialization**
  Each thermostat class is initialized with zone information and configuration.

**Metadata Retrieval**
  Methods to retrieve current thermostat status, temperature, and settings.

**Setpoint Control**
  Methods to get and set heating/cooling setpoints.

**Schedule Management**
  Methods to work with programmed schedules and temporary overrides.

**Zone Management**
  Methods to manage multiple zones within a single thermostat system.