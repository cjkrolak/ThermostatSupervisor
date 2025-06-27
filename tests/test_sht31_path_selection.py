"""
Unit test for SHT31 flask path selection logic.

This test validates the fix for issue where SHT31 ThermostatClass
was not using the correct path (/unit) during unit tests.
"""
import unittest
from unittest.mock import patch

from thermostatsupervisor import sht31
from thermostatsupervisor import sht31_config
from thermostatsupervisor import utilities as util
from tests import unit_test_common as utc


class TestSHT31PathSelection(utc.UnitTest):
    """Test SHT31 flask path selection logic."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.original_unit_test_mode = util.unit_test_mode

    def tearDown(self):
        """Clean up after tests."""
        super().tearDown()
        util.unit_test_mode = self.original_unit_test_mode

    @patch.object(sht31.ThermostatClass, 'get_target_zone_id')
    @patch.object(sht31.ThermostatClass, 'spawn_flask_server')
    def test_unit_test_zone_always_uses_unit_path(self, mock_spawn, mock_get_zone_id):
        """Test that zone 99 always uses unit test path."""
        mock_get_zone_id.return_value = "127.0.0.1"
        mock_spawn.return_value = None

        for unit_test_mode_setting in [False, True]:
            with self.subTest(unit_test_mode=unit_test_mode_setting):
                util.unit_test_mode = unit_test_mode_setting

                tstat = sht31.ThermostatClass(
                    sht31_config.UNIT_TEST_ZONE,
                    sht31_config.flask_folder.production,
                    verbose=False
                )

                self.assertEqual(tstat.path, sht31_config.flask_folder.unit_test)
                self.assertIn("/unit", tstat.url)
                self.assertIn("seed=", tstat.url)

    @patch.object(sht31.ThermostatClass, 'get_target_zone_id')
    def test_regular_zone_normal_mode_uses_production_path(self, mock_get_zone_id):
        """Test that regular zones use production path in normal mode."""
        mock_get_zone_id.return_value = "127.0.0.1"
        util.unit_test_mode = False

        tstat = sht31.ThermostatClass(
            1,
            sht31_config.flask_folder.production,
            verbose=False
        )

        self.assertEqual(tstat.path, sht31_config.flask_folder.production)
        self.assertIn("/data", tstat.url)
        self.assertNotIn("seed=", tstat.url)

    @patch.object(sht31.ThermostatClass, 'get_target_zone_id')
    def test_regular_zone_unit_test_mode_uses_unit_path(self, mock_get_zone_id):
        """Test that regular zones use unit test path in unit test mode."""
        mock_get_zone_id.return_value = "127.0.0.1"
        util.unit_test_mode = True

        # This is the main fix being tested
        tstat = sht31.ThermostatClass(
            1,
            sht31_config.flask_folder.production,
            verbose=False
        )

        self.assertEqual(tstat.path, sht31_config.flask_folder.unit_test)
        self.assertIn("/unit", tstat.url)
        self.assertIn("seed=", tstat.url)

    @patch.object(sht31.ThermostatClass, 'get_target_zone_id')
    def test_custom_path_preserved(self, mock_get_zone_id):
        """Test that custom paths are preserved."""
        mock_get_zone_id.return_value = "127.0.0.1"

        for unit_test_mode_setting in [False, True]:
            with self.subTest(unit_test_mode=unit_test_mode_setting):
                util.unit_test_mode = unit_test_mode_setting

                custom_path = "/custom"
                tstat = sht31.ThermostatClass(
                    1,
                    custom_path,
                    verbose=False
                )

                # Custom paths should not be changed
                self.assertEqual(tstat.path, custom_path)
                self.assertIn("/custom", tstat.url)
                self.assertNotIn("seed=", tstat.url)

    @patch.object(sht31.ThermostatClass, 'get_target_zone_id')
    def test_integration_test_scenario_fix(self, mock_get_zone_id):
        """
        Test the specific scenario that was failing.

        This reproduces the exact error scenario:
        - Zone 1 (from integration test argv)
        - Unit test mode enabled (as in test environment)
        - Should use /unit path, not /data
        """
        mock_get_zone_id.return_value = "bsl-pi0.ddns.net"
        util.unit_test_mode = True

        tstat = sht31.ThermostatClass(1, verbose=False)

        # Verify the URL contains the expected components
        self.assertIn("bsl-pi0.ddns.net:5000", tstat.url)
        self.assertIn("/unit", tstat.url)
        self.assertIn("measurements=10", tstat.url)
        self.assertIn("seed=127", tstat.url)

        # Most importantly, verify it does NOT contain /data
        self.assertNotIn("/data", tstat.url)


if __name__ == "__main__":
    unittest.main(verbosity=2)
