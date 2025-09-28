"""
Unit test for SHT31 environment variable fallback logic.

This test validates the fix for issue where SHT31 ThermostatClass
was failing when environment variables are missing in unit test mode.
"""

import os
import unittest
from unittest.mock import patch

from thermostatsupervisor import sht31
from thermostatsupervisor import sht31_config
from thermostatsupervisor import utilities as util
from tests import unit_test_common as utc


class TestSHT31MissingEnvVar(utc.UnitTest):
    """Test SHT31 environment variable fallback logic."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.original_unit_test_mode = util.unit_test_mode

    def tearDown(self):
        """Clean up after tests."""
        util.unit_test_mode = self.original_unit_test_mode
        super().tearDown()

    @patch.object(sht31.ThermostatClass, "spawn_flask_server")
    def test_missing_env_var_fallback_in_unit_test_mode(self, mock_spawn):
        """
        Test that missing environment variables fall back to localhost in unit
        test mode.

        This reproduces and fixes the exact error scenario:
        - Zone 1 (regular zone, not unit test zone 99)
        - Unit test mode enabled
        - Environment variable SHT31_REMOTE_IP_ADDRESS_1 is missing or placeholder
        - Should fall back to 127.0.0.1 instead of None or placeholder
        """
        mock_spawn.return_value = None

        # Save original state
        original_mode = util.unit_test_mode

        try:
            # Explicitly set unit test mode
            util.unit_test_mode = True

            # Verify unit test mode is actually set
            self.assertTrue(util.unit_test_mode,
                            "unit_test_mode should be True for this test")

            # This should NOT fail even if env var is missing or has placeholder
            tstat = sht31.ThermostatClass(1, verbose=False)

            # Debug information to help diagnose failures
            if tstat.ip_address != "127.0.0.1":
                from thermostatsupervisor import environment as env
                env_result = env.get_env_variable('SHT31_REMOTE_IP_ADDRESS_1')
                self.fail(
                    f"Expected IP address '127.0.0.1' but got "
                    f"'{tstat.ip_address}'. "
                    f"util.unit_test_mode={util.unit_test_mode}, "
                    f"env_result={env_result}, "
                    f"util module id={id(util)}"
                )

            # Verify the IP address fallback works for both missing and
            # placeholder values
            self.assertEqual(tstat.ip_address, "127.0.0.1")

            # Verify the URL is properly formed
            expected_components = [
                "http://127.0.0.1:5000",
                "/unit",
                "measurements=10",
                "seed=127"
            ]
            for component in expected_components:
                self.assertIn(component, tstat.url)

            # Verify URL does NOT contain None or empty host
            self.assertNotIn("http://:5000", tstat.url)
            self.assertNotIn("None", tstat.url)
        finally:
            # Always restore original mode
            util.unit_test_mode = original_mode

    @patch.object(sht31.ThermostatClass, "spawn_flask_server")
    def test_missing_env_var_fails_in_non_unit_test_mode(self, mock_spawn):
        """
        Test that missing environment variables still cause TypeError in
        non-unit test mode.

        This ensures the fallback behavior is only active in unit test mode.
        """
        mock_spawn.return_value = None

        # Save original state
        original_mode = util.unit_test_mode

        try:
            # Explicitly disable unit test mode
            util.unit_test_mode = False

            # Verify unit test mode is actually disabled
            self.assertFalse(util.unit_test_mode,
                             "unit_test_mode should be False for this test")

            # Create temporary environment where the env var is truly missing
            # by temporarily moving any supervisor-env.txt file
            import tempfile
            import shutil

            supervisor_env_path = "supervisor-env.txt"
            backup_path = None

            if os.path.exists(supervisor_env_path):
                # Use secure temporary file creation
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    backup_path = temp_file.name
                shutil.move(supervisor_env_path, backup_path)

            try:
                # This should fail when env var is missing and not in unit
                # test mode
                with self.assertRaises(TypeError) as context:
                    sht31.ThermostatClass(1, verbose=False)

                # Should get the concatenation error because ip_address is None
                self.assertIn("can only concatenate str", str(context.exception))

            finally:
                # Restore supervisor-env.txt if it existed
                if backup_path and os.path.exists(backup_path):
                    shutil.move(backup_path, supervisor_env_path)

        finally:
            # Always restore original mode
            util.unit_test_mode = original_mode

    @patch.object(sht31.ThermostatClass, "spawn_flask_server")
    def test_placeholder_value_preserved_in_non_unit_test_mode(self, mock_spawn):
        """
        Test that placeholder values are preserved in non-unit-test mode.

        This ensures that in production, placeholder values don't get replaced.
        """
        mock_spawn.return_value = None
        util.unit_test_mode = False

        # Create a temporary supervisor-env.txt with placeholder value
        import tempfile

        original_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                os.chdir(temp_dir)

                # Create supervisor-env.txt with placeholder value
                with open("supervisor-env.txt", "w") as f:
                    f.write("SHT31_REMOTE_IP_ADDRESS_1=***\n")

                # Test that placeholder value is NOT replaced in non-unit-test
                # mode
                tstat = sht31.ThermostatClass(1, verbose=False)
                self.assertEqual(tstat.ip_address, "***")

        finally:
            os.chdir(original_cwd)

    @patch.object(sht31.ThermostatClass, "spawn_flask_server")
    @patch.dict(os.environ, {}, clear=True)  # Clear environment variables
    def test_placeholder_value_fallback_in_unit_test_mode(self, mock_spawn):
        """
        Test that placeholder values (like '***') fall back to localhost in
        unit test mode.

        This handles the specific CI scenario where supervisor-env.txt has
        placeholder values.
        """
        mock_spawn.return_value = None
        util.unit_test_mode = True

        # Create a temporary supervisor-env.txt with placeholder value
        import tempfile

        original_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                os.chdir(temp_dir)

                # Create supervisor-env.txt with placeholder value
                with open("supervisor-env.txt", "w") as f:
                    f.write("SHT31_REMOTE_IP_ADDRESS_1=***\n")

                # Test that placeholder value gets replaced with localhost
                tstat = sht31.ThermostatClass(1, verbose=False)
                self.assertEqual(tstat.ip_address, "127.0.0.1")

        finally:
            os.chdir(original_cwd)

    @patch.object(sht31.ThermostatClass, "spawn_flask_server")
    def test_unit_test_zone_still_works(self, mock_spawn):
        """Test that the unit test zone (99) still works as expected."""
        mock_spawn.return_value = None
        util.unit_test_mode = True

        # Zone 99 should work (this was already working before the fix)
        tstat = sht31.ThermostatClass(
            sht31_config.UNIT_TEST_ZONE,
            verbose=False
        )

        # Should get local IP via existing logic in environment.py
        self.assertIsNotNone(tstat.ip_address)
        self.assertIn("http://", tstat.url)
        self.assertNotIn("http://:5000", tstat.url)


if __name__ == "__main__":
    unittest.main(verbosity=2)
