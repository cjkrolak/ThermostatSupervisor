#!/usr/bin/env python3
"""
Unit test for nest environment variable token cache functionality.

This test validates the new feature that allows automatic creation of
token_cache.json from environment variables to eliminate manual authorization
prompts in automated environments.
"""
import json
import os
import tempfile
import time
import unittest
from unittest.mock import patch

# local imports
from thermostatsupervisor import nest
from tests import unit_test_common as utc


class TestNestEnvTokenCache(utc.UnitTest):
    """Test nest environment variable token cache functionality."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.print_test_name()

        # Create a temporary directory for cache files
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file_path = os.path.join(self.temp_dir, "test_token_cache.json")

        # Sample environment variable token data
        self.env_access_token = "ya29.a0AfB_byENV_ACCESS_TOKEN"
        self.env_refresh_token = "1//040ENV_REFRESH_TOKEN_FROM_ENVIRONMENT_VARIABLES"
        self.env_expires_in = "3600"

    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up any files created
        if os.path.exists(self.cache_file_path):
            os.unlink(self.cache_file_path)
        os.rmdir(self.temp_dir)

        # Clean up environment variables
        for var in ["NEST_ACCESS_TOKEN", "NEST_REFRESH_TOKEN", "NEST_TOKEN_EXPIRES_IN"]:
            if var in os.environ:
                del os.environ[var]

    @patch.dict(os.environ, {}, clear=False)
    def test_create_token_cache_from_env_complete_data(self):
        """Test token cache creation when all environment variables are present."""
        # Set environment variables
        os.environ["NEST_ACCESS_TOKEN"] = self.env_access_token
        os.environ["NEST_REFRESH_TOKEN"] = self.env_refresh_token
        os.environ["NEST_TOKEN_EXPIRES_IN"] = self.env_expires_in

        # Create a minimal thermostat instance
        thermostat = nest.ThermostatClass.__new__(nest.ThermostatClass)
        thermostat.access_token_cache_file = self.cache_file_path
        thermostat.verbose = True

        # Call the method
        thermostat._create_token_cache_from_env_if_needed()

        # Verify cache file was created
        self.assertTrue(os.path.exists(self.cache_file_path))

        # Verify cache file contents
        with open(self.cache_file_path, "r", encoding="utf-8") as f:
            token_data = json.load(f)

        self.assertEqual(token_data["access_token"], self.env_access_token)
        self.assertEqual(token_data["refresh_token"], self.env_refresh_token)
        self.assertEqual(token_data["expires_in"], int(self.env_expires_in))
        self.assertEqual(
            token_data["scope"], ["https://www.googleapis.com/auth/sdm.service"]
        )
        self.assertEqual(token_data["token_type"], "Bearer")
        self.assertIn("expires_at", token_data)
        # Verify expires_at is approximately current time + expires_in
        expected_expires_at = time.time() + int(self.env_expires_in)
        self.assertAlmostEqual(token_data["expires_at"], expected_expires_at, delta=5)

    @patch.dict(os.environ, {}, clear=False)
    def test_create_token_cache_from_env_minimal_data(self):
        """Test token cache creation with minimal required environment variables."""
        # Set only required environment variables (no expires_in)
        os.environ["NEST_ACCESS_TOKEN"] = self.env_access_token
        os.environ["NEST_REFRESH_TOKEN"] = self.env_refresh_token

        # Create a minimal thermostat instance
        thermostat = nest.ThermostatClass.__new__(nest.ThermostatClass)
        thermostat.access_token_cache_file = self.cache_file_path
        thermostat.verbose = True

        # Call the method
        thermostat._create_token_cache_from_env_if_needed()

        # Verify cache file was created
        self.assertTrue(os.path.exists(self.cache_file_path))

        # Verify cache file contents use default expires_in
        with open(self.cache_file_path, "r", encoding="utf-8") as f:
            token_data = json.load(f)

        self.assertEqual(token_data["access_token"], self.env_access_token)
        self.assertEqual(token_data["refresh_token"], self.env_refresh_token)
        self.assertEqual(token_data["expires_in"], 3600)  # default value

    @patch.dict(os.environ, {}, clear=False)
    def test_create_token_cache_missing_access_token(self):
        """Test no cache file created when access token is missing."""
        # Set only refresh token (missing access token)
        os.environ["NEST_REFRESH_TOKEN"] = self.env_refresh_token
        os.environ["NEST_TOKEN_EXPIRES_IN"] = self.env_expires_in

        # Create a minimal thermostat instance
        thermostat = nest.ThermostatClass.__new__(nest.ThermostatClass)
        thermostat.access_token_cache_file = self.cache_file_path
        thermostat.verbose = True

        # Call the method
        thermostat._create_token_cache_from_env_if_needed()

        # Verify cache file was NOT created
        self.assertFalse(os.path.exists(self.cache_file_path))

    @patch.dict(os.environ, {}, clear=False)
    def test_create_token_cache_missing_refresh_token(self):
        """Test no cache file created when refresh token is missing."""
        # Set only access token (missing refresh token)
        os.environ["NEST_ACCESS_TOKEN"] = self.env_access_token
        os.environ["NEST_TOKEN_EXPIRES_IN"] = self.env_expires_in

        # Create a minimal thermostat instance
        thermostat = nest.ThermostatClass.__new__(nest.ThermostatClass)
        thermostat.access_token_cache_file = self.cache_file_path
        thermostat.verbose = True

        # Call the method
        thermostat._create_token_cache_from_env_if_needed()

        # Verify cache file was NOT created
        self.assertFalse(os.path.exists(self.cache_file_path))

    @patch.dict(os.environ, {}, clear=False)
    def test_create_token_cache_file_already_exists(self):
        """Test no action taken when cache file already exists."""
        # Create existing cache file
        existing_data = {"existing": "data"}
        with open(self.cache_file_path, "w", encoding="utf-8") as f:
            json.dump(existing_data, f)

        # Set environment variables
        os.environ["NEST_ACCESS_TOKEN"] = self.env_access_token
        os.environ["NEST_REFRESH_TOKEN"] = self.env_refresh_token

        # Create a minimal thermostat instance
        thermostat = nest.ThermostatClass.__new__(nest.ThermostatClass)
        thermostat.access_token_cache_file = self.cache_file_path
        thermostat.verbose = True

        # Call the method
        thermostat._create_token_cache_from_env_if_needed()

        # Verify existing cache file was not modified
        with open(self.cache_file_path, "r", encoding="utf-8") as f:
            unchanged_data = json.load(f)

        self.assertEqual(unchanged_data, existing_data)

    @patch.dict(os.environ, {}, clear=False)
    def test_create_token_cache_file_write_error(self):
        """Test graceful handling of file write errors."""
        # Set environment variables
        os.environ["NEST_ACCESS_TOKEN"] = self.env_access_token
        os.environ["NEST_REFRESH_TOKEN"] = self.env_refresh_token

        # Use invalid file path to trigger write error
        invalid_cache_path = "/invalid/directory/token_cache.json"

        # Create a minimal thermostat instance
        thermostat = nest.ThermostatClass.__new__(nest.ThermostatClass)
        thermostat.access_token_cache_file = invalid_cache_path
        thermostat.verbose = True

        # Call the method - should not raise exception
        try:
            thermostat._create_token_cache_from_env_if_needed()
        except Exception as e:
            self.fail(f"Method should not raise exception on write error: {e}")

        # Verify invalid file was not created
        self.assertFalse(os.path.exists(invalid_cache_path))


if __name__ == "__main__":
    unittest.main()
