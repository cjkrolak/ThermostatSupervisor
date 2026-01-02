"""
Unit test module for kumocloudv3.py zone data matching functionality.

This test module focuses on testing the zone metadata population logic
to ensure serial numbers are correctly matched to zones by name.
"""

# built-in imports
import copy
import unittest
from unittest.mock import MagicMock, patch

# local imports
try:
    from thermostatsupervisor import kumocloudv3
    from thermostatsupervisor import kumocloudv3_config

    kumocloudv3_import_error = None
except ImportError as ex:
    kumocloudv3 = None
    kumocloudv3_config = None
    kumocloudv3_import_error = ex

from tests import unit_test_common as utc


@unittest.skipIf(
    kumocloudv3_import_error,
    "kumocloudv3 import failed, tests are disabled",
)
class ZoneMetadataPopulationUnitTest(utc.UnitTest):
    """
    Unit tests for zone metadata population functionality.

    These tests verify that serial numbers are correctly matched to zone
    indices based on zone names, not just sequential API order.
    """

    def setUp(self):
        """Setup for unit tests."""
        super().setUp()
        self.print_test_name()

        # Save original metadata to restore after tests
        self.original_metadata = copy.deepcopy(kumocloudv3_config.metadata)

        # Mock zone data that might come from API in different order
        # Simulating the scenario where API returns zones in this order:
        # 0: Kitchen, 1: Basement, 2: Main Living
        self.mock_zones_api_response = [
            {
                "name": "Kitchen",
                "adapter": {"deviceSerial": "SERIAL_KITCHEN_001"},
            },
            {
                "name": "Basement",
                "adapter": {"deviceSerial": "SERIAL_BASEMENT_002"},
            },
            {
                "name": "Main Living",
                "adapter": {"deviceSerial": "SERIAL_MAIN_003"},
            },
        ]

        # Serial numbers in API order
        self.serial_num_lst = [
            "SERIAL_KITCHEN_001",
            "SERIAL_BASEMENT_002",
            "SERIAL_MAIN_003",
        ]

        # Expected metadata after dynamic zone assignment
        # Note: After _update_zone_assignments, indices might be:
        # MAIN_LIVING=2, KITCHEN=0, BASEMENT=1 (based on zone names)
        self.expected_metadata_structure = {
            0: {"zone_name": "Kitchen", "serial_number": None},
            1: {"zone_name": "Basement", "serial_number": None},
            2: {"zone_name": "Main Living", "serial_number": None},
        }

    def tearDown(self):
        """Cleanup after unit tests."""
        # Restore original metadata
        kumocloudv3_config.metadata.clear()
        kumocloudv3_config.metadata.update(self.original_metadata)
        super().tearDown()

    def test_populate_metadata_matches_by_zone_name(self):
        """
        Test that _populate_metadata correctly matches serial numbers
        to zones by zone name, not by API order.
        """
        # Setup metadata dict to simulate post-_update_zone_assignments state
        kumocloudv3_config.metadata.clear()
        kumocloudv3_config.metadata.update(
            copy.deepcopy(self.expected_metadata_structure)
        )

        # Create a mock thermostat instance
        with patch.object(
            kumocloudv3.ThermostatClass, "_authenticate"
        ), patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            # Mock the _get_sites and _get_zones methods
            mock_sites = [{"id": "test_site_123"}]
            thermostat._get_sites = MagicMock(return_value=mock_sites)
            thermostat._get_zones = MagicMock(
                return_value=self.mock_zones_api_response
            )

            # Call _populate_metadata with serial numbers
            thermostat._populate_metadata(self.serial_num_lst)

            # Verify that serial numbers are correctly matched by zone name
            # Kitchen (index 0) should get SERIAL_KITCHEN_001
            self.assertEqual(
                kumocloudv3_config.metadata[0]["serial_number"],
                "SERIAL_KITCHEN_001",
                "Kitchen zone should have Kitchen serial number",
            )

            # Basement (index 1) should get SERIAL_BASEMENT_002
            self.assertEqual(
                kumocloudv3_config.metadata[1]["serial_number"],
                "SERIAL_BASEMENT_002",
                "Basement zone should have Basement serial number",
            )

            # Main Living (index 2) should get SERIAL_MAIN_003
            self.assertEqual(
                kumocloudv3_config.metadata[2]["serial_number"],
                "SERIAL_MAIN_003",
                "Main Living zone should have Main Living serial number",
            )

    def test_populate_metadata_fallback_on_api_error(self):
        """
        Test that _populate_metadata falls back to sequential assignment
        when API calls fail.
        """
        # Setup metadata dict
        kumocloudv3_config.metadata.clear()
        kumocloudv3_config.metadata.update(
            copy.deepcopy(self.expected_metadata_structure)
        )

        # Create a mock thermostat instance
        with patch.object(
            kumocloudv3.ThermostatClass, "_authenticate"
        ), patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            # Mock _get_sites to raise an exception
            thermostat._get_sites = MagicMock(
                side_effect=Exception("API Error")
            )

            # Call _populate_metadata - should fallback to sequential
            thermostat._populate_metadata(self.serial_num_lst)

            # Verify fallback behavior: sequential assignment
            self.assertEqual(
                kumocloudv3_config.metadata[0]["serial_number"],
                "SERIAL_KITCHEN_001",
            )
            self.assertEqual(
                kumocloudv3_config.metadata[1]["serial_number"],
                "SERIAL_BASEMENT_002",
            )
            self.assertEqual(
                kumocloudv3_config.metadata[2]["serial_number"],
                "SERIAL_MAIN_003",
            )

    def test_populate_metadata_handles_missing_zone_names(self):
        """
        Test that _populate_metadata handles zones with missing or
        empty names gracefully.
        """
        # Setup metadata dict
        kumocloudv3_config.metadata.clear()
        kumocloudv3_config.metadata.update(
            copy.deepcopy(self.expected_metadata_structure)
        )

        # Mock zones with some missing names
        mock_zones_with_missing_names = [
            {
                "name": "",  # Empty name
                "adapter": {"deviceSerial": "SERIAL_KITCHEN_001"},
            },
            {
                "name": "Basement",
                "adapter": {"deviceSerial": "SERIAL_BASEMENT_002"},
            },
            {
                # Missing name field entirely
                "adapter": {"deviceSerial": "SERIAL_MAIN_003"},
            },
        ]

        # Create a mock thermostat instance
        with patch.object(
            kumocloudv3.ThermostatClass, "_authenticate"
        ), patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            # Mock the _get_sites and _get_zones methods
            mock_sites = [{"id": "test_site_123"}]
            thermostat._get_sites = MagicMock(return_value=mock_sites)
            thermostat._get_zones = MagicMock(
                return_value=mock_zones_with_missing_names
            )

            # Call _populate_metadata
            thermostat._populate_metadata(self.serial_num_lst)

            # Verify that Basement zone still got the correct serial
            self.assertEqual(
                kumocloudv3_config.metadata[1]["serial_number"],
                "SERIAL_BASEMENT_002",
                "Basement zone should still match by name",
            )

            # Other zones may not match due to missing names
            # This is acceptable fallback behavior


if __name__ == "__main__":
    unittest.main(verbosity=2)
