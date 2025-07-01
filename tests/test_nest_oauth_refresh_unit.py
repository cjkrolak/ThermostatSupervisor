#!/usr/bin/env python3
"""
Unit test for nest OAuth token refresh functionality.

This test validates the OAuth token refresh fix without requiring
actual nest hardware connection or valid OAuth credentials.
"""
import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

# local imports
from thermostatsupervisor import nest
from tests import unit_test_common as utc


class TestNestOAuthRefresh(utc.UnitTest):
    """Test nest OAuth token refresh functionality."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.print_test_name()

        # Create a temporary cache file
        self.test_cache_file = tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".json"
        )
        self.cache_file_path = self.test_cache_file.name

        # Sample initial token cache with valid tokens
        self.initial_token_data = {
            "access_token": "ya29.a0AfB_byOLD_ACCESS_TOKEN_EXPIRED",
            "refresh_token": (
                "1//040jmes6vvJ7gCgYIARAAGAQSNwF-L9IrdajcBypXM_Rbh0K"
                "clSy9j-oY3XYl8tb6Zhu1_0BgAPseN6pkAneuDmo0MY8qGGz8I"
                "ck"
            ),
            "expires_in": 3600,
        }

        # Write initial token data
        json.dump(self.initial_token_data, self.test_cache_file, indent=4)
        self.test_cache_file.close()

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.cache_file_path):
            os.unlink(self.cache_file_path)

    @patch("thermostatsupervisor.nest.requests.post")
    def test_refresh_oauth_token_with_new_refresh_token(self, mock_post):
        """Test OAuth refresh when server returns a new refresh token."""
        # Mock successful refresh response with new refresh token
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "access_token": "ya29.a0AfB_byNEW_ACCESS_TOKEN",
            "refresh_token": "1//040NEW_REFRESH_TOKEN_DIFFERENT",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        # Create a minimal thermostat instance
        thermostat = nest.ThermostatClass.__new__(nest.ThermostatClass)
        thermostat.access_token_cache_file = self.cache_file_path
        thermostat.client_id = "test_client_id"
        thermostat.client_secret = "test_client_secret"

        # Call the refresh method
        thermostat.refresh_oauth_token()

        # Verify the cache file was updated correctly
        with open(self.cache_file_path, "r", encoding="utf-8") as f:
            updated_data = json.load(f)

        # Check that both tokens were updated
        self.assertEqual(updated_data["access_token"], "ya29.a0AfB_byNEW_ACCESS_TOKEN")
        self.assertEqual(
            updated_data["refresh_token"], "1//040NEW_REFRESH_TOKEN_DIFFERENT"
        )
        self.assertEqual(updated_data["expires_in"], 3600)

        # Verify the refresh token was not overwritten with access token
        self.assertNotEqual(updated_data["refresh_token"], updated_data["access_token"])

    @patch("thermostatsupervisor.nest.requests.post")
    def test_refresh_oauth_token_without_new_refresh_token(self, mock_post):
        """Test OAuth refresh when server does NOT return a new refresh token."""
        # Mock successful refresh response without new refresh token
        # (common for Google OAuth)
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "access_token": "ya29.a0AfB_byNEW_ACCESS_TOKEN",
            "expires_in": 3600
            # No refresh_token in response
        }
        mock_post.return_value = mock_response

        # Save original refresh token for comparison
        original_refresh_token = self.initial_token_data["refresh_token"]

        # Create a minimal thermostat instance
        thermostat = nest.ThermostatClass.__new__(nest.ThermostatClass)
        thermostat.access_token_cache_file = self.cache_file_path
        thermostat.client_id = "test_client_id"
        thermostat.client_secret = "test_client_secret"

        # Call the refresh method
        thermostat.refresh_oauth_token()

        # Verify the cache file was updated correctly
        with open(self.cache_file_path, "r", encoding="utf-8") as f:
            updated_data = json.load(f)

        # Check that access token was updated but refresh token preserved
        self.assertEqual(updated_data["access_token"], "ya29.a0AfB_byNEW_ACCESS_TOKEN")
        self.assertEqual(updated_data["refresh_token"], original_refresh_token)
        self.assertEqual(updated_data["expires_in"], 3600)

        # Most importantly: verify refresh token was NOT overwritten with
        # access token
        self.assertNotEqual(updated_data["refresh_token"], updated_data["access_token"])

    @patch("thermostatsupervisor.nest.requests.post")
    def test_refresh_oauth_token_failure(self, mock_post):
        """Test OAuth refresh failure handling."""
        # Mock failed refresh response
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.text = (
            '{"error": "invalid_grant", '
            '"error_description": "Token has been expired or '
            'revoked."}'
        )
        mock_post.return_value = mock_response

        # Create a minimal thermostat instance
        thermostat = nest.ThermostatClass.__new__(nest.ThermostatClass)
        thermostat.access_token_cache_file = self.cache_file_path
        thermostat.client_id = "test_client_id"
        thermostat.client_secret = "test_client_secret"

        # Call the refresh method and expect exception
        with self.assertRaises(Exception) as context:
            thermostat.refresh_oauth_token()

        # Check that the exception contains the status code
        self.assertIn("Failed to refresh token: 400", str(context.exception))

        # Verify the cache file was NOT modified on failure
        with open(self.cache_file_path, "r", encoding="utf-8") as f:
            unchanged_data = json.load(f)

        # Data should be unchanged
        self.assertEqual(unchanged_data, self.initial_token_data)


if __name__ == "__main__":
    unittest.main()
