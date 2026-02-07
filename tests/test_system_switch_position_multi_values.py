"""
Unit tests for system_switch_position with multiple values support.

This test module verifies that system_switch_position can handle:
- Multiple values per key (lists)
- Mixed int and string datatypes
- Mode detection with get_key_from_value()
"""

import unittest
from unittest.mock import MagicMock

from src import thermostat_common as tc
from src import utilities as util
from tests import unit_test_common as utc


class TestSystemSwitchPositionMultiValues(utc.UnitTest):
    """Test multiple values and mixed datatypes in system_switch_position."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.setup_mock_thermostat_zone()

    def tearDown(self):
        """Clean up after tests."""
        self.teardown_mock_thermostat_zone()
        super().tearDown()

    def test_single_int_value_backward_compatibility(self):
        """Verify backward compatibility with single int values."""
        # Setup: Use traditional single int values
        # type: ignore[attr-defined]
        self.Zone.system_switch_position[tc.ThermostatCommonZone.HEAT_MODE] = 1
        # type: ignore[attr-defined]
        self.Zone.system_switch_position[tc.ThermostatCommonZone.COOL_MODE] = 2
        # type: ignore[attr-defined]
        self.Zone.system_switch_position[tc.ThermostatCommonZone.OFF_MODE] = 0

        # Mock get_system_switch_position to return int value
        # type: ignore[attr-defined]
        self.Zone.get_system_switch_position = MagicMock(return_value=1)

        # Test: is_heat_mode should return 1
        result = self.Zone.is_heat_mode()  # type: ignore[attr-defined]
        self.assertEqual(1, result, "Expected heat mode to be detected")

        # Test: is_cool_mode should return 0
        result = self.Zone.is_cool_mode()  # type: ignore[attr-defined]
        self.assertEqual(0, result, "Expected cool mode to not be detected")

    def test_single_string_value(self):
        """Verify single string values work correctly."""
        # Setup: Use string values
        # type: ignore[attr-defined, assignment]
        self.Zone.system_switch_position[tc.ThermostatCommonZone.HEAT_MODE] = "heat"
        # type: ignore[attr-defined, assignment]
        self.Zone.system_switch_position[tc.ThermostatCommonZone.COOL_MODE] = "cool"
        # type: ignore[attr-defined, assignment]
        self.Zone.system_switch_position[tc.ThermostatCommonZone.AUTO_MODE] = "auto"

        # Mock get_system_switch_position to return string value
        # type: ignore[attr-defined]
        self.Zone.get_system_switch_position = MagicMock(return_value="heat")

        # Test: is_heat_mode should return 1
        result = self.Zone.is_heat_mode()  # type: ignore[attr-defined]
        self.assertEqual(1, result, "Expected heat mode to be detected")

        # Test: is_auto_mode should return 0
        result = self.Zone.is_auto_mode()  # type: ignore[attr-defined]
        self.assertEqual(0, result, "Expected auto mode to not be detected")

    def test_list_of_string_values(self):
        """Verify list of string values work correctly."""
        # Setup: Use list of string values for AUTO_MODE
        # type: ignore[attr-defined, assignment]
        self.Zone.system_switch_position[tc.ThermostatCommonZone.HEAT_MODE] = "heat"
        # type: ignore[attr-defined, assignment]
        self.Zone.system_switch_position[
            tc.ThermostatCommonZone.AUTO_MODE
        ] = ["auto", "autoHeat", "autoCool"]
        # type: ignore[attr-defined, assignment]
        self.Zone.system_switch_position[tc.ThermostatCommonZone.COOL_MODE] = "cool"

        # Test: "auto" should be detected as AUTO_MODE
        # type: ignore[attr-defined]
        self.Zone.get_system_switch_position = MagicMock(return_value="auto")
        result = self.Zone.is_auto_mode()  # type: ignore[attr-defined]
        self.assertEqual(1, result, 'Expected "auto" to be detected as auto mode')

        # Test: "autoHeat" should be detected as AUTO_MODE
        # type: ignore[attr-defined]
        self.Zone.get_system_switch_position = MagicMock(return_value="autoHeat")
        result = self.Zone.is_auto_mode()  # type: ignore[attr-defined]
        self.assertEqual(
            1, result, 'Expected "autoHeat" to be detected as auto mode'
        )

        # Test: "autoCool" should be detected as AUTO_MODE
        # type: ignore[attr-defined]
        self.Zone.get_system_switch_position = MagicMock(return_value="autoCool")
        result = self.Zone.is_auto_mode()  # type: ignore[attr-defined]
        self.assertEqual(
            1, result, 'Expected "autoCool" to be detected as auto mode'
        )

        # Test: "heat" should not be detected as AUTO_MODE
        # type: ignore[attr-defined]
        self.Zone.get_system_switch_position = MagicMock(return_value="heat")
        result = self.Zone.is_auto_mode()  # type: ignore[attr-defined]
        self.assertEqual(0, result, 'Expected "heat" to not be auto mode')

    def test_list_of_int_values(self):
        """Verify list of int values work correctly."""
        # Setup: Use list of int values
        # type: ignore[attr-defined]
        self.Zone.system_switch_position[tc.ThermostatCommonZone.HEAT_MODE] = 1
        # type: ignore[attr-defined, assignment]
        self.Zone.system_switch_position[
            tc.ThermostatCommonZone.AUTO_MODE
        ] = [4, 5, 6]
        # type: ignore[attr-defined]
        self.Zone.system_switch_position[tc.ThermostatCommonZone.COOL_MODE] = 2

        # Test: 4 should be detected as AUTO_MODE
        # type: ignore[attr-defined]
        self.Zone.get_system_switch_position = MagicMock(return_value=4)
        result = self.Zone.is_auto_mode()  # type: ignore[attr-defined]
        self.assertEqual(1, result, "Expected 4 to be detected as auto mode")

        # Test: 5 should be detected as AUTO_MODE
        # type: ignore[attr-defined]
        self.Zone.get_system_switch_position = MagicMock(return_value=5)
        result = self.Zone.is_auto_mode()  # type: ignore[attr-defined]
        self.assertEqual(1, result, "Expected 5 to be detected as auto mode")

        # Test: 6 should be detected as AUTO_MODE
        # type: ignore[attr-defined]
        self.Zone.get_system_switch_position = MagicMock(return_value=6)
        result = self.Zone.is_auto_mode()  # type: ignore[attr-defined]
        self.assertEqual(1, result, "Expected 6 to be detected as auto mode")

        # Test: 1 should not be detected as AUTO_MODE
        # type: ignore[attr-defined]
        self.Zone.get_system_switch_position = MagicMock(return_value=1)
        result = self.Zone.is_auto_mode()  # type: ignore[attr-defined]
        self.assertEqual(0, result, "Expected 1 to not be auto mode")

    def test_mixed_int_and_string_values(self):
        """Verify mixed int and string values work correctly."""
        # Setup: Mix int and string values in the same list
        # type: ignore[attr-defined, assignment]
        self.Zone.system_switch_position[tc.ThermostatCommonZone.HEAT_MODE] = "heat"
        # type: ignore[attr-defined, assignment]
        self.Zone.system_switch_position[
            tc.ThermostatCommonZone.AUTO_MODE
        ] = ["auto", 4, "autoHeat", 5]
        # type: ignore[attr-defined, assignment]
        self.Zone.system_switch_position[tc.ThermostatCommonZone.COOL_MODE] = "cool"

        # Test: string "auto" should be detected
        # type: ignore[attr-defined]
        self.Zone.get_system_switch_position = MagicMock(return_value="auto")
        result = self.Zone.is_auto_mode()  # type: ignore[attr-defined]
        self.assertEqual(1, result, 'Expected "auto" to be detected')

        # Test: int 4 should be detected
        # type: ignore[attr-defined]
        self.Zone.get_system_switch_position = MagicMock(return_value=4)
        result = self.Zone.is_auto_mode()  # type: ignore[attr-defined]
        self.assertEqual(1, result, "Expected 4 to be detected")

        # Test: string "autoHeat" should be detected
        # type: ignore[attr-defined]
        self.Zone.get_system_switch_position = MagicMock(return_value="autoHeat")
        result = self.Zone.is_auto_mode()  # type: ignore[attr-defined]
        self.assertEqual(1, result, 'Expected "autoHeat" to be detected')

        # Test: int 5 should be detected
        # type: ignore[attr-defined]
        self.Zone.get_system_switch_position = MagicMock(return_value=5)
        result = self.Zone.is_auto_mode()  # type: ignore[attr-defined]
        self.assertEqual(1, result, "Expected 5 to be detected")

        # Test: "cool" should not be detected as auto mode
        # type: ignore[attr-defined]
        self.Zone.get_system_switch_position = MagicMock(return_value="cool")
        result = self.Zone.is_auto_mode()  # type: ignore[attr-defined]
        self.assertEqual(0, result, 'Expected "cool" to not be auto mode')

    def test_unknown_value_returns_false(self):
        """Verify unknown values are handled gracefully."""
        # Setup
        # type: ignore[attr-defined]
        self.Zone.system_switch_position[tc.ThermostatCommonZone.HEAT_MODE] = 1
        # type: ignore[attr-defined]
        self.Zone.system_switch_position[tc.ThermostatCommonZone.COOL_MODE] = 2

        # Mock get_system_switch_position to return unknown value
        # type: ignore[attr-defined]
        self.Zone.get_system_switch_position = MagicMock(return_value=999)

        # Test: Unknown value should return 0
        result = self.Zone.is_heat_mode()  # type: ignore[attr-defined]
        self.assertEqual(0, result, "Expected unknown value to return 0")

    def test_is_mode_helper_with_list_values(self):
        """Test the _is_mode helper method directly."""
        # Setup
        # type: ignore[attr-defined, assignment]
        self.Zone.system_switch_position[
            tc.ThermostatCommonZone.AUTO_MODE
        ] = ["auto", "autoHeat", "autoCool"]

        # Test with "auto"
        # type: ignore[attr-defined]
        self.Zone.get_system_switch_position = MagicMock(return_value="auto")
        # type: ignore[attr-defined]
        result = self.Zone._is_mode(tc.ThermostatCommonZone.AUTO_MODE)
        self.assertTrue(result, 'Expected _is_mode to return True for "auto"')

        # Test with "autoHeat"
        # type: ignore[attr-defined]
        self.Zone.get_system_switch_position = MagicMock(return_value="autoHeat")
        # type: ignore[attr-defined]
        result = self.Zone._is_mode(tc.ThermostatCommonZone.AUTO_MODE)
        self.assertTrue(result, 'Expected _is_mode to return True for "autoHeat"')

        # Test with non-matching value
        # type: ignore[attr-defined]
        self.Zone.get_system_switch_position = MagicMock(return_value="heat")
        # type: ignore[attr-defined]
        result = self.Zone._is_mode(tc.ThermostatCommonZone.AUTO_MODE)
        self.assertFalse(result, 'Expected _is_mode to return False for "heat"')

    def test_get_key_from_value_with_list(self):
        """Test get_key_from_value utility with list values."""
        # Setup
        test_dict = {
            "HEAT": "heat",
            "COOL": "cool",
            "AUTO": ["auto", "autoHeat", "autoCool"],
        }

        # Test: "auto" should return "AUTO"
        result = util.get_key_from_value(test_dict, "auto")
        self.assertEqual("AUTO", result, 'Expected "auto" to map to "AUTO"')

        # Test: "autoHeat" should return "AUTO"
        result = util.get_key_from_value(test_dict, "autoHeat")
        self.assertEqual("AUTO", result, 'Expected "autoHeat" to map to "AUTO"')

        # Test: "autoCool" should return "AUTO"
        result = util.get_key_from_value(test_dict, "autoCool")
        self.assertEqual("AUTO", result, 'Expected "autoCool" to map to "AUTO"')

        # Test: "heat" should return "HEAT"
        result = util.get_key_from_value(test_dict, "heat")
        self.assertEqual("HEAT", result, 'Expected "heat" to map to "HEAT"')

    def test_all_mode_detection_methods(self):
        """Test all is_*_mode methods with mixed values."""
        # Setup with mixed types
        # type: ignore[attr-defined]
        self.Zone.system_switch_position[tc.ThermostatCommonZone.HEAT_MODE] = 1
        # type: ignore[attr-defined]
        self.Zone.system_switch_position[tc.ThermostatCommonZone.COOL_MODE] = 2
        # type: ignore[attr-defined]
        self.Zone.system_switch_position[tc.ThermostatCommonZone.DRY_MODE] = 3
        # type: ignore[attr-defined, assignment]
        self.Zone.system_switch_position[
            tc.ThermostatCommonZone.AUTO_MODE
        ] = ["auto", "autoHeat", "autoCool"]
        # type: ignore[attr-defined, assignment]
        self.Zone.system_switch_position[tc.ThermostatCommonZone.FAN_MODE] = "fan"
        # type: ignore[attr-defined]
        self.Zone.system_switch_position[tc.ThermostatCommonZone.OFF_MODE] = 0
        # type: ignore[attr-defined, assignment]
        self.Zone.system_switch_position[tc.ThermostatCommonZone.ECO_MODE] = "eco"

        # Test each mode
        test_cases = [
            (1, "is_heat_mode", 1),
            (2, "is_cool_mode", 1),
            (3, "is_dry_mode", 1),
            ("auto", "is_auto_mode", 1),
            ("autoHeat", "is_auto_mode", 1),
            ("autoCool", "is_auto_mode", 1),
            ("fan", "is_fan_mode", 1),
            (0, "is_off_mode", 1),
            ("eco", "is_eco_mode", 1),
        ]

        for position, method_name, expected in test_cases:
            # type: ignore[attr-defined]
            self.Zone.get_system_switch_position = MagicMock(return_value=position)
            method = getattr(self.Zone, method_name)  # type: ignore[attr-defined]
            result = method()
            self.assertEqual(
                expected,
                result,
                f"Expected {method_name}() to return {expected} "
                f"for position {position}",
            )


if __name__ == "__main__":
    unittest.main()
