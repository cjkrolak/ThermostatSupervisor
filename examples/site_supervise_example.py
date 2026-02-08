#!/usr/bin/env python3
"""
Example script demonstrating ThermostatSite usage.

This script shows how to use the ThermostatSite class to monitor
multiple thermostats at a single site simultaneously.
"""

# local imports
from src import thermostat_site as ts
from src import utilities as util


def example_basic_usage():
    """Demonstrate basic ThermostatSite usage."""
    print("\n=== Example 1: Basic Site Usage ===\n")

    # Use default site configuration
    site = ts.ThermostatSite(verbose=True)

    # Display all zones in the site
    site.display_all_zones()

    # Display current temperatures
    site.display_all_temps()


def example_custom_config():
    """Demonstrate custom site configuration."""
    print("\n=== Example 2: Custom Site Configuration ===\n")

    # Create a custom site configuration
    custom_config = {
        "site_name": "my_home",
        "thermostats": [
            {
                "thermostat_type": "emulator",
                "zone": 0,
                "enabled": True,
                "poll_time": 30,
                "tolerance": 2,
                "target_mode": "OFF_MODE",
                "measurements": 2,
            },
            {
                "thermostat_type": "emulator",
                "zone": 1,
                "enabled": True,
                "poll_time": 30,
                "tolerance": 3,
                "target_mode": "OFF_MODE",
                "measurements": 2,
            },
        ],
    }

    site = ts.ThermostatSite(site_config_dict=custom_config, verbose=True)

    # Display configuration
    site.display_all_zones()


def example_supervise_site():
    """Demonstrate site supervision with multi-threading."""
    print("\n=== Example 3: Site Supervision ===\n")

    # Create a site configuration with quick poll times for demo
    demo_config = {
        "site_name": "demo_site",
        "thermostats": [
            {
                "thermostat_type": "emulator",
                "zone": 0,
                "enabled": True,
                "poll_time": 1,
                "tolerance": 2,
                "target_mode": "OFF_MODE",
                "measurements": 2,
            },
            {
                "thermostat_type": "emulator",
                "zone": 1,
                "enabled": True,
                "poll_time": 1,
                "tolerance": 2,
                "target_mode": "OFF_MODE",
                "measurements": 2,
            },
        ],
    }

    site = ts.ThermostatSite(site_config_dict=demo_config, verbose=True)

    # Run supervision with multi-threading
    print("Starting multi-threaded supervision...")
    result = site.supervise_all_zones(use_threading=True)

    # Display results summary
    print(f"\n{'='*60}")
    print("Supervision Results Summary")
    print(f"{'='*60}")

    # Handle the new return format with results and errors
    results = result.get("results", {})
    errors = result.get("errors", {})

    for thermostat_key, measurements in results.items():
        print(f"\n{thermostat_key}:")
        for measurement in measurements:
            # Safe formatting with None handling
            temp = measurement.get("temperature")
            humidity = measurement.get("humidity")
            mode = measurement.get("mode", "N/A")

            if isinstance(temp, (int, float)):
                temp_str = f"{temp:.1f}°F"
            else:
                temp_str = "N/A"

            if isinstance(humidity, (int, float)):
                humidity_str = f"{humidity:.1f}%"
            else:
                humidity_str = "N/A"

            print(
                f"  Measurement {measurement.get('measurement', 'N/A')}: "
                f"{temp_str}, {humidity_str}, Mode: {mode}"
            )

    # Display any errors
    if errors:
        print(f"\n{'='*60}")
        print("Errors:")
        print(f"{'='*60}")
        for thermostat_key, error_info in errors.items():
            print(f"\n{thermostat_key}: {error_info.get('error', 'Unknown error')}")


def example_disabled_thermostats():
    """Demonstrate thermostat exclusion via enabled flag."""
    print("\n=== Example 4: Thermostat Exclusion ===\n")

    # Create config with some thermostats disabled
    config_with_exclusions = {
        "site_name": "selective_site",
        "thermostats": [
            {
                "thermostat_type": "emulator",
                "zone": 0,
                "enabled": True,  # This one will be monitored
            },
            {
                "thermostat_type": "emulator",
                "zone": 1,
                "enabled": False,  # This one will be excluded
            },
            {
                "thermostat_type": "emulator",
                "zone": 2,
                "enabled": True,  # This one will be monitored
            },
        ],
    }

    site = ts.ThermostatSite(
        site_config_dict=config_with_exclusions,
        verbose=True
    )

    # Display zones (notice only enabled ones in supervision list)
    site.display_all_zones()


def main():
    """Run all examples."""
    util.log_msg.debug = True  # type: ignore[attr-defined]

    print("\n" + "="*60)
    print("ThermostatSite Usage Examples")
    print("="*60)

    # Run examples
    example_basic_usage()
    example_custom_config()
    example_disabled_thermostats()
    example_supervise_site()

    print("\n" + "="*60)
    print("Examples completed successfully!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
