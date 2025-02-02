"""
Unit tests for the `flask_generic` module in the `thermostatsupervisor` package.
Classes:
    TestFlaskGeneric: Contains unit tests for the `schedule_ipban_block_list_report` and `print_ipban_block_list_with_timestamp` functions.
Methods:
    test_schedule_ipban_block_list_report(MockAPScheduler):
        Tests the `schedule_ipban_block_list_report` function to ensure it schedules the IP ban block list report correctly with different debug modes.
    test_print_ipban_block_list_with_timestamp(mock_datetime):
        Tests the `print_ipban_block_list_with_timestamp` function to ensure it prints the IP ban block list with the correct timestamp.
"""

# built-in modules
import datetime
import unittest
from unittest.mock import MagicMock, patch

# thrird-party modules

# local modules
from thermostatsupervisor.flask_generic import (
    print_ipban_block_list_with_timestamp,
    schedule_ipban_block_list_report,
)
from tests import unit_test_common as utc
from thermostatsupervisor import utilities as util


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
        - Tests the `schedule_ipban_block_list_report` function to ensure that it schedules
        - Sets `debug_mode` to True and verifies that the print function is called with
          the expected message indicating that the IP ban blacklist report is scheduled
          every 1.0 minutes.
    3. `test_schedule_ipban_block_list_report_normal_mode`:
        - Tests the `schedule_ipban_block_list_report` function in normal mode.
        - Sets `debug_mode` to False and verifies that the print function is called with
          the expected message indicating that the IP ban blacklist report is scheduled
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
            - Call the print_ipban_block_list_with_timestamp function with the mocked IP ban list.
        Assert:
            - Verify that the print function is called once with the expected output string
              containing the timestamp and the IP ban block list.
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
                f"{expected_timestamp}: ip_ban black list: {self.mock_ip_ban.get_block_list()}"
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
            - Call `schedule_ipban_block_list_report` with the mock IP ban object and debug mode.
        Assert:
            - Verify that the print function is called once with the expected message indicating
              that the IP ban blacklist report is scheduled every 1.0 minutes.
        """

        # Arrange
        debug_mode = True
        expected_interval = "1.0"

        # Act
        with patch("apscheduler.schedulers.background.BackgroundScheduler"):
            schedule_ipban_block_list_report(self.mock_ip_ban, debug_mode)

        # Assert
        mock_print.assert_called_once_with(
            f"ip_ban blacklist report scheduled every {expected_interval} minutes"
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
            blacklist report is scheduled every 1440.0 minutes.
        """

        # Arrange
        debug_mode = False
        expected_interval = "1440.0"

        # Act
        with patch("apscheduler.schedulers.background.BackgroundScheduler"):
            schedule_ipban_block_list_report(self.mock_ip_ban, debug_mode)

        # Assert
        mock_print.assert_called_once_with(
            f"ip_ban blacklist report scheduled every {expected_interval} minutes"
        )


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
