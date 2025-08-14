#!/usr/bin/env python3
"""
Integration test for nest environment variable automation functionality.

This test validates that the full initialization process works correctly
with environment variable token cache automation.
"""
import json
import os
import tempfile
import unittest
from unittest.mock import patch

# local imports
from thermostatsupervisor import nest
from tests import unit_test_common as utc


class TestNestEnvIntegration(utc.UnitTest):
    """Integration test for nest environment variable automation."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.print_test_name()

        # Create a temporary directory for cache files
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file_path = os.path.join(self.temp_dir, "test_token_cache.json")

        # Mock required env vars
        self.mock_env_vars = {
            "GCLOUD_CLIENT_ID": "test_client_id",
            "GCLOUD_CLIENT_SECRET": "test_client_secret",
            "DAC_PROJECT_ID": "test_project_id",
            "NEST_ACCESS_TOKEN": "ya29.test_access_token",
            "NEST_REFRESH_TOKEN": "1//040test_refresh_token",
            "NEST_TOKEN_EXPIRES_IN": "3600",
        }

    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up any files created
        if os.path.exists(self.cache_file_path):
            os.unlink(self.cache_file_path)
        os.rmdir(self.temp_dir)

    @patch.dict(os.environ, {}, clear=False)
    def test_integration_token_cache_creation(self):
        """Test integration of token cache creation with environment variables."""
        # Set environment variables
        for key, value in self.mock_env_vars.items():
            os.environ[key] = value

        # Verify cache file doesn't exist initially
        self.assertFalse(os.path.exists(self.cache_file_path))

        # Create minimal thermostat instance and call the method
        thermostat = nest.ThermostatClass.__new__(nest.ThermostatClass)
        thermostat.access_token_cache_file = self.cache_file_path
        thermostat.verbose = True

        # Call the token cache creation method
        thermostat._create_token_cache_from_env_if_needed()

        # Verify token cache file was created
        self.assertTrue(os.path.exists(self.cache_file_path))

        # Verify token cache file contents
        with open(self.cache_file_path, "r", encoding="utf-8") as f:
            token_data = json.load(f)

        self.assertEqual(
            token_data["access_token"], self.mock_env_vars["NEST_ACCESS_TOKEN"]
        )
        self.assertEqual(
            token_data["refresh_token"], self.mock_env_vars["NEST_REFRESH_TOKEN"]
        )
        self.assertEqual(
            token_data["expires_in"], int(self.mock_env_vars["NEST_TOKEN_EXPIRES_IN"])
        )

    @patch.dict(os.environ, {}, clear=False)
    def test_no_env_vars_no_cache_created(self):
        """Test no cache file created when environment variables missing."""
        # Set only required OAuth credentials but no token env vars
        os.environ["GCLOUD_CLIENT_ID"] = "test_client_id"
        os.environ["GCLOUD_CLIENT_SECRET"] = "test_client_secret"
        os.environ["DAC_PROJECT_ID"] = "test_project_id"

        # Create minimal thermostat instance
        thermostat = nest.ThermostatClass.__new__(nest.ThermostatClass)
        thermostat.access_token_cache_file = self.cache_file_path
        thermostat.verbose = True

        # Call the token cache creation method
        thermostat._create_token_cache_from_env_if_needed()

        # Verify no cache file was created
        self.assertFalse(os.path.exists(self.cache_file_path))


if __name__ == "__main__":
    unittest.main()
