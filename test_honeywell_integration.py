"""
Integration test module for honeywell.py.

This test requires connection to Honeywell thermostat.
"""
# built-in imports
import unittest

# local imports
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
        self.setUpCommon()
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

        # network timing measurement
        self.timeout_limit = honeywell.http_timeout
        self.timing_measurements = 30  # fast measurement

        # temperature and humidity repeatability measurements
        # TCC server polling period to thermostat appears to be about 5-6 min
        # temperature and humidity data are int values
        # settings below are tuned for 12 minutes, 4 measurements per minute.
        self.temp_stdev_limit = 0.5  # 1 sigma temp repeatability limit in F
        self.temp_repeatability_measurements = 48  # number of temp msmts.
        self.humidity_stdev_limit = 0.5  # 1 sigma humid repeat. limit %RH
        self.humidity_repeatability_measurements = 48  # number of temp msmts.
        self.poll_interval_sec = 15  # delay between repeatability measurements


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
