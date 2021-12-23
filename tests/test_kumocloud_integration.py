"""
Integration test module for kumocloud.py.

This test requires connection to Kumocloud thermostat.
"""
# built-in imports
import unittest

# local imports
import context  # pylint: disable=unused-import.
import kumocloud
import kumocloud_config
import unit_test_common as utc
import utilities as util


@unittest.skipIf(not utc.enable_integration_tests,
                 "integration tests are disabled")
class IntegrationTest(utc.IntegrationTest):
    """
    Test functions in kumocloud.py.

    Tests are named to ensure basic checkout is executed first
    and supervise loop is executed last.
    """
    def setUp(self):
        self.print_test_name()

        # argv list must be valid settings
        self.unit_test_argv = [
            "supervise.py",  # module
            "kumocloud",  # thermostat
            "0",  # zone
            "30",  # poll time in sec
            "1000",  # reconnect time in sec
            "2",  # tolerance
            "",  # thermostat mode, no target
            "3",  # number of measurements
            ]
        self.mod = kumocloud
        self.mod_config = kumocloud_config


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
