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


class IntegrationTest(utc.IntegrationTest):
    """
    Test functions in mmm.py.
    """
    def setUpIntTest(self):
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


class FunctionalIntegrationTest(IntegrationTest,
                                utc.FunctionalIntegrationTest):
    """
    Test functional performance of mmm.py.
    """
    def setUp(self):
        self.setUpIntTest()
        # test_GetMetaData input parameters
        self.metadata_field = "network"
        self.metadata_type = dict

    def test_Get_UiData(self):
        """Verify get_uiData() function"""
        # setup class instances
        self.Thermostat, self.Zone = self.setUpThermostatZone()

        # verify function return value
        result = self.Thermostat.get_uiData(self.Thermostat.zone_number)
        print("get_uiData returned %s" % result)
        self.assertTrue(isinstance(result, dict),
                        "result returned is type (%s), "
                        "expected a dictionary" % type(result))

    def test_GetUiDataParam(self):
        """Verify get_uiData_param() function"""
        # setup class instances
        self.Thermostat, self.Zone = self.setUpThermostatZone()

        # verify function return value
        param = ""
        expected_data_type = str
        result = self.Thermostat.get_uiData_param(param)
        print("get_uiData_param(%s) returned %s" %
              (param, result))
        self.assertTrue(isinstance(result, expected_data_type),
                        "result returned is type (%s), "
                        "expected a %s" % (type(result), expected_data_type))

    def test_GetZoneName(self):
        """Verify get_zone_name() function"""
        # setup class instances
        self.Thermostat, self.Zone = self.setUpThermostatZone()

        # verify default option
        result = self.Thermostat.get_zone_name()
        print("get_zone_name() returned %s" % result)

        # verify override option
        result = self.Thermostat.get_zone_name(self.Thermostat.zone_number)
        print("get_zone_name(%s) returned %s" %
              (self.Thermostat.zone_number, result))


class SuperviseIntegrationTest(IntegrationTest,
                               utc.SuperviseIntegrationTest):
    """
    Test supervise functionality of mmm.py.
    """
    def setUp(self):
        self.setUpIntTest()


class PerformanceIntegrationTest(IntegrationTest,
                                 utc.PerformanceIntegrationTest):
    """
    Test performance of in mmm.py.
    """
    def setUp(self):
        self.setUpIntTest()
        # network timing measurement
        self.timeout_limit = mmm.socket_timeout
        self.timing_measurements = 100


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
