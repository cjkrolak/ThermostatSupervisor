"""
Integration test module for sht31.py.

This test requires connection to sht31 thermostat.
"""
# built-in imports
import unittest

# local imports
import sht31
import sht31_config
import supervise as sup
import thermostat_api as api
import thermostat_common as tc
import unit_test_common as utc
import utilities as util


class Test(utc.UnitTestCommon):
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

    def tearDown(self):
        self.print_test_result()

    @unittest.skip("sht31 thermostat is currently broken, skipping test")
    def test_A_Sht31ThermostatBasicCheckout(self):
        """
        Verify thermostat_basic_checkout on sht31.
        """
        mod = sht31
        tc.thermostat_basic_checkout(
            api,
            self.unit_test_argv[api.get_argv_position("thermostat_type")],
            self.unit_test_argv[api.get_argv_position("zone")],
            mod.ThermostatClass, mod.ThermostatZone
            )

    @unittest.skip("sht31 thermostat is currently broken, skipping test")
    def test_Z_Sht31Supervise(self):
        """
        Verify supervisor loop on sht31 Thermostat.
        """
        return_status = sup.exec_supervise(debug=True,
                                           argv_list=self.unit_test_argv)
        self.assertTrue(return_status, "return status=%s, expected True" %
                        return_status)


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
