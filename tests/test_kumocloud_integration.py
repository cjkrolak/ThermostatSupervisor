"""
Integration test module for kumocloud.py.

This test requires connection to Kumocloud thermostat.
"""

# built-in imports
import unittest

# local imports
# conditionally import kumocloud module to handle missing pykumo dependency
try:
    from src import kumocloud
    from src import kumocloud_config

    kumocloud_import_error = None
except ImportError as ex:
    # pykumo library not available, tests will be skipped
    kumocloud = None
    kumocloud_config = None
    kumocloud_import_error = ex

from src import utilities as util
from tests import unit_test_common as utc


class IntegrationTest(utc.IntegrationTest):
    """
    Test functions in kumocloud.py.
    """

    def setUpIntTest(self):
        """Setup common to integration tests."""
        self.setup_common()
        self.print_test_name()

        # argv list must be valid settings
        self.unit_test_argv = [
            "supervise.py",  # module
            "kumocloud",  # thermostat
            "0",  # zone
            "30",  # poll time in sec
            "1000",  # reconnect time in sec
            "2",  # tolerance
            "UNKNOWN_MODE",  # thermostat mode, no target
            "3",  # number of measurements
        ]
        self.mod = kumocloud
        self.mod_config = kumocloud_config


@unittest.skipIf(
    not utc.ENABLE_KUMOCLOUD_TESTS or kumocloud_import_error,
    "kumocloud tests are disabled",
)
class FunctionalIntegrationTest(IntegrationTest, utc.FunctionalIntegrationTest):
    """
    Test functional performance of kumocloud.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()
        # test_GetMetaData input parameters
        self.trait_field = None
        self.metadata_field = "address"
        self.metadata_type = str


@unittest.skipIf(
    not utc.ENABLE_KUMOCLOUD_TESTS or kumocloud_import_error,
    "kumocloud tests are disabled",
)
class SuperviseIntegrationTest(IntegrationTest, utc.SuperviseIntegrationTest):
    """
    Test supervise functionality of kumocloud.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()


@unittest.skipIf(
    not utc.ENABLE_KUMOCLOUD_TESTS or kumocloud_import_error,
    "kumocloud tests are disabled",
)
class PerformanceIntegrationTest(IntegrationTest, utc.PerformanceIntegrationTest):
    """
    Test performance of kumocloud.py.
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
    util.log_msg.debug = True  # type: ignore[attr-defined]
    unittest.main(verbosity=2)
