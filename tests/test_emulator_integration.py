"""
Integration test module for emulator.py.

This test requires connection to emulator thermostat.
"""
# built-in imports
import math
import unittest

# local imports
from thermostatsupervisor import emulator
from thermostatsupervisor import emulator_config
from thermostatsupervisor import utilities as util
from tests import unit_test_common as utc


class IntegrationTest(utc.IntegrationTest):
    """
    Test functions in emulator.py.
    """

    def setUpIntTest(self):
        """Setup common to integration tests."""
        self.setup_common()
        self.print_test_name()

        # emulator argv list must be valid settings
        self.unit_test_argv = [
            "supervise.py",  # module
            "emulator",  # thermostat type
            "0",  # zone
            "5",  # poll time in sec, this value violates min
            # cycle time for TCC if reverting temperature deviation
            "11",  # reconnect time in sec
            "2",  # tolerance
            "UNKNOWN_MODE",  # thermostat mode, no target
            "6",  # number of measurements
        ]
        self.mod = emulator
        self.mod_config = emulator_config


class FunctionalIntegrationTest(IntegrationTest,
                                utc.FunctionalIntegrationTest):
    """
    Test functional performance of emulator.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()
        # test_GetMetaData input parameters
        self.metadata_field = "display_temp"
        self.metadata_type = float


class SuperviseIntegrationTest(IntegrationTest,
                               utc.SuperviseIntegrationTest):
    """
    Test supervise functionality of emulator.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()


class PerformanceIntegrationTest(IntegrationTest,
                                 utc.PerformanceIntegrationTest):
    """
    Test performance of in emulator.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()
        # network timing measurement
        self.timeout_limit = 1
        self.timing_measurements = 30  # fast measurement

        # temperature and humidity repeatability measurements
        # data is uniform distribution, 1 std= (range)/sqrt(12)
        # adding 0.1 buffer to prevent false failures due to rounding, etc.
        self.temp_stdev_limit = \
            emulator_config.NORMAL_TEMP_VARIATION * 2 / math.sqrt(12) + 0.1
        self.temp_repeatability_measurements = 100  # number of temp msmts.
        self.humidity_stdev_limit = \
            emulator_config.NORMAL_HUMIDITY_VARIATION * 2 / math.sqrt(12) + 0.1
        self.humidity_repeatability_measurements = 100  # number of temp msmts.
        self.poll_interval_sec = 0.5  # delay between repeatability msmts


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
