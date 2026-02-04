"""
Unit tests for sht31.py to improve code coverage.

This test file focuses on edge cases and error paths that are not
covered by existing integration and functional tests.
"""

import json
import unittest
from unittest.mock import Mock, patch
import requests

from src import sht31
from src import utilities as util


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

    @patch('src.environment.get_env_variable')
    def test_should_use_fallback_with_none(self, mock_env):
        """Test _should_use_fallback with None value."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        result = tstat._should_use_fallback(None)
        self.assertTrue(result)

    @patch('src.environment.get_env_variable')
    def test_should_use_fallback_with_non_string(self, mock_env):
        """Test _should_use_fallback with non-string value."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        # Non-string values should return False
        result = tstat._should_use_fallback(123)
        self.assertFalse(result)

        result = tstat._should_use_fallback(['list'])
        self.assertFalse(result)

    @patch('src.environment.get_env_variable')
    def test_should_use_fallback_with_whitespace(self, mock_env):
        """Test _should_use_fallback with whitespace-only strings."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        # Whitespace-only strings should return True
        result = tstat._should_use_fallback("   ")
        self.assertTrue(result)

        result = tstat._should_use_fallback("\t\n")
        self.assertTrue(result)

    @patch('src.environment.get_env_variable')
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

    @patch('src.environment.get_env_variable')
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

    @patch('src.environment.get_env_variable')
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

    @patch('src.environment.get_env_variable')
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

    @patch('src.environment.get_env_variable')
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

    @patch('src.environment.get_env_variable')
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

    @patch('src.utilities.execute_with_extended_retries')
    @patch('src.environment.get_env_variable')
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

    @patch('src.environment.get_env_variable')
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

    @patch('src.environment.get_env_variable')
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

    @patch('src.environment.get_env_variable')
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

    @patch('src.environment.get_env_variable')
    def test_get_client_ip_success(self, mock_env):
        """Test _get_client_ip with successful resolution."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        # Mock socket functions
        with patch('socket.gethostname', return_value='testhost'):
            with patch('socket.gethostbyname', return_value='192.168.1.100'):
                result = tstat._get_client_ip()
                self.assertEqual(result, '192.168.1.100')

    @patch('src.environment.get_env_variable')
    def test_get_client_ip_socket_error(self, mock_env):
        """Test _get_client_ip with socket error."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        # Mock socket to raise error
        import socket
        with patch('socket.gethostname', side_effect=socket.error("Error")):
            result = tstat._get_client_ip()
            self.assertEqual(result, 'unknown')

    @patch('src.environment.get_env_variable')
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

    @patch('src.environment.get_env_variable')
    def test_get_system_switch_position_with_list(self, mock_env):
        """Test get_system_switch_position when OFF_MODE is a list."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        # Create a zone to test
        from src import thermostat_common as tc
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

    @patch('src.environment.get_env_variable')
    def test_get_system_switch_position_with_int(self, mock_env):
        """Test get_system_switch_position when OFF_MODE is an int."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        # Create a zone to test
        from src import thermostat_common as tc
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

    @patch('src.environment.get_env_variable')
    def test_handle_404_error(self, mock_env):
        """Test _handle_http_errors with 404 error."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        mock_response = Mock()
        mock_response.text = "404 Not Found"

        with self.assertRaises(RuntimeError) as context:
            tstat._handle_http_errors(mock_response)

        self.assertIn("404", str(context.exception))

    @patch('src.environment.get_env_variable')
    def test_get_ip_address_production_mode_with_blank_value(self, mock_env):
        """Test get_ip_address in production mode with blank value."""
        # Set up for production mode
        original_mode = util.unit_test_mode
        util.unit_test_mode = False

        try:
            mock_env.return_value = {"value": ""}
            with self.assertRaises(ValueError) as context:
                sht31.ThermostatClass(zone=0, verbose=False)

            self.assertIn("empty or missing", str(context.exception))
        finally:
            util.unit_test_mode = original_mode

    @patch('src.environment.get_env_variable')
    def test_get_ip_address_unit_test_mode_with_blank_value(self, mock_env):
        """Test get_ip_address in unit test mode with blank value."""
        original_mode = util.unit_test_mode
        util.unit_test_mode = True

        try:
            mock_env.return_value = {"value": ""}
            tstat = sht31.ThermostatClass(zone=0, verbose=False)
            # Should get localhost fallback
            self.assertEqual(tstat.ip_address, "127.0.0.1")
        finally:
            util.unit_test_mode = original_mode

    @patch('requests.get')
    @patch('src.environment.get_env_variable')
    def test_get_metadata_without_retry(self, mock_env, mock_get):
        """Test get_metadata with retry=False."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        mock_response = Mock()
        mock_response.json.return_value = {"temp": 72.5}
        mock_response.text = '{"temp": 72.5}'  # Add text attribute
        mock_get.return_value = mock_response

        result = tstat.get_metadata(zone=0, retry=False)
        self.assertEqual(result, {"temp": 72.5})

    @patch('requests.get')
    @patch('src.environment.get_env_variable')
    def test_get_all_metadata(self, mock_env, mock_get):
        """Test get_all_metadata method."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        mock_response = Mock()
        mock_response.json.return_value = {"temp": 72.5, "humidity": 45}
        mock_response.text = '{"temp": 72.5, "humidity": 45}'  # Add text
        mock_get.return_value = mock_response

        result = tstat.get_all_metadata(zone=0, retry=False)
        self.assertEqual(result, {"temp": 72.5, "humidity": 45})

    @patch('src.environment.get_env_variable')
    def test_print_all_thermostat_metadata(self, mock_env):
        """Test print_all_thermostat_metadata method."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)

        with patch.object(
            tstat, 'get_all_metadata', return_value={"temp": 72.5}
        ):
            with patch.object(
                tstat, 'exec_print_all_thermostat_metadata',
                return_value={"status": "ok"}
            ):
                result = tstat.print_all_thermostat_metadata(zone=0)
                self.assertEqual(result, {"status": "ok"})


class TestSht31ZoneMetadataMethods(unittest.TestCase):
    """Test ThermostatZone metadata and HTTP error handling methods."""

    def setUp(self):
        """Set up test environment."""
        self.original_unit_test_mode = util.unit_test_mode
        util.unit_test_mode = False

    def tearDown(self):
        """Clean up test environment."""
        util.unit_test_mode = self.original_unit_test_mode

    @patch('requests.get')
    @patch('src.environment.get_env_variable')
    def test_zone_get_metadata_without_retry(self, mock_env, mock_get):
        """Test zone get_metadata with retry=False."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        mock_response = Mock()
        mock_response.json.return_value = {"temp": 72.5}
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = zone.get_metadata(retry=False)
        self.assertEqual(result, {"temp": 72.5})

    @patch('requests.get')
    @patch('src.environment.get_env_variable')
    def test_zone_get_metadata_with_parameter(self, mock_env, mock_get):
        """Test zone get_metadata with parameter extraction."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        mock_response = Mock()
        mock_response.json.return_value = {"temp": 72.5, "humidity": 45}
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = zone.get_metadata(parameter="temp", retry=False)
        self.assertEqual(result, 72.5)

    @patch('src.environment.get_env_variable')
    def test_zone_handle_403_error_with_ipban(self, mock_env):
        """Test zone _handle_zone_403_error with IP ban message."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        mock_response = Mock()
        mock_response.text = (
            "You don't have the permission to access the "
            "requested resource. It is either read-protected "
            "or not readable by the server."
        )

        with self.assertRaises(RuntimeError) as context:
            zone._handle_zone_403_error(mock_response)

        self.assertIn("blocked", str(context.exception))

    @patch('src.environment.get_env_variable')
    def test_zone_handle_403_error_generic(self, mock_env):
        """Test zone _handle_zone_403_error with generic message."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        mock_response = Mock()
        mock_response.text = "Forbidden for some other reason"

        with self.assertRaises(RuntimeError) as context:
            zone._handle_zone_403_error(mock_response)

        self.assertIn("403", str(context.exception))
        self.assertIn("forbidden", str(context.exception))

    @patch('requests.get')
    @patch('src.environment.get_env_variable')
    def test_zone_handle_http_errors_403(self, mock_env, mock_get):
        """Test zone _handle_zone_http_errors with 403 status."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Generic forbidden"

        with self.assertRaises(RuntimeError):
            zone._handle_zone_http_errors(mock_response)

    @patch('src.environment.get_env_variable')
    def test_zone_get_client_ip_success(self, mock_env):
        """Test zone _get_zone_client_ip success."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        with patch('socket.gethostname', return_value='testhost'):
            with patch('socket.gethostbyname', return_value='192.168.1.100'):
                result = zone._get_zone_client_ip()
                self.assertEqual(result, '192.168.1.100')

    @patch('src.environment.get_env_variable')
    def test_zone_get_client_ip_socket_error(self, mock_env):
        """Test zone _get_zone_client_ip with socket error."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        import socket
        with patch('socket.gethostname', side_effect=socket.error("Error")):
            result = zone._get_zone_client_ip()
            self.assertEqual(result, 'unknown')

    @patch('src.environment.get_env_variable')
    def test_zone_get_client_ip_os_error(self, mock_env):
        """Test zone _get_zone_client_ip with OS error."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        with patch('socket.gethostname', side_effect=OSError("Error")):
            result = zone._get_zone_client_ip()
            self.assertEqual(result, 'unknown')

    @patch('src.environment.get_env_variable')
    def test_zone_parse_response_json_decode_error(self, mock_env):
        """Test zone _parse_zone_response with JSONDecodeError."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        mock_response = Mock()
        mock_response.json.side_effect = json.decoder.JSONDecodeError(
            "Invalid JSON", "doc", 0
        )

        with self.assertRaises(RuntimeError) as context:
            zone._parse_zone_response(mock_response, None)

        self.assertIn("not responding", str(context.exception))

    @patch('src.environment.get_env_variable')
    def test_zone_parse_response_missing_parameter_key(self, mock_env):
        """Test zone _parse_zone_response with missing parameter key."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        mock_response = Mock()
        mock_response.json.return_value = {"temp": 72.5}

        with self.assertRaises(KeyError) as context:
            zone._parse_zone_response(mock_response, "humidity")

        self.assertIn("did not contain key", str(context.exception))

    @patch('src.environment.get_env_variable')
    def test_zone_parse_response_missing_param_with_message(self, mock_env):
        """Test zone _parse_zone_response with message in response."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        mock_response = Mock()
        mock_response.json.return_value = {
            "message": "Parameter not available"
        }

        with self.assertRaises(KeyError):
            zone._parse_zone_response(mock_response, "humidity")

    @patch('src.utilities.execute_with_extended_retries')
    @patch('src.environment.get_env_variable')
    def test_zone_execute_with_retry(self, mock_env, mock_retry):
        """Test zone _execute_zone_with_retry."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        mock_func = Mock(return_value="success")
        mock_retry.return_value = "success"

        result = zone._execute_zone_with_retry(mock_func)

        mock_retry.assert_called_once()
        self.assertEqual(result, "success")

        call_args = mock_retry.call_args
        exception_types = call_args[1]['exception_types']
        self.assertIn(requests.exceptions.RequestException, exception_types)
        self.assertIn(KeyError, exception_types)


class TestSht31ZoneSimpleMethods(unittest.TestCase):
    """Test simple ThermostatZone methods."""

    def setUp(self):
        """Set up test environment."""
        self.original_unit_test_mode = util.unit_test_mode
        util.unit_test_mode = False

    def tearDown(self):
        """Clean up test environment."""
        util.unit_test_mode = self.original_unit_test_mode

    @patch('requests.get')
    @patch('src.environment.get_env_variable')
    def test_get_display_temp(self, mock_env, mock_get):
        """Test get_display_temp method."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        mock_response = Mock()
        mock_response.json.return_value = {"Temp(F) mean": 72.5}
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with patch.object(zone, 'get_metadata', return_value=72.5):
            result = zone.get_display_temp()
            self.assertEqual(result, 72.5)

    @patch('src.environment.get_env_variable')
    def test_get_display_humidity_with_value(self, mock_env):
        """Test get_display_humidity with valid value."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        with patch.object(zone, 'get_metadata', return_value=45.5):
            result = zone.get_display_humidity()
            self.assertEqual(result, 45.5)

    @patch('src.environment.get_env_variable')
    def test_get_display_humidity_with_none(self, mock_env):
        """Test get_display_humidity with None value."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        with patch.object(zone, 'get_metadata', return_value=None):
            result = zone.get_display_humidity()
            self.assertIsNone(result)

    @patch('src.environment.get_env_variable')
    def test_get_is_humidity_supported(self, mock_env):
        """Test get_is_humidity_supported method."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        with patch.object(zone, 'get_display_humidity', return_value=45.5):
            result = zone.get_is_humidity_supported()
            self.assertTrue(result)

        with patch.object(zone, 'get_display_humidity', return_value=None):
            result = zone.get_is_humidity_supported()
            self.assertFalse(result)

    @patch('src.environment.get_env_variable')
    def test_mode_methods(self, mock_env):
        """Test all mode checking methods."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        self.assertEqual(zone.is_heat_mode(), 0)
        self.assertEqual(zone.is_cool_mode(), 0)
        self.assertEqual(zone.is_dry_mode(), 0)
        self.assertEqual(zone.is_auto_mode(), 0)
        self.assertEqual(zone.is_eco_mode(), 0)
        self.assertEqual(zone.is_fan_mode(), 0)
        self.assertEqual(zone.is_off_mode(), 1)

    @patch('src.environment.get_env_variable')
    def test_relay_status_methods(self, mock_env):
        """Test all relay status methods."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        self.assertEqual(zone.is_heating(), 0)
        self.assertEqual(zone.is_cooling(), 0)
        self.assertEqual(zone.is_drying(), 0)
        self.assertEqual(zone.is_auto(), 0)
        self.assertEqual(zone.is_eco(), 0)
        self.assertEqual(zone.is_fanning(), 0)
        self.assertEqual(zone.is_power_on(), 1)
        self.assertEqual(zone.is_fan_on(), 0)
        self.assertEqual(zone.is_defrosting(), 0)
        self.assertEqual(zone.is_standby(), 0)

    @patch('src.environment.get_env_variable')
    def test_get_wifi_strength_with_value(self, mock_env):
        """Test get_wifi_strength with valid value."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        with patch.object(zone, 'get_metadata', return_value=-55.0):
            result = zone.get_wifi_strength()
            self.assertEqual(result, -55.0)

    @patch('src.utilities.execute_with_extended_retries')
    @patch('src.environment.get_env_variable')
    def test_get_wifi_strength_key_error(self, mock_env, mock_retry):
        """Test get_wifi_strength when key is missing."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        # Simulate KeyError being raised by the retry mechanism
        mock_retry.side_effect = KeyError("Key not found")

        result = zone.get_wifi_strength()
        # Should return BOGUS_INT when KeyError is raised
        self.assertEqual(result, float(util.BOGUS_INT))

    @patch('src.environment.get_env_variable')
    def test_get_wifi_strength_with_none(self, mock_env):
        """Test get_wifi_strength with None value."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        with patch.object(zone, 'get_metadata', return_value=None):
            result = zone.get_wifi_strength()
            self.assertEqual(result, float(util.BOGUS_INT))

    @patch('src.environment.get_env_variable')
    def test_refresh_zone_info_force_refresh(self, mock_env):
        """Test refresh_zone_info with force_refresh=True."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        zone.zone_info = {"old": "data"}
        zone.refresh_zone_info(force_refresh=True)
        self.assertEqual(zone.zone_info, {})

    @patch('src.environment.get_env_variable')
    def test_refresh_zone_info_expired(self, mock_env):
        """Test refresh_zone_info when data is expired."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        zone.zone_info = {"old": "data"}
        # Set last_fetch_time to a time in the past
        zone.last_fetch_time = 0
        zone.refresh_zone_info(force_refresh=False)
        self.assertEqual(zone.zone_info, {})

    @patch('src.environment.get_env_variable')
    def test_refresh_zone_info_not_expired(self, mock_env):
        """Test refresh_zone_info when data is not expired."""
        mock_env.return_value = {"value": "192.168.1.1"}
        tstat = sht31.ThermostatClass(zone=0, verbose=False)
        zone = sht31.ThermostatZone(
            Thermostat_obj=tstat,
            verbose=False
        )

        zone.zone_info = {"current": "data"}
        # Set last_fetch_time to now
        import time
        zone.last_fetch_time = time.time()
        zone.refresh_zone_info(force_refresh=False)
        # Should not be cleared
        self.assertEqual(zone.zone_info, {"current": "data"})


if __name__ == "__main__":
    unittest.main()
