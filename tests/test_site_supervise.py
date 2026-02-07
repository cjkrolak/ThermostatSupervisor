"""
Unit test module for site_supervise.py.
"""

# built-in imports
import unittest
from unittest.mock import patch, MagicMock

# local imports
from src import site_supervise
from src import utilities as util
from tests import unit_test_common as utc


class TestSiteSupervise(utc.UnitTest):
    """Test functions in site_supervise.py."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

    def tearDown(self):
        """Clean up after tests."""
        super().tearDown()

    def test_parse_arguments_defaults(self):
        """Verify parse_arguments with default values."""
        args = site_supervise.parse_arguments([])
        self.assertIsNone(args.config)
        self.assertIsNone(args.measurements)
        self.assertTrue(args.use_threading)
        self.assertTrue(args.verbose)
        self.assertFalse(args.display_zones)
        self.assertFalse(args.display_temps)
        self.assertFalse(args.debug)

    def test_parse_arguments_custom_config(self):
        """Verify parse_arguments with custom config path."""
        args = site_supervise.parse_arguments(["-c", "myconfig.json"])
        self.assertEqual(args.config, "myconfig.json")

    def test_parse_arguments_measurements(self):
        """Verify parse_arguments with measurements override."""
        args = site_supervise.parse_arguments(["-n", "5"])
        self.assertEqual(args.measurements, 5)

    def test_parse_arguments_no_threading(self):
        """Verify parse_arguments with threading disabled."""
        args = site_supervise.parse_arguments(["--no-threading"])
        self.assertFalse(args.use_threading)

    def test_parse_arguments_quiet(self):
        """Verify parse_arguments with quiet mode."""
        args = site_supervise.parse_arguments(["-q"])
        self.assertFalse(args.verbose)

    def test_parse_arguments_display_zones(self):
        """Verify parse_arguments with display-zones option."""
        args = site_supervise.parse_arguments(["--display-zones"])
        self.assertTrue(args.display_zones)

    def test_parse_arguments_display_temps(self):
        """Verify parse_arguments with display-temps option."""
        args = site_supervise.parse_arguments(["--display-temps"])
        self.assertTrue(args.display_temps)

    def test_parse_arguments_debug(self):
        """Verify parse_arguments with debug option."""
        args = site_supervise.parse_arguments(["--debug"])
        self.assertTrue(args.debug)

    @patch('src.site_supervise.ts.ThermostatSite')
    def test_site_supervisor_keyboard_interrupt(self, mock_site_class):
        """Verify site_supervisor handles KeyboardInterrupt gracefully."""
        # Create mock site instance
        mock_site = MagicMock()
        mock_site_class.return_value = mock_site
        # Mock supervise_all_zones to raise KeyboardInterrupt
        mock_site.supervise_all_zones.side_effect = KeyboardInterrupt(
            "User interrupted"
        )

        # Parse arguments
        args = site_supervise.parse_arguments([])

        # Verify SystemExit is raised when KeyboardInterrupt occurs
        with self.assertRaises(SystemExit) as context:
            site_supervise.site_supervisor(args)

        # Verify exit code is 0 (graceful exit)
        self.assertEqual(context.exception.code, 0)

    @patch('src.site_supervise.ts.ThermostatSite')
    def test_site_supervisor_display_zones_only(self, mock_site_class):
        """Verify site_supervisor with display_zones doesn't supervise."""
        # Create mock site instance
        mock_site = MagicMock()
        mock_site_class.return_value = mock_site

        # Parse arguments with display-zones
        args = site_supervise.parse_arguments(["--display-zones"])

        # Run site supervisor
        site_supervise.site_supervisor(args)

        # Verify display_all_zones was called
        mock_site.display_all_zones.assert_called_once()
        # Verify supervise_all_zones was NOT called
        mock_site.supervise_all_zones.assert_not_called()

    @patch('src.site_supervise.ts.ThermostatSite')
    def test_site_supervisor_display_temps_only(self, mock_site_class):
        """Verify site_supervisor with display_temps doesn't supervise."""
        # Create mock site instance
        mock_site = MagicMock()
        mock_site_class.return_value = mock_site

        # Parse arguments with display-temps
        args = site_supervise.parse_arguments(["--display-temps"])

        # Run site supervisor
        site_supervise.site_supervisor(args)

        # Verify display_all_temps was called
        mock_site.display_all_temps.assert_called_once()
        # Verify supervise_all_zones was NOT called
        mock_site.supervise_all_zones.assert_not_called()


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
