"""
Integration test module for sht31.py.

This test requires connection to sht31 thermostat.
"""
# built-in imports
import unittest

# local imports
from thermostatsupervisor import sht31
from thermostatsupervisor import sht31_config
from tests import unit_test_common as utc
from thermostatsupervisor import utilities as util


class IntegrationTest(utc.IntegrationTest):
    """
    Test functions in sht31.py.
    """
    def setUpIntTest(self):
        self.setup_common()
        self.print_test_name()

        # argv list must be valid settings
        local_host = sht31_config.sht31_metadata[
            sht31_config.LOFT_SHT31]["host_name"]
        self.unit_test_argv = [
            "supervise.py",  # module
            "sht31",  # thermostat
            # loopback does not work so use local sht31 zone if testing
            # on the local net.  If not, use the DNS name.
            str([sht31_config.LOFT_SHT31_REMOTE,
                 sht31_config.LOFT_SHT31][
                     util.is_host_on_local_net(local_host)[0]]),
            "30",  # poll time in sec
            "1000",  # reconnect time in sec
            "2",  # tolerance
            "",  # thermostat mode, no target
            "3",  # number of measurements
            ]
        self.mod = sht31
        self.mod_config = sht31_config


class FunctionalIntegrationTest(IntegrationTest,
                                utc.FunctionalIntegrationTest):
    """
    Test functional performance of sht31.py.
    """
    def setUp(self):
        self.setUpIntTest()
        # test_GetMetaData input parameters
        self.metadata_field = sht31_config.API_TEMPF_MEAN
        self.metadata_type = float


class SuperviseIntegrationTest(IntegrationTest,
                               utc.SuperviseIntegrationTest):
    """
    Test supervise functionality of sht31.py.
    """
    def setUp(self):
        self.setUpIntTest()


class PerformanceIntegrationTest(IntegrationTest,
                                 utc.PerformanceIntegrationTest):
    """
    Test performance of in honeywell.py.
    """
    def setUp(self):
        self.setUpIntTest()
        # network timing measurement
        # mean timing = 0.5 sec per measurement plus 0.75 sec overhead
        self.timeout_limit = (6.0 * 0.1 +
                              (sht31_config.MEASUREMENTS * 0.5 + 0.75))

        # temperature and humidity repeatability measurements
        # settings below are tuned short term repeatability assessment
        # assuming sht31_config.measurements = 10
        self.temp_stdev_limit = 0.5  # 1 sigma temp repeatability limit in F
        self.temp_repeatability_measurements = 30  # number of temp msmts.
        self.humidity_stdev_limit = 0.5  # 1 sigma humid repeat. limit %RH
        self.humidity_repeatability_measurements = 30  # number of temp msmts.
        self.poll_interval_sec = 1  # delay between repeatability measurements


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)