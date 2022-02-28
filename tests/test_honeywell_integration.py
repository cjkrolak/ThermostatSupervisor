"""
Integration test module for honeywell.py.

This test requires connection to Honeywell thermostat.
"""
# built-in imports
import unittest

# local imports
from thermostatsupervisor import honeywell
from thermostatsupervisor import honeywell_config
from thermostatsupervisor import utilities as util
from tests import unit_test_common as utc


class IntegrationTest(utc.IntegrationTest):
    """
    Test functions in honeywell.py.
    """

    def setUpIntTest(self):
        """Setup common to integration tests."""
        self.setup_common()
        self.print_test_name()

        # Honeywell argv list must be valid settings
        self.unit_test_argv = [
            "supervise.py",  # module
            "honeywell",  # thermostat
            "0",  # zone
            "30",  # poll time in sec, this value violates min
            # cycle time for TCC if reverting temperature deviation
            "1000",  # reconnect time in sec
            "2",  # tolerance
            "UNKNOWN_MODE",  # thermostat mode, no target
            "3",  # number of measurements
        ]
        self.mod = honeywell
        self.mod_config = honeywell_config


class FunctionalIntegrationTest(IntegrationTest,
                                utc.FunctionalIntegrationTest):
    """
    Test functional performance of honeywell.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()
        # test_GetMetaData input parameters
        self.metadata_field = "DeviceID"
        self.metadata_type = int


class SuperviseIntegrationTest(IntegrationTest,
                               utc.SuperviseIntegrationTest):
    """
    Test supervise functionality of honeywell.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()


class PerformanceIntegrationTest(IntegrationTest,
                                 utc.PerformanceIntegrationTest):
    """
    Test performance of in honeywell.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()
        # network timing measurement
        self.timeout_limit = honeywell.HTTP_TIMEOUT
        self.timing_measurements = 30  # fast measurement

        # temperature and humidity repeatability measurements
        # TCC server polling period to thermostat appears to be about 5-6 min
        # temperature and humidity data are int values
        # settings below are tuned for 12 minutes, 4 measurements per minute.
        self.temp_stdev_limit = 0.5  # 1 sigma temp repeatability limit in F
        self.temp_repeatability_measurements = 48  # number of temp msmts.
        self.humidity_stdev_limit = 0.5  # 1 sigma humid repeat. limit %RH
        self.humidity_repeatability_measurements = 48  # number of temp msmts.
        self.poll_interval_sec = 15  # delay between repeatability measurements


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
