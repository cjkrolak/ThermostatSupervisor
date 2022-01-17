"""
Integration test module for emulator.py.

This test requires connection to emulator thermostat.
"""
# built-in imports
import unittest

# local imports
import emulator
import emulator_config
import unit_test_common as utc
import utilities as util


class IntegrationTest(utc.IntegrationTest):
    """
    Test functions in emulator.py.
    """
    def setUpIntTest(self):
        self.setUpCommon()
        self.print_test_name()

        # emulator argv list must be valid settings
        self.unit_test_argv = [
            "supervise.py",  # module
            "emulator",  # thermostat
            "0",  # zone
            "5",  # poll time in sec, this value violates min
            # cycle time for TCC if reverting temperature deviation
            "1000",  # reconnect time in sec
            "2",  # tolerance
            "",  # thermostat mode, no target
            "3",  # number of measurements
            ]
        self.mod = emulator
        self.mod_config = emulator_config


class FunctionalIntegrationTest(IntegrationTest,
                                utc.FunctionalIntegrationTest):
    """
    Test functional performance of emulator.py.
    """
    def setUp(self):
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
        self.setUpIntTest()


class PerformanceIntegrationTest(IntegrationTest,
                                 utc.PerformanceIntegrationTest):
    """
    Test performance of in emulator.py.
    """
    def setUp(self):
        self.setUpIntTest()
        # network timing measurement
        self.timeout_limit = 30
        self.timing_measurements = 30  # fast measurement

        # temperature and humidity repeatability measurements
        # TCC server polling period to thermostat appears to be about 5-6 min
        # temperature and humidity data are int values
        # settings below are tuned for 12 minutes, 4 measurements per minute.
        self.temp_stdev_limit = 0.5  # 1 sigma temp repeatability limit in F
        self.temp_repeatability_measurements = 48  # number of temp msmts.
        self.humidity_stdev_limit = 0.5  # 1 sigma humid repeat. limit %RH
        self.humidity_repeatability_measurements = 48  # number of temp msmts.
        self.poll_interval_sec = 5  # delay between repeatability measurements


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
