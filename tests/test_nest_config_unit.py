"""
Unit tests for `src.nest_config`.
"""

import unittest

from src import nest_config


class TestNestConfig(unittest.TestCase):
    """Validate Nest zone configuration is internally consistent."""

    def test_supported_configs_zones_include_four_zones(self) -> None:
        """Ensure Nest exposes 4 zones in a stable order."""
        self.assertEqual(
            nest_config.supported_configs["zones"],
            [
                nest_config.MAIN_LEVEL,
                nest_config.BASEMENT,
                nest_config.PORCH,
                nest_config.GARAGE,
            ],
        )

    def test_metadata_covers_all_supported_zones(self) -> None:
        """Ensure `metadata` contains entries for every supported zone."""
        for zone in nest_config.supported_configs["zones"]:
            self.assertIn(zone, nest_config.metadata)
            zone_meta = nest_config.metadata[zone]
            self.assertIsInstance(zone_meta.get("ip_address"), str)
            self.assertIsInstance(zone_meta.get("zone_name"), str)
            self.assertIsInstance(zone_meta.get("host_name"), str)
            self.assertTrue(zone_meta["zone_name"])

    def test_default_zone_is_first_supported_zone(self) -> None:
        """Ensure default zone remains the first entry in supported zones."""
        self.assertEqual(nest_config.default_zone, nest_config.MAIN_LEVEL)
        self.assertEqual(
            nest_config.default_zone_name,
            nest_config.metadata[nest_config.default_zone]["zone_name"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
