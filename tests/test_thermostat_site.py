"""
Unit test module for thermostat_site.py.
"""

# built-in imports
import unittest

# local imports
from thermostatsupervisor import site_config
from thermostatsupervisor import thermostat_site as ts
from thermostatsupervisor import utilities as util
from tests import unit_test_common as utc


class TestThermostatSite(utc.UnitTest):
    """Test functions in thermostat_site.py."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        # Create a test site configuration
        self.test_site_config = {
            "site_name": "test_site",
            "thermostats": [
                {
                    "thermostat_type": "emulator",
                    "zone": 0,
                    "enabled": True,
                    "poll_time": 1,
                    "connection_time": 10,
                    "tolerance": 2,
                    "target_mode": "OFF_MODE",
                    "measurements": 1,
                },
                {
                    "thermostat_type": "emulator",
                    "zone": 1,
                    "enabled": True,
                    "poll_time": 1,
                    "connection_time": 10,
                    "tolerance": 2,
                    "target_mode": "OFF_MODE",
                    "measurements": 1,
                },
            ],
        }

    def tearDown(self):
        """Clean up after tests."""
        super().tearDown()

    def test_site_initialization(self):
        """Verify ThermostatSite initializes correctly."""
        site = ts.ThermostatSite(
            site_config_dict=self.test_site_config,
            verbose=False
        )
        self.assertEqual(site.site_name, "test_site")
        self.assertEqual(len(site.thermostats), 2)
        self.assertEqual(site.thermostats[0]["thermostat_type"], "emulator")

    def test_site_initialization_with_defaults(self):
        """Verify ThermostatSite uses default config when none provided."""
        site = ts.ThermostatSite(verbose=False)
        self.assertIsNotNone(site.site_name)
        self.assertIsNotNone(site.thermostats)

    def test_site_initialization_with_disabled_thermostats(self):
        """Verify disabled thermostats are filtered out."""
        config_with_disabled = {
            "site_name": "test_site",
            "thermostats": [
                {
                    "thermostat_type": "emulator",
                    "zone": 0,
                    "enabled": True,
                },
                {
                    "thermostat_type": "emulator",
                    "zone": 1,
                    "enabled": False,
                },
                {
                    "thermostat_type": "emulator",
                    "zone": 2,
                    "enabled": True,
                },
            ],
        }
        site = ts.ThermostatSite(
            site_config_dict=config_with_disabled,
            verbose=False
        )
        # Should only have 2 enabled thermostats
        self.assertEqual(len(site.thermostats), 2)
        # Verify disabled thermostat is not in the list
        zones = [t["zone"] for t in site.thermostats]
        self.assertNotIn(1, zones)

    def test_display_all_zones(self):
        """Verify display_all_zones shows all thermostats."""
        site = ts.ThermostatSite(
            site_config_dict=self.test_site_config,
            verbose=False
        )
        # This should not raise an exception
        site.display_all_zones()

    def test_display_all_zones_empty_site(self):
        """Verify display_all_zones handles empty site gracefully."""
        empty_config = {
            "site_name": "empty_site",
            "thermostats": [],
        }
        site = ts.ThermostatSite(
            site_config_dict=empty_config,
            verbose=False
        )
        # This should not raise an exception
        site.display_all_zones()

    def test_display_all_temps(self):
        """Verify display_all_temps queries thermostats."""
        site = ts.ThermostatSite(
            site_config_dict=self.test_site_config,
            verbose=False
        )
        # This should not raise an exception
        site.display_all_temps()

    def test_display_all_temps_empty_site(self):
        """Verify display_all_temps handles empty site gracefully."""
        empty_config = {
            "site_name": "empty_site",
            "thermostats": [],
        }
        site = ts.ThermostatSite(
            site_config_dict=empty_config,
            verbose=False
        )
        # This should not raise an exception
        site.display_all_temps()

    def test_supervise_all_zones_sequential(self):
        """Verify supervise_all_zones works in sequential mode."""
        # Use a smaller config for faster testing
        small_config = {
            "site_name": "test_site",
            "thermostats": [
                {
                    "thermostat_type": "emulator",
                    "zone": 0,
                    "enabled": True,
                    "poll_time": 1,
                    "tolerance": 2,
                    "target_mode": "OFF_MODE",
                    "measurements": 1,
                },
            ],
        }
        site = ts.ThermostatSite(
            site_config_dict=small_config,
            verbose=False
        )
        results = site.supervise_all_zones(
            measurement_count=1,
            use_threading=False
        )
        # Verify we got results
        self.assertIsInstance(results, dict)
        self.assertGreater(len(results), 0)

    def test_supervise_all_zones_threaded(self):
        """Verify supervise_all_zones works with multi-threading."""
        site = ts.ThermostatSite(
            site_config_dict=self.test_site_config,
            verbose=False
        )
        results = site.supervise_all_zones(
            measurement_count=1,
            use_threading=True
        )
        # Verify we got results from both thermostats
        self.assertIsInstance(results, dict)
        self.assertGreater(len(results), 0)
        # Check that we have measurements
        total_measurements = sum(len(v) for v in results.values())
        self.assertGreater(total_measurements, 0)

    def test_supervise_all_zones_empty_site(self):
        """Verify supervise_all_zones handles empty site gracefully."""
        empty_config = {
            "site_name": "empty_site",
            "thermostats": [],
        }
        site = ts.ThermostatSite(
            site_config_dict=empty_config,
            verbose=False
        )
        results = site.supervise_all_zones(measurement_count=1)
        # Should return empty dict
        self.assertIsInstance(results, dict)
        self.assertEqual(len(results), 0)

    def test_default_site_config(self):
        """Verify default site config is valid."""
        config = site_config.get_default_site_config()
        self.assertIsInstance(config, dict)
        self.assertIn("site_name", config)
        self.assertIn("thermostats", config)
        self.assertIsInstance(config["thermostats"], list)


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
