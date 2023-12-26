"""
Integration test module for nest.py.

This test requires connection to nest thermostat.
"""
# built-in imports
import unittest

# local imports
from thermostatsupervisor import nest
from thermostatsupervisor import nest_config
from thermostatsupervisor import utilities as util
from tests import unit_test_common as utc


class IntegrationTest(utc.IntegrationTest):
    """
    Test functions in nest.py.
    """

    def setUpIntTest(self):
        """Setup common to integration tests."""
        self.setup_common()
        self.print_test_name()

        # argv list must be valid settings
        self.unit_test_argv = [
            "supervise.py",  # module
            "nest",  # thermostat
            "0",  # zone
            "30",  # poll time in sec
            "1000",  # reconnect time in sec
            "2",  # tolerance
            "UNKNOWN_MODE",  # thermostat mode, no target
            "3",  # number of measurements
        ]
        self.mod = nest
        self.mod_config = nest_config


@unittest.skipIf(not utc.ENABLE_NEST_TESTS, "nest tests are disabled")
class FunctionalIntegrationTest(IntegrationTest, utc.FunctionalIntegrationTest):
    """
    Test functional performance of nest.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()
        # test_GetMetaData input parameters
        self.trait_field = "Info"
        self.metadata_field = "customName"
        self.metadata_type = str


@unittest.skipIf(not utc.ENABLE_NEST_TESTS, "nest tests are disabled")
class SuperviseIntegrationTest(IntegrationTest, utc.SuperviseIntegrationTest):
    """
    Test supervise functionality of nest.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()


@unittest.skipIf(not utc.ENABLE_NEST_TESTS, "nest tests are disabled")
class PerformanceIntegrationTest(IntegrationTest, utc.PerformanceIntegrationTest):
    """
    Test performance of nest.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()
        # network timing measurement
        self.timeout_limit = 30
        self.timing_measurements = 30
        self.timing_func = self.Zone.refresh_zone_info

        # temperature and humidity repeatability measurements
        # temperature and humidity data are int values
        # settings below are tuned for 12 minutes, 4 measurements per minute.
        self.temp_stdev_limit = 2.0  # 1 sigma temp repeatability limit in F
        self.temp_repeatability_measurements = 48  # number of temp msmts.
        self.humidity_stdev_limit = 2.0  # 1 sigma humid repeat. limit %RH
        self.humidity_repeatability_measurements = 48  # number of temp msmts.
        self.poll_interval_sec = (
            nest_config.cache_period_sec + 0.5
        )  # delay between repeatability measurements


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
