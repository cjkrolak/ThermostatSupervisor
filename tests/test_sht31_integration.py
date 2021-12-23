"""
Integration test module for sht31.py.

This test requires connection to sht31 thermostat.
"""
# built-in imports
import unittest

# local imports
import context  # noqa F401, pylint: disable=unused-import.
import sht31
import sht31_config
import unit_test_common as utc
import utilities as util


@unittest.skipIf(not utc.enable_sht31_tests,
                 "sht31 tests are disabled")
@unittest.skipIf(not utc.enable_integration_tests,
                 "integration tests are disabled")
class IntegrationTest(utc.IntegrationTest):
    """
    Test functions in sht31.py.

    Tests are named to ensure basic checkout is executed first
    and supervise loop is executed last.
    """
    def setUp(self):
        self.print_test_name()

        # argv list must be valid settings
        self.unit_test_argv = [
            "supervise.py",  # module
            "sht31",  # thermostat
            str(sht31_config.LOFT_SHT31_REMOTE),  # zone, remote
            "30",  # poll time in sec
            "1000",  # reconnect time in sec
            "2",  # tolerance
            "",  # thermostat mode, no target
            "3",  # number of measurements
            ]
        self.mod = sht31
        self.mod_config = sht31_config


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
