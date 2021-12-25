"""
Integration test module for honeywell.py.

This test requires connection to Honeywell thermostat.
"""
# built-in imports
import pprint
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

    def test_B_MMMNetworkTiming(self):
        """
        Verify network timing for Honeywell thermostat.
        """
        # measure thermostat response time
        measurements = 100
        print("Thermostat response times for %s measurements..." %
              measurements)
        meas_data = self.Zone.measure_thermostat_response_time(measurements)
        ppp = pprint.PrettyPrinter(indent=4)
        ppp.pprint(meas_data)

        # fail test if thermostat timing margin is poor
        self.assertTrue(meas_data['6sigma_upper'] < honeywell.http_timeout,
                        "6 sigma timing margin (%s) is greater than "
                        "timout setting (%s)" % (meas_data['6sigma_upper'],
                                                 honeywell.http_timeout))


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
