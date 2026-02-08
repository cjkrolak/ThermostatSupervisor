"""
Unit test module for kumocloudv3.py zone data matching functionality.

This test module focuses on testing the zone metadata population logic
to ensure serial numbers are correctly matched to zones by name.
"""

# built-in imports
import copy
import unittest
from unittest.mock import MagicMock, Mock, patch

# third-party imports
import requests

# local imports
try:
    from src import kumocloudv3
    from src import kumocloudv3_config
    from src import thermostat_common as tc
    from src import utilities as util

    kumocloudv3_import_error = None
except ImportError as ex:
    kumocloudv3 = None
    kumocloudv3_config = None
    tc = None
    util = None
    kumocloudv3_import_error = ex

from tests import unit_test_common as utc


@unittest.skipIf(
    kumocloudv3_import_error,
    "kumocloudv3 import failed, tests are disabled",
)
class ZoneMetadataPopulationUnitTest(utc.UnitTest):
    """
    Unit tests for zone metadata population functionality.

    These tests verify that serial numbers are correctly matched to zone
    indices based on zone names, not just sequential API order.
    """

    def setUp(self):
        """Setup for unit tests."""
        super().setUp()
        self.print_test_name()

        # Save original metadata to restore after tests
        self.original_metadata = copy.deepcopy(kumocloudv3_config.metadata)

        # Mock zone data that might come from API in different order
        # Simulating the scenario where API returns zones in this order:
        # 0: Kitchen, 1: Basement, 2: Main Living
        self.mock_zones_api_response = [
            {
                "name": "Kitchen",
                "adapter": {"deviceSerial": "SERIAL_KITCHEN_001"},
            },
            {
                "name": "Basement",
                "adapter": {"deviceSerial": "SERIAL_BASEMENT_002"},
            },
            {
                "name": "Main Living",
                "adapter": {"deviceSerial": "SERIAL_MAIN_003"},
            },
        ]

        # Serial numbers in API order
        self.serial_num_lst = [
            "SERIAL_KITCHEN_001",
            "SERIAL_BASEMENT_002",
            "SERIAL_MAIN_003",
        ]

        # Expected metadata after dynamic zone assignment
        # Note: After _update_zone_assignments, indices might be:
        # MAIN_LIVING=2, KITCHEN=0, BASEMENT=1 (based on zone names)
        self.expected_metadata_structure = {
            0: {"zone_name": "Kitchen", "serial_number": None},
            1: {"zone_name": "Basement", "serial_number": None},
            2: {"zone_name": "Main Living", "serial_number": None},
        }

    def tearDown(self):
        """Cleanup after unit tests."""
        # Restore original metadata
        kumocloudv3_config.metadata.clear()
        kumocloudv3_config.metadata.update(self.original_metadata)
        super().tearDown()

    def test_populate_metadata_matches_by_zone_name(self):
        """
        Test that _populate_metadata correctly matches serial numbers
        to zones by zone name, not by API order.
        """
        # Setup metadata dict to simulate post-_update_zone_assignments state
        kumocloudv3_config.metadata.clear()
        kumocloudv3_config.metadata.update(
            copy.deepcopy(self.expected_metadata_structure)
        )

        # Create a mock thermostat instance
        with patch.object(
            kumocloudv3.ThermostatClass, "_authenticate"
        ), patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            # Mock the _get_sites and _get_zones methods
            mock_sites = [{"id": "test_site_123"}]
            # type: ignore[attr-defined]
            thermostat._get_sites = MagicMock(return_value=mock_sites)
            # type: ignore[attr-defined]
            thermostat._get_zones = MagicMock(
                return_value=self.mock_zones_api_response
            )

            # Call _populate_metadata with serial numbers
            # type: ignore[attr-defined]
            thermostat._populate_metadata(self.serial_num_lst)

            # Verify that serial numbers are correctly matched by zone name
            # Kitchen (index 0) should get SERIAL_KITCHEN_001
            self.assertEqual(
                kumocloudv3_config.metadata[0]["serial_number"],
                "SERIAL_KITCHEN_001",
                "Kitchen zone should have Kitchen serial number",
            )

            # Basement (index 1) should get SERIAL_BASEMENT_002
            self.assertEqual(
                kumocloudv3_config.metadata[1]["serial_number"],
                "SERIAL_BASEMENT_002",
                "Basement zone should have Basement serial number",
            )

            # Main Living (index 2) should get SERIAL_MAIN_003
            self.assertEqual(
                kumocloudv3_config.metadata[2]["serial_number"],
                "SERIAL_MAIN_003",
                "Main Living zone should have Main Living serial number",
            )

    def test_populate_metadata_fallback_on_api_error(self):
        """
        Test that _populate_metadata falls back to sequential assignment
        when API calls fail.
        """
        # Setup metadata dict
        kumocloudv3_config.metadata.clear()
        kumocloudv3_config.metadata.update(
            copy.deepcopy(self.expected_metadata_structure)
        )

        # Create a mock thermostat instance
        with patch.object(
            kumocloudv3.ThermostatClass, "_authenticate"
        ), patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            # Mock _get_sites to raise an exception
            # type: ignore[attr-defined]
            thermostat._get_sites = MagicMock(
                side_effect=Exception("API Error")
            )

            # Call _populate_metadata - should fallback to sequential
            # type: ignore[attr-defined]
            thermostat._populate_metadata(self.serial_num_lst)

            # Verify fallback behavior: sequential assignment
            self.assertEqual(
                kumocloudv3_config.metadata[0]["serial_number"],
                "SERIAL_KITCHEN_001",
            )
            self.assertEqual(
                kumocloudv3_config.metadata[1]["serial_number"],
                "SERIAL_BASEMENT_002",
            )
            self.assertEqual(
                kumocloudv3_config.metadata[2]["serial_number"],
                "SERIAL_MAIN_003",
            )

    def test_populate_metadata_handles_missing_zone_names(self):
        """
        Test that _populate_metadata handles zones with missing or
        empty names gracefully.
        """
        # Setup metadata dict
        kumocloudv3_config.metadata.clear()
        kumocloudv3_config.metadata.update(
            copy.deepcopy(self.expected_metadata_structure)
        )

        # Mock zones with some missing names
        mock_zones_with_missing_names = [
            {
                "name": "",  # Empty name
                "adapter": {"deviceSerial": "SERIAL_KITCHEN_001"},
            },
            {
                "name": "Basement",
                "adapter": {"deviceSerial": "SERIAL_BASEMENT_002"},
            },
            {
                # Missing name field entirely
                "adapter": {"deviceSerial": "SERIAL_MAIN_003"},
            },
        ]

        # Create a mock thermostat instance
        with patch.object(
            kumocloudv3.ThermostatClass, "_authenticate"
        ), patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            # Mock the _get_sites and _get_zones methods
            mock_sites = [{"id": "test_site_123"}]
            # type: ignore[attr-defined]
            thermostat._get_sites = MagicMock(return_value=mock_sites)
            # type: ignore[attr-defined]
            thermostat._get_zones = MagicMock(
                return_value=mock_zones_with_missing_names
            )

            # Call _populate_metadata
            # type: ignore[attr-defined]
            thermostat._populate_metadata(self.serial_num_lst)

            # Verify that Basement zone still got the correct serial
            self.assertEqual(
                kumocloudv3_config.metadata[1]["serial_number"],
                "SERIAL_BASEMENT_002",
                "Basement zone should still match by name",
            )

            # Other zones may not match due to missing names
            # This is acceptable fallback behavior

    def test_get_specific_zone_data_uses_metadata_serial(self):
        """
        Test that _get_specific_zone_data uses the serial number from
        metadata (populated by zone name matching), not from serial_num_lst
        by index.
        """
        # Setup metadata dict to simulate post-_populate_metadata state
        kumocloudv3_config.metadata.clear()
        kumocloudv3_config.metadata.update(
            copy.deepcopy(self.expected_metadata_structure)
        )

        # Manually populate with correct serial numbers by zone name
        kumocloudv3_config.metadata[0]["serial_number"] = "SERIAL_KITCHEN_001"
        kumocloudv3_config.metadata[1]["serial_number"] = "SERIAL_BASEMENT_002"
        kumocloudv3_config.metadata[2]["serial_number"] = "SERIAL_MAIN_003"

        # Create a mock thermostat instance for zone 2 (Main Living)
        with patch.object(
            kumocloudv3.ThermostatClass, "_authenticate"
        ), patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=2, verbose=False)

            # Mock get_raw_json to return zone data
            mock_raw_json = [
                {},  # token_info
                "",  # last_update
                {
                    "children": [
                        {
                            "zoneTable": {
                                "SERIAL_KITCHEN_001": {
                                    "label": "Kitchen",
                                    "reportedCondition": {"room_temp": 20.0},
                                },
                                "SERIAL_BASEMENT_002": {
                                    "label": "Basement",
                                    "reportedCondition": {"room_temp": 18.0},
                                },
                                "SERIAL_MAIN_003": {
                                    "label": "Main Living",
                                    "reportedCondition": {"room_temp": 22.0},
                                },
                            }
                        }
                    ]
                },
                "",  # device_token
            ]
            thermostat.get_raw_json = MagicMock(return_value=mock_raw_json)

            # Call _get_specific_zone_data for zone 2 (Main Living)
            # Pass serial_num_lst in API order (not zone index order)
            # type: ignore[attr-defined]
            result = thermostat._get_specific_zone_data(
                2, self.serial_num_lst
            )

            # Verify it returned Main Living's data (temp 22.0), not Kitchen's
            self.assertEqual(
                result["label"],
                "Main Living",
                "Should return Main Living data for zone 2",
            )
            self.assertEqual(
                result["reportedCondition"]["room_temp"],
                22.0,
                "Should return correct temperature for Main Living",
            )

            # Verify the serial_number was set correctly
            self.assertEqual(
                thermostat.serial_number,
                "SERIAL_MAIN_003",
                "Should use serial from metadata, not serial_num_lst[2]",
            )


