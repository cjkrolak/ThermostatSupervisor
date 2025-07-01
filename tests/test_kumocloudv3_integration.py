"""
Integration test module for kumocloudv3.py.

This test requires connection to Kumocloud thermostat using v3 API.
"""
# built-in imports
import unittest

# local imports
# conditionally import kumocloudv3 module to handle missing dependencies
try:
    from thermostatsupervisor import kumocloudv3
    from thermostatsupervisor import kumocloudv3_config

    kumocloudv3_import_error = None
except ImportError as ex:
    # requests library or other dependencies not available, tests will be skipped
    kumocloudv3 = None
    kumocloudv3_config = None
    kumocloudv3_import_error = ex

from thermostatsupervisor import utilities as util
from tests import unit_test_common as utc


class IntegrationTest(utc.IntegrationTest):
    """
    Test functions in kumocloudv3.py.
    """

    def setUpIntTest(self):
        """Setup common to integration tests."""
        self.setup_common()
        self.print_test_name()

        # argv list must be valid settings
        self.unit_test_argv = [
            "supervise.py",  # module
            "kumocloudv3",  # thermostat
            "0",  # zone
            "30",  # poll time in sec
            "1000",  # reconnect time in sec
            "2",  # tolerance
            "UNKNOWN_MODE",  # thermostat mode, no target
            "3",  # number of measurements
        ]
        self.mod = kumocloudv3
        self.mod_config = kumocloudv3_config


@unittest.skipIf(
    not utc.ENABLE_KUMOCLOUDV3_TESTS or kumocloudv3_import_error,
    "kumocloudv3 tests are disabled",
)
class FunctionalIntegrationTest(IntegrationTest, utc.FunctionalIntegrationTest):
    """
    Test functional performance of kumocloudv3.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()
        # test_GetMetaData input parameters
        self.trait_field = None
        self.metadata_field = "address"
        self.metadata_type = str


@unittest.skipIf(
    not utc.ENABLE_KUMOCLOUDV3_TESTS or kumocloudv3_import_error,
    "kumocloudv3 tests are disabled",
)
class SuperviseIntegrationTest(IntegrationTest, utc.SuperviseIntegrationTest):
    """
    Test supervise functionality of kumocloudv3.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()


@unittest.skipIf(
    not utc.ENABLE_KUMOCLOUDV3_TESTS or kumocloudv3_import_error,
    "kumocloudv3 tests are disabled",
)
class PerformanceIntegrationTest(IntegrationTest, utc.PerformanceIntegrationTest):
    """
    Test performance of kumocloudv3.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()
        # network timing measurement
        self.timeout_limit = 30
        self.timing_measurements = 30

        # temperature and humidity repeatability measurements
        # temperature and humidity data are int values
        # settings below are tuned for 12 minutes, 4 measurements per minute.
        self.temp_stdev_limit = 2.0  # 1 sigma temp repeatability limit in F
        self.temp_repeatability_measurements = 48  # number of temp msmts.
        self.humidity_stdev_limit = 2.0  # 1 sigma humid repeat. limit %RH
        self.humidity_repeatability_measurements = 48  # number of temp msmts.
        self.poll_interval_sec = 15  # delay between repeatability measurements


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
