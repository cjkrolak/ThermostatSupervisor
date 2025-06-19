#!/usr/bin/env python3
"""
Test the WSGI entry points for production deployment.

This test verifies that the WSGI applications can be created successfully
and are properly configured for production use.
"""

import unittest

# local imports
from thermostatsupervisor import supervisor_wsgi
from thermostatsupervisor import sht31_wsgi


class TestWSGIEntryPoints(unittest.TestCase):
    """Test WSGI entry points for production deployment."""

    def test_supervisor_wsgi_application_creation(self):
        """Test that supervisor WSGI application can be created."""
        # The application should already be created when importing the module
        self.assertIsNotNone(supervisor_wsgi.application)
        self.assertTrue(hasattr(supervisor_wsgi.application, "wsgi_app"))
        print("Supervisor WSGI application created successfully")

    def test_sht31_wsgi_application_creation(self):
        """Test that SHT31 WSGI application can be created."""
        # The application should already be created when importing the module
        self.assertIsNotNone(sht31_wsgi.application)
        self.assertTrue(hasattr(sht31_wsgi.application, "wsgi_app"))
        print("SHT31 WSGI application created successfully")

    def test_supervisor_wsgi_app_config(self):
        """Test supervisor WSGI application configuration."""
        app = supervisor_wsgi.application
        # Should not be in debug mode for production
        self.assertFalse(app.debug)
        print("Supervisor WSGI application properly configured for production")

    def test_sht31_wsgi_app_config(self):
        """Test SHT31 WSGI application configuration."""
        app = sht31_wsgi.application
        # Should not be in debug mode for production
        self.assertFalse(app.debug)
        print("SHT31 WSGI application properly configured for production")


if __name__ == "__main__":
    print("Testing WSGI entry points for production deployment")
    unittest.main(verbosity=2)