@unittest.skipIf(
    kumocloudv3_import_error,
    "kumocloudv3 import failed, tests are disabled",
)
class AuthenticationUnitTest(utc.UnitTest):
    """
    Unit tests for authentication functionality.

    Tests authentication, token refresh, and authentication state management.
    """

    def setUp(self):
        """Setup for unit tests."""
        super().setUp()
        self.print_test_name()
        self.original_metadata = copy.deepcopy(kumocloudv3_config.metadata)

    def tearDown(self):
        """Cleanup after unit tests."""
        kumocloudv3_config.metadata.clear()
        kumocloudv3_config.metadata.update(self.original_metadata)
        super().tearDown()

    @patch("src.kumocloudv3.requests.Session")
    def test_authenticate_success(self, mock_session_class):
        """Test successful authentication with JWT tokens."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock successful auth response with nested token structure
        mock_response = Mock()
        mock_response.json.return_value = {
            "token": {
                "access": "test_access_token_123",
                "refresh": "test_refresh_token_456",
            }
        }
        mock_response.raise_for_status = Mock()
        mock_session.post.return_value = mock_response

        with patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            # Verify authentication succeeded
            self.assertTrue(thermostat._authenticated)  # type: ignore[attr-defined]
            self.assertEqual(thermostat.auth_token, "test_access_token_123")
            self.assertEqual(
                thermostat.refresh_token, "test_refresh_token_456"
            )

    @patch("src.kumocloudv3.requests.Session")
    def test_authenticate_top_level_tokens(self, mock_session_class):
        """Test authentication with top-level token structure."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock auth response with tokens at top level
        mock_response = Mock()
        mock_response.json.return_value = {
            "access": "top_level_access_token",
            "refresh": "top_level_refresh_token",
        }
        mock_response.raise_for_status = Mock()
        mock_session.post.return_value = mock_response

        with patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            self.assertTrue(thermostat._authenticated)  # type: ignore[attr-defined]
            self.assertEqual(
                thermostat.auth_token, "top_level_access_token"
            )
            self.assertEqual(
                thermostat.refresh_token, "top_level_refresh_token"
            )

    @patch("src.kumocloudv3.requests.Session")
    def test_authenticate_no_token(self, mock_session_class):
        """Test authentication failure when no token received."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock auth response without tokens
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()
        mock_session.post.return_value = mock_response

        with patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            # Should not raise during init, but store error
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            # Should not be authenticated
            self.assertFalse(thermostat._authenticated)  # type: ignore[attr-defined]
            # Should have stored error
            # type: ignore[attr-defined]
            self.assertIsNotNone(thermostat._authentication_error)

    @patch("src.kumocloudv3.requests.Session")
    def test_authenticate_request_exception(self, mock_session_class):
        """Test authentication failure with request exception."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock request exception
        mock_session.post.side_effect = requests.exceptions.ConnectionError(
            "Connection failed"
        )

        with patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            # Should not raise during init, but store error
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            # Should not be authenticated
            self.assertFalse(thermostat._authenticated)  # type: ignore[attr-defined]
            # Should have stored error
            # type: ignore[attr-defined]
            self.assertIsNotNone(thermostat._authentication_error)

    @patch("src.kumocloudv3.requests.Session")
    @patch("src.kumocloudv3.time.time")
    def test_refresh_auth_token_success(
        self, mock_time, mock_session_class
    ):
        """Test successful token refresh."""
        mock_time.return_value = 1000.0
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock session headers as a dict
        mock_session.headers = {"Authorization": "Bearer old_token"}

        # Mock initial authentication
        auth_response = Mock()
        auth_response.json.return_value = {
            "token": {"access": "initial_token", "refresh": "refresh_token"}
        }
        auth_response.raise_for_status = Mock()

        # Mock refresh response
        refresh_response = Mock()
        refresh_response.json.return_value = {
            "access": "new_access_token",
            "refresh": "new_refresh_token",
        }
        refresh_response.raise_for_status = Mock()

        mock_session.post.side_effect = [auth_response, refresh_response]

        with patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            # Call refresh
            result = thermostat._refresh_auth_token()  # type: ignore[attr-defined]

            # Verify refresh succeeded
            self.assertTrue(result)
            self.assertEqual(thermostat.auth_token, "new_access_token")
            self.assertEqual(thermostat.refresh_token, "new_refresh_token")

    @patch("src.kumocloudv3.requests.Session")
    @patch("src.kumocloudv3.time.time")
    def test_refresh_token_expired(self, mock_time, mock_session_class):
        """Test re-authentication when refresh token expired."""
        mock_time.return_value = 3000000.0  # Far in future
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock authentication responses
        auth_response = Mock()
        auth_response.json.return_value = {
            "token": {"access": "token", "refresh": "refresh"}
        }
        auth_response.raise_for_status = Mock()
        mock_session.post.return_value = auth_response

        with patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)
            thermostat.refresh_token_expires_at = 1000.0

            # Should trigger full re-authentication
            # type: ignore[attr-defined]
            result = thermostat._refresh_auth_token()
            self.assertTrue(result)

    @patch("src.kumocloudv3.requests.Session")
    @patch("src.kumocloudv3.time.time")
    def test_ensure_authenticated_not_authenticated(
        self, mock_time, mock_session_class
    ):
        """Test _ensure_authenticated when not authenticated."""
        mock_time.return_value = 1000.0
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock failed authentication
        mock_session.post.side_effect = requests.exceptions.ConnectionError(
            "Failed"
        )

        with patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            # Should raise authentication error
            with self.assertRaises(tc.AuthenticationError):
                # type: ignore[attr-defined]
                thermostat._ensure_authenticated()

    @patch("src.kumocloudv3.requests.Session")
    @patch("src.kumocloudv3.time.time")
    def test_ensure_authenticated_token_expired(
        self, mock_time, mock_session_class
    ):
        """Test _ensure_authenticated refreshes expired token."""
        current_time = 2000.0
        mock_time.return_value = current_time
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock session headers as a dict
        mock_session.headers = {"Authorization": "Bearer old_token"}

        # Mock authentication responses
        auth_response = Mock()
        auth_response.json.return_value = {
            "token": {"access": "token", "refresh": "refresh"}
        }
        auth_response.raise_for_status = Mock()

        refresh_response = Mock()
        refresh_response.json.return_value = {
            "access": "refreshed_token",
            "refresh": "new_refresh",
        }
        refresh_response.raise_for_status = Mock()

        mock_session.post.side_effect = [auth_response, refresh_response]

        with patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)
            # Set token to expired
            thermostat.token_expires_at = 1000.0

            # Should trigger refresh
            thermostat._ensure_authenticated()  # type: ignore[attr-defined]

            # Verify refresh was called
            self.assertEqual(mock_session.post.call_count, 2)


