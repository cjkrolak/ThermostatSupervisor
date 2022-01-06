"""
Integration test module for mmm.py.

This test requires connection to mmm thermostat.
"""
# built-in imports
import unittest

# local imports
import mmm
import mmm_config
import unit_test_common as utc
import utilities as util


@unittest.skipIf(not utc.enable_integration_tests,
                 "integration tests are disabled")
@unittest.skipIf(not utc.enable_mmm_tests,
                 "mmm tests are disabled")
class IntegrationTest(utc.IntegrationTest):
    """
    Test functions in mmm.py.

    Tests are named to ensure basic checkout is executed first
    and supervise loop is executed last.
    """
    def setUp(self):
        self.setUpCommon()
        self.print_test_name()

        # argv list must be valid settings
        self.unit_test_argv = [
            "supervise.py",  # module
            "mmm50",  # thermostat
            "0",  # zone
            "30",  # poll time in sec
            "1000",  # reconnect time in sec
            "2",  # tolerance
            "",  # thermostat mode, no target
            "3",  # number of measurements
            ]
        self.mod = mmm
        self.mod_config = mmm_config
        self.timeout_limit = mmm.socket_timeout
        self.timing_measurements = 100


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
