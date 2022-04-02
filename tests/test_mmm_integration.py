"""
Integration test module for mmm.py.

This test requires connection to mmm thermostat.
"""
# built-in imports
import unittest

# local imports
from thermostatsupervisor import mmm
from thermostatsupervisor import mmm_config
from thermostatsupervisor import utilities as util
from tests import unit_test_common as utc


class IntegrationTest(utc.IntegrationTest):
    """
    Test functions in mmm.py.
    """

    def setUpIntTest(self):
        """Setup common to integration tests."""
        self.setup_common()
        self.print_test_name()

        # argv list must be valid settings
        self.unit_test_argv = [
            "supervise.py",  # module
            "mmm50",  # thermostat
            "0",  # zone
            "30",  # poll time in sec
            "1000",  # reconnect time in sec
            "2",  # tolerance
            "UNKNOWN_MODE",  # thermostat mode, no target
            "3",  # number of measurements
        ]
        self.mod = mmm
        self.mod_config = mmm_config


@unittest.skipIf(not utc.ENABLE_MMM_TESTS,
                 "mmm tests are disabled")
class FunctionalIntegrationTest(IntegrationTest,
                                utc.FunctionalIntegrationTest):
    """
    Test functional performance of mmm.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()
        # test_GetMetaData input parameters
        self.metadata_field = "network"
        self.metadata_type = dict

    def test_thermostat_get_ui_data(self):
        """Verify Thermostat.get_ui_data() function"""
        # setup class instances
        self.Thermostat, self.Zone = self.setup_thermostat_zone()

        # verify function return value
        result = self.Thermostat.get_ui_data(self.Thermostat.zone_name)
        print(f"Thermostat.get_ui_data returned {result}")
        self.assertTrue(isinstance(result, dict),
                        f"result returned is type ({type(result)}), "
                        "expected a dictionary")

    def test_thermostat_get_ui_data_param(self):
        """Verify Thermostat.get_ui_data_param() function"""
        # setup class instances
        self.Thermostat, self.Zone = self.setup_thermostat_zone()

        # verify function return value
        param = "cloud"
        expected_data_type = dict
        result = self.Thermostat.get_ui_data_param(self.Thermostat.zone_name,
                                                   param)
        print(f"Thermostat.get_ui_data_param({self.Thermostat.zone_name}, "
              f" {param}) returned {result}")
        self.assertTrue(isinstance(result, expected_data_type),
                        f"result returned is type ({type(result)}), expected "
                        f"a {expected_data_type}")

    def test_zone_get_zone_name(self):
        """Verify Zone.get_zone_name() function"""
        # setup class instances
        self.Thermostat, self.Zone = self.setup_thermostat_zone()

        # verify default option
        result = self.Zone.get_zone_name()
        print(f"Zone.get_zone_name() returned {result}")

        # verify override option
        result = self.Zone.get_zone_name(self.Thermostat.zone_name)
        print(f"Zone.get_zone_name({self.Thermostat.zone_name}) "
              f"returned {result}")


@unittest.skipIf(not utc.ENABLE_MMM_TESTS,
                 "mmm tests are disabled")
class SuperviseIntegrationTest(IntegrationTest,
                               utc.SuperviseIntegrationTest):
    """
    Test supervise functionality of mmm.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()


@unittest.skipIf(not utc.ENABLE_MMM_TESTS,
                 "mmm tests are disabled")
class PerformanceIntegrationTest(IntegrationTest,
                                 utc.PerformanceIntegrationTest):
    """
    Test performance of in mmm.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()
        # network timing measurement
        self.timeout_limit = mmm.SOCKET_TIMEOUT
        self.timing_measurements = 100


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
