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
