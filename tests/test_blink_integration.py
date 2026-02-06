"""
Integration test module for blink.py.
"""

# built-in imports
import unittest
from unittest.mock import patch, MagicMock

# local imports
from src import blink
from src import blink_config
from src import utilities as util
from tests import unit_test_common as utc


@unittest.skipIf(not utc.ENABLE_BLINK_TESTS, "Blink camera tests are disabled")
class IntegrationTest(utc.IntegrationTest):
    """
    Test functions in blink.py.
    """

    def setUpIntTest(self):
        """
        Set up the integration test environment for the Blink thermostat.
        This method initializes common setup procedures and prints the test name.
        It also configures the command-line arguments required for the Blink thermostat
        integration test, including the module name, thermostat type, default zone,
        poll time, reconnect time, tolerance, thermostat mode, and the number of
        measurements.
        Attributes:
            unit_test_argv (list): List of command-line arguments for the Blink
                                   thermostat.
            mod (module): The Blink thermostat module.
            mod_config (module): The configuration module for the Blink thermostat.
        """
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


@unittest.skipIf(not utc.ENABLE_BLINK_TESTS, "Blink camera tests are disabled")
class FunctionalIntegrationTest(IntegrationTest, utc.FunctionalIntegrationTest):
    """
    Test functional performance of blink.py.
    """

    def setUp(self):
        self.setUpIntTest()
        # test_GetMetaData input parameters
        self.trait_field = None
        self.metadata_field = blink_config.API_TEMPF_MEAN
        self.metadata_type = int  # type of raw value in metadata dict.


@unittest.skipIf(not utc.ENABLE_BLINK_TESTS, "blink tests are disabled")
class SuperviseIntegrationTest(IntegrationTest, utc.SuperviseIntegrationTest):
    """
    Test supervise functionality of blink.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()


@unittest.skipIf(not utc.ENABLE_BLINK_TESTS, "blink tests are disabled")
class PerformanceIntegrationTest(IntegrationTest, utc.PerformanceIntegrationTest):
    """
    Test performance of blink.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()
        # network timing measurement
        # mean timing = 0.5 sec per measurement plus 0.75 sec overhead
        self.timeout_limit = 6.0 * 0.1 + (blink_config.MEASUREMENTS * 0.5 + 0.75)

        # temperature and humidity repeatability measurements
        # settings below are tuned short term repeatability assessment
        self.temp_stdev_limit = 0.5  # 1 sigma temp repeatability limit in F
        self.temp_repeatability_measurements = 30  # number of temp msmts.
        self.humidity_stdev_limit = 0.5  # 1 sigma humid repeat. limit %RH
        self.humidity_repeatability_measurements = 30  # number of temp msmts.
        self.poll_interval_sec = 1  # delay between repeatability measurements


