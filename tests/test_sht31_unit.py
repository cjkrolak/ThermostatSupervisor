"""
Unit tests for sht31.py to improve code coverage.

This test file focuses on edge cases and error paths that are not
covered by existing integration and functional tests.
"""

import json
import unittest
from unittest.mock import Mock, patch
import requests

from thermostatsupervisor import sht31
from thermostatsupervisor import utilities as util


class TestSht31EdgeCases(unittest.TestCase):
    """Test edge cases and error paths in sht31 module."""

    def setUp(self):
        """Set up test environment."""
        # Mock unit_test_mode to avoid spawning Flask server
        self.original_unit_test_mode = util.unit_test_mode
        util.unit_test_mode = False

    def tearDown(self):
        """Clean up test environment."""
        util.unit_test_mode = self.original_unit_test_mode

    @patch('thermostatsupervisor.environment.get_env_variable')
    def test_should_use_fallback_with_none(self, mock_env):
        """Test _should_use_fallback with None value."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        result = tstat._should_use_fallback(None)
        self.assertTrue(result)

    @patch('thermostatsupervisor.environment.get_env_variable')
    def test_should_use_fallback_with_non_string(self, mock_env):
        """Test _should_use_fallback with non-string value."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        # Non-string values should return False
        result = tstat._should_use_fallback(123)
        self.assertFalse(result)

        result = tstat._should_use_fallback(['list'])
        self.assertFalse(result)

    @patch('thermostatsupervisor.environment.get_env_variable')
    def test_should_use_fallback_with_whitespace(self, mock_env):
        """Test _should_use_fallback with whitespace-only strings."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        # Whitespace-only strings should return True
        result = tstat._should_use_fallback("   ")
        self.assertTrue(result)

        result = tstat._should_use_fallback("\t\n")
        self.assertTrue(result)

    @patch('thermostatsupervisor.environment.get_env_variable')
    def test_should_use_fallback_with_placeholder_in_unit_test_mode(
        self, mock_env
    ):
        """Test _should_use_fallback with placeholder in unit test mode."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        # Enable unit test mode temporarily
        original_mode = util.unit_test_mode
        util.unit_test_mode = True

        try:
            # Placeholder patterns should return True in unit test mode
            result = tstat._should_use_fallback("***")
            self.assertTrue(result)

            result = tstat._should_use_fallback("  ***  ")
            self.assertTrue(result)

            # Valid IP should return False
            result = tstat._should_use_fallback("192.168.1.100")
            self.assertFalse(result)

        finally:
            util.unit_test_mode = original_mode

    @patch('thermostatsupervisor.environment.get_env_variable')
    def test_handle_403_error_with_ipban_message(self, mock_env):
        """Test _handle_403_error with IP ban message."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        # Create mock response with IP ban message
        mock_response = Mock()
        mock_response.text = (
            "You don't have the permission to access the "
            "requested resource. It is either read-protected "
            "or not readable by the server."
        )

        with self.assertRaises(RuntimeError) as context:
            tstat._handle_403_error(mock_response)

        self.assertIn("IP address", str(context.exception))
        self.assertIn("blocked", str(context.exception))

    @patch('thermostatsupervisor.environment.get_env_variable')
    def test_handle_403_error_without_ipban_message(self, mock_env):
        """Test _handle_403_error without IP ban message."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        # Create mock response with generic 403 error
        mock_response = Mock()
        mock_response.text = "Forbidden - some other reason"

        with self.assertRaises(RuntimeError) as context:
            tstat._handle_403_error(mock_response)

        self.assertIn("403", str(context.exception))
        self.assertIn("forbidden", str(context.exception))

    @patch('thermostatsupervisor.environment.get_env_variable')
    def test_parse_response_json_decode_error(self, mock_env):
        """Test _parse_response with JSON decode error."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        # Create mock response that raises JSONDecodeError
        mock_response = Mock()
        mock_response.json.side_effect = json.decoder.JSONDecodeError(
            "Invalid JSON", "doc", 0
        )

        with self.assertRaises(RuntimeError) as context:
            tstat._parse_response(mock_response, None)

        self.assertIn("not responding", str(context.exception))

    @patch('thermostatsupervisor.environment.get_env_variable')
    def test_parse_response_with_parameter(self, mock_env):
        """Test _parse_response with parameter extraction."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        # Create mock response with JSON data
        mock_response = Mock()
        mock_response.json.return_value = {
            "temperature": 72.5,
            "humidity": 45.2
        }

        result = tstat._parse_response(mock_response, "temperature")
        self.assertEqual(result, 72.5)

    @patch('thermostatsupervisor.environment.get_env_variable')
    def test_parse_response_without_parameter(self, mock_env):
        """Test _parse_response without parameter."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        # Create mock response with JSON data
        mock_response = Mock()
        mock_data = {"temperature": 72.5, "humidity": 45.2}
        mock_response.json.return_value = mock_data

        result = tstat._parse_response(mock_response, None)
        self.assertEqual(result, mock_data)

    @patch('thermostatsupervisor.utilities.execute_with_extended_retries')
    @patch('thermostatsupervisor.environment.get_env_variable')
    def test_execute_with_retry_delegates_correctly(
        self, mock_env, mock_retry
    ):
        """Test _execute_with_retry delegates to utilities correctly."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        # Mock the retry function
        mock_func = Mock(return_value="success")
        mock_retry.return_value = "success"

        result = tstat._execute_with_retry(mock_func)

        # Verify it called execute_with_extended_retries
        mock_retry.assert_called_once()
        self.assertEqual(result, "success")

        # Verify the exception types include expected errors
        call_args = mock_retry.call_args
        exception_types = call_args[1]['exception_types']
        self.assertIn(requests.exceptions.ConnectionError, exception_types)
        self.assertIn(json.decoder.JSONDecodeError, exception_types)
        self.assertIn(RuntimeError, exception_types)

    @patch('thermostatsupervisor.environment.get_env_variable')
    def test_get_wifi_status_with_valid_rssi(self, mock_env):
        """Test get_wifi_status with valid RSSI value."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        # Create a zone to test
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        # Mock get_wifi_strength to return a valid value
        with patch.object(zone, 'get_wifi_strength', return_value=-50.0):
            result = zone.get_wifi_status()
            self.assertTrue(result)

    @patch('thermostatsupervisor.environment.get_env_variable')
    def test_get_wifi_status_with_weak_signal(self, mock_env):
        """Test get_wifi_status with weak signal."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        # Create a zone to test
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        # Mock get_wifi_strength to return a weak signal
        with patch.object(zone, 'get_wifi_strength', return_value=-90.0):
            result = zone.get_wifi_status()
            self.assertFalse(result)

    @patch('thermostatsupervisor.environment.get_env_variable')
    def test_get_wifi_status_with_non_numeric_rssi(self, mock_env):
        """Test get_wifi_status with non-numeric RSSI value."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        # Create a zone to test
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        # Mock get_wifi_strength to return non-numeric value
        with patch.object(zone, 'get_wifi_strength', return_value="N/A"):
            result = zone.get_wifi_status()
            self.assertFalse(result)

        # Test with None
        with patch.object(zone, 'get_wifi_strength', return_value=None):
            result = zone.get_wifi_status()
            self.assertFalse(result)

    @patch('thermostatsupervisor.environment.get_env_variable')
    def test_get_client_ip_success(self, mock_env):
        """Test _get_client_ip with successful resolution."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        # Mock socket functions
        with patch('socket.gethostname', return_value='testhost'):
            with patch('socket.gethostbyname', return_value='192.168.1.100'):
                result = tstat._get_client_ip()
                self.assertEqual(result, '192.168.1.100')

    @patch('thermostatsupervisor.environment.get_env_variable')
    def test_get_client_ip_socket_error(self, mock_env):
        """Test _get_client_ip with socket error."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        # Mock socket to raise error
        import socket
        with patch('socket.gethostname', side_effect=socket.error("Error")):
            result = tstat._get_client_ip()
            self.assertEqual(result, 'unknown')

    @patch('thermostatsupervisor.environment.get_env_variable')
    def test_get_client_ip_os_error(self, mock_env):
        """Test _get_client_ip with OS error."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        # Mock socket to raise OSError
        with patch('socket.gethostname', side_effect=OSError("Error")):
            result = tstat._get_client_ip()
            self.assertEqual(result, 'unknown')


