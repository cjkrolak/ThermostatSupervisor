"""
Unit test module for nest spam mitigation functionality.

This test validates that the nest module properly implements caching
to prevent triggering Nest's rate limiting.
"""

# built-in imports
import unittest
from unittest.mock import MagicMock, patch

# local imports
from thermostatsupervisor import nest
from thermostatsupervisor import nest_config


class NestSpamMitigationTest(unittest.TestCase):
    """
    Test nest spam mitigation functionality.
    """

    def setUp(self):
        """Set up test fixtures."""
        # Create mock thermostat object
        self.mock_thermostat = MagicMock()
        self.mock_thermostat.devices = [MagicMock(), MagicMock()]
        self.mock_thermostat.zone_number = 0
        self.mock_thermostat.zone_name = "Test Zone"
        self.mock_thermostat.get_device_data = MagicMock()

        # Mock the thermostat metadata access
        self.mock_thermostat.devices[0].traits = {
            "Info": {"customName": "Test Zone"},
            "Temperature": {"ambientTemperatureCelsius": 20.0},
            "ThermostatMode": {"mode": "HEAT"}
        }

    def test_refresh_zone_info_caching_simple(self):
        """Test that refresh_zone_info respects cache timeout."""
        # Setup proper device access for constructor
        self.mock_thermostat.devices = [self.mock_thermostat.devices[0]]

        # Create zone instance
        with patch(
            "thermostatsupervisor.nest.nest.Device.filter_for_trait",
            return_value=self.mock_thermostat.devices,
        ):
            zone = nest.ThermostatZone(self.mock_thermostat, verbose=False)

        # Reset the call count after construction
        self.mock_thermostat.get_device_data.reset_mock()

        # Set last_fetch_time to far in the past to force refresh
        zone.last_fetch_time = 0.0

        # First call - should refresh (cache expired)
        zone.refresh_zone_info()
        self.assertEqual(self.mock_thermostat.get_device_data.call_count, 1)

        # Second call immediately - should NOT refresh (within cache period)
        zone.refresh_zone_info()
        self.assertEqual(self.mock_thermostat.get_device_data.call_count, 1)

        # Force cache expiry and call again
        zone.last_fetch_time = 0.0
        zone.refresh_zone_info()
        self.assertEqual(self.mock_thermostat.get_device_data.call_count, 2)

    def test_refresh_zone_info_force_refresh_simple(self):
        """Test that force_refresh=True bypasses cache."""
        # Setup proper device access for constructor
        self.mock_thermostat.devices = [self.mock_thermostat.devices[0]]

        # Create zone instance
        with patch(
            "thermostatsupervisor.nest.nest.Device.filter_for_trait",
            return_value=self.mock_thermostat.devices,
        ):
            zone = nest.ThermostatZone(self.mock_thermostat, verbose=False)

        # Reset the call count after construction
        self.mock_thermostat.get_device_data.reset_mock()

        # Set cache to expired to ensure first call refreshes
        zone.last_fetch_time = 0.0

        # First call - should refresh (cache expired)
        zone.refresh_zone_info()
        self.assertEqual(self.mock_thermostat.get_device_data.call_count, 1)

        # Force refresh should bypass cache even though data is fresh
        zone.refresh_zone_info(force_refresh=True)
        self.assertEqual(self.mock_thermostat.get_device_data.call_count, 2)

    @patch("thermostatsupervisor.nest.util.log_msg")
    def test_refresh_zone_info_logging_simple(self, mock_log):
        """Test that refresh_zone_info logs cache operations when verbose."""
        # Setup proper device access for constructor
        self.mock_thermostat.devices = [self.mock_thermostat.devices[0]]

        # Create zone instance with verbose logging
        with patch(
            "thermostatsupervisor.nest.nest.Device.filter_for_trait",
            return_value=self.mock_thermostat.devices,
        ):
            zone = nest.ThermostatZone(self.mock_thermostat, verbose=True)

        # Reset mocks
        mock_log.reset_mock()
        self.mock_thermostat.get_device_data.reset_mock()

        # Force cache to be expired
        zone.last_fetch_time = 0.0

        # First call - should log refresh
        zone.refresh_zone_info()

        # Should have called log_msg
        self.assertGreater(mock_log.call_count, 0)

        # Reset log mock
        mock_log.reset_mock()

        # Second call - should log cache usage
        zone.refresh_zone_info()

        # Should have called log_msg for cache usage
        self.assertGreater(mock_log.call_count, 0)

    def test_cache_period_config_synchronization(self):
        """Test that zone cache period matches config."""
        # Setup proper device access for constructor
        self.mock_thermostat.devices = [self.mock_thermostat.devices[0]]

        # Create zone instance
        with patch(
            "thermostatsupervisor.nest.nest.Device.filter_for_trait",
            return_value=self.mock_thermostat.devices,
        ):
            zone = nest.ThermostatZone(self.mock_thermostat, verbose=False)

        # Verify fetch_interval_sec matches config
        self.assertEqual(zone.fetch_interval_sec, nest_config.cache_period_sec)

    @patch("thermostatsupervisor.nest.util.execute_with_extended_retries")
    def test_get_metadata_retry_mechanism_simple(self, mock_retry):
        """Test that get_metadata uses retry mechanism when requested."""
        # Mock the retry function to return test data
        mock_retry.return_value = {"test": "data"}

        # Create a mock thermostat with minimal setup
        mock_tstat = MagicMock()
        mock_tstat.devices = [MagicMock()]
        mock_tstat.devices[0].traits = {"test": "data"}

        # Test the retry mechanism by directly calling the method
        # without going through the full constructor
        result = nest.ThermostatClass.get_metadata(
            mock_tstat, zone=0, retry=True
        )

        # Verify retry mechanism was called
        self.assertTrue(mock_retry.called)
        self.assertEqual(result, {"test": "data"})

        # Verify retry parameters
        call_args = mock_retry.call_args
        self.assertEqual(call_args[1]["thermostat_type"], "Nest")
        self.assertEqual(call_args[1]["number_of_retries"], 5)
        self.assertEqual(call_args[1]["initial_retry_delay_sec"], 60)

        # Verify exception types include network-related exceptions
        exception_types = call_args[1]["exception_types"]
        self.assertIn(ConnectionError, exception_types)
        self.assertIn(TimeoutError, exception_types)

    @patch("thermostatsupervisor.nest.time.time")
    @patch("thermostatsupervisor.nest.util.log_msg")
    def test_cached_data_message_reduction(self, mock_log, mock_time):
        """Test that cached data messages are only printed when refresh time changes."""
        # Setup time progression for repeated cache access with similar refresh times
        start_time = 1000.0
        mock_time.side_effect = [
            start_time - 120,  # Constructor time (force initial refresh)
            start_time,  # First cache access
            start_time + 0.5,  # Second cache access (should not log)
            start_time + 1.0,  # Third cache access (should log)
            start_time + 1.5,  # Fourth cache access (should not log)
            start_time + 2.0,  # Fifth cache access (should log)
        ]

        # Setup proper device access for constructor
        self.mock_thermostat.devices = [self.mock_thermostat.devices[0]]

        # Create zone instance with verbose=True
        with patch(
            "thermostatsupervisor.nest.nest.Device.filter_for_trait",
            return_value=self.mock_thermostat.devices,
        ), patch(
            "thermostatsupervisor.thermostat_common.time.time",
            return_value=start_time - 120,
        ):
            zone = nest.ThermostatZone(self.mock_thermostat, verbose=True)

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
    unittest.main(verbosity=2)
