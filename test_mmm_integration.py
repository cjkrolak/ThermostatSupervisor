"""
Integration test module for mmm.py.

This test requires connection to mmm thermostat.
"""
# built-in imports
import pprint
import unittest

# local imports
import mmm
import mmm_config
import supervise as sup
import thermostat_api as api
import thermostat_common as tc
import unit_test_common as utc
import utilities as util


class Test(utc.UnitTestCommon):
    """
    Test functions in mmm.py.

    Tests are named to ensure basic checkout is executed first
    and supervise loop is executed last.
    """

    def setUp(self):
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

    def tearDown(self):
        self.print_test_result()

    @unittest.skipIf(utc.is_azure_environment(),
                     "mmm is only supported on local network")
    def test_A_MMMThermostatBasicCheckout(self):
        """
        Verify thermostat_basic_checkout on mmm.
        """
        _, Zone = tc.thermostat_basic_checkout(api, mmm_config.ALIAS,
                                               mmm.ThermostatClass,
                                               mmm.ThermostatZone,
                                               self.unit_test_argv)

        # measure thermostat response time
        measurements = 100
        print("Thermostat response times for %s measurements..." %
              measurements)
        meas_data = Zone.measure_thermostat_response_time(measurements)
        ppp = pprint.PrettyPrinter(indent=4)
        ppp.pprint(meas_data)

        # fail test if thermostat timing margin is poor
        self.assertTrue(meas_data['6sigma_upper'] < mmm.socket_timeout,
                        "6 sigma timing margin (%s) is greater than "
                        "timout setting (%s)" % (meas_data['6sigma_upper'],
                                                 mmm.socket_timeout))

    @unittest.skipIf(utc.is_azure_environment(),
                     "mmm is only supported on local network")
    def test_Z_MMMSupervise(self):
        """
        Verify supervisor loop on mmm Thermostat.
        """
        return_status = sup.exec_supervise(debug=True,
                                           argv_list=self.unit_test_argv)
        self.assertTrue(return_status, "return status=%s, expected True" %
                        return_status)


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