class TestSht31ThermostatZone(unittest.TestCase):
    """Test ThermostatZone methods in sht31 module."""

    def setUp(self):
        """Set up test environment."""
        self.original_unit_test_mode = util.unit_test_mode
        util.unit_test_mode = False

    def tearDown(self):
        """Clean up test environment."""
        util.unit_test_mode = self.original_unit_test_mode

    @patch('thermostatsupervisor.environment.get_env_variable')
    def test_get_system_switch_position_with_list(self, mock_env):
        """Test get_system_switch_position when OFF_MODE is a list."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        # Create a zone to test
        from thermostatsupervisor import thermostat_common as tc
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        # Mock system_switch_position with list value
        zone.system_switch_position = {
            tc.ThermostatCommonZone.OFF_MODE: [0, 1, 2]
        }

        result = zone.get_system_switch_position()
        self.assertEqual(result, 0)

    @patch('thermostatsupervisor.environment.get_env_variable')
    def test_get_system_switch_position_with_int(self, mock_env):
        """Test get_system_switch_position when OFF_MODE is an int."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        # Create a zone to test
        from thermostatsupervisor import thermostat_common as tc
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        # Mock system_switch_position with int value
        zone.system_switch_position = {
            tc.ThermostatCommonZone.OFF_MODE: 3
        }

        result = zone.get_system_switch_position()
        self.assertEqual(result, 3)


if __name__ == "__main__":
    unittest.main()
