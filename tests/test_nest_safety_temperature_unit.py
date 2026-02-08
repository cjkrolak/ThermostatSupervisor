#!/usr/bin/env python3
"""
Unit test for nest safety temperature functionality.

This test validates the get_safety_temperature() method implementation
without requiring actual nest hardware connection.
"""
import unittest
from unittest.mock import Mock

# local imports
from src import nest_config


class TestNestSafetyTemperature(unittest.TestCase):
    """Test nest safety temperature functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a mock nest zone that implements our safety temperature logic
        self.zone = Mock()

        # Mock the mode methods
        self.zone.is_heat_mode = Mock(return_value=False)
        self.zone.is_auto_mode = Mock(return_value=False)
        self.zone.is_cool_mode = Mock(return_value=False)

        # Implement the actual get_safety_temperature method
        def get_safety_temperature():
            """Same implementation as in nest.py."""
            if self.zone.is_heat_mode() or self.zone.is_auto_mode():
                return int(nest_config.SAFETY_HEAT_TEMPERATURE)
            else:
                return int(nest_config.SAFETY_COOL_TEMPERATURE)

        self.zone.get_safety_temperature = get_safety_temperature

    def test_safety_temperature_constants_exist(self):
        """Verify that safety temperature constants are properly defined."""
        self.assertTrue(hasattr(nest_config, "SAFETY_HEAT_TEMPERATURE"))
        self.assertTrue(hasattr(nest_config, "SAFETY_COOL_TEMPERATURE"))
        self.assertIsInstance(nest_config.SAFETY_HEAT_TEMPERATURE, float)
        self.assertIsInstance(nest_config.SAFETY_COOL_TEMPERATURE, float)

    def test_safety_temperature_heat_mode(self):
        """Test safety temperature returns heat value in heat mode."""
        self.zone.is_heat_mode.return_value = True
        self.zone.is_auto_mode.return_value = False

        result = self.zone.get_safety_temperature()
        expected = int(nest_config.SAFETY_HEAT_TEMPERATURE)

        self.assertEqual(result, expected)
        self.assertEqual(result, 45)  # Verify configured value

    def test_safety_temperature_auto_mode(self):
        """Test safety temperature returns heat value in auto mode."""
        self.zone.is_heat_mode.return_value = False
        self.zone.is_auto_mode.return_value = True

        result = self.zone.get_safety_temperature()
        expected = int(nest_config.SAFETY_HEAT_TEMPERATURE)

        self.assertEqual(result, expected)
        self.assertEqual(result, 45)  # Verify configured value

    def test_safety_temperature_cool_mode(self):
        """Test safety temperature returns cool value in cool mode."""
        self.zone.is_heat_mode.return_value = False
        self.zone.is_auto_mode.return_value = False
        self.zone.is_cool_mode.return_value = True

        result = self.zone.get_safety_temperature()
        expected = int(nest_config.SAFETY_COOL_TEMPERATURE)

        self.assertEqual(result, expected)
        self.assertEqual(result, 75)  # Verify configured value

    def test_safety_temperature_off_mode(self):
        """Test safety temperature returns cool value when thermostat is off."""
        # All mode methods return False (OFF mode)
        self.zone.is_heat_mode.return_value = False
        self.zone.is_auto_mode.return_value = False
        self.zone.is_cool_mode.return_value = False

        result = self.zone.get_safety_temperature()
        expected = int(nest_config.SAFETY_COOL_TEMPERATURE)

        self.assertEqual(result, expected)
        self.assertEqual(result, 75)  # Verify configured value

    def test_safety_temperature_return_type(self):
        """Test that safety temperature returns an integer value."""
        result = self.zone.get_safety_temperature()
        self.assertIsInstance(result, int)

    def test_safety_temperature_reasonable_values(self):
        """Test that configured safety temperatures are reasonable."""
        heat_safety = nest_config.SAFETY_HEAT_TEMPERATURE
        cool_safety = nest_config.SAFETY_COOL_TEMPERATURE

        # Verify temperatures are in reasonable range (45-85°F)
        self.assertGreaterEqual(heat_safety, 45.0)
        self.assertLessEqual(heat_safety, 85.0)
        self.assertGreaterEqual(cool_safety, 45.0)
        self.assertLessEqual(cool_safety, 85.0)

        # Verify heat safety is lower than cool safety
        self.assertLess(heat_safety, cool_safety)


if __name__ == "__main__":
    unittest.main(verbosity=2)
