#!/usr/bin/env python3
"""
Unit tests for Nest fan timer mode handling.

Nest responses can omit the Fan.timerMode key (and sometimes the Fan trait).
The zone methods should treat missing fan timer mode as fan-off rather than
raising KeyError.
"""

import time
import unittest
from unittest.mock import MagicMock, patch

# local imports
from src import nest


class TestNestFanTimerMode(unittest.TestCase):
    """Test nest Fan.timerMode missing-key behavior."""

    def _make_zone_with_traits(self, traits: dict) -> nest.ThermostatZone:
        """Create a ThermostatZone with a single mocked device and traits."""
        mock_thermostat = MagicMock()
        mock_thermostat.zone_number = 0
        mock_thermostat.zone_name = "Test Zone"
        mock_thermostat.get_device_data = MagicMock()

        device = MagicMock()
        device.traits = traits
        mock_thermostat.devices = [device]

        patcher = patch(
            "src.nest.nest.Device.filter_for_trait",
            return_value=mock_thermostat.devices,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        zone = nest.ThermostatZone(mock_thermostat, verbose=False)

        # Keep refresh_zone_info from calling get_device_data during these tests.
        zone.fetch_interval_sec = 365 * 24 * 60 * 60
        zone.last_fetch_time = time.time()
        return zone

    def test_is_fanning_missing_timer_mode_returns_off(self) -> None:
        """Return 0 when Fan trait exists but timerMode is missing."""
        zone = self._make_zone_with_traits(
            {
                "Info": {"customName": "Test Zone"},
                "Fan": {},
            }
        )

        self.assertEqual(zone.is_fanning(), 0)
        self.assertEqual(zone.is_fan_on(), 0)

    def test_is_fanning_missing_fan_trait_returns_off(self) -> None:
        """Return 0 when Fan trait is missing entirely."""
        zone = self._make_zone_with_traits(
            {
                "Info": {"customName": "Test Zone"},
            }
        )

        self.assertEqual(zone.is_fanning(), 0)
        self.assertEqual(zone.is_fan_on(), 0)

    def test_is_fanning_timer_mode_on_returns_on(self) -> None:
        """Return 1 when Fan.timerMode is ON."""
        zone = self._make_zone_with_traits(
            {
                "Info": {"customName": "Test Zone"},
                "Fan": {"timerMode": "ON"},
            }
        )

        self.assertEqual(zone.is_fanning(), 1)
        self.assertEqual(zone.is_fan_on(), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
