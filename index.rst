.. ThermostatSupervisor documentation master file

ThermostatSupervisor API Documentation
=======================================

Welcome to ThermostatSupervisor's API documentation. This project provides a comprehensive
framework for monitoring and controlling various thermostat types remotely.

Overview
--------

ThermostatSupervisor supports multiple thermostat brands and types including:

* Honeywell (via pyhtcc)
* 3M-50 thermostats (via radiotherm)
* KumoCloud/KumoLocal
* Nest thermostats
* Blink cameras (temperature sensors)
* SHT31 temperature sensors
* Emulator for testing

Key Features
------------

* Remote thermostat monitoring and control
* Flask-based web interface
* Scheduled temperature management
* Deviation detection and correction
* Multi-zone support
* Temperature and humidity logging
* Email notifications

.. toctree::
   :maxdepth: 2
   :caption: API Documentation:
   
   api/overview
   api/thermostat_api
   api/thermostat_classes
   api/zone_classes

.. toctree::
   :maxdepth: 2
   :caption: Module Reference:
   
   docs/src

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

