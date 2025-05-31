"""
Unit test module for honeywell.py.

Tests retry functionality with mocked exceptions.
"""
# built-in imports
import http.client
import time
import unittest
import urllib3.exceptions
from unittest import mock

# local imports
from thermostatsupervisor import honeywell
from thermostatsupervisor import utilities as util
from tests import unit_test_common as utc


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
                    import pyhtcc

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


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
