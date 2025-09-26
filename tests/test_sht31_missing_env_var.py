"""
Unit test for SHT31 environment variable fallback logic.

This test validates the fix for issue where SHT31 ThermostatClass
was failing when environment variables are missing in unit test mode.
"""

import unittest
from unittest.mock import patch

from thermostatsupervisor import sht31
from thermostatsupervisor import sht31_config
from thermostatsupervisor import utilities as util
from tests import unit_test_common as utc


class TestSHT31MissingEnvVar(utc.UnitTest):
    """Test SHT31 environment variable fallback logic."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.original_unit_test_mode = util.unit_test_mode

    def tearDown(self):
        """Clean up after tests."""
        util.unit_test_mode = self.original_unit_test_mode
        super().tearDown()

    @patch.object(sht31.ThermostatClass, "spawn_flask_server")
    def test_missing_env_var_fallback_in_unit_test_mode(self, mock_spawn):
        """
        Test that missing environment variables fall back to localhost in unit
        test mode.

        This reproduces and fixes the exact error scenario:
        - Zone 1 (regular zone, not unit test zone 99)
        - Unit test mode enabled
        - Environment variable SHT31_REMOTE_IP_ADDRESS_1 is missing
        - Should fall back to 127.0.0.1 instead of None
        """
        mock_spawn.return_value = None
        util.unit_test_mode = True

        # This should NOT fail even if env var is missing
        tstat = sht31.ThermostatClass(1, verbose=False)

        # Verify the IP address fallback
        self.assertEqual(tstat.ip_address, "127.0.0.1")

        # Verify the URL is properly formed
        expected_components = [
            "http://127.0.0.1:5000",
            "/unit",
            "measurements=10",
            "seed=127"
        ]
        for component in expected_components:
            self.assertIn(component, tstat.url)

        # Verify URL does NOT contain None or empty host
        self.assertNotIn("http://:5000", tstat.url)
        self.assertNotIn("None", tstat.url)

    @patch.object(sht31.ThermostatClass, "spawn_flask_server")
    def test_missing_env_var_fails_in_non_unit_test_mode(self, mock_spawn):
        """
        Test that missing environment variables still fail in non-unit test
        mode.

        This ensures the fallback behavior is only active in unit test mode.
        """
        mock_spawn.return_value = None
        util.unit_test_mode = False

        # This should fail when env var is missing and not in unit test mode
        with self.assertRaises(TypeError) as context:
            sht31.ThermostatClass(1, verbose=False)

        # Should get the concatenation error because ip_address is None
        self.assertIn("can only concatenate str", str(context.exception))

    @patch.object(sht31.ThermostatClass, "spawn_flask_server")
    def test_unit_test_zone_still_works(self, mock_spawn):
        """Test that the unit test zone (99) still works as expected."""
        mock_spawn.return_value = None
        util.unit_test_mode = True

        # Zone 99 should work (this was already working before the fix)
        tstat = sht31.ThermostatClass(
            sht31_config.UNIT_TEST_ZONE,
            verbose=False
        )

        # Should get local IP via existing logic in environment.py
        self.assertIsNotNone(tstat.ip_address)
        self.assertIn("http://", tstat.url)
        self.assertNotIn("http://:5000", tstat.url)


if __name__ == "__main__":
    unittest.main(verbosity=2)
