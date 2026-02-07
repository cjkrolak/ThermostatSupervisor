"""
Unit test module for site_supervise.py.
"""

# built-in imports
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

# local imports
from src import site_supervise as ss
from src import utilities as util
from tests import unit_test_common as utc


class TestParseArguments(utc.UnitTest):
    """Test parse_arguments function."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        # Set test-specific log file
        self.original_log_file = util.log_msg.file_name
        util.log_msg.file_name = "unit_test.txt"

    def tearDown(self):
        """Clean up after tests."""
        util.log_msg.file_name = self.original_log_file
        super().tearDown()

    def test_parse_arguments_defaults(self):
        """Verify default argument parsing."""
        args = ss.parse_arguments([])
        self.assertIsNone(args.config)
        self.assertIsNone(args.measurements)
        self.assertTrue(args.use_threading)
        self.assertTrue(args.verbose)
        self.assertFalse(args.display_zones)
        self.assertFalse(args.display_temps)

    def test_parse_arguments_with_config(self):
        """Verify config file argument parsing."""
        args = ss.parse_arguments(["-c", "myconfig.json"])
        self.assertEqual(args.config, "myconfig.json")

    def test_parse_arguments_with_config_long(self):
        """Verify config file argument parsing with long option."""
        args = ss.parse_arguments(["--config", "myconfig.json"])
        self.assertEqual(args.config, "myconfig.json")

    def test_parse_arguments_with_measurements(self):
        """Verify measurements argument parsing."""
        args = ss.parse_arguments(["-n", "5"])
        self.assertEqual(args.measurements, 5)

    def test_parse_arguments_with_measurements_long(self):
        """Verify measurements argument parsing with long option."""
        args = ss.parse_arguments(["--measurements", "10"])
        self.assertEqual(args.measurements, 10)

    def test_parse_arguments_threading_enabled(self):
        """Verify threading enabled argument parsing."""
        args = ss.parse_arguments(["--threading"])
        self.assertTrue(args.use_threading)

    def test_parse_arguments_threading_disabled(self):
        """Verify threading disabled argument parsing."""
        args = ss.parse_arguments(["--no-threading"])
        self.assertFalse(args.use_threading)

    def test_parse_arguments_verbose_enabled(self):
        """Verify verbose enabled argument parsing."""
        args = ss.parse_arguments(["-v"])
        self.assertTrue(args.verbose)

    def test_parse_arguments_verbose_disabled(self):
        """Verify verbose disabled argument parsing."""
        args = ss.parse_arguments(["-q"])
        self.assertFalse(args.verbose)

    def test_parse_arguments_quiet_flag(self):
        """Verify quiet flag disables verbose."""
        args = ss.parse_arguments(["--quiet"])
        self.assertFalse(args.verbose)

    def test_parse_arguments_display_zones(self):
        """Verify display zones argument parsing."""
        args = ss.parse_arguments(["--display-zones"])
        self.assertTrue(args.display_zones)

    def test_parse_arguments_display_temps(self):
        """Verify display temps argument parsing."""
        args = ss.parse_arguments(["--display-temps"])
        self.assertTrue(args.display_temps)

    def test_parse_arguments_combined_options(self):
        """Verify combined argument parsing."""
        args = ss.parse_arguments(
            ["-c", "test.json", "-n", "3", "--no-threading", "-q"]
        )
        self.assertEqual(args.config, "test.json")
        self.assertEqual(args.measurements, 3)
        self.assertFalse(args.use_threading)
        self.assertFalse(args.verbose)

    def test_parse_arguments_with_sys_argv(self):
        """Verify parsing uses sys.argv when argv_list is None."""
        with patch.object(sys, 'argv', ['site_supervise.py', '-n', '7']):
            args = ss.parse_arguments(None)
            self.assertEqual(args.measurements, 7)


class TestLoadSiteConfigFromFile(utc.UnitTest):
    """Test load_site_config_from_file function."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        # Set test-specific log file
        self.original_log_file = util.log_msg.file_name
        util.log_msg.file_name = "unit_test.txt"

    def tearDown(self):
        """Clean up after tests."""
        util.log_msg.file_name = self.original_log_file
        super().tearDown()

    def test_load_valid_config(self):
        """Verify loading a valid JSON configuration file."""
        # Create a temporary JSON config file
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            test_config = {
                "site_name": "test_site",
                "thermostats": [
                    {
                        "thermostat_type": "emulator",
                        "zone": 0,
                        "enabled": True,
                    }
                ]
            }
            json.dump(test_config, f)
            temp_file = f.name

        try:
            config = ss.load_site_config_from_file(temp_file)
            self.assertEqual(config["site_name"], "test_site")
            self.assertEqual(len(config["thermostats"]), 1)
            self.assertEqual(
                config["thermostats"][0]["thermostat_type"],
                "emulator"
            )
        finally:
            os.unlink(temp_file)

    def test_load_missing_config_file(self):
        """Verify error handling for missing configuration file."""
        with self.assertRaises(SystemExit) as cm:
            ss.load_site_config_from_file("/nonexistent/path/config.json")
        self.assertEqual(cm.exception.code, 1)

    def test_load_invalid_json_config(self):
        """Verify error handling for invalid JSON configuration."""
        # Create a temporary file with invalid JSON
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            f.write("{ invalid json content }")
            temp_file = f.name

        try:
            with self.assertRaises(SystemExit) as cm:
                ss.load_site_config_from_file(temp_file)
            self.assertEqual(cm.exception.code, 1)
        finally:
            os.unlink(temp_file)

    def test_load_empty_json_file(self):
        """Verify loading an empty JSON object."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            config = ss.load_site_config_from_file(temp_file)
            self.assertEqual(config, {})
        finally:
            os.unlink(temp_file)


class TestSiteSupervisor(utc.UnitTest):
    """Test site_supervisor function."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        # Set test-specific log file
        self.original_log_file = util.log_msg.file_name
        util.log_msg.file_name = "unit_test.txt"
        # Create a minimal args namespace
        self.default_args = type('Args', (), {
            'config': None,
            'measurements': None,
            'verbose': False,
            'use_threading': False,
            'display_zones': False,
            'display_temps': False,
        })()

    def tearDown(self):
        """Clean up after tests."""
        util.log_msg.file_name = self.original_log_file
        super().tearDown()

    def test_site_supervisor_with_default_config(self):
        """Verify site_supervisor with default configuration.

        Tests that site supervision completes successfully with default
        settings. If an exception is raised, the test will fail.
        """
        args = self.default_args
        args.measurements = 1
        ss.site_supervisor(args)

    def test_site_supervisor_with_custom_config_file(self):
        """Verify site_supervisor with custom config file."""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            test_config = {
                "site_name": "test_site",
                "thermostats": [
                    {
                        "thermostat_type": "emulator",
                        "zone": 0,
                        "enabled": True,
                        "poll_time": 1,
                        "measurements": 1,
                    }
                ]
            }
            json.dump(test_config, f)
            temp_file = f.name

        try:
            args = self.default_args
            args.config = temp_file
            ss.site_supervisor(args)
        finally:
            os.unlink(temp_file)

    def test_site_supervisor_with_measurement_override(self):
        """Verify measurement count override.

        Tests that the measurement override is properly processed
        (lines 175-181 of site_supervise.py). If an exception is raised,
        the test will fail.
        """
        args = self.default_args
        args.measurements = 1
        ss.site_supervisor(args)

    def test_site_supervisor_with_threading(self):
        """Verify site_supervisor with threading enabled."""
        args = self.default_args
        args.use_threading = True
        args.measurements = 1
        ss.site_supervisor(args)

    def test_site_supervisor_display_zones_only(self):
        """Verify site_supervisor with display_zones flag."""
        args = self.default_args
        args.display_zones = True
        # Should display zones and return early
        ss.site_supervisor(args)

    def test_site_supervisor_display_temps_only(self):
        """Verify site_supervisor with display_temps flag."""
        args = self.default_args
        args.display_temps = True
        # Should display temps and return early
        ss.site_supervisor(args)

    def test_site_supervisor_with_results(self):
        """Verify site_supervisor processes results correctly.

        Tests that full supervision execution completes and results are
        displayed (lines 214-239 of site_supervise.py). If an exception
        is raised, the test will fail.
        """
        args = self.default_args
        args.measurements = 1
        ss.site_supervisor(args)

    def test_site_supervisor_with_errors(self):
        """Verify site_supervisor handles errors in results."""
        # Create a config with an invalid thermostat type that will error
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            test_config = {
                "site_name": "test_site",
                "thermostats": [
                    {
                        "thermostat_type": "invalid_type_999",
                        "zone": 0,
                        "enabled": True,
                        "poll_time": 1,
                        "measurements": 1,
                    }
                ]
            }
            json.dump(test_config, f)
            temp_file = f.name

        try:
            args = self.default_args
            args.config = temp_file
            args.measurements = 1
            # Run supervision - errors are logged but don't crash
            ss.site_supervisor(args)
        finally:
            os.unlink(temp_file)

    def test_site_supervisor_verbose_mode(self):
        """Verify site_supervisor with verbose logging."""
        args = self.default_args
        args.verbose = True
        args.measurements = 1
        ss.site_supervisor(args)


