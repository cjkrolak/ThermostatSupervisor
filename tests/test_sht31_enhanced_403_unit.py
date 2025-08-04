"""
Unit test module for enhanced 403 error handling in sht31.py.

These tests verify that the enhanced 403 error messages provide better
feedback when IP addresses are blocked by ipban.
"""
# built-in imports
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Mock the RPi.GPIO import before importing sht31
sys.modules['RPi'] = MagicMock()
sys.modules['RPi.GPIO'] = MagicMock()
sys.modules['smbus2'] = MagicMock()

# local imports
from thermostatsupervisor import sht31
from thermostatsupervisor import sht31_config
from tests import unit_test_common as utc


@unittest.skipIf(False, "Test always enabled for 403 error validation")
class Enhanced403ErrorTest(utc.UnitTest):
    """Test enhanced 403 error handling in sht31.py."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_zone = sht31_config.UNIT_TEST_ZONE
        # Use unit test path to avoid real server connections
        self.thermostat = sht31.ThermostatClass(
            zone=self.test_zone,
            path=sht31_config.flask_folder.unit_test,
            verbose=False
        )
        self.thermostat_zone = sht31.ThermostatZone(
            self.thermostat,
            verbose=False
        )

    @patch('thermostatsupervisor.sht31.requests.get')
    def test_ipban_403_error_thermostat_class(self, mock_get):
        """Test enhanced 403 error message for ipban block in ThermostatClass."""
        # Mock a 403 response with ipban message
        mock_response = MagicMock()
        mock_response.text = (
            "403 Forbidden: You don't have the permission to access the "
            "requested resource. It is either read-protected or not "
            "readable by the server."
        )
        mock_get.return_value = mock_response

        # Test that the enhanced error message is generated
        with self.assertRaises(RuntimeError) as context:
            self.thermostat.get_metadata(zone=self.test_zone, retry=False)

        error_message = str(context.exception)
        # Verify the enhanced error message contains key information
        self.assertIn("IP address", error_message)
        self.assertIn("blocked due to suspicious activity", error_message)
        self.assertIn("IP ban protection mechanism", error_message)
        self.assertIn("clear_block_list endpoint", error_message)

    @patch('thermostatsupervisor.sht31.requests.get')
    def test_generic_403_error_thermostat_class(self, mock_get):
        """Test generic 403 error message for non-ipban 403 errors."""
        # Mock a 403 response without ipban message
        mock_response = MagicMock()
        mock_response.text = "403 Forbidden: Access denied for other reasons"
        mock_get.return_value = mock_response

        # Test that the generic error message is generated
        with self.assertRaises(RuntimeError) as context:
            self.thermostat.get_metadata(zone=self.test_zone, retry=False)

        error_message = str(context.exception)
        # Verify the generic error message
        self.assertIn("FATAL ERROR 403: client is forbidden", error_message)
        self.assertNotIn("IP ban protection mechanism", error_message)

    @patch('thermostatsupervisor.sht31.requests.get')
    def test_ipban_403_error_thermostat_zone(self, mock_get):
        """Test enhanced 403 error message for ipban block in ThermostatZone."""
        # Mock a 403 response with ipban message
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = (
            "You don't have the permission to access the requested resource. "
            "It is either read-protected or not readable by the server."
        )
        mock_get.return_value = mock_response

        # Test that the enhanced error message is generated
        with self.assertRaises(RuntimeError) as context:
            self.thermostat_zone.get_metadata(retry=False)

        error_message = str(context.exception)
        # Verify the enhanced error message contains key information
        self.assertIn("IP address", error_message)
        self.assertIn("blocked due to suspicious activity", error_message)
        self.assertIn("IP ban protection mechanism", error_message)
        self.assertIn("clear_block_list endpoint", error_message)

    @patch('thermostatsupervisor.sht31.requests.get')
    def test_generic_403_error_thermostat_zone(self, mock_get):
        """Test generic 403 error message for non-ipban 403 errors."""
        # Mock a 403 response without ipban message
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Access denied for other reasons"
        mock_get.return_value = mock_response

        # Test that the generic error message is generated
        with self.assertRaises(RuntimeError) as context:
            self.thermostat_zone.get_metadata(retry=False)

        error_message = str(context.exception)
        # Verify the generic error message
        self.assertIn("FATAL ERROR 403: client is forbidden", error_message)
        self.assertNotIn("IP ban protection mechanism", error_message)

    @patch('socket.gethostbyname')
    @patch('socket.gethostname')
    @patch('thermostatsupervisor.sht31.requests.get')
    def test_ip_address_detection(self, mock_get, mock_hostname, mock_gethostbyname):
        """Test IP address detection in error message."""
        # Mock socket functions
        mock_hostname.return_value = "test-host"
        mock_gethostbyname.return_value = "192.168.1.100"

        # Mock a 403 response with ipban message
        mock_response = MagicMock()
        mock_response.text = (
            "403 Forbidden: You don't have the permission to access the "
            "requested resource. It is either read-protected or not "
            "readable by the server."
        )
        mock_get.return_value = mock_response

        # Test that the IP address is included in the error message
        with self.assertRaises(RuntimeError) as context:
            self.thermostat.get_metadata(zone=self.test_zone, retry=False)

        error_message = str(context.exception)
        self.assertIn("192.168.1.100", error_message)

    @patch('socket.gethostbyname', side_effect=OSError("Network error"))
    @patch('socket.gethostname', side_effect=OSError("Network error"))
    @patch('thermostatsupervisor.sht31.requests.get')
    def test_ip_address_fallback(self, mock_get, mock_hostname, mock_gethostbyname):
        """Test fallback when IP address detection fails."""
        # Mock a 403 response with ipban message
        mock_response = MagicMock()
        mock_response.text = (
            "403 Forbidden: You don't have the permission to access the "
            "requested resource. It is either read-protected or not "
            "readable by the server."
        )
        mock_get.return_value = mock_response

        # Test that fallback IP is used when detection fails
        with self.assertRaises(RuntimeError) as context:
            self.thermostat.get_metadata(zone=self.test_zone, retry=False)

        error_message = str(context.exception)
        self.assertIn("IP address unknown", error_message)


if __name__ == "__main__":
    unittest.main()