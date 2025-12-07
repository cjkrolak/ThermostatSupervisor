"""
Unit test to verify sht31.py does not import server dependencies.

This test validates that the refactoring successfully eliminates
the server-side dependency from the client-side sht31.py module.
"""

import sys
import unittest
from unittest.mock import patch

from tests import unit_test_common as utc


class TestSHT31ImportIsolation(utc.UnitTest):
    """Test that sht31.py doesn't load Flask dependencies unnecessarily."""

    def test_flask_not_loaded_on_module_import(self):
        """Test that Flask is not loaded when importing sht31 module."""
        # Remove sht31 module if already loaded
        # Use list() to create a snapshot to avoid RuntimeError in Python 3.13+
        modules_to_remove = [
            key for key in list(sys.modules.keys())
            if 'sht31' in key or 'flask' in key.lower()
        ]
        for module in modules_to_remove:
            del sys.modules[module]

        # Verify Flask is not in sys.modules before import
        self.assertModuleNotIn('flask')
        self.assertModuleNotIn('flask_restful')
        self.assertModuleNotIn('flask_limiter')

        # Import sht31 module
        from thermostatsupervisor import sht31  # noqa: F401

        # Verify Flask dependencies are still not loaded
        self.assertModuleNotIn(
            'flask', "Flask should not be loaded on sht31 import"
        )
        self.assertModuleNotIn(
            'flask_restful',
            "flask_restful should not be loaded on sht31 import"
        )
        self.assertModuleNotIn(
            'flask_limiter',
            "flask_limiter should not be loaded on sht31 import"
        )

    def test_flask_not_loaded_for_regular_zone(self):
        """Test that Flask is not loaded when creating a regular zone."""
        # Remove modules to get a clean state
        # Use list() to create a snapshot to avoid RuntimeError in Python 3.13+
        modules_to_remove = [
            key for key in list(sys.modules.keys())
            if 'sht31_flask_server' in key or 'flask' in key.lower()
        ]
        for module in modules_to_remove:
            del sys.modules[module]

        # Import sht31 and create regular zone
        from thermostatsupervisor import sht31

        # Mock to avoid actual network calls
        with patch.object(
            sht31.ThermostatClass,
            'get_target_zone_id',
            return_value='127.0.0.1'
        ):
            # Create a regular zone (not zone 99)
            tstat = sht31.ThermostatClass(1, verbose=False)

            # Verify thermostat was created
            self.assertIsNotNone(tstat)
            self.assertEqual(tstat.zone_name, 1)

            # Verify Flask dependencies are still not loaded
            self.assertModuleNotIn(
                'flask',
                "Flask should not be loaded for regular zone instantiation"
            )
            self.assertModuleNotIn(
                'flask_restful',
                "flask_restful should not be loaded for regular zone"
            )
            self.assertModuleNotIn(
                'thermostatsupervisor.sht31_flask_server',
                "sht31_flask_server should not be loaded for regular zone"
            )

    def test_flask_loaded_only_for_unit_test_zone(self):
        """Test that Flask IS loaded when creating unit test zone."""
        # Remove modules to get a clean state
        # Use list() to create a snapshot to avoid RuntimeError in Python 3.13+
        modules_to_remove = [
            key for key in list(sys.modules.keys())
            if 'sht31_flask_server' in key or 'flask' in key.lower()
        ]
        for module in modules_to_remove:
            del sys.modules[module]

        # Import sht31 and utilities
        from thermostatsupervisor import sht31
        from thermostatsupervisor import utilities as util

        # Ensure unit_test_mode is True (required for Flask server spawn)
        util.unit_test_mode = True

        # Verify Flask is not loaded yet
        self.assertModuleNotIn('flask')

        # Mock to avoid actual network calls
        with patch.object(
            sht31.ThermostatClass,
            'get_target_zone_id',
            return_value='127.0.0.1'
        ):
            # Create unit test zone (zone 99) which should load Flask
            tstat = sht31.ThermostatClass(99, verbose=False)

            # Verify thermostat was created
            self.assertIsNotNone(tstat)
            self.assertEqual(tstat.zone_name, 99)

            # Verify Flask dependencies ARE now loaded (because of zone 99)
            self.assertModuleIn(
                'flask', "Flask should be loaded for unit test zone 99"
            )
            self.assertModuleIn(
                'thermostatsupervisor.sht31_flask_server',
                "sht31_flask_server should be loaded for unit test zone 99"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