class TestExecSiteSupervise(utc.UnitTest):
    """Test exec_site_supervise function."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        # Save current log file and debug mode
        self.original_log_file = util.log_msg.file_name
        self.original_debug = getattr(util.log_msg, 'debug', False)
        # Set test-specific log file
        util.log_msg.file_name = "unit_test.txt"

    def tearDown(self):
        """Clean up after tests."""
        # Restore original log file and debug mode
        util.log_msg.file_name = self.original_log_file
        util.log_msg.debug = self.original_debug
        super().tearDown()

    def test_exec_site_supervise_default(self):
        """Verify exec_site_supervise with defaults."""
        result = ss.exec_site_supervise(
            debug=False,
            argv_list=["-n", "1"]
        )
        self.assertTrue(result)

    def test_exec_site_supervise_with_debug(self):
        """Verify exec_site_supervise with debug mode."""
        result = ss.exec_site_supervise(
            debug=True,
            argv_list=["-n", "1"]
        )
        self.assertTrue(result)
        # Verify debug mode was set
        self.assertTrue(util.log_msg.debug)

    def test_exec_site_supervise_with_arguments(self):
        """Verify exec_site_supervise with custom arguments."""
        result = ss.exec_site_supervise(
            debug=False,
            argv_list=["-n", "1", "--no-threading"]
        )
        self.assertTrue(result)

    def test_exec_site_supervise_with_display_zones(self):
        """Verify exec_site_supervise with display zones."""
        result = ss.exec_site_supervise(
            debug=False,
            argv_list=["--display-zones"]
        )
        self.assertTrue(result)

    def test_exec_site_supervise_with_display_temps(self):
        """Verify exec_site_supervise with display temps."""
        result = ss.exec_site_supervise(
            debug=False,
            argv_list=["--display-temps"]
        )
        self.assertTrue(result)

    def test_exec_site_supervise_with_config_file(self):
        """Verify exec_site_supervise with config file."""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            test_config = {
                "site_name": "test_site",
                "thermostats": [
                    {
                        "thermostat_type": "emulator",
                        "zone": 0,
                        "enabled": True,
                        "poll_time": 1,
                        "measurements": 1,
                    }
                ]
            }
            json.dump(test_config, f)
            temp_file = f.name

        try:
            result = ss.exec_site_supervise(
                debug=False,
                argv_list=["-c", temp_file, "-n", "1"]
            )
            self.assertTrue(result)
        finally:
            os.unlink(temp_file)

    def test_exec_site_supervise_all_options(self):
        """Verify exec_site_supervise with all options."""
        result = ss.exec_site_supervise(
            debug=True,
            argv_list=["-n", "1", "--threading", "-v"]
        )
        self.assertTrue(result)


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
