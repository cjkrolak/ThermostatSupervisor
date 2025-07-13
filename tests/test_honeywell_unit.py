"""
Unit test module for honeywell.py.

Tests retry functionality with mocked exceptions.
"""
# built-in imports
import http.client
import unittest
from unittest import mock

# third-party imports
import pyhtcc
import urllib3.exceptions

# local imports
from thermostatsupervisor import honeywell
import thermostatsupervisor.thermostat_common as tc
from thermostatsupervisor import utilities as util
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
                    "thermostatsupervisor.email_notification.send_email_alert"
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
            "thermostatsupervisor.email_notification.send_email_alert"
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
            "thermostatsupervisor.email_notification.send_email_alert"
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


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
