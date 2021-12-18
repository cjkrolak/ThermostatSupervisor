"""
Integration test module for kumolocal.py.

This test requires connection to kumolocal thermostat.
"""
# built-in imports
import unittest

# local imports
import kumolocal
import supervise as sup
import thermostat_api as api
import thermostat_common as tc
import unit_test_common as utc
import utilities as util


@unittest.skipIf(not utc.enable_integration_tests,
                 "integration tests are disabled")
@unittest.skipIf(not utc.enable_kumolocal_tests,
                 "kumolocal tests are disabled")
class IntegrationTest(utc.UnitTestCommon):
    """
    Test functions in kumolocal.py.

    Tests are named to ensure basic checkout is executed first
    and supervise loop is executed last.
    """

    def setUp(self):
        self.print_test_name()

        # argv list must be valid settings
        self.unit_test_argv = [
            "supervise.py",  # module
            "kumolocal",  # thermostat
            "0",  # zone
            "30",  # poll time in sec
            "1000",  # reconnect time in sec
            "2",  # tolerance
            "",  # thermostat mode, no target
            "3",  # number of measurements
            ]

    def tearDown(self):
        self.print_test_result()

    def test_A_KumolocalThermostatBasicCheckout(self):
        """
        Verify thermostat_basic_checkout on kumolocal.
        """
        mod = kumolocal
        tc.thermostat_basic_checkout(
            api,
            self.unit_test_argv[api.get_argv_position("thermostat_type")],
            self.unit_test_argv[api.get_argv_position("zone")],
            mod.ThermostatClass, mod.ThermostatZone
            )

    def test_Z_KumolocalSupervise(self):
        """
        Verify supervisor loop on kumolocal Thermostat.
        """
        return_status = sup.exec_supervise(debug=True,
                                           argv_list=self.unit_test_argv)
        self.assertTrue(return_status, "return status=%s, expected True" %
                        return_status)


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
