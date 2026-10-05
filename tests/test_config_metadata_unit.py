"""Unit tests for per-zone thermostat configuration metadata."""

import unittest

from src import (
    blink_config,
    emulator_config,
    honeywell_config,
    kumocloud_config,
    kumolocal_config,
    mmm_config,
    nest_config,
    sht31_config,
)


class TestConfigMetadata(unittest.TestCase):
    """Validate metadata and default names across thermostat configs."""

    def test_metadata_covers_supported_zones(self) -> None:
        """Ensure every configured metadata map covers its supported zones."""
        configs = (
            blink_config,
            kumocloud_config,
            kumolocal_config,
            mmm_config,
            nest_config,
            sht31_config,
        )
        allowed_fields = {
            "zone_name",
            "host_name",
            "ip_address",
            "serial_number",
            "local_net_available",
        }

        for config in configs:
            with self.subTest(config=config.ALIAS):
                self.assertEqual(
                    set(config.metadata),
                    set(config.supported_configs["zones"]),
                )
                for zone_metadata in config.metadata.values():
                    self.assertIsInstance(zone_metadata.get("zone_name"), str)
                    self.assertTrue(zone_metadata["zone_name"])
                    self.assertLessEqual(set(zone_metadata), allowed_fields)

    def test_default_zone_names_are_strings(self) -> None:
        """Ensure each config exposes a displayable default zone name."""
        configs = (
            blink_config,
            emulator_config,
            honeywell_config,
            kumocloud_config,
            kumolocal_config,
            mmm_config,
            nest_config,
            sht31_config,
        )

        for config in configs:
            with self.subTest(config=config.ALIAS):
                self.assertIsInstance(config.default_zone_name, str)
                self.assertTrue(config.default_zone_name)