@unittest.skipIf(
    kumocloudv3_import_error,
    "kumocloudv3 import failed, tests are disabled",
)
class ApiRequestsUnitTest(utc.UnitTest):
    """
    Unit tests for API request methods.

    Tests _make_authenticated_request, _get_sites, _get_zones, _get_device.
    """

    def setUp(self):
        """Setup for unit tests."""
        super().setUp()
        self.print_test_name()
        self.original_metadata = copy.deepcopy(kumocloudv3_config.metadata)

    def tearDown(self):
        """Cleanup after unit tests."""
        kumocloudv3_config.metadata.clear()
        kumocloudv3_config.metadata.update(self.original_metadata)
        super().tearDown()

    @patch("src.kumocloudv3.requests.Session")
    def test_make_authenticated_request_success(self, mock_session_class):
        """Test successful authenticated request."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock authentication
        auth_response = Mock()
        auth_response.json.return_value = {
            "token": {"access": "token", "refresh": "refresh"}
        }
        auth_response.raise_for_status = Mock()

        # Mock API request
        api_response = Mock()
        api_response.status_code = 200
        api_response.json.return_value = {"data": "test"}
        api_response.raise_for_status = Mock()

        mock_session.post.return_value = auth_response
        mock_session.request.return_value = api_response

        with patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            # type: ignore[attr-defined]
            response = thermostat._make_authenticated_request(
                "GET", "https://test.com/api"
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"data": "test"})

    @patch("src.kumocloudv3.requests.Session")
    def test_make_authenticated_request_401_retry(
        self, mock_session_class
    ):
        """Test authenticated request retries on 401."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock session headers as a dict
        mock_session.headers = {"Authorization": "Bearer old_token"}

        # Mock authentication
        auth_response = Mock()
        auth_response.json.return_value = {
            "token": {"access": "token", "refresh": "refresh"}
        }
        auth_response.raise_for_status = Mock()

        # Mock 401 response then success
        first_response = Mock()
        first_response.status_code = 401

        second_response = Mock()
        second_response.status_code = 200
        second_response.raise_for_status = Mock()

        # Auth, first request (401), refresh, retry (200)
        refresh_response = Mock()
        refresh_response.json.return_value = {
            "access": "new_token",
            "refresh": "new_refresh",
        }
        refresh_response.raise_for_status = Mock()

        mock_session.post.side_effect = [
            auth_response,
            refresh_response,
        ]
        mock_session.request.side_effect = [
            first_response,
            second_response,
        ]

        with patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            # type: ignore[attr-defined]
            response = thermostat._make_authenticated_request(
                "GET", "https://test.com/api"
            )

            # Should have retried and succeeded
            self.assertEqual(response.status_code, 200)
            self.assertEqual(mock_session.request.call_count, 2)

    @patch("src.kumocloudv3.requests.Session")
    def test_get_sites_success(self, mock_session_class):
        """Test _get_sites returns site list."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock authentication
        auth_response = Mock()
        auth_response.json.return_value = {
            "token": {"access": "token", "refresh": "refresh"}
        }
        auth_response.raise_for_status = Mock()
        mock_session.post.return_value = auth_response

        # Mock sites response
        sites_response = Mock()
        sites_response.status_code = 200
        sites_response.json.return_value = [
            {"id": "site1", "name": "Home"}
        ]
        sites_response.raise_for_status = Mock()
        mock_session.request.return_value = sites_response

        with patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            sites = thermostat._get_sites()  # type: ignore[attr-defined]

            self.assertEqual(len(sites), 1)
            self.assertEqual(sites[0]["id"], "site1")

    @patch("src.kumocloudv3.requests.Session")
    @patch("src.kumocloudv3.time.time")
    def test_get_sites_cached(self, mock_time, mock_session_class):
        """Test _get_sites uses cached data."""
        mock_time.return_value = 1000.0
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock authentication
        auth_response = Mock()
        auth_response.json.return_value = {
            "token": {"access": "token", "refresh": "refresh"}
        }
        auth_response.raise_for_status = Mock()
        mock_session.post.return_value = auth_response

        # Mock sites response
        sites_response = Mock()
        sites_response.json.return_value = [{"id": "site1"}]
        sites_response.raise_for_status = Mock()
        mock_session.request.return_value = sites_response

        with patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            # First call - should make request
            sites1 = thermostat._get_sites()  # type: ignore[attr-defined]

            # Second call - should use cache
            mock_time.return_value = 1100.0  # Within cache duration
            sites2 = thermostat._get_sites()  # type: ignore[attr-defined]

            # Should be same data
            self.assertEqual(sites1, sites2)
            # Should have only made one API request
            self.assertEqual(mock_session.request.call_count, 1)

    @patch("src.kumocloudv3.requests.Session")
    def test_get_zones_success(self, mock_session_class):
        """Test _get_zones returns zone list."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock authentication
        auth_response = Mock()
        auth_response.json.return_value = {
            "token": {"access": "token", "refresh": "refresh"}
        }
        auth_response.raise_for_status = Mock()
        mock_session.post.return_value = auth_response

        # Mock zones response
        zones_response = Mock()
        zones_response.status_code = 200
        zones_response.json.return_value = [
            {"name": "Kitchen", "adapter": {"deviceSerial": "SERIAL1"}}
        ]
        zones_response.raise_for_status = Mock()
        mock_session.request.return_value = zones_response

        with patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            zones = thermostat._get_zones("site123")  # type: ignore[attr-defined]

            self.assertEqual(len(zones), 1)
            self.assertEqual(zones[0]["name"], "Kitchen")

    @patch("src.kumocloudv3.requests.Session")
    def test_get_device_success(self, mock_session_class):
        """Test _get_device returns device data."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock authentication
        auth_response = Mock()
        auth_response.json.return_value = {
            "token": {"access": "token", "refresh": "refresh"}
        }
        auth_response.raise_for_status = Mock()
        mock_session.post.return_value = auth_response

        # Mock device response
        device_response = Mock()
        device_response.status_code = 200
        device_response.json.return_value = {
            "roomTemp": 22.0,
            "power": True,
        }
        device_response.raise_for_status = Mock()
        mock_session.request.return_value = device_response

        with patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            device = thermostat._get_device("SERIAL123")  # type: ignore[attr-defined]

            self.assertEqual(device["roomTemp"], 22.0)
            self.assertTrue(device["power"])


@unittest.skipIf(
    kumocloudv3_import_error,
    "kumocloudv3 import failed, tests are disabled",
)
class ZoneAssignmentUnitTest(utc.UnitTest):
    """
    Unit tests for zone assignment functionality.

    Tests _update_zone_assignments and related helper methods.
    """

    def setUp(self):
        """Setup for unit tests."""
        super().setUp()
        self.print_test_name()
        self.original_metadata = copy.deepcopy(kumocloudv3_config.metadata)

    def tearDown(self):
        """Cleanup after unit tests."""
        kumocloudv3_config.metadata.clear()
        kumocloudv3_config.metadata.update(self.original_metadata)
        super().tearDown()

    def test_build_zone_name_mapping(self):
        """Test building zone name to index mapping."""
        zones = [
            {"name": "Kitchen"},
            {"name": "Basement"},
            {"name": "Main Living"},
        ]

        with patch.object(
            kumocloudv3.ThermostatClass, "_authenticate"
        ), patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            # type: ignore[attr-defined]
            mapping = thermostat._build_zone_name_mapping(zones)

            self.assertEqual(mapping["Kitchen"], 0)
            self.assertEqual(mapping["Basement"], 1)
            self.assertEqual(mapping["Main Living"], 2)

    def test_build_zone_name_mapping_empty_names(self):
        """Test mapping handles empty zone names."""
        zones = [
            {"name": ""},
            {"name": "Kitchen"},
            {},
        ]

        with patch.object(
            kumocloudv3.ThermostatClass, "_authenticate"
        ), patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            # type: ignore[attr-defined]
            mapping = thermostat._build_zone_name_mapping(zones)

            # Only Kitchen should be in mapping
            self.assertEqual(len(mapping), 1)
            self.assertEqual(mapping["Kitchen"], 1)

    def test_find_zone_indices_by_patterns(self):
        """Test finding zones by naming patterns."""
        zone_mapping = {
            "Main Living Room": 0,
            "Kitchen Area": 1,
            "Basement Suite": 2,
        }

        with patch.object(
            kumocloudv3.ThermostatClass, "_authenticate"
        ), patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            main, kitchen, basement = (
                # type: ignore[attr-defined]
                thermostat._find_zone_indices_by_patterns(zone_mapping)
            )

            self.assertEqual(main, 0)
            self.assertEqual(kitchen, 1)
            self.assertEqual(basement, 2)

    def test_find_zone_indices_partial_match(self):
        """Test finding zones with only partial matches."""
        zone_mapping = {
            "First Floor": 0,
            "Office": 1,
        }

        with patch.object(
            kumocloudv3.ThermostatClass, "_authenticate"
        ), patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            main, kitchen, basement = (
                # type: ignore[attr-defined]
                thermostat._find_zone_indices_by_patterns(zone_mapping)
            )

            # First Floor matches "main" pattern
            self.assertEqual(main, 0)
            self.assertIsNone(kitchen)
            self.assertIsNone(basement)

    @patch("src.kumocloudv3.requests.Session")
    def test_update_zone_assignments_success(self, mock_session_class):
        """Test successful zone assignment update."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock authentication
        auth_response = Mock()
        auth_response.json.return_value = {
            "token": {"access": "token", "refresh": "refresh"}
        }
        auth_response.raise_for_status = Mock()
        mock_session.post.return_value = auth_response

        # Mock API responses
        sites_response = Mock()
        sites_response.json.return_value = [{"id": "site1"}]
        sites_response.raise_for_status = Mock()

        zones_response = Mock()
        zones_response.json.return_value = [
            {"name": "Main Living"},
            {"name": "Kitchen"},
            {"name": "Basement"},
        ]
        zones_response.raise_for_status = Mock()

        mock_session.request.side_effect = [
            sites_response,
            zones_response,
        ]

        _ = kumocloudv3.ThermostatClass(zone=0, verbose=False)

        # Verify zone assignments were updated
        self.assertEqual(kumocloudv3_config.MAIN_LIVING, 0)
        self.assertEqual(kumocloudv3_config.KITCHEN, 1)
        self.assertEqual(kumocloudv3_config.BASEMENT, 2)

    @patch("src.kumocloudv3.requests.Session")
    def test_update_zone_assignments_api_error(self, mock_session_class):
        """Test zone assignment handles API errors gracefully."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock authentication
        auth_response = Mock()
        auth_response.json.return_value = {
            "token": {"access": "token", "refresh": "refresh"}
        }
        auth_response.raise_for_status = Mock()
        mock_session.post.return_value = auth_response

        # Mock API error
        mock_session.request.side_effect = requests.exceptions.RequestException(
            "API Error"
        )

        # Should not raise, should use fallback
        _ = kumocloudv3.ThermostatClass(zone=0, verbose=False)

        # Should complete without exception
        # (Test passes if no exception raised)


@unittest.skipIf(
    kumocloudv3_import_error,
    "kumocloudv3 import failed, tests are disabled",
)
class GetMetadataUnitTest(utc.UnitTest):
    """
    Unit tests for metadata retrieval methods.

    Tests get_metadata, get_indoor_units, get_raw_json.
    """

    def setUp(self):
        """Setup for unit tests."""
        super().setUp()
        self.print_test_name()
        self.original_metadata = copy.deepcopy(kumocloudv3_config.metadata)

    def tearDown(self):
        """Cleanup after unit tests."""
        kumocloudv3_config.metadata.clear()
        kumocloudv3_config.metadata.update(self.original_metadata)
        super().tearDown()

    @patch("src.kumocloudv3.requests.Session")
    def test_get_indoor_units_success(self, mock_session_class):
        """Test get_indoor_units returns serial numbers."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock authentication
        auth_response = Mock()
        auth_response.json.return_value = {
            "token": {"access": "token", "refresh": "refresh"}
        }
        auth_response.raise_for_status = Mock()
        mock_session.post.return_value = auth_response

        # Mock API responses
        sites_response = Mock()
        sites_response.json.return_value = [{"id": "site1"}]
        sites_response.raise_for_status = Mock()

        zones_response = Mock()
        zones_response.json.return_value = [
            {"adapter": {"deviceSerial": "SERIAL1"}},
            {"adapter": {"deviceSerial": "SERIAL2"}},
        ]
        zones_response.raise_for_status = Mock()

        mock_session.request.side_effect = [
            sites_response,
            zones_response,
            sites_response,
            zones_response,
        ]

        with patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            serials = thermostat.get_indoor_units()

            self.assertEqual(len(serials), 2)
            self.assertIn("SERIAL1", serials)
            self.assertIn("SERIAL2", serials)

    @patch("src.kumocloudv3.requests.Session")
    def test_get_indoor_units_auth_error(self, mock_session_class):
        """Test get_indoor_units handles auth errors."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock authentication
        auth_response = Mock()
        auth_response.json.return_value = {
            "token": {"access": "token", "refresh": "refresh"}
        }
        auth_response.raise_for_status = Mock()
        mock_session.post.return_value = auth_response

        # Mock API error
        mock_session.request.side_effect = requests.exceptions.RequestException(
            "Auth Error"
        )

        with patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            with self.assertRaises(tc.AuthenticationError):
                thermostat.get_indoor_units()

    def test_get_zone_index_from_name(self):
        """Test getting zone index from zone name."""
        kumocloudv3_config.metadata.clear()
        kumocloudv3_config.metadata.update({
            0: {"zone_name": "Kitchen"},
            1: {"zone_name": "Basement"},
        })

        with patch.object(
            kumocloudv3.ThermostatClass, "_authenticate"
        ), patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)
            thermostat.zone_name = "Basement"

            index = thermostat.get_zone_index_from_name()

            self.assertEqual(index, 1)

    def test_get_zone_index_from_name_not_found(self):
        """Test getting zone index with invalid zone name."""
        kumocloudv3_config.metadata.clear()
        kumocloudv3_config.metadata.update({
            0: {"zone_name": "Kitchen"},
        })

        with patch.object(
            kumocloudv3.ThermostatClass, "_authenticate"
        ), patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)
            thermostat.zone_name = "NonExistent"

            with self.assertRaises(ValueError) as context:
                thermostat.get_zone_index_from_name()

            self.assertIn("not found", str(context.exception))

    def test_process_raw_data_with_parameter(self):
        """Test _process_raw_data extracts specific parameter."""
        raw_json = {
            "label": "Kitchen",
            "reportedCondition": {"room_temp": 22.0},
        }

        with patch.object(
            kumocloudv3.ThermostatClass, "_authenticate"
        ), patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            result = thermostat._process_raw_data(  # type: ignore[attr-defined]
                raw_json, "label", zone=0
            )

            self.assertEqual(result, "Kitchen")

    def test_process_raw_data_missing_parameter(self):
        """Test _process_raw_data with missing parameter."""
        raw_json = {"label": "Kitchen"}

        with patch.object(
            kumocloudv3.ThermostatClass, "_authenticate"
        ), patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            result = thermostat._process_raw_data(  # type: ignore[attr-defined]
                raw_json, "nonexistent", zone=0
            )

            # Should return None for missing parameters
            self.assertIsNone(result)

    def test_process_raw_data_auth_failed(self):
        """Test _process_raw_data with authentication failure."""
        raw_json = {"authentication_status": "failed", "zones": []}

        with patch.object(
            kumocloudv3.ThermostatClass, "_authenticate"
        ), patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            result = thermostat._process_raw_data(  # type: ignore[attr-defined]
                raw_json, "address", zone=0
            )

            # Should return mock value
            self.assertEqual(result, "127.0.0.1")


@unittest.skipIf(
    kumocloudv3_import_error,
    "kumocloudv3 import failed, tests are disabled",
)
class ThermostatZoneUnitTest(utc.UnitTest):
    """
    Unit tests for ThermostatZone class.

    Tests zone parameter retrieval and mode detection methods.
    """

    def setUp(self):
        """Setup for unit tests."""
        super().setUp()
        self.print_test_name()
        self.original_metadata = copy.deepcopy(kumocloudv3_config.metadata)

    def tearDown(self):
        """Cleanup after unit tests."""
        kumocloudv3_config.metadata.clear()
        kumocloudv3_config.metadata.update(self.original_metadata)
        super().tearDown()

    def _create_mock_thermostat(self, zone_info):
        """Helper to create mock thermostat with zone info."""
        # Ensure zone_info always has a label for get_zone_name()
        if "label" not in zone_info:
            zone_info["label"] = "Test Zone"

        mock_thermostat = Mock()
        mock_thermostat.device_id = 0
        mock_thermostat.zone_number = 0
        mock_thermostat.get_all_metadata.return_value = zone_info
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        return mock_thermostat

    def test_get_parameter_simple(self):
        """Test get_parameter with simple key."""
        zone_info = {"label": "Kitchen", "address": "192.168.1.100"}

        mock_thermostat = self._create_mock_thermostat(zone_info)
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.get_parameter("label")
        self.assertEqual(result, "Kitchen")

    def test_get_parameter_nested(self):
        """Test get_parameter with nested keys."""
        zone_info = {
            "reportedCondition": {"room_temp": 22.0, "humidity": 50}
        }

        mock_thermostat = self._create_mock_thermostat(zone_info)
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.get_parameter("room_temp", "reportedCondition")
        self.assertEqual(result, 22.0)

    def test_get_parameter_deeply_nested(self):
        """Test get_parameter with deeply nested keys."""
        zone_info = {
            "status_display": {
                "reportedCondition": {"defrost": 1, "standby": 0}
            }
        }

        mock_thermostat = self._create_mock_thermostat(zone_info)
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.get_parameter(
            "defrost", "reportedCondition", "status_display"
        )
        self.assertEqual(result, 1)

    def test_get_parameter_with_default(self):
        """Test get_parameter returns default on error."""
        zone_info = {"label": "Kitchen"}

        mock_thermostat = self._create_mock_thermostat(zone_info)
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.get_parameter(
            "nonexistent", default_val="default_value"
        )
        self.assertEqual(result, "default_value")

    def test_get_parameter_auth_failed(self):
        """Test get_parameter with authentication failure."""
        zone_info = {"authentication_status": "failed"}

        mock_thermostat = self._create_mock_thermostat(zone_info)
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.get_parameter("label")
        # Should return mock zone name
        self.assertEqual(result, "Zone_0")

    def test_get_display_temp(self):
        """Test get_display_temp converts Celsius to Fahrenheit."""
        zone_info = {"reportedCondition": {"room_temp": 20.0}}

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        temp = zone.get_display_temp()
        # 20°C = 68°F
        self.assertAlmostEqual(temp, 68.0, places=1)

    def test_get_display_humidity_supported(self):
        """Test get_display_humidity when supported."""
        zone_info = {
            "reportedCondition": {"humidity": 50},
            "inputs": {"acoilSettings": {"humidistat": 1}},
        }

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        humidity = zone.get_display_humidity()
        # Should return converted value
        self.assertIsNotNone(humidity)

    def test_get_display_humidity_not_supported(self):
        """Test get_display_humidity when not supported."""
        zone_info = {
            "inputs": {"acoilSettings": {"humidistat": 0}},
        }

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        humidity = zone.get_display_humidity()
        self.assertIsNone(humidity)

    def test_is_heat_mode(self):
        """Test is_heat_mode detection."""
        zone_info = {
            "reportedCondition": {"operation_mode": 1, "power": 1}
        }

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.is_heat_mode()
        self.assertEqual(result, 1)

    def test_is_cool_mode(self):
        """Test is_cool_mode detection."""
        zone_info = {
            "reportedCondition": {"operation_mode": 3, "power": 1}
        }

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.is_cool_mode()
        self.assertEqual(result, 1)

    def test_is_fan_mode(self):
        """Test is_fan_mode detection."""
        zone_info = {
            "reportedCondition": {"operation_mode": 7, "power": 1}
        }

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.is_fan_mode()
        self.assertEqual(result, 1)

    def test_is_off_mode(self):
        """Test is_off_mode detection."""
        zone_info = {
            "reportedCondition": {"operation_mode": 16, "power": 0}
        }

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.is_off_mode()
        self.assertEqual(result, 1)

    def test_is_power_on(self):
        """Test is_power_on returns correct value."""
        zone_info = {"reportedCondition": {"power": 1}}

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.is_power_on()
        self.assertEqual(result, 1)

    def test_is_fan_on_numeric_speed(self):
        """Test is_fan_on with numeric fan speed."""
        zone_info = {
            "reportedCondition": {
                "power": 1,
                "fan_speed": 3,
                "more": {"fan_speed_text": "on"},
            }
        }

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.is_fan_on()
        self.assertEqual(result, 1)

    def test_is_fan_on_string_auto(self):
        """Test is_fan_on with auto fan speed."""
        zone_info = {
            "reportedCondition": {
                "power": 1,
                "fan_speed": "auto",
                "more": {"fan_speed_text": "on"},
            }
        }

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.is_fan_on()
        self.assertEqual(result, 1)

    def test_is_fan_on_off(self):
        """Test is_fan_on when fan is off."""
        zone_info = {
            "reportedCondition": {
                "power": 1,
                "fan_speed": 0,
                "more": {"fan_speed_text": "off"},
            }
        }

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.is_fan_on()
        self.assertEqual(result, 0)

    def test_is_heating(self):
        """Test is_heating logic."""
        zone_info = {
            "reportedCondition": {
                "operation_mode": 1,
                "power": 1,
                "room_temp": 18.0,
                "sp_heat": 20.0,
            }
        }

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        # Temp below setpoint, should be heating
        result = zone.is_heating()
        self.assertEqual(result, 1)

    def test_is_cooling(self):
        """Test is_cooling logic."""
        zone_info = {
            "reportedCondition": {
                "operation_mode": 3,
                "power": 1,
                "room_temp": 26.0,
                "sp_cool": 24.0,
            }
        }

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        # Temp above setpoint, should be cooling
        result = zone.is_cooling()
        self.assertEqual(result, 1)

    def test_get_heat_setpoint_raw(self):
        """Test get_heat_setpoint_raw conversion."""
        zone_info = {"reportedCondition": {"sp_heat": 20.0}}

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        setpoint = zone.get_heat_setpoint_raw()
        # 20°C = 68°F
        self.assertAlmostEqual(setpoint, 68.0, places=1)

    def test_get_cool_setpoint_raw(self):
        """Test get_cool_setpoint_raw conversion."""
        zone_info = {"reportedCondition": {"sp_cool": 24.0}}

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        setpoint = zone.get_cool_setpoint_raw()
        # 24°C = 75.2°F
        self.assertAlmostEqual(setpoint, 75.2, places=1)

    def test_get_system_switch_position_off(self):
        """Test get_system_switch_position when power off."""
        zone_info = {"reportedCondition": {"power": 0}}

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        position = zone.get_system_switch_position()
        # Should return off mode value
        self.assertEqual(position, 16)

    def test_get_system_switch_position_on(self):
        """Test get_system_switch_position when power on."""
        zone_info = {
            "reportedCondition": {"power": 1, "operation_mode": 3}
        }

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        position = zone.get_system_switch_position()
        self.assertEqual(position, 3)

    def test_get_wifi_strength(self):
        """Test get_wifi_strength returns rssi value."""
        zone_info = {"rssi": {"rssi": -50.0}}

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        strength = zone.get_wifi_strength()
        self.assertEqual(strength, -50.0)

    def test_get_wifi_status_good(self):
        """Test get_wifi_status with good signal."""
        zone_info = {"rssi": {"rssi": -50.0}}

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        status = zone.get_wifi_status()
        self.assertTrue(status)

    def test_get_battery_voltage(self):
        """Test get_battery_voltage returns line power value."""
        zone_info = {"rssi": {"rssi": -50.0}}

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        voltage = zone.get_battery_voltage()
        self.assertEqual(voltage, 120.0)

    def test_is_drying(self):
        """Test is_drying logic."""
        zone_info = {
            "reportedCondition": {
                "operation_mode": 2,
                "power": 1,
                "room_temp": 26.0,
                "sp_cool": 24.0,
            }
        }

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.is_drying()
        self.assertEqual(result, 1)

    def test_is_auto(self):
        """Test is_auto logic."""
        zone_info = {
            "reportedCondition": {
                "operation_mode": 5,
                "power": 1,
                "room_temp": 20.0,
                "sp_heat": 22.0,
                "sp_cool": 18.0,
            }
        }

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.is_auto()
        self.assertEqual(result, 1)

    def test_is_eco(self):
        """Test is_eco logic."""
        zone_info = {
            "reportedCondition": {
                "power": 1,
                "room_temp": 26.0,
                "sp_cool": 24.0,
                "sp_heat": 18.0,
            },
            "reportedInitialSettings": {"energy_save": 1},
        }

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.is_eco()
        self.assertEqual(result, 1)

    def test_is_fanning(self):
        """Test is_fanning logic."""
        zone_info = {
            "reportedCondition": {
                "power": 1,
                "fan_speed": 3,
                "more": {"fan_speed_text": "on"},
            }
        }

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.is_fanning()
        self.assertEqual(result, 1)

    def test_is_defrosting(self):
        """Test is_defrosting returns correct value."""
        zone_info = {
            "reportedCondition": {
                "status_display": {"defrost": 1}
            }
        }

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.is_defrosting()
        self.assertEqual(result, 1)

    def test_is_standby(self):
        """Test is_standby returns correct value."""
        zone_info = {
            "reportedCondition": {
                "status_display": {"standby": 1}
            }
        }

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.is_standby()
        self.assertEqual(result, 1)

    def test_get_heat_setpoint(self):
        """Test get_heat_setpoint with units."""
        zone_info = {"reportedCondition": {"sp_heat": 20.0}}

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        setpoint = zone.get_heat_setpoint()
        # Should include units
        self.assertIsInstance(setpoint, str)

    def test_get_cool_setpoint(self):
        """Test get_cool_setpoint with units."""
        zone_info = {"reportedCondition": {"sp_cool": 24.0}}

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        setpoint = zone.get_cool_setpoint()
        # Should include units
        self.assertIsInstance(setpoint, str)

    def test_get_schedule_heat_sp(self):
        """Test get_schedule_heat_sp returns max setpoint."""
        zone_info = {}

        mock_thermostat = self._create_mock_thermostat(zone_info)
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        sp = zone.get_schedule_heat_sp()
        self.assertEqual(sp, kumocloudv3_config.MAX_HEAT_SETPOINT)

    def test_get_schedule_cool_sp(self):
        """Test get_schedule_cool_sp returns min setpoint."""
        zone_info = {}

        mock_thermostat = self._create_mock_thermostat(zone_info)
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        sp = zone.get_schedule_cool_sp()
        self.assertEqual(sp, kumocloudv3_config.MIN_COOL_SETPOINT)

    def test_get_is_invacation_hold_mode(self):
        """Test get_is_invacation_hold_mode returns False."""
        zone_info = {}

        mock_thermostat = self._create_mock_thermostat(zone_info)
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.get_is_invacation_hold_mode()
        self.assertFalse(result)

    def test_get_vacation_hold(self):
        """Test get_vacation_hold returns False."""
        zone_info = {}

        mock_thermostat = self._create_mock_thermostat(zone_info)
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.get_vacation_hold()
        self.assertFalse(result)

    def test_get_battery_status(self):
        """Test get_battery_status returns True for line power."""
        zone_info = {"rssi": {"rssi": -50.0}}

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        status = zone.get_battery_status()
        self.assertTrue(status)

    def test_set_heat_setpoint_not_implemented(self):
        """Test set_heat_setpoint logs warning."""
        zone_info = {}

        mock_thermostat = self._create_mock_thermostat(zone_info)
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        # Should not raise, just log warning
        zone.set_heat_setpoint(70)

    def test_set_cool_setpoint_not_implemented(self):
        """Test set_cool_setpoint logs warning."""
        zone_info = {}

        mock_thermostat = self._create_mock_thermostat(zone_info)
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        # Should not raise, just log warning
        zone.set_cool_setpoint(72)

    def test_refresh_zone_info_force(self):
        """Test refresh_zone_info with force_refresh."""
        zone_info = {"label": "Kitchen"}
        updated_info = {"label": "Kitchen Updated"}

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat.get_all_metadata.side_effect = [
            zone_info,
            zone_info,  # Called again during get_zone_name
            updated_info,
        ]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        # Force refresh
        zone.refresh_zone_info(force_refresh=True)

        # Should have called get_all_metadata three times
        # (once in init, once in get_zone_name, once in refresh)
        self.assertEqual(mock_thermostat.get_all_metadata.call_count, 3)

    def test_refresh_zone_info_with_exception(self):
        """Test refresh_zone_info handles exceptions."""
        zone_info = {"label": "Kitchen"}

        mock_thermostat = self._create_mock_thermostat(zone_info)
        mock_thermostat.get_all_metadata.side_effect = [
            zone_info,
            zone_info,
            Exception("API Error"),
        ]
        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        # Should not raise, just log warning
        zone.refresh_zone_info(force_refresh=True)


@unittest.skipIf(
    kumocloudv3_import_error,
    "kumocloudv3 import failed, tests are disabled",
)
class RawJsonAndConversionUnitTest(utc.UnitTest):
    """
    Unit tests for get_raw_json and device conversion methods.
    """

    def setUp(self):
        """Setup for unit tests."""
        super().setUp()
        self.print_test_name()
        self.original_metadata = copy.deepcopy(kumocloudv3_config.metadata)

    def tearDown(self):
        """Cleanup after unit tests."""
        kumocloudv3_config.metadata.clear()
        kumocloudv3_config.metadata.update(self.original_metadata)
        super().tearDown()

    @patch("src.kumocloudv3.requests.Session")
    def test_get_raw_json_success(self, mock_session_class):
        """Test get_raw_json returns legacy format."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock authentication
        auth_response = Mock()
        auth_response.json.return_value = {
            "token": {"access": "token", "refresh": "refresh"}
        }
        auth_response.raise_for_status = Mock()
        mock_session.post.return_value = auth_response

        # Mock sites response
        sites_response = Mock()
        sites_response.status_code = 200
        sites_response.json.return_value = [{"id": "site1"}]
        sites_response.raise_for_status = Mock()

        # Mock zones response
        zones_response = Mock()
        zones_response.status_code = 200
        zones_response.json.return_value = [
            {
                "name": "Kitchen",
                "adapter": {"deviceSerial": "SERIAL1"},
            }
        ]
        zones_response.raise_for_status = Mock()

        # Mock device response
        device_response = Mock()
        device_response.status_code = 200
        device_response.json.return_value = {
            "roomTemp": 22.0,
            "spHeat": 20.0,
            "spCool": 24.0,
            "operationMode": 3,
            "power": True,
            "fanSpeed": 3,
            "humidity": 50,
            "macAddress": "AA:BB:CC:DD:EE:FF",
        }
        device_response.raise_for_status = Mock()

        # Responses for: sites, zones for _update_zone_assignments,
        # then sites, zones, device for get_raw_json
        mock_session.request.side_effect = [
            sites_response,
            zones_response,
            sites_response,
            zones_response,
            device_response,
        ]

        thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

        raw_json = thermostat.get_raw_json()

        # Verify legacy format structure
        self.assertEqual(len(raw_json), 4)
        self.assertIn("token", raw_json[0])
        self.assertIsInstance(raw_json[1], str)  # timestamp
        self.assertIn("children", raw_json[2])
        self.assertIsInstance(raw_json[3], str)  # device_token

    def test_convert_device_to_legacy_format(self):
        """Test _convert_device_to_legacy_format conversion."""
        device = {
            "roomTemp": 22.0,
            "spHeat": 20.0,
            "spCool": 24.0,
            "operationMode": 3,
            "power": True,
            "fanSpeed": 3,
            "humidity": 50,
            "macAddress": "AA:BB:CC:DD:EE:FF",
            "energySave": False,
            "hasHumiditySensor": True,
            "rssi": -45,
            "displayConfig": {"defrost": False, "standby": False},
        }

        zone = {"name": "Kitchen"}

        with patch.object(
            kumocloudv3.ThermostatClass, "_authenticate"
        ), patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            legacy = thermostat._convert_device_to_legacy_format(
                device, zone
            )

            # Verify legacy format fields
            self.assertEqual(legacy["label"], "Kitchen")
            self.assertEqual(legacy["address"], "AA:BB:CC:DD:EE:FF")
            self.assertEqual(
                legacy["reportedCondition"]["room_temp"], 22.0
            )
            self.assertEqual(legacy["reportedCondition"]["sp_heat"], 20.0)
            self.assertEqual(legacy["reportedCondition"]["sp_cool"], 24.0)
            self.assertEqual(
                legacy["reportedCondition"]["operation_mode"], 3
            )
            self.assertEqual(legacy["reportedCondition"]["power"], 1)
            self.assertEqual(legacy["reportedCondition"]["fan_speed"], 3)
            self.assertEqual(legacy["reportedCondition"]["humidity"], 50)
            self.assertEqual(
                legacy["reportedInitialSettings"]["energy_save"], 0
            )

    def test_convert_device_to_legacy_format_fan_speed_zero(self):
        """Test conversion with fan_speed of zero."""
        device = {
            "roomTemp": 22.0,
            "fanSpeed": 0,
        }
        zone = {"name": "Test"}

        with patch.object(
            kumocloudv3.ThermostatClass, "_authenticate"
        ), patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            legacy = thermostat._convert_device_to_legacy_format(
                device, zone
            )

            # Fan speed 0 should be "off"
            self.assertEqual(
                legacy["reportedCondition"]["more"]["fan_speed_text"], "off"
            )

    def test_convert_device_to_legacy_format_fan_speed_on(self):
        """Test conversion with fan_speed greater than zero."""
        device = {
            "roomTemp": 22.0,
            "fanSpeed": 3,
        }
        zone = {"name": "Test"}

        with patch.object(
            kumocloudv3.ThermostatClass, "_authenticate"
        ), patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            legacy = thermostat._convert_device_to_legacy_format(
                device, zone
            )

            # Fan speed > 0 should be "on"
            self.assertEqual(
                legacy["reportedCondition"]["more"]["fan_speed_text"], "on"
            )


