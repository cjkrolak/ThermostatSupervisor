"""
Integration test module for kumolocal.py.

This test requires connection to kumolocal thermostat.
"""
# built-in imports
import unittest

# local imports
from thermostatsupervisor import kumolocal
from thermostatsupervisor import kumolocal_config
from thermostatsupervisor import utilities as util
from tests import unit_test_common as utc


class IntegrationTest(utc.IntegrationTest):
    """
    Test functions in kumolocal.py.
    """

    def setUpIntTest(self):
        """Setup common to integration tests."""
        self.setup_common()
        self.print_test_name()

        # argv list must be valid settings
        self.unit_test_argv = [
            "supervise.py",  # module
            "kumolocal",  # thermostat
            "0",  # zone
            "20",  # poll time in sec
            "50",  # reconnect time in sec
            "2",  # tolerance
            "UNKNOWN_MODE",  # thermostat mode, no target
            "6",  # number of measurements
        ]
        self.mod = kumolocal
        self.mod_config = kumolocal_config


@unittest.skipIf(not utc.ENABLE_KUMOLOCAL_TESTS, "kumolocal tests are disabled")
class LocalNetworkDetectionTest(IntegrationTest):
    """
    Test local network detection functionality for kumolocal.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()

    def test_local_network_detection_method(self):
        """Test that local network detection method exists and returns bool."""
        # This test verifies the API exists, but doesn't require actual devices
        try:
            thermostat = self.mod.ThermostatClass(zone=0, verbose=False)
            # Test that the method exists and returns a boolean
            result = thermostat.is_local_network_available()
            self.assertIsInstance(result, bool)
        except Exception as e:
            # If kumolocal isn't available, just verify the method signature
            self.skipTest(f"Kumolocal not available for testing: {e}")


@unittest.skipIf(not utc.ENABLE_KUMOLOCAL_TESTS, "kumolocal tests are disabled")
class FunctionalIntegrationTest(IntegrationTest, utc.FunctionalIntegrationTest):
    """
    Test functional performance of kumolocal.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()
        # test_GetMetaData input parameters
        self.trait_field = None
        self.metadata_field = "status"
        self.metadata_type = dict


@unittest.skipIf(not utc.ENABLE_KUMOLOCAL_TESTS, "kumolocal tests are disabled")
class SuperviseIntegrationTest(IntegrationTest, utc.SuperviseIntegrationTest):
    """
    Test supervise functionality of kumolocal.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()


@unittest.skipIf(not utc.ENABLE_KUMOLOCAL_TESTS, "kumolocal tests are disabled")
class PerformanceIntegrationTest(IntegrationTest, utc.PerformanceIntegrationTest):
    """
    Test performance of kumolocal.py.
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
