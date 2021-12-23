"""
Integration test module for honeywell.py.

This test requires connection to Honeywell thermostat.
"""
# built-in imports
import unittest

# local imports
import context  # pylint: disable=unused-import.
import honeywell
import honeywell_config
import unit_test_common as utc
import utilities as util


@unittest.skipIf(not utc.enable_integration_tests,
                 "integration tests are disabled")
class IntegrationTest(utc.IntegrationTest):
    """
    Test functions in honeywell.py.

    Tests are named to ensure basic checkout is executed first
    and supervise loop is executed last.
    """
    def setUp(self):
        self.print_test_name()

        # Honeywell argv list must be valid settings
        self.unit_test_argv = [
            "supervise.py",  # module
            "honeywell",  # thermostat
            "0",  # zone
            "30",  # poll time in sec, this value violates min
            # cycle time for TCC if reverting temperature deviation
            "1000",  # reconnect time in sec
            "2",  # tolerance
            "",  # thermostat mode, no target
            "3",  # number of measurements
            ]
        self.mod = honeywell
        self.mod_config = honeywell_config


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