@unittest.skipIf(
    kumocloudv3_import_error,
    "kumocloudv3 import failed, tests are disabled",
)
class ErrorHandlingUnitTest(utc.UnitTest):
    """
    Unit tests for error handling and edge cases.
    """

    def setUp(self):
        """Setup for unit tests."""
        super().setUp()
        self.print_test_name()
        self.original_metadata = copy.deepcopy(kumocloudv3_config.metadata)

    def tearDown(self):
        """Cleanup after unit tests."""
        kumocloudv3_config.metadata.clear()
        kumocloudv3_config.metadata.update(self.original_metadata)
        super().tearDown()

    def test_get_target_zone_id(self):
        """Test get_target_zone_id returns zone value."""
        with patch.object(
            kumocloudv3.ThermostatClass, "_authenticate"
        ), patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            zone_id = thermostat.get_target_zone_id(5)
            self.assertEqual(zone_id, 5)

    def test_validate_serial_numbers_empty_authenticated(self):
        """Test _validate_serial_numbers with empty list but authenticated."""
        with patch.object(
            kumocloudv3.ThermostatClass, "_authenticate"
        ), patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)
            thermostat._authenticated = True  # type: ignore[attr-defined]

            # Should raise AuthenticationError
            with self.assertRaises(tc.AuthenticationError):
                thermostat._validate_serial_numbers([])

    @patch("src.kumocloudv3.requests.Session")
    def test_get_specific_zone_data_by_name(self, mock_session_class):
        """Test _get_specific_zone_data with zone name."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Setup metadata
        kumocloudv3_config.metadata.clear()
        kumocloudv3_config.metadata.update({
            0: {"zone_name": "Kitchen", "serial_number": "SERIAL1"}
        })

        # Mock authentication
        auth_response = Mock()
        auth_response.json.return_value = {
            "token": {"access": "token", "refresh": "refresh"}
        }
        auth_response.raise_for_status = Mock()
        mock_session.post.return_value = auth_response

        with patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            # Mock get_raw_json
            mock_raw = [
                {},
                "",
                {
                    "children": [
                        {"zoneTable": {"SERIAL1": {"label": "Kitchen"}}}
                    ]
                },
                "",
            ]
            thermostat.get_raw_json = Mock(return_value=mock_raw)

            result = thermostat._get_specific_zone_data(
                "Kitchen", ["SERIAL1"]
            )

            self.assertEqual(result["label"], "Kitchen")

    def test_print_all_thermostat_metadata(self):
        """Test print_all_thermostat_metadata doesn't raise."""
        with patch.object(
            kumocloudv3.ThermostatClass, "_authenticate"
        ), patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ), patch.object(
            kumocloudv3.ThermostatClass, "get_all_metadata"
        ) as mock_metadata, patch.object(
            kumocloudv3.ThermostatClass,
            "exec_print_all_thermostat_metadata",
        ):
            mock_metadata.return_value = {"test": "data"}
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            # Should not raise
            thermostat.print_all_thermostat_metadata(0)

    @patch("src.kumocloudv3.requests.Session")
    def test_assign_serials_sequentially(self, mock_session_class):
        """Test _assign_serials_sequentially fallback method."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock authentication
        auth_response = Mock()
        auth_response.json.return_value = {
            "token": {"access": "token", "refresh": "refresh"}
        }
        auth_response.raise_for_status = Mock()
        mock_session.post.return_value = auth_response

        # Setup metadata
        kumocloudv3_config.metadata.clear()
        kumocloudv3_config.metadata.update({
            0: {"zone_name": "Zone 0", "serial_number": None},
            1: {"zone_name": "Zone 1", "serial_number": None},
        })

        with patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            serials = ["SERIAL1", "SERIAL2"]
            thermostat._assign_serials_sequentially(serials)

            # Verify sequential assignment
            self.assertEqual(
                kumocloudv3_config.metadata[0]["serial_number"], "SERIAL1"
            )
            self.assertEqual(
                kumocloudv3_config.metadata[1]["serial_number"], "SERIAL2"
            )

    def test_thermostat_zone_get_mock_value_for_failed_auth_temp(self):
        """Test _get_mock_value_for_failed_auth with temp key."""
        zone_info = {"authentication_status": "failed"}

        mock_thermostat = Mock()
        mock_thermostat.device_id = 0
        mock_thermostat.zone_number = 0
        mock_thermostat.get_all_metadata.return_value = zone_info
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]

        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        # Request temperature parameter when auth failed
        result = zone.get_parameter("temp", default_val=None)

        # Should return bogus int for temp
        self.assertEqual(result, util.BOGUS_INT)

    def test_thermostat_zone_get_mock_value_for_failed_auth_humidity(
        self,
    ):
        """Test _get_mock_value_for_failed_auth with humidity key."""
        zone_info = {"authentication_status": "failed"}

        mock_thermostat = Mock()
        mock_thermostat.device_id = 0
        mock_thermostat.zone_number = 0
        mock_thermostat.get_all_metadata.return_value = zone_info
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]

        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.get_parameter("humidity", default_val=None)
        self.assertEqual(result, util.BOGUS_INT)

    def test_thermostat_zone_get_mock_value_for_failed_auth_mode(self):
        """Test _get_mock_value_for_failed_auth with mode key."""
        zone_info = {"authentication_status": "failed"}

        mock_thermostat = Mock()
        mock_thermostat.device_id = 0
        mock_thermostat.zone_number = 0
        mock_thermostat.get_all_metadata.return_value = zone_info
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]

        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.get_parameter("operation_mode", default_val=None)
        self.assertEqual(result, 0)

    def test_thermostat_zone_get_setpoint_default_heat(self):
        """Test _get_setpoint_default with heat setpoint."""
        zone_info = {"authentication_status": "failed"}

        mock_thermostat = Mock()
        mock_thermostat.device_id = 0
        mock_thermostat.zone_number = 0
        mock_thermostat.get_all_metadata.return_value = zone_info
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]

        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.get_parameter("heat_setpoint", default_val=None)
        self.assertEqual(result, 68)

    def test_thermostat_zone_get_setpoint_default_cool(self):
        """Test _get_setpoint_default with cool setpoint."""
        zone_info = {"authentication_status": "failed"}

        mock_thermostat = Mock()
        mock_thermostat.device_id = 0
        mock_thermostat.zone_number = 0
        mock_thermostat.get_all_metadata.return_value = zone_info
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]

        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        result = zone.get_parameter("cool_setpoint", default_val=None)
        self.assertEqual(result, 70)

    def test_thermostat_zone_handle_parameter_error_raises(self):
        """Test _handle_parameter_error raises when no default."""
        zone_info = {"label": "Test Zone"}

        mock_thermostat = Mock()
        mock_thermostat.device_id = 0
        mock_thermostat.zone_number = 0
        mock_thermostat.get_all_metadata.return_value = zone_info
        mock_thermostat._cache_expires_at = 0  # type: ignore[attr-defined]

        zone = kumocloudv3.ThermostatZone(mock_thermostat, verbose=False)

        # Request nonexistent key with no default
        with self.assertRaises((KeyError, TypeError)):
            zone.get_parameter("nonexistent_key")

    @patch("src.kumocloudv3.requests.Session")
    def test_update_config_with_indices_duplicates(
        self, mock_session_class
    ):
        """Test _update_config_with_indices handles duplicate indices."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock authentication
        auth_response = Mock()
        auth_response.json.return_value = {
            "token": {"access": "token", "refresh": "refresh"}
        }
        auth_response.raise_for_status = Mock()
        mock_session.post.return_value = auth_response

        with patch.object(
            kumocloudv3.ThermostatClass, "_update_zone_assignments"
        ):
            thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=False)

            # Pass same index multiple times
            thermostat._update_config_with_indices(0, 0, 0)

            # Should only add once
            zones = kumocloudv3_config.supported_configs.get("zones", [])
            self.assertEqual(zones.count(0), 1)

    @patch("src.kumocloudv3.requests.Session")
    def test_populate_metadata_requests_exception(
        self, mock_session_class
    ):
        """Test _populate_metadata handles RequestException."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock authentication
        auth_response = Mock()
        auth_response.json.return_value = {
            "token": {"access": "token", "refresh": "refresh"}
        }
        auth_response.raise_for_status = Mock()
        mock_session.post.return_value = auth_response

        # Setup metadata
        kumocloudv3_config.metadata.clear()
        kumocloudv3_config.metadata.update({
            0: {"zone_name": "Zone 0", "serial_number": None}
        })

        # Mock request to raise exception
        mock_session.request.side_effect = (
            requests.exceptions.RequestException("Network error")
        )

        thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=True)

        # Should fall back to sequential assignment
        thermostat._populate_metadata(["SERIAL1"])

        # Should have assigned sequentially
        self.assertEqual(
            kumocloudv3_config.metadata[0]["serial_number"], "SERIAL1"
        )

    @patch("src.kumocloudv3.requests.Session")
    def test_populate_metadata_key_error(self, mock_session_class):
        """Test _populate_metadata handles KeyError in data structure."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock authentication
        auth_response = Mock()
        auth_response.json.return_value = {
            "token": {"access": "token", "refresh": "refresh"}
        }
        auth_response.raise_for_status = Mock()
        mock_session.post.return_value = auth_response

        # Setup metadata
        kumocloudv3_config.metadata.clear()
        kumocloudv3_config.metadata.update({
            0: {"zone_name": "Zone 0", "serial_number": None}
        })

        # Mock sites response
        sites_response = Mock()
        sites_response.json.return_value = [{"id": "site1"}]
        sites_response.raise_for_status = Mock()

        # Mock zones response with bad structure
        zones_response = Mock()
        zones_response.json.return_value = [
            {"name": "Zone"}
            # Missing adapter.deviceSerial
        ]
        zones_response.raise_for_status = Mock()

        mock_session.request.side_effect = [
            sites_response,
            zones_response,
        ]

        thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=True)

        # Should fall back to sequential assignment
        thermostat._populate_metadata(["SERIAL1"])

        # Should have assigned sequentially
        self.assertEqual(
            kumocloudv3_config.metadata[0]["serial_number"], "SERIAL1"
        )

    @patch("src.kumocloudv3.requests.Session")
    def test_populate_metadata_type_error(self, mock_session_class):
        """Test _populate_metadata handles TypeError."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock authentication
        auth_response = Mock()
        auth_response.json.return_value = {
            "token": {"access": "token", "refresh": "refresh"}
        }
        auth_response.raise_for_status = Mock()
        mock_session.post.return_value = auth_response

        # Setup metadata
        kumocloudv3_config.metadata.clear()
        kumocloudv3_config.metadata.update({
            0: {"zone_name": "Zone 0", "serial_number": None}
        })

        # Mock sites to return None (causes TypeError)
        sites_response = Mock()
        sites_response.json.return_value = None
        sites_response.raise_for_status = Mock()

        mock_session.request.return_value = sites_response

        thermostat = kumocloudv3.ThermostatClass(zone=0, verbose=True)

        # Should fall back to sequential assignment
        thermostat._populate_metadata(["SERIAL1"])

        # Should have assigned sequentially
        self.assertEqual(
            kumocloudv3_config.metadata[0]["serial_number"], "SERIAL1"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
