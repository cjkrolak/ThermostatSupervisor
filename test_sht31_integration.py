"""
Integration test module for sht31.py.

This test requires connection to sht31 thermostat.
"""
# built-in imports
import unittest

# local imports
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
        self.setUpCommon()
        self.print_test_name()

        # argv list must be valid settings
        self.unit_test_argv = [
            "supervise.py",  # module
            "sht31",  # thermostat
            # TODO #291 enhancement for local zone detection
            str(0),  # zone for local net (loopback doesn't work)
            # sht31_config.LOFT_SHT31_REMOTE,  # zone, remote
            "30",  # poll time in sec
            "1000",  # reconnect time in sec
            "2",  # tolerance
            "",  # thermostat mode, no target
            "3",  # number of measurements
            ]
        self.mod = sht31
        self.mod_config = sht31_config

        # network timing measurement
        # mean timing = 0.5 sec per measurement plus 0.75 sec overhead
        self.timeout_limit = (6.0 * 0.1 +
                              (sht31_config.measurements * 0.5 + 0.75))

        # temperature and humidity repeatability measurements
        # settings below are tuned short term repeatability assessment
        # assuming sht31_config.measurements = 10
        self.temp_stdev_limit = 0.5  # 1 sigma temp repeatability limit in F
        self.temp_repeatability_measurements = 30  # number of temp msmts.
        self.humidity_stdev_limit = 0.5  # 1 sigma humid repeat. limit %RH
        self.humidity_repeatability_measurements = 30  # number of temp msmts.
        self.poll_interval_sec = 1  # delay between repeatability measurements


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
