"""
Unit tests for the `flask_generic` module in the `thermostatsupervisor` package.
Classes:
    TestFlaskGeneric: Contains unit tests for the `schedule_ipban_block_list_report`
                      and `print_ipban_block_list_with_timestamp` functions.
Methods:
    test_schedule_ipban_block_list_report(MockAPScheduler):
        Tests the `schedule_ipban_block_list_report` function to ensure it schedules
        the IP ban block list report correctly with different debug modes.
    test_print_ipban_block_list_with_timestamp(mock_datetime):
        Tests the `print_ipban_block_list_with_timestamp` function to ensure it prints
        the IP ban block list with the correct timestamp.
"""

# built-in modules
import datetime
import unittest
from unittest.mock import MagicMock, patch
import unittest.mock

# thrird-party modules

# local modules
from src.flask_generic import (
    CustomJSONEncoder,
    clear_ipban_block_list,
    initialize_ipban,
    print_ipban_block_list,
    print_ipban_block_list_with_timestamp,
    print_flask_config,
    schedule_ipban_block_list_report,
    set_flask_cookie_config,
)
from src import utilities as util
from tests import unit_test_common as utc


class TestFlaskGeneric(utc.UnitTest):
    """
    Test suite for Flask generic functionalities related to IP ban management.
    This test suite includes the following test cases:
    1. `test_print_ipban_block_list_with_timestamp`:
        - Tests the `print_ipban_block_list_with_timestamp` function to ensure it prints
        - Mocks the current datetime to return a specific timestamp and verifies that
          the print function is called with the expected output string containing the
          timestamp and the IP ban block list.
    2. `test_schedule_ipban_block_list_report_debug_mode`:
        - Tests the `schedule_ipban_block_list_report` function to ensure that it
          schedules.
        - Sets `debug_mode` to True and verifies that the print function is called with
          the expected message indicating that the IP ban BlockList report is scheduled
          every 1.0 minutes.
    3. `test_schedule_ipban_block_list_report_normal_mode`:
        - Tests the `schedule_ipban_block_list_report` function in normal mode.
        - Sets `debug_mode` to False and verifies that the print function is called with
          the expected message indicating that the IP ban BlockList report is scheduled
          every 1440.0 minutes.
    """

    def setUp(self):
        """
        Set up the test environment for the Flask application.
        This method is called before each test is executed. It initializes a mock
        IP ban object and sets up its return value for the get_block_list method.
        Attributes:
            mock_ip_ban (MagicMock): A mock object for simulating IP ban functionality.
        """

        super().setUp()
        self.mock_ip_ban = MagicMock()
        self.mock_ip_ban.get_block_list.return_value = {
            "192.168.1.1": {
                "count": 3,
                "timestamp": datetime.datetime(2024, 1, 1, 12, 0, 0),
            }
        }

    @patch("builtins.print")
    def test_print_ipban_block_list_with_timestamp(self, mock_print):
        """
        Test the print_ipban_block_list_with_timestamp function to ensure it prints
        the IP ban block list with the correct timestamp.
        Args:
            mock_print (Mock): Mock object for the print function.
        Arrange:
            - Set the expected timestamp to "2024-01-01 12:00:00".
            - Mock the current datetime to return the expected timestamp.
        Act:
            - Call the print_ipban_block_list_with_timestamp function with the mocked
              IP ban list.
        Assert:
            - Verify that the print function is called once with the expected output
              string containing the timestamp and the IP ban block list.
        """

        # Arrange
        expected_timestamp = "2024-01-01 12:00:00"
        mock_now = datetime.datetime(2024, 1, 1, 12, 0, 0)

        with patch("datetime.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now

            # Act
            print_ipban_block_list_with_timestamp(self.mock_ip_ban)

            # Assert
            mock_print.assert_called_once_with(
                f"{expected_timestamp}: ip_ban block list: "
                f"{self.mock_ip_ban.get_block_list()}"
            )

    @patch("builtins.print")
    def test_schedule_ipban_block_list_report_debug_mode(self, mock_print):
        """
        Test the `schedule_ipban_block_list_report` function to ensure that it schedules
        the IP ban block list report correctly when debug mode is enabled.
        Args:
            mock_print (Mock): Mock object for the print function.
        Arrange:
            - Set `debug_mode` to True.
            - Define the expected interval as "1.0" minutes.
        Act:
            - Patch the `BackgroundScheduler` from `apscheduler.schedulers.background`.
            - Call `schedule_ipban_block_list_report` with the mock IP ban object and
              debug mode.
        Assert:
            - Verify that the print function is called once with the expected message
              indicating that the IP ban BlockList report is scheduled every
              1.0 minutes.
        """

        # Arrange
        debug_mode = True
        expected_interval = "1.0"

        # Act
        with patch("apscheduler.schedulers.background.BackgroundScheduler"):
            schedule_ipban_block_list_report(self.mock_ip_ban, debug_mode)

        # Assert
        mock_print.assert_called_once_with(
            f"ip_ban BlockList report scheduled every {expected_interval} minutes"
        )

    @patch("builtins.print")
    def test_schedule_ipban_block_list_report_normal_mode(self, mock_print):
        """
        Test the `schedule_ipban_block_list_report` function in normal mode.
        This test verifies that the `schedule_ipban_block_list_report` function
        schedules the IP ban block list report correctly when the debug mode is
        set to False. It mocks the `BackgroundScheduler` and checks that the
        `mock_print` function is called with the expected message.
        Args:
            mock_print (Mock): Mock object for the print function.
        Assertions:
            mock_print.assert_called_once_with: Verifies that the print function
            is called once with the expected message indicating the IP ban
            BlockList report is scheduled every 1440.0 minutes.
        """

        # Arrange
        debug_mode = False
        expected_interval = "1440.0"

        # Act
        with patch("apscheduler.schedulers.background.BackgroundScheduler"):
            schedule_ipban_block_list_report(self.mock_ip_ban, debug_mode)

        # Assert
        mock_print.assert_called_once_with(
            f"ip_ban BlockList report scheduled every {expected_interval} minutes"
        )

    def test_custom_json_encoder_default_datetime(self):
        """Test CustomJSONEncoder.default() with datetime object."""
        encoder = CustomJSONEncoder()
        test_datetime = datetime.datetime(2024, 1, 1, 12, 0, 0)

        with patch("builtins.print") as mock_print:
            result = encoder.default(test_datetime)
            self.assertEqual(result, "2024-01-01T12:00:00")
            mock_print.assert_called_once_with(
                f"CustomJSONEncoder enabled: {test_datetime}"
            )

    def test_custom_json_encoder_default_non_datetime(self):
        """Test CustomJSONEncoder.default() with non-datetime object."""
        encoder = CustomJSONEncoder()
        test_obj = {"key": "value"}

        with patch("builtins.print") as mock_print:
            with self.assertRaises(TypeError):
                encoder.default(test_obj)
            mock_print.assert_called_once_with(
                f"CustomJSONEncoder bypassed: {test_obj}, {type(test_obj)}"
            )

    @patch("builtins.print")
    def test_clear_ipban_block_list_all_ips(self, mock_print):
        """Test clear_ipban_block_list() clearing all IP addresses."""
        # Setup mock with multiple IPs
        self.mock_ip_ban.get_block_list.return_value = {
            "192.168.1.1": {"count": 3},
            "192.168.1.2": {"count": 5},
        }
        self.mock_ip_ban.remove.return_value = True

        # Call function with no specific IP address
        clear_ipban_block_list(self.mock_ip_ban)

        # Verify prints and removes were called
        # Should have: before, clearing all, after = 3 prints
        self.assertEqual(mock_print.call_count, 3)
        self.assertEqual(self.mock_ip_ban.remove.call_count, 2)

    @patch("builtins.print")
    def test_clear_ipban_block_list_specific_ip(self, mock_print):
        """Test clear_ipban_block_list() clearing specific IP address."""
        self.mock_ip_ban.remove.return_value = True
        test_ip = "192.168.1.100"

        # Call function with specific IP address
        clear_ipban_block_list(self.mock_ip_ban, test_ip)

        # Verify remove was called with specific IP
        self.mock_ip_ban.remove.assert_called_once_with(test_ip)
        self.assertEqual(mock_print.call_count, 3)  # before, clearing, after

    @patch("builtins.print")
    def test_clear_ipban_block_list_ip_not_found(self, mock_print):
        """Test clear_ipban_block_list() when IP is not found."""
        self.mock_ip_ban.remove.return_value = False
        test_ip = "192.168.1.100"

        # Call function with IP that doesn't exist
        clear_ipban_block_list(self.mock_ip_ban, test_ip)

        # Verify warning message was printed
        warning_calls = [
            call for call in mock_print.call_args_list if "WARNING" in str(call)
        ]
        self.assertTrue(len(warning_calls) > 0)

    @patch("builtins.print")
    def test_print_ipban_block_list(self, mock_print):
        """Test print_ipban_block_list() function."""
        expected_block_list = {"192.168.1.1": {"count": 3}}
        self.mock_ip_ban.get_block_list.return_value = expected_block_list

        print_ipban_block_list(self.mock_ip_ban)

        mock_print.assert_called_once_with(f"ip_ban block list: {expected_block_list}")

    @patch("src.flask_generic.IpBan")
    @patch("builtins.print")
    def test_initialize_ipban(self, mock_print, mock_ipban_class):
        """Test initialize_ipban() function."""
        # Setup mock app and ipban instance
        mock_app = MagicMock()
        mock_ipban_instance = MagicMock()
        mock_ipban_class.return_value = mock_ipban_instance

        # Call function
        result = initialize_ipban(mock_app)

        # Verify IpBan was created with correct parameters
        mock_ipban_class.assert_called_once()
        mock_ipban_instance.init_app.assert_called_once_with(mock_app)
        mock_ipban_instance.load_nuisances.assert_called_once()
        self.assertEqual(result, mock_ipban_instance)

    def test_set_flask_cookie_config(self):
        """Test set_flask_cookie_config() function."""
        mock_app = MagicMock()

        set_flask_cookie_config(mock_app)

        mock_app.config.update.assert_called_once_with(
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE="Lax",
        )

    @patch("builtins.print")
    def test_print_flask_config(self, mock_print):
        """Test print_flask_config() function."""
        mock_app = MagicMock()
        test_config = {"DEBUG": False, "TESTING": True}
        mock_app.config = test_config

        print_flask_config(mock_app)

        # Verify both print statements were called
        expected_calls = [
            unittest.mock.call("flask config:"),
            unittest.mock.call(f"{test_config}"),
        ]
        mock_print.assert_has_calls(expected_calls)


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
