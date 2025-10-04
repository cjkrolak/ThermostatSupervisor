"""
Unit test for SHT31 empty IP address validation.

This test validates the fix for issue where SHT31 ThermostatClass
was creating invalid URLs when environment variables contain empty values.
"""

import os
import tempfile
import unittest
from unittest.mock import patch

from thermostatsupervisor import sht31
from thermostatsupervisor import utilities as util
from tests import unit_test_common as utc


class TestSHT31EmptyIP(utc.UnitTest):
    """Test SHT31 empty IP address validation."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.original_unit_test_mode = util.unit_test_mode
        self.original_cwd = os.getcwd()

    def tearDown(self):
        """Clean up after tests."""
        util.unit_test_mode = self.original_unit_test_mode
        os.chdir(self.original_cwd)
        super().tearDown()

    @patch.object(sht31.ThermostatClass, "spawn_flask_server")
    def test_empty_ip_address_raises_error_in_non_unit_test_mode(
        self, mock_spawn
    ):
        """
        Test that empty IP addresses raise ValueError in non-unit test mode.

        This ensures the server name is never blank in production.
        """
        mock_spawn.return_value = None
        util.unit_test_mode = False

        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            # Create supervisor-env.txt with empty value
            with open("supervisor-env.txt", "w") as f:
                f.write("SHT31_REMOTE_IP_ADDRESS_1=\n")

            # This should raise ValueError
            with self.assertRaises(ValueError) as context:
                sht31.ThermostatClass(1, verbose=False)

            # Verify the error message is informative
            error_msg = str(context.exception)
            self.assertIn("SHT31_REMOTE_IP_ADDRESS_1", error_msg)
            self.assertIn("empty or missing", error_msg)
            self.assertIn("Server IP address cannot be blank", error_msg)

    @patch.object(sht31.ThermostatClass, "spawn_flask_server")
    def test_empty_ip_address_uses_fallback_in_unit_test_mode(
        self, mock_spawn
    ):
        """
        Test that empty IP addresses use localhost fallback in unit test mode.

        This ensures unit tests can run without environment variables.
        """
        mock_spawn.return_value = None
        util.unit_test_mode = True

        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            # Create supervisor-env.txt with empty value
            with open("supervisor-env.txt", "w") as f:
                f.write("SHT31_REMOTE_IP_ADDRESS_1=\n")

            # This should NOT fail in unit test mode
            tstat = sht31.ThermostatClass(1, verbose=False)

            # Verify the IP address fallback works
            self.assertEqual(tstat.ip_address, "127.0.0.1")

            # Verify the URL is properly formed with localhost
            self.assertIn("http://127.0.0.1:5000", tstat.url)
            self.assertNotIn("http://:5000", tstat.url)

    @patch.object(sht31.ThermostatClass, "spawn_flask_server")
    def test_valid_ip_address_works_in_both_modes(self, mock_spawn):
        """
        Test that valid IP addresses work correctly in both modes.
        """
        mock_spawn.return_value = None

        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            # Create supervisor-env.txt with valid IP
            with open("supervisor-env.txt", "w") as f:
                f.write("SHT31_REMOTE_IP_ADDRESS_1=192.168.1.100\n")

            # Test in non-unit test mode
            util.unit_test_mode = False
            tstat = sht31.ThermostatClass(1, verbose=False)
            self.assertEqual(tstat.ip_address, "192.168.1.100")
            self.assertIn("http://192.168.1.100:5000", tstat.url)

            # Test in unit test mode
            util.unit_test_mode = True
            tstat = sht31.ThermostatClass(1, verbose=False)
            self.assertEqual(tstat.ip_address, "192.168.1.100")
            self.assertIn("http://192.168.1.100:5000", tstat.url)

    @patch.object(sht31.ThermostatClass, "spawn_flask_server")
    def test_none_ip_address_raises_error_in_non_unit_test_mode(
        self, mock_spawn
    ):
        """
        Test that None IP addresses raise ValueError in non-unit test mode.
        """
        mock_spawn.return_value = None
        util.unit_test_mode = False

        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            # Don't create supervisor-env.txt, so env var is missing
            # This should raise ValueError
            with self.assertRaises(ValueError) as context:
                sht31.ThermostatClass(1, verbose=False)

            # Verify the error message is informative
            error_msg = str(context.exception)
            self.assertIn("SHT31_REMOTE_IP_ADDRESS_1", error_msg)
            self.assertIn("empty or missing", error_msg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