@unittest.skipIf(not utc.ENABLE_BLINK_TESTS, "blink tests are disabled")
class BlinkSpamMitigationTest(unittest.TestCase):
    """
    Test blink spam mitigation functionality.
    """

    def setUp(self):
        """Set up test environment for spam mitigation tests."""
        # Create mock thermostat and zone objects
        self.mock_thermostat = MagicMock()
        self.mock_thermostat.get_metadata.return_value = {
            blink_config.API_TEMPF_MEAN: 72.5,
            blink_config.API_WIFI_STRENGTH: -45,
            blink_config.API_BATTERY_VOLTAGE: 350,
            blink_config.API_BATTERY_STATUS: "ok",
        }
        self.mock_thermostat.zone_number = 0
        self.mock_thermostat.device_id = 0

    @patch("src.blink.time.time")
    @patch("src.blink.util.log_msg")
    def test_refresh_zone_info_caching(self, mock_log, mock_time):
        """Test that refresh_zone_info respects cache timeout."""
        # Setup time progression
        start_time = 1000.0
        mock_time.side_effect = [
            start_time - 120,  # Constructor time (force initial refresh)
            start_time,  # First refresh check
            start_time + 30,  # Second refresh check (within cache time)
            start_time + 70,  # Third refresh check (past cache time)
        ]

        # Create zone instance
        with patch(
            "src.thermostat_common.time.time",
            return_value=start_time - 120,
        ):
            zone = blink.ThermostatZone(self.mock_thermostat, verbose=False)

        # Reset the get_metadata call count
        self.mock_thermostat.get_metadata.reset_mock()

        # First call - should refresh (cache expired)
        zone.refresh_zone_info()
        self.assertEqual(self.mock_thermostat.get_metadata.call_count, 1)

        # Second call - should use cache (within 60 seconds)
        zone.refresh_zone_info()
        self.assertEqual(self.mock_thermostat.get_metadata.call_count, 1)

        # Third call - should refresh again (past 60 seconds)
        zone.refresh_zone_info()
        self.assertEqual(self.mock_thermostat.get_metadata.call_count, 2)

    @patch("src.blink.time.time")
    def test_refresh_zone_info_force_refresh(self, mock_time):
        """Test that force_refresh=True bypasses cache."""
        start_time = 1000.0
        mock_time.side_effect = [
            start_time - 120,  # Constructor time
            start_time,  # First refresh
            start_time + 10,  # Force refresh (within cache time)
        ]

        # Create zone instance
        with patch(
            "src.thermostat_common.time.time",
            return_value=start_time - 120,
        ):
            zone = blink.ThermostatZone(self.mock_thermostat, verbose=False)

        # Reset the get_metadata call count
        self.mock_thermostat.get_metadata.reset_mock()

        # First call
        zone.refresh_zone_info()
        self.assertEqual(self.mock_thermostat.get_metadata.call_count, 1)

        # Force refresh should bypass cache
        zone.refresh_zone_info(force_refresh=True)
        self.assertEqual(self.mock_thermostat.get_metadata.call_count, 2)

    def test_get_display_temp_calls_refresh(self):
        """Test that get_display_temp calls refresh_zone_info."""
        zone = blink.ThermostatZone(self.mock_thermostat, verbose=False)

        with patch.object(zone, "refresh_zone_info") as mock_refresh:
            temp = zone.get_display_temp()
            mock_refresh.assert_called_once()
            self.assertEqual(temp, 72.5)

    def test_fetch_interval_configuration(self):
        """Test that fetch interval is set to 60 seconds for spam mitigation."""
        zone = blink.ThermostatZone(self.mock_thermostat, verbose=False)
        self.assertEqual(zone.fetch_interval_sec, 60)

    @patch("src.blink.time.time")
    @patch("src.blink.util.log_msg")
    def test_cached_data_message_reduction(self, mock_log, mock_time):
        """Test that cached data messages are only printed when refresh time changes."""
        # Setup time progression for repeated cache access with similar refresh times
        start_time = 1000.0
        mock_time.side_effect = [
            start_time - 120,  # Constructor time (force initial refresh)
            start_time,  # First cache access (60s refresh time)
            start_time + 0.5,  # Second cache access (59.5s - should not log)
            start_time + 1.0,  # Third cache access (59s - should log)
            start_time + 1.5,  # Fourth cache access (58.5s - should not log)
            start_time + 2.0,  # Fifth cache access (58s - should log)
        ]

        # Create zone instance with verbose=True
        with patch(
            "src.thermostat_common.time.time",
            return_value=start_time - 120,
        ):
            zone = blink.ThermostatZone(self.mock_thermostat, verbose=True)

        # Reset mock call count
        mock_log.reset_mock()

        # Multiple cache accesses within cache period
        zone.refresh_zone_info()  # First access - should log
        zone.refresh_zone_info()  # Second access - should NOT log (same rounded time)
        zone.refresh_zone_info()  # Third access - should log (different rounded time)
        zone.refresh_zone_info()  # Fourth access - should NOT log (same rounded time)
        zone.refresh_zone_info()  # Fifth access - should log (different rounded time)

        # Count calls that contain "Using cached data"
        cached_data_calls = [
            call for call in mock_log.call_args_list
            if len(call[0]) > 0 and "Using cached data" in call[0][0]
        ]

        # Should only have 3 cached data messages (first, third, and fifth calls)
        self.assertEqual(len(cached_data_calls), 3)


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
