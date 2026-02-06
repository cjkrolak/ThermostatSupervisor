"""
Unit test module for honeywell.py.

Tests retry functionality with mocked exceptions.
"""

# built-in imports
import http.client
import logging
import time
import types
import unittest
from unittest import mock

# third-party imports
import pyhtcc
import urllib3.exceptions

# local imports
from src import honeywell
import src.thermostat_common as tc
from src import utilities as util
from tests import unit_test_common as utc


@unittest.skipIf(
    not utc.ENABLE_HONEYWELL_TESTS,
    "Honeywell tests are disabled",
)
class Test(utc.UnitTest):
    """Test functions in honeywell.py."""

    def test_get_zones_info_with_retries_new_exceptions(self):
        """
        Test get_zones_info_with_retries() with newly added exceptions.

        Verify that urllib3.exceptions.ProtocolError and
        http.client.RemoteDisconnected are properly caught and retried.
        """
        # List of new exceptions to test
        new_exceptions = [
            (urllib3.exceptions.ProtocolError, ["mock ProtocolError"]),
            (http.client.RemoteDisconnected, ["mock RemoteDisconnected"]),
        ]

        for exception_type, exception_args in new_exceptions:
            with self.subTest(exception=exception_type):
                print(f"testing mocked '{str(exception_type)}' exception...")

                # Mock time.sleep and email notifications to speed up the test
                with mock.patch("time.sleep"), mock.patch(
                    "src.email_notification.send_email_alert"
                ):
                    # Create a mock function that raises the exception on first calls,
                    # then succeeds on the final call
                    call_count = 0

                    def mock_func():
                        nonlocal call_count
                        call_count += 1
                        if call_count < 3:  # Fail first 2 times
                            utc.mock_exception(exception_type, exception_args)
                        else:  # Succeed on 3rd call
                            return [{"test": "success"}]

                    # Test that the function retries and eventually succeeds
                    result = honeywell.get_zones_info_with_retries(
                        mock_func, "test_thermostat", "test_zone"
                    )

                    # Verify the function succeeded after retries
                    self.assertEqual(result, [{"test": "success"}])
                    # Verify it was called multiple times (retried)
                    self.assertEqual(call_count, 3)

    def test_get_zones_info_with_retries_existing_exceptions(self):
        """
        Test get_zones_info_with_retries() with existing exceptions.

        Verify that previously supported exceptions still work.
        """
        # Mock time.sleep and email notifications to speed up the test
        with mock.patch("time.sleep"), mock.patch(
            "src.email_notification.send_email_alert"
        ):
            # Mock a function that raises ConnectionError then succeeds
            call_count = 0

            def mock_func():
                nonlocal call_count
                call_count += 1
                if call_count < 2:  # Fail first time
                    raise pyhtcc.requests.exceptions.ConnectionError(
                        "mock ConnectionError"
                    )
                else:  # Succeed on 2nd call
                    return [{"test": "success"}]

            # Test that the function retries and eventually succeeds
            result = honeywell.get_zones_info_with_retries(
                mock_func, "test_thermostat", "test_zone"
            )

            # Verify the function succeeded after retry
            self.assertEqual(result, [{"test": "success"}])
            # Verify it was called multiple times (retried)
            self.assertEqual(call_count, 2)

    def test_get_zones_info_with_retries_too_many_attempts_error(self):
        """
        Test get_zones_info_with_retries() with TooManyAttemptsError.

        Verify that TooManyAttemptsError is caught and the server_spamming_detected
        flag is set in thermostat_common.
        """

        # Reset the server_spamming_detected flag
        tc.server_spamming_detected = False

        # Mock time.sleep and email notifications to speed up the test
        with mock.patch("time.sleep"), mock.patch(
            "src.email_notification.send_email_alert"
        ):
            # Mock a function that always raises TooManyAttemptsError
            def mock_func():
                raise pyhtcc.pyhtcc.TooManyAttemptsError(
                    "mock TooManyAttemptsError for server spamming detection"
                )

            # Test that the function raises TooManyAttemptsError after retries
            with self.assertRaises(pyhtcc.pyhtcc.TooManyAttemptsError):
                honeywell.get_zones_info_with_retries(
                    mock_func, "test_thermostat", "test_zone"
                )

            # Verify the server_spamming_detected flag was set
            self.assertTrue(
                tc.server_spamming_detected,
                "server_spamming_detected flag should be set when "
                "TooManyAttemptsError is detected",
            )

            # Test reset functionality
            tc.reset_server_spamming_flag()
            self.assertFalse(
                tc.server_spamming_detected,
                "server_spamming_detected flag should be reset after calling "
                "reset_server_spamming_flag()",
            )

    def test_refresh_zone_info_caching_with_slow_api(self):
        """
        Test that refresh_zone_info() caching works correctly with slow API calls.

        Verifies that the cache timestamp is set AFTER the API call completes,
        not before, so that subsequent calls within the fetch_interval don't
        trigger unnecessary API calls.
        """
        # Test constants
        API_DELAY_SECONDS = 2  # Simulated API call delay
        api_call_count = 0

        def slow_get_zones_info_func():
            nonlocal api_call_count
            api_call_count += 1
            # Simulate a slow API call
            time.sleep(API_DELAY_SECONDS)
            return [
                {
                    "DeviceID": 123456,
                    "Name": "Test Zone",
                    "latestData": {"uiData": {}},
                }
            ]

        # Create a mock zone object
        mock_zone = mock.Mock(spec=honeywell.ThermostatZone)
        mock_zone.device_id = 123456
        mock_zone.thermostat_type = "honeywell"
        mock_zone.zone_name = "test_zone"
        mock_zone.fetch_interval_sec = 60
        mock_zone.last_fetch_time = time.time() - 120  # 2 minutes ago

        # Create a mock pyhtcc instance
        mock_pyhtcc = mock.Mock()
        mock_pyhtcc.get_zones_info = slow_get_zones_info_func
        mock_zone.pyhtcc = mock_pyhtcc

        # Bind the actual refresh_zone_info method to our mock zone
        # using types.MethodType
        mock_zone.refresh_zone_info = types.MethodType(
            honeywell.ThermostatZone.refresh_zone_info, mock_zone
        )
        mock_zone.zone_info = {}

        # Record start time
        start_time = time.time()

        # First call should trigger API call (cache is stale by default)
        mock_zone.refresh_zone_info()
        first_call_duration = time.time() - start_time

        # Verify API was called
        self.assertEqual(api_call_count, 1, "API should be called on first refresh")

        # Verify the slow API call took at least the expected delay
        self.assertGreaterEqual(
            first_call_duration,
            API_DELAY_SECONDS,
            f"First call should take at least {API_DELAY_SECONDS} seconds "
            f"due to slow API",
        )

        # Second call immediately after (within fetch_interval_sec)
        # should NOT trigger another API call if caching is working correctly
        second_call_start = time.time()
        mock_zone.refresh_zone_info()
        second_call_duration = time.time() - second_call_start

        # Verify API was NOT called again (still using cache)
        self.assertEqual(
            api_call_count,
            1,
            "API should NOT be called again within fetch_interval_sec",
        )

        # Verify the second call was fast (< 0.1 seconds)
        self.assertLess(
            second_call_duration,
            0.1,
            "Second call should be fast (cached), not trigger slow API call",
        )

    def test_thermostat_class_init(self):
        """Test ThermostatClass initialization."""
        # Mock environment variables
        with mock.patch.dict(
            "os.environ",
            {
                "TCC_USERNAME": "test_user",
                "TCC_PASSWORD": "test_pass",
            },
        ):
            # Mock pyhtcc.PyHTCC.__init__ to avoid actual API calls
            with mock.patch("pyhtcc.PyHTCC.__init__", return_value=None):
                # Mock get_zones_info to return test data
                with mock.patch.object(
                    honeywell.ThermostatClass,
                    "get_zones_info",
                    return_value=[{"DeviceID": 12345}, {"DeviceID": 67890}],
                ):
                    tstat = honeywell.ThermostatClass(zone=0, verbose=True)

                    # Verify attributes
                    self.assertEqual(tstat.tcc_uname, "test_user")
                    self.assertEqual(tstat.tcc_pwd, "test_pass")
                    self.assertEqual(tstat.thermostat_type, "honeywell")
                    self.assertEqual(tstat.zone_name, 0)
                    self.assertEqual(tstat.device_id, 12345)

    def test_thermostat_class_init_missing_env_vars(self):
        """Test ThermostatClass initialization with missing env variables."""
        # Clear environment variables
        with mock.patch.dict("os.environ", {}, clear=True):
            # Mock pyhtcc.PyHTCC.__init__
            with mock.patch("pyhtcc.PyHTCC.__init__", return_value=None):
                with mock.patch.object(
                    honeywell.ThermostatClass,
                    "get_zones_info",
                    return_value=[{"DeviceID": 12345}],
                ):
                    tstat = honeywell.ThermostatClass(zone=0)

                    # Verify missing key indicators
                    self.assertIn("TCC_USERNAME", tstat.tcc_uname)
                    self.assertIn("KEY_MISSING", tstat.tcc_uname)
                    self.assertIn("TCC_PASSWORD", tstat.tcc_pwd)
                    self.assertIn("KEY_MISSING", tstat.tcc_pwd)

    def test_get_zone_device_ids(self):
        """Test _get_zone_device_ids method."""
        with mock.patch.dict(
            "os.environ",
            {"TCC_USERNAME": "test_user", "TCC_PASSWORD": "test_pass"},
        ):
            with mock.patch("pyhtcc.PyHTCC.__init__", return_value=None):
                mock_zones = [
                    {"DeviceID": 111, "Name": "Zone1"},
                    {"DeviceID": 222, "Name": "Zone2"},
                    {"DeviceID": 333, "Name": "Zone3"},
                ]
                with mock.patch.object(
                    honeywell.ThermostatClass,
                    "get_zones_info",
                    return_value=mock_zones,
                ):
                    tstat = honeywell.ThermostatClass(zone=0)
                    zone_ids = tstat._get_zone_device_ids()

                    # Verify all zone IDs are returned
                    self.assertEqual(zone_ids, [111, 222, 333])

    def test_get_target_zone_id_valid(self):
        """Test get_target_zone_id with valid zone."""
        with mock.patch.dict(
            "os.environ",
            {"TCC_USERNAME": "test_user", "TCC_PASSWORD": "test_pass"},
        ):
            with mock.patch("pyhtcc.PyHTCC.__init__", return_value=None):
                mock_zones = [
                    {"DeviceID": 111},
                    {"DeviceID": 222},
                    {"DeviceID": 333},
                ]
                with mock.patch.object(
                    honeywell.ThermostatClass,
                    "get_zones_info",
                    return_value=mock_zones,
                ):
                    tstat = honeywell.ThermostatClass(zone=0)

                    # Test valid zone indices
                    self.assertEqual(tstat.get_target_zone_id(0), 111)
                    self.assertEqual(tstat.get_target_zone_id(1), 222)
                    self.assertEqual(tstat.get_target_zone_id(2), 333)

    def test_get_target_zone_id_invalid(self):
        """Test get_target_zone_id with invalid zone."""
        with mock.patch.dict(
            "os.environ",
            {"TCC_USERNAME": "test_user", "TCC_PASSWORD": "test_pass"},
        ):
            with mock.patch("pyhtcc.PyHTCC.__init__", return_value=None):
                mock_zones = [{"DeviceID": 111}, {"DeviceID": 222}]
                with mock.patch.object(
                    honeywell.ThermostatClass,
                    "get_zones_info",
                    return_value=mock_zones,
                ):
                    tstat = honeywell.ThermostatClass(zone=0)

                    # Test invalid zone index
                    with self.assertRaises(ValueError) as context:
                        tstat.get_target_zone_id(5)

                    self.assertIn("not a valid choice", str(context.exception))

    def test_get_all_metadata(self):
        """Test get_all_metadata method."""
        with mock.patch.dict(
            "os.environ",
            {"TCC_USERNAME": "test_user", "TCC_PASSWORD": "test_pass"},
        ):
            with mock.patch("pyhtcc.PyHTCC.__init__", return_value=None):
                mock_zones = [
                    {
                        "DeviceID": 111,
                        "Name": "TestZone",
                        "latestData": {"temp": 72},
                    }
                ]
                with mock.patch.object(
                    honeywell.ThermostatClass,
                    "get_zones_info",
                    return_value=mock_zones,
                ):
                    tstat = honeywell.ThermostatClass(zone=0)
                    metadata = tstat.get_all_metadata(zone=0)

                    # Verify metadata contains expected fields
                    self.assertEqual(metadata["DeviceID"], 111)
                    self.assertEqual(metadata["Name"], "TestZone")
                    self.assertIn("latestData", metadata)

    def test_get_metadata_full_zone(self):
        """Test get_metadata with no parameter (full zone data)."""
        with mock.patch.dict(
            "os.environ",
            {"TCC_USERNAME": "test_user", "TCC_PASSWORD": "test_pass"},
        ):
            with mock.patch("pyhtcc.PyHTCC.__init__", return_value=None):
                mock_zones = [
                    {"DeviceID": 111, "Name": "TestZone", "Setting": "Value1"}
                ]
                with mock.patch.object(
                    honeywell.ThermostatClass,
                    "get_zones_info",
                    return_value=mock_zones,
                ):
                    tstat = honeywell.ThermostatClass(zone=0)
                    metadata = tstat.get_metadata(zone=0, parameter=None)

                    # Verify full zone data is returned
                    self.assertEqual(metadata["DeviceID"], 111)
                    self.assertEqual(metadata["Name"], "TestZone")

    def test_get_metadata_specific_parameter(self):
        """Test get_metadata with specific parameter."""
        with mock.patch.dict(
            "os.environ",
            {"TCC_USERNAME": "test_user", "TCC_PASSWORD": "test_pass"},
        ):
            with mock.patch("pyhtcc.PyHTCC.__init__", return_value=None):
                mock_zones = [
                    {"DeviceID": 111, "Name": "TestZone", "Setting": "Value1"}
                ]
                with mock.patch.object(
                    honeywell.ThermostatClass,
                    "get_zones_info",
                    return_value=mock_zones,
                ):
                    tstat = honeywell.ThermostatClass(zone=0)
                    name = tstat.get_metadata(zone=0, parameter="Name")

                    # Verify specific parameter is returned
                    self.assertEqual(name, "TestZone")

    def test_get_metadata_with_retry(self):
        """Test get_metadata with retry=True."""
        with mock.patch.dict(
            "os.environ",
            {"TCC_USERNAME": "test_user", "TCC_PASSWORD": "test_pass"},
        ):
            with mock.patch("pyhtcc.PyHTCC.__init__", return_value=None):
                mock_zones = [{"DeviceID": 111, "Name": "TestZone"}]
                with mock.patch.object(
                    honeywell.ThermostatClass,
                    "get_zones_info",
                    return_value=mock_zones,
                ):
                    with mock.patch(
                        "src.utilities."
                        "execute_with_extended_retries"
                    ) as mock_retry:
                        mock_retry.return_value = mock_zones[0]
                        tstat = honeywell.ThermostatClass(zone=0)
                        metadata = tstat.get_metadata(zone=0, retry=True)

                        # Verify retry mechanism was called
                        mock_retry.assert_called_once()
                        self.assertEqual(metadata["Name"], "TestZone")

    def test_get_metadata_index_error(self):
        """Test get_metadata with invalid zone index."""
        with mock.patch.dict(
            "os.environ",
            {"TCC_USERNAME": "test_user", "TCC_PASSWORD": "test_pass"},
        ):
            with mock.patch("pyhtcc.PyHTCC.__init__", return_value=None):
                mock_zones = [{"DeviceID": 111, "Name": "TestZone"}]
                with mock.patch.object(
                    honeywell.ThermostatClass,
                    "get_zones_info",
                    return_value=mock_zones,
                ):
                    tstat = honeywell.ThermostatClass(zone=0)

                    # Test invalid zone index
                    with self.assertRaises(IndexError):
                        tstat.get_metadata(zone=5)

    def test_get_latestdata(self):
        """Test get_latestdata method."""
        with mock.patch.dict(
            "os.environ",
            {"TCC_USERNAME": "test_user", "TCC_PASSWORD": "test_pass"},
        ):
            with mock.patch("pyhtcc.PyHTCC.__init__", return_value=None):
                mock_zones = [
                    {
                        "DeviceID": 111,
                        "latestData": {
                            "uiData": {"temp": 72},
                            "fanData": {"running": True},
                        },
                    }
                ]
                with mock.patch.object(
                    honeywell.ThermostatClass,
                    "get_zones_info",
                    return_value=mock_zones,
                ):
                    tstat = honeywell.ThermostatClass(zone=0)
                    latest_data = tstat.get_latestdata(zone=0)

                    # Verify latest data structure
                    self.assertIn("uiData", latest_data)
                    self.assertIn("fanData", latest_data)

    def test_get_latestdata_debug(self):
        """Test get_latestdata with debug=True."""
        with mock.patch.dict(
            "os.environ",
            {"TCC_USERNAME": "test_user", "TCC_PASSWORD": "test_pass"},
        ):
            with mock.patch("pyhtcc.PyHTCC.__init__", return_value=None):
                mock_zones = [
                    {
                        "DeviceID": 111,
                        "latestData": {"uiData": {"temp": 72}},
                    }
                ]
                with mock.patch.object(
                    honeywell.ThermostatClass,
                    "get_zones_info",
                    return_value=mock_zones,
                ):
                    tstat = honeywell.ThermostatClass(zone=0)
                    with mock.patch(
                        "src.utilities.log_msg"
                    ) as mock_log:
                        latest_data = tstat.get_latestdata(zone=0, debug=True)

                        # Verify logging was called with debug
                        mock_log.assert_called()
                        self.assertIn("uiData", latest_data)

    def test_get_ui_data(self):
        """Test get_ui_data method."""
        with mock.patch.dict(
            "os.environ",
            {"TCC_USERNAME": "test_user", "TCC_PASSWORD": "test_pass"},
        ):
            with mock.patch("pyhtcc.PyHTCC.__init__", return_value=None):
                mock_zones = [
                    {
                        "DeviceID": 111,
                        "latestData": {
                            "uiData": {
                                "DispTemperature": 72,
                                "SystemSwitchPosition": 1,
                            }
                        },
                    }
                ]
                with mock.patch.object(
                    honeywell.ThermostatClass,
                    "get_zones_info",
                    return_value=mock_zones,
                ):
                    tstat = honeywell.ThermostatClass(zone=0)
                    ui_data = tstat.get_ui_data(zone=0)

                    # Verify ui data contents
                    self.assertEqual(ui_data["DispTemperature"], 72)
                    self.assertEqual(ui_data["SystemSwitchPosition"], 1)

    def test_get_ui_data_param(self):
        """Test get_ui_data_param method."""
        with mock.patch.dict(
            "os.environ",
            {"TCC_USERNAME": "test_user", "TCC_PASSWORD": "test_pass"},
        ):
            with mock.patch("pyhtcc.PyHTCC.__init__", return_value=None):
                mock_zones = [
                    {
                        "DeviceID": 111,
                        "latestData": {
                            "uiData": {
                                "DispTemperature": 72,
                                "HeatSetpoint": 70,
                            }
                        },
                    }
                ]
                with mock.patch.object(
                    honeywell.ThermostatClass,
                    "get_zones_info",
                    return_value=mock_zones,
                ):
                    tstat = honeywell.ThermostatClass(zone=0)
                    temp = tstat.get_ui_data_param(zone=0, parameter="DispTemperature")

                    # Verify specific parameter value
                    self.assertEqual(temp, 72)

    def test_thermostat_class_close(self):
        """Test ThermostatClass close method."""
        with mock.patch.dict(
            "os.environ",
            {"TCC_USERNAME": "test_user", "TCC_PASSWORD": "test_pass"},
        ):
            with mock.patch("pyhtcc.PyHTCC.__init__", return_value=None):
                with mock.patch.object(
                    honeywell.ThermostatClass,
                    "get_zones_info",
                    return_value=[{"DeviceID": 111}],
                ):
                    tstat = honeywell.ThermostatClass(zone=0)
                    # Create a mock session
                    mock_session = mock.Mock()
                    tstat.session = mock_session

                    # Test close
                    tstat.close()

                    # Verify session was closed
                    mock_session.close.assert_called_once()
                    self.assertIsNone(tstat.session)

    def test_thermostat_class_del(self):
        """Test ThermostatClass __del__ method."""
        with mock.patch.dict(
            "os.environ",
            {"TCC_USERNAME": "test_user", "TCC_PASSWORD": "test_pass"},
        ):
            with mock.patch("pyhtcc.PyHTCC.__init__", return_value=None):
                with mock.patch.object(
                    honeywell.ThermostatClass,
                    "get_zones_info",
                    return_value=[{"DeviceID": 111}],
                ):
                    tstat = honeywell.ThermostatClass(zone=0)
                    mock_session = mock.Mock()
                    tstat.session = mock_session

                    # Test __del__
                    tstat.__del__()

                    # Verify close was called
                    mock_session.close.assert_called_once()

    def test_thermostat_class_del_exception_handling(self):
        """Test ThermostatClass __del__ exception handling."""
        with mock.patch.dict(
            "os.environ",
            {"TCC_USERNAME": "test_user", "TCC_PASSWORD": "test_pass"},
        ):
            with mock.patch("pyhtcc.PyHTCC.__init__", return_value=None):
                with mock.patch.object(
                    honeywell.ThermostatClass,
                    "get_zones_info",
                    return_value=[{"DeviceID": 111}],
                ):
                    tstat = honeywell.ThermostatClass(zone=0)

                    # Mock close to raise AttributeError
                    with mock.patch.object(
                        tstat, "close", side_effect=AttributeError("test error")
                    ):
                        # Should not raise exception
                        tstat.__del__()

    def test_get_metadata_with_parameter_index_error(self):
        """Test get_metadata with parameter and invalid zone index."""
        with mock.patch.dict(
            "os.environ",
            {"TCC_USERNAME": "test_user", "TCC_PASSWORD": "test_pass"},
        ):
            with mock.patch("pyhtcc.PyHTCC.__init__", return_value=None):
                mock_zones = [{"DeviceID": 111, "Name": "TestZone"}]
                with mock.patch.object(
                    honeywell.ThermostatClass,
                    "get_zones_info",
                    return_value=mock_zones,
                ):
                    tstat = honeywell.ThermostatClass(zone=0)

                    # Test invalid zone index with parameter
                    with self.assertRaises(IndexError):
                        tstat.get_metadata(zone=5, parameter="Name")

    def test_print_all_thermostat_metadata(self):
        """Test print_all_thermostat_metadata method."""
        with mock.patch.dict(
            "os.environ",
            {"TCC_USERNAME": "test_user", "TCC_PASSWORD": "test_pass"},
        ):
            with mock.patch("pyhtcc.PyHTCC.__init__", return_value=None):
                mock_zones = [
                    {
                        "DeviceID": 111,
                        "Name": "TestZone",
                        "latestData": {"uiData": {"temp": 72}},
                    }
                ]
                with mock.patch.object(
                    honeywell.ThermostatClass,
                    "get_zones_info",
                    return_value=mock_zones,
                ):
                    tstat = honeywell.ThermostatClass(zone=0)

                    # Mock exec_print_all_thermostat_metadata
                    with mock.patch.object(
                        tstat, "exec_print_all_thermostat_metadata"
                    ) as mock_exec:
                        tstat.print_all_thermostat_metadata(zone=0)

                        # Verify exec_print_all_thermostat_metadata was called
                        mock_exec.assert_called_once()

    def test_thermostat_class_get_zones_info_override(self):
        """Test ThermostatClass get_zones_info override method."""
        with mock.patch.dict(
            "os.environ",
            {"TCC_USERNAME": "test_user", "TCC_PASSWORD": "test_pass"},
        ):
            with mock.patch("pyhtcc.PyHTCC.__init__", return_value=None):
                mock_zones = [{"DeviceID": 111}]

                # Mock the parent class get_zones_info method
                with mock.patch(
                    "pyhtcc.PyHTCC.get_zones_info", return_value=mock_zones
                ):
                    # Create instance with proper initialization
                    tstat = honeywell.ThermostatClass(zone=0, verbose=False)

                    # Call get_zones_info - this should call the retry wrapper
                    result = tstat.get_zones_info()

                    # Verify result matches expected zones
                    self.assertEqual(result, mock_zones)

    def test_thermostat_zone_init(self):
        """Test ThermostatZone initialization."""
        # Create mock thermostat object
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0
        mock_tstat.thermostat_type = "honeywell"

        # Mock both parent class __init__ methods to avoid resetting attributes
        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch(
                "src.thermostat_common."
                "ThermostatCommonZone.__init__",
                return_value=None,
            ):
                # Mock get_zone_name to avoid refresh_zone_info call in __init__
                with mock.patch.object(
                    honeywell.ThermostatZone,
                    "get_zone_name",
                    return_value="TestZone",
                ):
                    zone = honeywell.ThermostatZone(mock_tstat, verbose=True)

                    # Verify attributes - thermostat_type is set in __init__
                    # before calling parent classes
                    self.assertEqual(zone.device_id, 12345)
                    self.assertEqual(zone.thermostat_type, "honeywell")
                    self.assertTrue(zone.verbose)
                    # Verify zone_name was set
                    self.assertEqual(zone.zone_name, "TestZone")

    def test_thermostat_zone_init_invalid_device_id(self):
        """Test ThermostatZone init with invalid device_id type."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = "not_an_int"  # Invalid type
        mock_tstat.zone_name = 0

        # Should raise TypeError
        with self.assertRaises(TypeError) as context:
            honeywell.ThermostatZone(mock_tstat)

        self.assertIn("expected type 'int'", str(context.exception))

    def test_zone_get_zone_name(self):
        """Test ThermostatZone get_zone_name method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0
        mock_tstat.thermostat_type = "honeywell"

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            # Create zone object without calling get_zone_name in __init__
            with mock.patch.object(
                honeywell.ThermostatZone,
                "get_zone_name",
                return_value="InitialZone",
            ):
                zone = honeywell.ThermostatZone(mock_tstat)

            # Now set zone_info and test get_zone_name directly
            zone.zone_info = {"Name": "Living Room"}

            # Mock refresh_zone_info to avoid API call
            with mock.patch.object(zone, "refresh_zone_info"):
                name = zone.get_zone_name()
                self.assertEqual(name, "Living Room")

    def test_zone_get_display_temp(self):
        """Test ThermostatZone get_display_temp method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)

                # Mock get_indoor_temperature_raw
                with mock.patch.object(
                    zone, "get_indoor_temperature_raw", return_value=72.5
                ):
                    temp = zone.get_display_temp()
                    self.assertEqual(temp, 72.5)

    def test_zone_get_display_humidity_available(self):
        """Test get_display_humidity when humidity is available."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)

                # Mock get_indoor_humidity_raw to return value
                with mock.patch.object(
                    zone, "get_indoor_humidity_raw", return_value=45
                ):
                    humidity = zone.get_display_humidity()
                    self.assertEqual(humidity, 45.0)

    def test_zone_get_display_humidity_not_available(self):
        """Test get_display_humidity when humidity is not available."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)

                # Mock get_indoor_humidity_raw to return None
                with mock.patch.object(
                    zone, "get_indoor_humidity_raw", return_value=None
                ):
                    humidity = zone.get_display_humidity()
                    self.assertIsNone(humidity)

    def test_zone_get_is_humidity_supported(self):
        """Test get_is_humidity_supported method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)
                zone.zone_info = {
                    "latestData": {
                        "uiData": {
                            "IndoorHumiditySensorAvailable": 1,
                            "IndoorHumiditySensorNotFault": 1,
                        }
                    }
                }

                with mock.patch.object(zone, "refresh_zone_info"):
                    # Test both available and not faulted
                    self.assertTrue(zone.get_is_humidity_supported())

                # Test when sensor is faulted
                zone.zone_info["latestData"]["uiData"][
                    "IndoorHumiditySensorNotFault"
                ] = 0
                with mock.patch.object(zone, "refresh_zone_info"):
                    self.assertFalse(zone.get_is_humidity_supported())

    def test_zone_mode_checks(self):
        """Test zone mode check methods."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)

                # Test heat mode
                with mock.patch.object(zone, "_is_mode", return_value=True):
                    self.assertEqual(zone.is_heat_mode(), 1)

                # Test cool mode
                with mock.patch.object(zone, "_is_mode", return_value=True):
                    self.assertEqual(zone.is_cool_mode(), 1)

                # Test dry mode
                with mock.patch.object(zone, "_is_mode", return_value=False):
                    self.assertEqual(zone.is_dry_mode(), 0)

                # Test auto mode
                with mock.patch.object(zone, "_is_mode", return_value=True):
                    self.assertEqual(zone.is_auto_mode(), 1)

                # Test eco mode
                with mock.patch.object(zone, "_is_mode", return_value=False):
                    self.assertEqual(zone.is_eco_mode(), 0)

    def test_zone_is_fan_mode(self):
        """Test is_fan_mode method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)

                # Test fan mode enabled (off mode + fan on)
                def mock_is_mode(mode):
                    return mode == zone.OFF_MODE

                with mock.patch.object(zone, "_is_mode", side_effect=mock_is_mode):
                    with mock.patch.object(zone, "is_fan_on_mode", return_value=1):
                        self.assertEqual(zone.is_fan_mode(), 1)

                # Test fan mode disabled (not in off mode)
                with mock.patch.object(zone, "_is_mode", return_value=False):
                    self.assertEqual(zone.is_fan_mode(), 0)

    def test_zone_is_heating(self):
        """Test is_heating method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)

                with mock.patch.object(zone, "refresh_zone_info"):
                    # Test heating active (heat mode, temp below setpoint)
                    with mock.patch.object(zone, "is_heat_mode", return_value=1):
                        with mock.patch.object(
                            zone, "get_display_temp", return_value=68.0
                        ):
                            with mock.patch.object(
                                zone, "get_heat_setpoint_raw", return_value=70.0
                            ):
                                self.assertEqual(zone.is_heating(), 1)

                    # Test heating not active (temp above setpoint)
                    with mock.patch.object(zone, "is_heat_mode", return_value=1):
                        with mock.patch.object(
                            zone, "get_display_temp", return_value=72.0
                        ):
                            with mock.patch.object(
                                zone, "get_heat_setpoint_raw", return_value=70.0
                            ):
                                self.assertEqual(zone.is_heating(), 0)

    def test_zone_is_cooling(self):
        """Test is_cooling method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)

                with mock.patch.object(zone, "refresh_zone_info"):
                    # Test cooling active (cool mode, temp above setpoint)
                    with mock.patch.object(zone, "is_cool_mode", return_value=1):
                        with mock.patch.object(
                            zone, "get_display_temp", return_value=76.0
                        ):
                            with mock.patch.object(
                                zone, "get_cool_setpoint_raw", return_value=74.0
                            ):
                                self.assertEqual(zone.is_cooling(), 1)

                    # Test cooling not active (temp below setpoint)
                    with mock.patch.object(zone, "is_cool_mode", return_value=1):
                        with mock.patch.object(
                            zone, "get_display_temp", return_value=72.0
                        ):
                            with mock.patch.object(
                                zone, "get_cool_setpoint_raw", return_value=74.0
                            ):
                                self.assertEqual(zone.is_cooling(), 0)

    def test_zone_is_drying(self):
        """Test is_drying method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)

                # Test drying active
                with mock.patch.object(zone, "is_dry_mode", return_value=1):
                    with mock.patch.object(zone, "is_power_on", return_value=1):
                        with mock.patch.object(
                            zone, "get_cool_setpoint_raw", return_value=70.0
                        ):
                            with mock.patch.object(
                                zone, "get_display_temp", return_value=72.0
                            ):
                                self.assertEqual(zone.is_drying(), 1)

                # Test drying not active (power off)
                with mock.patch.object(zone, "is_dry_mode", return_value=1):
                    with mock.patch.object(zone, "is_power_on", return_value=0):
                        self.assertEqual(zone.is_drying(), 0)

    def test_zone_is_auto(self):
        """Test is_auto method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)

                # Test auto active (cooling needed)
                with mock.patch.object(zone, "is_auto_mode", return_value=1):
                    with mock.patch.object(zone, "is_power_on", return_value=1):
                        with mock.patch.object(
                            zone, "get_cool_setpoint_raw", return_value=74.0
                        ):
                            with mock.patch.object(
                                zone, "get_display_temp", return_value=76.0
                            ):
                                with mock.patch.object(
                                    zone, "get_heat_setpoint_raw", return_value=68.0
                                ):
                                    self.assertEqual(zone.is_auto(), 1)

    def test_zone_is_eco(self):
        """Test is_eco method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)

                # Test eco active (heating needed)
                with mock.patch.object(zone, "is_eco_mode", return_value=1):
                    with mock.patch.object(zone, "is_power_on", return_value=1):
                        with mock.patch.object(
                            zone, "get_heat_setpoint_raw", return_value=70.0
                        ):
                            with mock.patch.object(
                                zone, "get_display_temp", return_value=68.0
                            ):
                                with mock.patch.object(
                                    zone, "get_cool_setpoint_raw", return_value=76.0
                                ):
                                    self.assertEqual(zone.is_eco(), 1)

    def test_zone_fan_modes(self):
        """Test fan mode detection methods."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)

                # Test fan circulate mode
                zone.zone_info = {"latestData": {"fanData": {"fanMode": 2}}}
                with mock.patch.object(zone, "refresh_zone_info"):
                    self.assertEqual(zone.is_fan_circulate_mode(), 1)

                # Test fan auto mode
                zone.zone_info = {"latestData": {"fanData": {"fanMode": 0}}}
                with mock.patch.object(zone, "refresh_zone_info"):
                    self.assertEqual(zone.is_fan_auto_mode(), 1)

                # Test fan on mode
                zone.zone_info = {"latestData": {"fanData": {"fanMode": 1}}}
                with mock.patch.object(zone, "refresh_zone_info"):
                    self.assertEqual(zone.is_fan_on_mode(), 1)

    def test_zone_is_fanning(self):
        """Test is_fanning method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)

                # Test fanning active
                with mock.patch.object(zone, "is_fan_on", return_value=1):
                    with mock.patch.object(zone, "is_power_on", return_value=1):
                        self.assertEqual(zone.is_fanning(), 1)

                # Test fanning inactive (power off)
                with mock.patch.object(zone, "is_fan_on", return_value=1):
                    with mock.patch.object(zone, "is_power_on", return_value=0):
                        self.assertEqual(zone.is_fanning(), 0)

    def test_zone_is_power_on(self):
        """Test is_power_on method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)

                # Test power on (position > 0)
                zone.zone_info = {
                    "latestData": {"uiData": {"SystemSwitchPosition": 1}}
                }
                with mock.patch.object(zone, "refresh_zone_info"):
                    self.assertEqual(zone.is_power_on(), 1)

                # Test power off (position = 0)
                zone.zone_info = {
                    "latestData": {"uiData": {"SystemSwitchPosition": 0}}
                }
                with mock.patch.object(zone, "refresh_zone_info"):
                    self.assertEqual(zone.is_power_on(), 0)

    def test_zone_is_fan_on(self):
        """Test is_fan_on method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)

                # Test fan running
                zone.zone_info = {"latestData": {"fanData": {"fanIsRunning": 1}}}
                with mock.patch.object(zone, "refresh_zone_info"):
                    self.assertEqual(zone.is_fan_on(), 1)

                # Test fan not running
                zone.zone_info = {"latestData": {"fanData": {"fanIsRunning": 0}}}
                with mock.patch.object(zone, "refresh_zone_info"):
                    self.assertEqual(zone.is_fan_on(), 0)

    def test_zone_get_wifi_strength(self):
        """Test get_wifi_strength method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)

                with mock.patch.object(zone, "refresh_zone_info"):
                    strength = zone.get_wifi_strength()
                    # Should return BOGUS_INT
                    self.assertEqual(strength, float(util.BOGUS_INT))

    def test_zone_get_wifi_status(self):
        """Test get_wifi_status method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)

                # Test wifi connected
                zone.zone_info = {"communicationLost": False}
                self.assertTrue(zone.get_wifi_status())

                # Test wifi disconnected
                zone.zone_info = {"communicationLost": True}
                self.assertFalse(zone.get_wifi_status())

    def test_zone_get_battery_voltage(self):
        """Test get_battery_voltage method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)

                # Test device live (line power)
                zone.zone_info = {"deviceLive": True}
                self.assertEqual(zone.get_battery_voltage(), 120.0)

                # Test device not live
                zone.zone_info = {"deviceLive": False}
                self.assertEqual(zone.get_battery_voltage(), 0.0)

    def test_zone_get_battery_status(self):
        """Test get_battery_status method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)

                # Test positive voltage (good status)
                with mock.patch.object(zone, "get_battery_voltage", return_value=120.0):
                    self.assertTrue(zone.get_battery_status())

                # Test zero voltage (bad status)
                with mock.patch.object(zone, "get_battery_voltage", return_value=0.0):
                    self.assertFalse(zone.get_battery_status())

    def test_zone_get_schedule_heat_sp(self):
        """Test get_schedule_heat_sp method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)
                zone.zone_info = {
                    "latestData": {"uiData": {"ScheduleHeatSp": 68}}
                }

                with mock.patch.object(zone, "refresh_zone_info"):
                    heat_sp = zone.get_schedule_heat_sp()
                    self.assertEqual(heat_sp, 68.0)

    def test_zone_get_schedule_cool_sp(self):
        """Test get_schedule_cool_sp method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)
                zone.zone_info = {
                    "latestData": {"uiData": {"ScheduleCoolSp": 74}}
                }

                with mock.patch.object(zone, "refresh_zone_info"):
                    cool_sp = zone.get_schedule_cool_sp()
                    self.assertEqual(cool_sp, 74.0)

    def test_zone_get_is_invacation_hold_mode(self):
        """Test get_is_invacation_hold_mode method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)

                # Test vacation hold enabled
                zone.zone_info = {
                    "latestData": {"uiData": {"IsInVacationHoldMode": 1}}
                }
                with mock.patch.object(zone, "refresh_zone_info"):
                    self.assertTrue(zone.get_is_invacation_hold_mode())

                # Test vacation hold disabled
                zone.zone_info = {
                    "latestData": {"uiData": {"IsInVacationHoldMode": 0}}
                }
                with mock.patch.object(zone, "refresh_zone_info"):
                    self.assertFalse(zone.get_is_invacation_hold_mode())

    def test_zone_get_vacation_hold(self):
        """Test get_vacation_hold method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)

                # Test vacation hold set
                zone.zone_info = {
                    "latestData": {"uiData": {"VacationHold": True}}
                }
                with mock.patch.object(zone, "refresh_zone_info"):
                    self.assertTrue(zone.get_vacation_hold())

                # Test vacation hold not set
                zone.zone_info = {
                    "latestData": {"uiData": {"VacationHold": False}}
                }
                with mock.patch.object(zone, "refresh_zone_info"):
                    self.assertFalse(zone.get_vacation_hold())

    def test_zone_get_vacation_hold_until_time(self):
        """Test get_vacation_hold_until_time method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)
                zone.zone_info = {
                    "latestData": {"uiData": {"VacationHoldUntilTime": 1440}}
                }

                with mock.patch.object(zone, "refresh_zone_info"):
                    until_time = zone.get_vacation_hold_until_time()
                    self.assertEqual(until_time, 1440)

    def test_zone_get_temporary_hold_until_time(self):
        """Test get_temporary_hold_until_time method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)
                zone.zone_info = {
                    "latestData": {"uiData": {"TemporaryHoldUntilTime": 720}}
                }

                with mock.patch.object(zone, "refresh_zone_info"):
                    until_time = zone.get_temporary_hold_until_time()
                    self.assertEqual(until_time, 720)

    def test_zone_get_setpoint_change_allowed(self):
        """Test get_setpoint_change_allowed method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)

                # Test setpoint change allowed
                zone.zone_info = {
                    "latestData": {"uiData": {"SetpointChangeAllowed": True}}
                }
                with mock.patch.object(zone, "refresh_zone_info"):
                    self.assertTrue(zone.get_setpoint_change_allowed())

                # Test setpoint change not allowed
                zone.zone_info = {
                    "latestData": {"uiData": {"SetpointChangeAllowed": False}}
                }
                with mock.patch.object(zone, "refresh_zone_info"):
                    self.assertFalse(zone.get_setpoint_change_allowed())

    def test_zone_get_system_switch_position(self):
        """Test get_system_switch_position method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)
                zone.zone_info = {
                    "latestData": {"uiData": {"SystemSwitchPosition": 1}}
                }

                with mock.patch.object(zone, "refresh_zone_info"):
                    position = zone.get_system_switch_position()
                    self.assertEqual(position, 1)

    def test_zone_set_heat_setpoint(self):
        """Test set_heat_setpoint method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)

                with mock.patch.object(
                    zone, "submit_control_changes"
                ) as mock_submit:
                    zone.set_heat_setpoint(70)

                    # Verify submit_control_changes was called with correct params
                    mock_submit.assert_called_once()
                    call_args = mock_submit.call_args[0][0]
                    self.assertEqual(call_args["HeatSetpoint"], 70)
                    self.assertEqual(
                        call_args["SystemSwitch"],
                        zone.system_switch_position[zone.HEAT_MODE],
                    )

    def test_zone_set_cool_setpoint(self):
        """Test set_cool_setpoint method."""
        mock_tstat = mock.Mock()
        mock_tstat.device_id = 12345
        mock_tstat.zone_name = 0

        with mock.patch("pyhtcc.Zone.__init__", return_value=None):
            with mock.patch.object(
                honeywell.ThermostatZone, "get_zone_name", return_value="TestZone"
            ):
                zone = honeywell.ThermostatZone(mock_tstat)

                with mock.patch.object(
                    zone, "submit_control_changes"
                ) as mock_submit:
                    zone.set_cool_setpoint(74)

                    # Verify submit_control_changes was called with correct params
                    mock_submit.assert_called_once()
                    call_args = mock_submit.call_args[0][0]
                    self.assertEqual(call_args["CoolSetpoint"], 74)
                    self.assertEqual(
                        call_args["SystemSwitch"],
                        zone.system_switch_position[zone.COOL_MODE],
                    )

    def test_supervisor_log_handler_emit(self):
        """Test SupervisorLogHandler emit method."""
        handler = honeywell.SupervisorLogHandler()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        with mock.patch("src.utilities.log_msg") as mock_log:
            handler.emit(record)
            # Verify log_msg was called
            mock_log.assert_called()

    def test_supervisor_log_handler_error_handling(self):
        """Test SupervisorLogHandler error handling."""
        handler = honeywell.SupervisorLogHandler()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error message",
            args=(),
            exc_info=None,
        )

        # Mock handleError to verify it's called on exception
        with mock.patch.object(handler, "handleError") as mock_handle_error:
            with mock.patch(
                "src.utilities.log_msg",
                side_effect=Exception("Test error"),
            ):
                handler.emit(record)
                mock_handle_error.assert_called_once()

    def test_timeout_http_adapter_init(self):
        """Test TimeoutHTTPAdapter initialization."""
        # Test with default timeout
        adapter = honeywell.TimeoutHTTPAdapter()
        self.assertEqual(adapter.timeout, honeywell.HTTP_TIMEOUT)

        # Test with custom timeout
        adapter = honeywell.TimeoutHTTPAdapter(timeout=5.0)
        self.assertEqual(adapter.timeout, 5.0)

    def test_timeout_http_adapter_send(self):
        """Test TimeoutHTTPAdapter send method."""
        adapter = honeywell.TimeoutHTTPAdapter(timeout=3.0)

        mock_request = mock.Mock()
        mock_response = mock.Mock()

        # Mock parent send method
        with mock.patch(
            "requests.adapters.HTTPAdapter.send", return_value=mock_response
        ) as mock_send:
            # Test with no timeout in kwargs
            adapter.send(mock_request)
            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args[1]
            self.assertEqual(call_kwargs["timeout"], 3.0)

            # Reset mock
            mock_send.reset_mock()

            # Test with timeout already in kwargs
            adapter.send(mock_request, timeout=10.0)
            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args[1]
            self.assertEqual(call_kwargs["timeout"], 10.0)

    def test_setup_pyhtcc_logging(self):
        """Test _setup_pyhtcc_logging method."""
        with mock.patch.dict(
            "os.environ",
            {"TCC_USERNAME": "test_user", "TCC_PASSWORD": "test_pass"},
        ):
            with mock.patch("pyhtcc.PyHTCC.__init__", return_value=None):
                with mock.patch.object(
                    honeywell.ThermostatClass,
                    "get_zones_info",
                    return_value=[{"DeviceID": 111}],
                ):
                    # Mock pyhtcc.logger with proper handlers list
                    mock_logger = mock.Mock()
                    mock_logger.handlers = []  # Empty list of handlers
                    with mock.patch("pyhtcc.logger", mock_logger):
                        honeywell.ThermostatClass(zone=0)

                        # Verify logger was configured
                        self.assertTrue(mock_logger.addHandler.called)
                        self.assertTrue(mock_logger.setLevel.called)


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
