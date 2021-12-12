"""
Integration test module for honeywell.py.

This test requires connection to Honeywell thermostat.
"""
# built-in imports
import unittest

# local imports
import honeywell
import honeywell_config
import supervise as sup
import thermostat_api as api
import thermostat_common as tc
import unit_test_common as utc
import utilities as util


class Test(utc.UnitTestCommon):
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

    def tearDown(self):
        self.print_test_result()

    def test_A_HoneywellThermostatBasicCheckout(self):
        """
        Verify thermostat_basic_checkout on Honeywell.
        """
        tc.thermostat_basic_checkout(api, honeywell_config.ALIAS,
                                     honeywell.ThermostatClass,
                                     honeywell.ThermostatZone,
                                     self.unit_test_argv)

    def test_Z_HoneywellSupervise(self):
        """
        Verify supervisor loop on Honeywell Thermostat.

        PYHTCC requests.session() is left open after the test is complete,
        so this test is titled to run last in the module.
        """
        return_status = sup.exec_supervise(debug=True,
                                           argv_list=self.unit_test_argv)
        self.assertTrue(return_status, "return status=%s, expected True" %
                        return_status)


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
