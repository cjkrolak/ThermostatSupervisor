"""
Integration test module for bink.py.
"""
# built-in imports
import unittest

# local imports
from thermostatsupervisor import blink
from thermostatsupervisor import blink_config
from thermostatsupervisor import utilities as util
from tests import unit_test_common as utc


@unittest.skipIf(not utc.ENABLE_BLINK_TESTS,
                 "Blink camera tests are disabled")
class IntegrationTest(utc.IntegrationTest):
    """
    Test functions in blink.py.
    """

    def setUpIntTest(self):
        self.setup_common()
        self.print_test_name()

        # argv list must be valid settings
        self.unit_test_argv = [
            "supervise.py",  # module
            "blink",  # thermostat
            str(blink_config.default_zone),
            "5",  # poll time in sec
            "12",  # reconnect time in sec
            "2",  # tolerance
            "UNKNOWN_MODE",  # thermostat mode, no target
            "6",  # number of measurements
        ]
        self.mod = blink
        self.mod_config = blink_config


@unittest.skipIf(not utc.ENABLE_BLINK_TESTS,
                 "Blink camera tests are disabled")
class FunctionalIntegrationTest(IntegrationTest,
                                utc.FunctionalIntegrationTest):
    """
    Test functional performance of blink.py.
    """

    def setUp(self):
        self.setUpIntTest()
        # test_GetMetaData input parameters
        self.metadata_field = blink_config.API_TEMPF_MEAN
        self.metadata_type = int  # type of raw value in metadata dict.


@unittest.skipIf(not utc.ENABLE_BLINK_TESTS,
                 "blink tests are disabled")
class SuperviseIntegrationTest(IntegrationTest,
                               utc.SuperviseIntegrationTest):
    """
    Test supervise functionality of blink.py.
    """
    def setUp(self):
        super().setUp()
        self.setUpIntTest()


@unittest.skipIf(not utc.ENABLE_BLINK_TESTS,
                 "blink tests are disabled")
class PerformanceIntegrationTest(IntegrationTest,
                                 utc.PerformanceIntegrationTest):
    """
    Test performance of in honeywell.py.
    """
    def setUp(self):
        super().setUp()
        self.setUpIntTest()
        # network timing measurement
        # mean timing = 0.5 sec per measurement plus 0.75 sec overhead
        self.timeout_limit = (6.0 * 0.1 +
                              (blink_config.MEASUREMENTS * 0.5 + 0.75))

        # temperature and humidity repeatability measurements
        # settings below are tuned short term repeatability assessment
        self.temp_stdev_limit = 0.5  # 1 sigma temp repeatability limit in F
        self.temp_repeatability_measurements = 30  # number of temp msmts.
        self.humidity_stdev_limit = 0.5  # 1 sigma humid repeat. limit %RH
        self.humidity_repeatability_measurements = 30  # number of temp msmts.
        self.poll_interval_sec = 1  # delay between repeatability measurements


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
