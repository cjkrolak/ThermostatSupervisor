"""KumoCloud v3 API integration"""

# built-in imports
import os
import pprint
import time
import traceback
from typing import Union, Dict, Any, List

# third party imports
import requests

# local imports
from thermostatsupervisor import environment as env
from thermostatsupervisor import kumocloudv3_config
from thermostatsupervisor import thermostat_api as api
from thermostatsupervisor import thermostat_common as tc
from thermostatsupervisor import utilities as util


class ThermostatClass(tc.ThermostatCommon):
    """KumoCloud v3 API thermostat functions."""

    def __init__(self, zone, verbose=True):
        """
        Constructor, connect to thermostat using v3 API.

        inputs:
            zone(str):  zone of thermostat.
            verbose(bool): debug flag.
        """
        # Kumocloud server auth credentials from env vars
        self.KC_UNAME_KEY = "KUMO_USERNAME"
        self.KC_PASSWORD_KEY = "KUMO_PASSWORD"
        self.kc_uname = os.environ.get(
            self.KC_UNAME_KEY, "<" + self.KC_UNAME_KEY + api.KEY_MISSING_SUFFIX
        )
        self.kc_pwd = os.environ.get(
            self.KC_PASSWORD_KEY, "<" + self.KC_PASSWORD_KEY + api.KEY_MISSING_SUFFIX
        )

        # construct the superclass
        tc.ThermostatCommon.__init__(self)

        # set tstat type and debug flag
        self.thermostat_type = kumocloudv3_config.ALIAS
        self.verbose = verbose

        # v3 API endpoints and session
        self.base_url = "https://app-prod.kumocloud.com"
        self.session = requests.Session()

        # Set base headers required by v3 API
        self.session.headers.update(
            {
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US, en",
                "x-app-version": "3.0.9",
                "Content-Type": "application/json",
            }
        )
        self.auth_token = None
        self.refresh_token = None
        self.token_expires_at = 0
        self.refresh_token_expires_at = 0

        # configure zone info
        self.zone_number = int(zone)
        # Note: zone_name will be updated after dynamic zone assignment
        self.zone_name = kumocloudv3_config.metadata.get(
            self.zone_number, {"zone_name": f"Zone {self.zone_number}"}
        )["zone_name"]
        self.device_id = self.get_target_zone_id(self.zone_name)
        self.serial_number = None  # will be populated when unit is queried.
        self.zone_info = {}

        # cached data
        self._cached_sites = None
        self._cached_zones = None
        self._cached_devices = None
        self._cache_expires_at = 0
        self._cache_duration = 300  # 5 minutes cache duration

        # authentication state
        self._authenticated = False
        self._authentication_attempted = False
        self._authentication_error = None

        # attempt initial authentication, but don't fail if it doesn't work
        # (needed for test environments with network restrictions)
        try:
            self._authenticate()
            # After successful authentication, update zone assignments dynamically
            self._update_zone_assignments()
            # Update zone_name with the dynamically assigned name
            self.zone_name = kumocloudv3_config.metadata.get(
                self.zone_number, {"zone_name": f"Zone {self.zone_number}"}
            )["zone_name"]
        except tc.AuthenticationError as e:
            # Store the error but don't crash during initialization
            self._authentication_error = e
            if self.verbose:
                print(f"Warning: Initial authentication failed: {e}")
                print("Authentication will be retried when API calls are made.")
        except Exception as e:
            # Handle zone assignment update failures
            if self.verbose:
                print(f"Warning: Zone assignment update failed: {e}")
                print("Using static zone assignments as fallback.")

    def _authenticate(self) -> bool:
        """
        Authenticate with KumoCloud v3 API using JWT tokens.

        returns:
            (bool): True if authentication successful
        """
        self._authentication_attempted = True

        login_url = f"{self.base_url}/v3/login"
        login_data = {
            "username": self.kc_uname,
            "password": self.kc_pwd,
            "appVersion": "3.0.9",
        }

        try:
            response = self.session.post(login_url, json=login_data, timeout=30)
            response.raise_for_status()

            auth_response = response.json()

            # Extract tokens - try nested structure first, then top-level
            # This handles both possible response formats from the v3 API
            if "token" in auth_response:
                token_data = auth_response["token"]
                self.auth_token = token_data.get("access")
                self.refresh_token = token_data.get("refresh")
            else:
                # Tokens at top level
                self.auth_token = auth_response.get("access")
                self.refresh_token = auth_response.get("refresh")

            if not self.auth_token:
                error = tc.AuthenticationError("No auth token received from v3 API")
                self._authentication_error = error
                self._authenticated = False
                raise error

            # Set token expiration (access token expires in 20 minutes)
            self.token_expires_at = time.time() + 1200  # 20 minutes

            # Set refresh token expiration (refresh token expires in 1 month)
            self.refresh_token_expires_at = time.time() + 2592000  # 30 days

            # Set authorization header for future requests
            self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})

            # Mark as successfully authenticated
            self._authenticated = True
            self._authentication_error = None

            if self.verbose:
                util.log_msg(
                    "Successfully authenticated with KumoCloud v3 API",
                    mode=util.DEBUG_LOG + util.STDOUT_LOG,
                    func_name=1,
                )

            return True

        except requests.exceptions.RequestException as exc:
            error = tc.AuthenticationError(f"Failed to authenticate with v3 API: {exc}")
            self._authentication_error = error
            self._authenticated = False
            raise error from exc
        except (KeyError, ValueError) as exc:
            error = tc.AuthenticationError(f"Invalid response from v3 API: {exc}")
            self._authentication_error = error
            self._authenticated = False
            raise error from exc

    def _refresh_auth_token(self) -> bool:
        """
        Refresh the authentication token using refresh token.

        returns:
            (bool): True if refresh successful
        """
        if not self.refresh_token:
            return self._authenticate()

        # Check if refresh token has expired
        if time.time() >= self.refresh_token_expires_at - 300:  # 5 min buffer
            return self._authenticate()

        refresh_url = f"{self.base_url}/v3/refresh"

        # According to the API docs and working implementation,
        # refresh does NOT use Authorization header - only sends refresh token in body
        refresh_data = {"refresh": self.refresh_token}

        # Store the current auth header to restore later
        current_auth_header = self.session.headers.get("Authorization")

        # Remove Authorization header for refresh request
        # (refresh token goes only in JSON body)
        if "Authorization" in self.session.headers:
            del self.session.headers["Authorization"]

        try:
            response = self.session.post(refresh_url, json=refresh_data, timeout=30)
            response.raise_for_status()

            refresh_response = response.json()

            # Extract tokens from refresh response - tokens are at top level
            new_auth_token = refresh_response.get("access")
            new_refresh_token = refresh_response.get("refresh")

            if not new_auth_token:
                # Refresh failed, try full authentication
                return self._authenticate()

            # Update instance variables only after successful token extraction
            self.auth_token = new_auth_token
            if new_refresh_token:
                self.refresh_token = new_refresh_token
                self.refresh_token_expires_at = time.time() + 2592000  # 30 days

            self.token_expires_at = time.time() + 1200  # 20 minutes

            # Update authorization header with new access token
            self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})

            return True

        except requests.exceptions.RequestException:
            # Refresh failed, restore original header and try full authentication
            if current_auth_header:
                self.session.headers.update({"Authorization": current_auth_header})
            return self._authenticate()
        except Exception:
            # Any other error, restore original header
            if current_auth_header:
                self.session.headers.update({"Authorization": current_auth_header})
            raise

    def _ensure_authenticated(self) -> None:
        """Ensure we have a valid authentication token."""
        # If we've never successfully authenticated, try to authenticate now
        if not self._authenticated:
            if not self._authentication_attempted:
                # Haven't tried yet, attempt authentication
                try:
                    self._authenticate()
                    return
                except tc.AuthenticationError:
                    # Authentication failed, fall through to error handling
                    pass

            # If we get here, authentication failed
            if self._authentication_error:
                # Re-raise the stored authentication error
                raise self._authentication_error
            else:
                # Shouldn't happen, but provide a generic error
                raise tc.AuthenticationError(
                    "Authentication failed and no specific error stored"
                )

        # We are authenticated, check if token needs refresh
        # Refresh 5 minutes early
        if time.time() >= self.token_expires_at - 300:
            # Check if refresh token is still valid (with 1 hour buffer)
            if time.time() >= self.refresh_token_expires_at - 3600:
                # Refresh token expired, need full re-authentication
                self._authenticate()
            else:
                # Refresh token still valid, just refresh access token
                self._refresh_auth_token()

    def _get_sites_and_zones(self):
        """Get sites and zones from API with validation."""
        sites = self._get_sites()

        if not sites:
            if self.verbose:
                print("Warning: No sites found, using default zone assignments")
            return None, None

        # Get zones for the first site (assuming single site setup)
        site_id = sites[0].get("id")
        if not site_id:
            if self.verbose:
                print("Warning: No site ID found, using default zone assignments")
            return None, None

        zones = self._get_zones(site_id)
        return sites, zones

    def _build_zone_name_mapping(self, zones):
        """Build mapping of zone names to indices."""
        zone_name_to_index = {}
        for index, zone in enumerate(zones):
            zone_name = zone.get("name", "").strip()
            if zone_name:
                zone_name_to_index[zone_name] = index

        if self.verbose:
            print(f"Dynamic zone mapping discovered: {zone_name_to_index}")

        return zone_name_to_index

    def _find_zone_indices_by_patterns(self, zone_name_to_index):
        """Find main level, kitchen, and basement indices based on naming patterns."""
        main_living_index = None
        kitchen_index = None
        basement_index = None

        # Check for various naming patterns
        for zone_name, index in zone_name_to_index.items():
            zone_name_lower = zone_name.lower()

            # Check for main level patterns
            if any(
                pattern in zone_name_lower
                for pattern in [
                    "main",
                    "level",
                    "living",
                    "first floor",
                    "1st floor",
                ]
            ):
                main_living_index = index

            # Check for kitchen patterns
            if any(
                pattern in zone_name_lower
                for pattern in [
                    "kitchen",
                ]
            ):
                kitchen_index = index

            # Check for basement patterns
            elif any(
                pattern in zone_name_lower
                for pattern in ["basement", "lower", "cellar", "downstairs"]
            ):
                basement_index = index

        return main_living_index, kitchen_index, basement_index

    def _update_config_with_indices(
        self, main_living_index, kitchen_index, basement_index
    ):
        """Update config module with discovered zone indices."""
        # Rebuild zones list from scratch to avoid inconsistent indices
        # when some zones are not found
        discovered_zones = []

        # Update the config module with discovered assignments
        # Use a set to track already-added indices to prevent duplicates
        added_indices = set()

        if main_living_index is not None and main_living_index not in added_indices:
            kumocloudv3_config.MAIN_LIVING = main_living_index
            discovered_zones.append(main_living_index)
            added_indices.add(main_living_index)

        if kitchen_index is not None and kitchen_index not in added_indices:
            kumocloudv3_config.KITCHEN = kitchen_index
            discovered_zones.append(kitchen_index)
            added_indices.add(kitchen_index)

        if basement_index is not None and basement_index not in added_indices:
            kumocloudv3_config.BASEMENT = basement_index
            discovered_zones.append(basement_index)
            added_indices.add(basement_index)

        # Only update the zones list if we discovered at least one zone
        # If no zones were discovered, keep the existing configuration as fallback
        if discovered_zones:
            kumocloudv3_config.supported_configs["zones"] = discovered_zones

    def _rebuild_metadata_dict(
        self,
        zone_name_to_index,
        main_living_index,
        kitchen_index,
        basement_index
    ):
        """Rebuild metadata dict with discovered assignments."""
        if all(idx is not None for idx in
               (main_living_index, kitchen_index, basement_index)):
            # Clear existing metadata and rebuild with correct indices
            kumocloudv3_config.metadata.clear()

            # Rebuild metadata with correct zone indices
            for zone_name, index in zone_name_to_index.items():
                kumocloudv3_config.metadata[index] = {
                    "zone_name": zone_name,
                    "host_name": "tbd",
                    "serial_number": None,
                }

        if self.verbose:
            print(
                f"Updated zone assignments - MAIN_LIVING: "
                f"{kumocloudv3_config.MAIN_LIVING}, "
                f"KITCHEN: {kumocloudv3_config.KITCHEN}, "
                f"BASEMENT: {kumocloudv3_config.BASEMENT}"
            )
            print(f"Updated metadata: {kumocloudv3_config.metadata}")

    def _update_zone_assignments(self) -> None:
        """
        Update zone assignments dynamically by querying the v3 API.

        This method retrieves zone information from the API and updates the
        config module's zone assignments to match the actual API response.
        Zone assignments are not static in v3 API - sometimes zone 0 is
        MAIN_LIVING and other times zone 1 is MAIN_LIVING.
        """
        try:
            # Get sites and zones from API
            sites, zones = self._get_sites_and_zones()
            if sites is None or zones is None:
                return

            # Build mapping of zone names to indices
            zone_name_to_index = self._build_zone_name_mapping(zones)

            # Find zone indices by patterns
            main_living_index, kitchen_index, basement_index = \
                self._find_zone_indices_by_patterns(zone_name_to_index)

            # Update config with discovered indices
            self._update_config_with_indices(
                main_living_index, kitchen_index, basement_index
            )

            # Update metadata dict with discovered assignments
            self._rebuild_metadata_dict(
                zone_name_to_index,
                main_living_index,
                kitchen_index,
                basement_index
            )

        except Exception as e:
            if self.verbose:
                print(f"Failed to update zone assignments: {e}")
                print("Continuing with static zone assignments as fallback")

    def _make_authenticated_request(
        self, method: str, url: str, **kwargs
    ) -> requests.Response:
        """
        Make an authenticated request with automatic token refresh on 401.

        inputs:
            method(str): HTTP method (GET, POST, etc.)
            url(str): Request URL
            **kwargs: Additional arguments for requests

        returns:
            (requests.Response): HTTP response
        """
        # Ensure we have valid authentication before making request
        self._ensure_authenticated()

        # Ensure the session has the correct auth header
        if self.auth_token:
            self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})

        # Make the first request attempt
        response = self.session.request(method, url, timeout=30, **kwargs)

        # If we get 401, try to refresh token and retry once
        if response.status_code == 401:
            # Token might be expired, try refresh
            if self._refresh_auth_token():
                # Ensure session header is updated with new token
                if self.auth_token:
                    self.session.headers.update(
                        {"Authorization": f"Bearer {self.auth_token}"}
                    )
                # Retry the request with new token
                response = self.session.request(method, url, timeout=30, **kwargs)

        response.raise_for_status()
        return response

    def _get_sites(self) -> List[Dict[str, Any]]:
        """
        Get sites data from v3 API.

        returns:
            (List[Dict]): List of sites
        """
        if self._cached_sites and time.time() < self._cache_expires_at:
            return self._cached_sites

        sites_url = f"{self.base_url}/v3/sites/"
        response = self._make_authenticated_request("GET", sites_url)

        self._cached_sites = response.json()
        self._cache_expires_at = time.time() + self._cache_duration

        return self._cached_sites

    def _get_zones(self, site_id: str) -> List[Dict[str, Any]]:
        """
        Get zones data for a site from v3 API.

        inputs:
            site_id(str): Site identifier

        returns:
            (List[Dict]): List of zones
        """
        zones_url = f"{self.base_url}/v3/sites/{site_id}/zones/"
        response = self._make_authenticated_request("GET", zones_url)

        return response.json()

    def _get_device(self, device_serial: str) -> Dict[str, Any]:
        """
        Get device data from v3 API using device serial number.

        inputs:
            device_serial(str): Device serial number from adapter.deviceSerial

        returns:
            (Dict): Device data
        """
        device_url = f"{self.base_url}/v3/devices/{device_serial}"
        response = self._make_authenticated_request("GET", device_url)

        return response.json()

    def get_indoor_units(self) -> List[str]:
        """
        Get list of indoor unit serial numbers.

        returns:
            (List[str]): List of serial numbers
        """
        try:
            sites = self._get_sites()
            serial_numbers = []

            for site in sites:
                site_id = site.get("id")
                if not site_id:
                    continue

                zones = self._get_zones(site_id)
                for zone in zones:
                    # Extract device serial from zone's adapter.deviceSerial field
                    adapter = zone.get("adapter", {})
                    device_serial = adapter.get("deviceSerial")
                    if device_serial:
                        serial_numbers.append(device_serial)

            return serial_numbers

        except requests.exceptions.RequestException as exc:
            raise tc.AuthenticationError(f"Failed to get indoor units: {exc}") from exc

    def get_raw_json(self) -> List[Any]:
        """
        Get raw JSON data in legacy format for compatibility.

        returns:
            (List): Raw JSON data compatible with pykumo format
        """
        try:
            sites = self._get_sites()

            # Convert v3 API response to legacy format
            # Legacy format: [token_info, last_update, zone_data, device_token]
            token_info = {"token": self.auth_token, "username": self.kc_uname}

            last_update = time.strftime("%Y-%m-%d %H:%M:%S")

            # Build zone data structure compatible with legacy format
            zone_data = {"children": [{"zoneTable": {}}]}

            for site in sites:
                site_id = site.get("id")
                if not site_id:
                    continue

                zones = self._get_zones(site_id)
                for zone in zones:
                    # Extract device serial from zone's adapter.deviceSerial field
                    adapter = zone.get("adapter", {})
                    device_serial = adapter.get("deviceSerial")
                    if device_serial:
                        # Get device details using the device serial
                        device = self._get_device(device_serial)
                        # Convert v3 device data to legacy format
                        legacy_device = self._convert_device_to_legacy_format(
                            device, zone
                        )
                        zone_data["children"][0]["zoneTable"][
                            device_serial
                        ] = legacy_device

            device_token = self.auth_token

            return [token_info, last_update, zone_data, device_token]

        except Exception as exc:
            raise tc.AuthenticationError(f"Failed to get raw JSON: {exc}") from exc

    def _convert_device_to_legacy_format(
        self, device: Dict[str, Any], zone: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convert v3 API device data to legacy pykumo format.

        inputs:
            device(Dict): v3 API device data
            zone(Dict): v3 API zone data

        returns:
            (Dict): Legacy format device data
        """
        # Map v3 API fields to legacy format
        legacy_device = {
            "label": zone.get("name", "Unknown Zone"),
            "address": device.get("macAddress", ""),
            "reportedCondition": {
                "room_temp": device.get("roomTemp", util.BOGUS_INT),
                "sp_heat": device.get("spHeat", util.BOGUS_INT),
                "sp_cool": device.get("spCool", util.BOGUS_INT),
                "operation_mode": device.get("operationMode", util.BOGUS_INT),
                "power": 1 if device.get("power", util.BOGUS_BOOL) else 0,
                "fan_speed": device.get("fanSpeed", util.BOGUS_INT),
                "humidity": device.get("humidity", util.BOGUS_INT),
            },
            "reportedInitialSettings": {
                "energy_save": 1 if device.get("energySave", util.BOGUS_BOOL) else 0,
            },
            "inputs": {
                "acoilSettings": {
                    "humidistat": 1 if device.get("hasHumiditySensor",
                                                  util.BOGUS_BOOL) else 0,
                }
            },
            "rssi": {"rssi": device.get("rssi", util.BOGUS_INT)},
            "status_display": {
                "reportedCondition": {
                    "defrost": 1
                    if device.get("displayConfig", {}).get(
                        "defrost", util.BOGUS_BOOL
                    )
                    else 0,
                    "standby": 1
                    if device.get("displayConfig", {}).get(
                        "standby", util.BOGUS_BOOL
                    )
                    else 0,
                }
            },
        }

        # Handle missing fan_speed_text
        if "reportedCondition" not in legacy_device:
            legacy_device["reportedCondition"] = {}

        fan_speed = legacy_device["reportedCondition"].get(
            "fan_speed", util.BOGUS_INT
        )
        legacy_device["reportedCondition"]["more"] = {
            # Explicitly handle missing/invalid fan_speed values represented
            # by util.BOGUS_INT, so we do not incorrectly report them as "on".
            "fan_speed_text": (
                "unknown"
                if fan_speed == util.BOGUS_INT
                else ("off" if fan_speed == 0 else "on")
            )
        }

        return legacy_device

    def get_target_zone_id(self, zone=0):
        """
        Return the target zone ID.

        inputs:
            zone(int):  zone number.
        returns:
            (int): device_id
        """
        return zone

    def get_zone_index_from_name(self):
        """
        Return zone index for specified zone_name.

        inputs:
            None
        returns:
            (int): zone index.
        """
        if self.verbose:
            print(f"getting index for zone_name={self.zone_name}...")
            print(f"metadata dict={kumocloudv3_config.metadata}")
        try:
            zone_index = [
                i
                for i in kumocloudv3_config.metadata
                if kumocloudv3_config.metadata[i]["zone_name"] == self.zone_name
            ][0]
        except IndexError:
            # Create a helpful error message with valid zone names
            valid_zone_names = [
                kumocloudv3_config.metadata[i]["zone_name"]
                for i in kumocloudv3_config.metadata
            ]
            error_msg = (
                f"zone_name='{self.zone_name}' not found in kumocloudv3 metadata. "
                f"Valid zone names are: {valid_zone_names}. "
                f"Available zone indices are: "
                f"{list(kumocloudv3_config.metadata.keys())}"
            )
            raise ValueError(error_msg) from None
        return zone_index

    def get_all_metadata(self, zone=None, retry=False):
        """Get all thermostat meta data for zone from kumocloud.

        inputs:
            zone(int): specified zone, if None will print all zones.
            retry(bool): if True will retry with extended retry mechanism.
        returns:
            (dict): JSON dict
        """
        return self.get_metadata(zone, retry=retry)

    def get_metadata(self, zone=None, trait=None, parameter=None, retry=False):
        """Get all thermostat meta data for zone from kumocloud v3 API.

        inputs:
            zone(int): specified zone, if None will print all zones.
            trait(str): trait or parent key, if None will assume a non-nested
                        dict
            parameter(str): target parameter, if None will return all.
            retry(bool): if True will retry with extended retry mechanism
        returns:
            (int, float, str, dict): depends on parameter
        """
        del trait  # not needed on Kumocloud

        def _get_metadata_internal():
            serial_num_lst = self._get_serial_numbers_with_retry()
            raw_json = self._get_zone_raw_data(zone, serial_num_lst)
            return self._process_raw_data(raw_json, parameter, zone)

        if retry:
            result = self._execute_with_extended_retry(_get_metadata_internal, zone)
        else:
            result = _get_metadata_internal()

        # Post-process result for authentication failures
        return self._post_process_result(result, parameter, zone)

    def _get_serial_numbers_with_retry(self):
        """Get indoor unit serial numbers with retry logic."""
        try:
            return self._attempt_get_indoor_units()
        except tc.AuthenticationError as exc:
            return self._handle_auth_error(exc)
        except Exception as exc:
            return self._handle_general_error(exc)

    def _attempt_get_indoor_units(self):
        """Attempt to get indoor units."""
        serial_num_lst = list(self.get_indoor_units())
        if self.verbose:
            util.log_msg(
                f"indoor unit serial numbers: {str(serial_num_lst)}",
                mode=util.DEBUG_LOG + util.STDOUT_LOG,
                func_name=1,
            )
        return serial_num_lst

    def _handle_auth_error(self, exc):
        """Handle authentication error."""
        util.log_msg(
            f"WARNING: Kumocloud v3 authentication failed: {exc}",
            mode=util.BOTH_LOG,
            func_name=1,
        )
        return []

    def _handle_general_error(self, exc):
        """Handle general errors with retry."""
        util.log_msg(
            f"WARNING: Kumocloud v3 refresh failed: {exc}",
            mode=util.BOTH_LOG,
            func_name=1,
        )
        time.sleep(30)
        try:
            return list(self.get_indoor_units())
        except tc.AuthenticationError:
            return []

    def _get_zone_raw_data(self, zone, serial_num_lst):
        """Get raw data for zone."""
        self._validate_serial_numbers(serial_num_lst)
        self._populate_metadata(serial_num_lst)

        if zone is None:
            return self.get_raw_json()[2]
        else:
            return self._get_specific_zone_data(zone, serial_num_lst)

    def _validate_serial_numbers(self, serial_num_lst):
        """Validate serial number list."""
        if not serial_num_lst:
            if not self._authenticated:
                util.log_msg(
                    "kumocloud v3 authentication failed, "
                    "returning minimal metadata for testing",
                    mode=util.BOTH_LOG,
                    func_name=1,
                )
                return {"authentication_status": "failed", "zones": []}
            else:
                raise tc.AuthenticationError(
                    "kumocloud v3 meta data is blank, probably"
                    " due to an Authentication Error,"
                    " check your credentials."
                )

    def _assign_serials_sequentially(self, serial_num_lst):
        """
        Assign serial numbers to metadata sequentially (fallback method).

        Args:
            serial_num_lst (list): List of serial numbers
        """
        for idx, serial_number in enumerate(serial_num_lst):
            if idx in kumocloudv3_config.metadata:
                kumocloudv3_config.metadata[idx]["serial_number"] = (
                    serial_number
                )

    def _populate_metadata(self, serial_num_lst):
        """
        Populate metadata with serial numbers matched by zone name.

        This method correctly matches serial numbers to zone indices
        by using zone names from the API response, ensuring correct
        assignment regardless of API response order.

        Modifies kumocloudv3_config.metadata in-place by setting the
        'serial_number' field for each zone based on zone name matching.
        Falls back to sequential assignment on API errors.

        Args:
            serial_num_lst (list): List of serial numbers from API
        """
        try:
            # Get zones data to match zone names with serial numbers
            sites = self._get_sites()
            if not sites:
                # Fallback to sequential assignment if no sites data
                self._assign_serials_sequentially(serial_num_lst)
                return

            site_id = sites[0].get("id")
            if not site_id:
                # Fallback to sequential assignment
                self._assign_serials_sequentially(serial_num_lst)
                return

            zones = self._get_zones(site_id)
            if not zones:
                # Fallback to sequential assignment if no zones data
                self._assign_serials_sequentially(serial_num_lst)
                return

            # Build mapping of serial number to zone name
            serial_to_zone_name = {}
            for zone in zones:
                adapter = zone.get("adapter", {})
                device_serial = adapter.get("deviceSerial")
                zone_name = zone.get("name", "").strip()
                if device_serial and zone_name:
                    serial_to_zone_name[device_serial] = zone_name

            # Build reverse lookup: zone_name -> metadata index
            # This improves performance from O(n*m) to O(n+m)
            zone_name_to_idx = {
                meta.get("zone_name"): idx
                for idx, meta in kumocloudv3_config.metadata.items()
                if meta.get("zone_name")
            }

            # Assign serial numbers to correct metadata indices
            # by matching zone names
            for serial_number in serial_num_lst:
                zone_name = serial_to_zone_name.get(serial_number)
                if zone_name:
                    idx = zone_name_to_idx.get(zone_name)
                    if idx is not None:
                        kumocloudv3_config.metadata[idx]["serial_number"] = (
                            serial_number
                        )
                        if self.verbose:
                            util.log_msg(
                                f"zone index={idx}, "
                                f"name={zone_name}, "
                                f"serial_number={serial_number}",
                                mode=util.DEBUG_LOG + util.STDOUT_LOG,
                                func_name=1,
                            )
                    elif self.verbose:
                        # Log a warning when a zone name from the API
                        # cannot be mapped to a metadata index. This
                        # helps debug configuration mismatches.
                        util.log_msg(
                            "Warning: Zone name from API not found in "
                            f"metadata: zone_name={zone_name!r}, "
                            f"serial_number={serial_number}",
                            mode=util.DEBUG_LOG + util.STDOUT_LOG,
                            func_name=1,
                        )
                elif self.verbose:
                    # Log a warning when a serial number from the indoor
                    # units list cannot be matched to any zone name from
                    # the zones API response. This condition is silent
                    # otherwise and may cause issues later when specific
                    # zone data is requested.
                    util.log_msg(
                        "Warning: Serial number from indoor units could "
                        "not be matched to any zone name from API: "
                        f"serial_number={serial_number}",
                        mode=util.DEBUG_LOG + util.STDOUT_LOG,
                        func_name=1,
                    )

        except requests.exceptions.RequestException as exc:
            # API communication errors - fallback to sequential assignment
            if self.verbose:
                util.log_msg(
                    f"Warning: API request failed during serial matching: {exc}",
                    mode=util.DEBUG_LOG + util.STDOUT_LOG,
                    func_name=1,
                )
                util.log_msg(
                    "Using sequential assignment as fallback",
                    mode=util.DEBUG_LOG + util.STDOUT_LOG,
                    func_name=1,
                )
            self._assign_serials_sequentially(serial_num_lst)
        except (KeyError, TypeError, AttributeError) as exc:
            # Data structure issues - fallback to sequential assignment
            if self.verbose:
                util.log_msg(
                    f"Warning: Unexpected data structure during serial "
                    f"matching: {exc}",
                    mode=util.DEBUG_LOG + util.STDOUT_LOG,
                    func_name=1,
                )
                util.log_msg(
                    "Using sequential assignment as fallback",
                    mode=util.DEBUG_LOG + util.STDOUT_LOG,
                    func_name=1,
                )
            self._assign_serials_sequentially(serial_num_lst)
        except Exception as exc:
            # Unexpected errors - log and fallback to sequential assignment
            if self.verbose:
                util.log_msg(
                    f"Warning: Failed to match serial numbers by name: {exc}",
                    mode=util.DEBUG_LOG + util.STDOUT_LOG,
                    func_name=1,
                )
                util.log_msg(
                    "Using sequential assignment as fallback",
                    mode=util.DEBUG_LOG + util.STDOUT_LOG,
                    func_name=1,
                )
            self._assign_serials_sequentially(serial_num_lst)

    def _get_specific_zone_data(self, zone, serial_num_lst):
        """
        Get data for specific zone from API.

        Retrieves the zone data from the API's zoneTable by looking up
        the serial number that was matched to this zone by _populate_metadata.
        This ensures the correct device data is returned regardless of API
        response ordering.

        Args:
            zone (int or str): Zone index (int) or zone name (str)
            serial_num_lst (list): List of serial numbers from API (used as
                fallback if metadata serial not populated)

        Returns:
            dict: Zone data from API containing device information and
                reported conditions

        Raises:
            IndexError: If zone_index is invalid or serial number cannot be
                found in metadata or serial_num_lst
        """
        if not isinstance(zone, int):
            self.zone_name = zone
            zone_index = self.get_zone_index_from_name()
        else:
            zone_index = zone

        # Get serial number from metadata (populated by _populate_metadata)
        # This ensures we use the correct serial for this zone_index
        # regardless of the order in serial_num_lst
        try:
            self.serial_number = kumocloudv3_config.metadata[zone_index][
                "serial_number"
            ]
            if self.serial_number is None:
                # Fallback to index-based lookup if metadata not populated
                self.serial_number = serial_num_lst[zone_index]
        except (KeyError, IndexError, TypeError) as exc:
            raise IndexError(
                f"ERROR: Invalid Zone, index ({zone_index}) does "
                "not exist in metadata or serial number list "
                f"(metadata keys: {list(kumocloudv3_config.metadata.keys())}, "
                f"serial_num_lst: {serial_num_lst})"
            ) from exc

        return self.get_raw_json()[2]["children"][0]["zoneTable"][
            self.serial_number
        ]

    def _process_raw_data(self, raw_json, parameter, zone):
        """Process raw JSON data."""
        if self._is_auth_failed(raw_json):
            return self._handle_auth_failed_data(raw_json, parameter, zone)

        if parameter is None:
            return raw_json
        else:
            return raw_json[parameter]

    def _is_auth_failed(self, raw_json):
        """Check if authentication failed."""
        return (
            isinstance(raw_json, dict)
            and raw_json.get("authentication_status") == "failed"
        )

    def _handle_auth_failed_data(self, raw_json, parameter, zone):
        """Handle data when authentication failed."""
        if parameter is None:
            return raw_json
        else:
            return self._get_mock_parameter_value(parameter, zone)

    def _get_mock_parameter_value(self, parameter, zone):
        """Get mock value for parameter when authentication failed."""
        mock_values = {
            "address": "127.0.0.1",
            "temp": util.BOGUS_INT,
            "humidity": util.BOGUS_INT,
            "zone": f"Zone_{zone or 0}",
            "name": f"Zone_{zone or 0}",
            "serial": f"MOCK_SERIAL_{zone or 0}",
        }

        for key, value in mock_values.items():
            if key in parameter.lower():
                return value

        return f"mock_{parameter}"

    def _execute_with_extended_retry(self, func, zone):
        """Execute function with extended retry mechanism."""
        return util.execute_with_extended_retries(
            func=func,
            thermostat_type=getattr(self, "thermostat_type", "KumoCloudv3"),
            zone_name=str(getattr(self, "zone_name", str(zone))),
            number_of_retries=5,
            initial_retry_delay_sec=60,
            exception_types=(
                tc.AuthenticationError,
                IndexError,
                KeyError,
                ConnectionError,
                TimeoutError,
                requests.exceptions.RequestException,
            ),
            email_notification=None,
        )

    def _post_process_result(self, result, parameter, zone):
        """Post-process result to handle authentication failure."""
        if (
            isinstance(result, dict)
            and result.get("authentication_status") == "failed"
            and parameter is not None
        ):
            return self._get_mock_parameter_value(parameter, zone)
        return result

    def print_all_thermostat_metadata(self, zone):
        """Print all metadata for zone to the screen.

        inputs:
            zone(int): specified zone, if None will print all zones.
        returns:
            None, prints result to screen
        """
        self.exec_print_all_thermostat_metadata(self.get_all_metadata, [zone])


class ThermostatZone(tc.ThermostatCommonZone):
    """
    KumoCloud v3 API single zone from kumocloud.

    Class needs to be updated for multi-zone support.
    """

    def __init__(self, Thermostat_obj, verbose=True):
        """
        Zone constructor.

        inputs:
            Thermostat(obj): Thermostat class instance.
            verbose(bool): debug flag.
        """
        # construct the superclass, requires auth setup first
        super().__init__()

        # runtime parameter defaults
        self.poll_time_sec = 10 * 60  # default to 10 minutes
        self.connection_time_sec = 8 * 60 * 60  # default to 8 hours

        # server data cache expiration parameters
        self.fetch_interval_sec = 60  # age of server data before refresh
        self.last_fetch_time = time.time() - 2 * self.fetch_interval_sec

        # switch config for this thermostat
        self.system_switch_position[
            tc.ThermostatCommonZone.HEAT_MODE
        ] = "heat"  # "Heat" 0 0001
        self.system_switch_position[
            tc.ThermostatCommonZone.OFF_MODE
        ] = "off"  # "Off"  1 0000
        self.system_switch_position[
            tc.ThermostatCommonZone.FAN_MODE
        ] = "vent"  # "Fan"   0 0111
        self.system_switch_position[
            tc.ThermostatCommonZone.DRY_MODE
        ] = "dry"  # dry     0 0010
        self.system_switch_position[
            tc.ThermostatCommonZone.COOL_MODE
        ] = "cool"  # cool   0 0011
        self.system_switch_position[
            tc.ThermostatCommonZone.AUTO_MODE
        ] = ["auto", "autoHeat", "autoCool"]  # auto modes  0 0101

        # zone info
        self.verbose = verbose
        self.thermostat_type = kumocloudv3_config.ALIAS
        self.device_id = Thermostat_obj.device_id
        self.Thermostat = Thermostat_obj
        self.zone_info = Thermostat_obj.get_all_metadata(Thermostat_obj.zone_number)
        self.zone_number = Thermostat_obj.zone_number
        self.zone_name = self.get_zone_name()  # get real zone name from device

    def get_parameter(
        self, key, parent_key=None, grandparent_key=None, default_val=None
    ):
        """
        Get parameter from zone dictionary.

        inputs:
            key(str): target dict key
            parent_key(str): first level dict key
            grandparent_key(str): second level dict key
            default_val(str, int, float): default value on key errors
        """
        if self._is_authentication_failed():
            return self._get_mock_value_for_failed_auth(key, default_val)

        try:
            return self._extract_parameter_value(key, parent_key, grandparent_key)
        except (KeyError, TypeError):
            return self._handle_parameter_error(key, default_val)

    def _is_authentication_failed(self):
        """Check if authentication failed."""
        return (
            isinstance(self.zone_info, dict)
            and self.zone_info.get("authentication_status") == "failed"
        )

    def _get_mock_value_for_failed_auth(self, key, default_val):
        """Get mock value when authentication failed."""
        if key == "label":
            return f"Zone_{self.zone_number}"
        elif default_val is not None:
            return default_val
        else:
            return self._get_default_value_by_key_type(key)

    def _get_default_value_by_key_type(self, key):
        """Get default value based on key type."""
        key_lower = key.lower()

        if "temp" in key_lower or "humidity" in key_lower:
            return util.BOGUS_INT
        elif "energy_save" in key_lower or "mode" in key_lower:
            return 0
        elif "setpoint" in key_lower or "set_point" in key_lower:
            return self._get_setpoint_default(key_lower)
        elif "schedule" in key_lower or "program" in key_lower:
            return {}
        elif "speed" in key_lower:
            return 0
        else:
            return 0

    def _get_setpoint_default(self, key_lower):
        """Get default setpoint value."""
        if "heat" in key_lower:
            return 68
        elif "cool" in key_lower:
            return 70
        else:
            return 70

    def _extract_parameter_value(self, key, parent_key, grandparent_key):
        """Extract parameter value from zone info."""
        if grandparent_key is not None:
            return self.zone_info[grandparent_key][parent_key][key]
        elif parent_key is not None:
            return self.zone_info[parent_key][key]
        else:
            return self.zone_info[key]

    def _handle_parameter_error(self, key, default_val):
        """Handle parameter extraction errors."""
        if default_val is None:
            util.log_msg(traceback.format_exc(), mode=util.BOTH_LOG, func_name=1)
            util.log_msg(
                f"target key={key}, raw zone_info dict:",
                mode=util.BOTH_LOG,
                func_name=1,
            )
            raise
        return default_val

    def get_zone_name(self):
        """
        Return the name associated with the zone number.

        inputs:
            None
        returns:
            (str) zone name
        """
        self.refresh_zone_info()
        zone_name = self.get_parameter("label")
        # update metadata dict.
        kumocloudv3_config.metadata[self.zone_number]["zone_name"] = zone_name
        return zone_name

    def get_display_temp(self) -> float:  # used
        """
        Refresh the cached zone information and return Indoor Temp in °F.

        inputs:
            None
        returns:
            (float): indoor temp in °F.
        """
        self.refresh_zone_info()
        return util.c_to_f(
            self.get_parameter(
                "room_temp", "reportedCondition", default_val=util.BOGUS_INT
            )
        )

    def get_display_humidity(self) -> Union[float, None]:
        """
        Refresh the cached zone information and return IndoorHumidity.

        inputs:
            None
        returns:
            (float, None): indoor humidity in %RH, None if not supported.
        """
        if not self.get_is_humidity_supported():
            return None
        else:
            # untested, don't have humidity support
            # zone refreshed during if clause above
            return util.c_to_f(
                self.get_parameter(
                    "humidity", "reportedCondition", default_val=util.BOGUS_INT
                )
            )

    def get_is_humidity_supported(self) -> bool:  # used
        """
        Refresh the cached zone information and return the
          True if humidity sensor data is trustworthy.

        inputs:
            None
        returns:
            (booL): True if is in humidity sensor is available and not faulted.
        """
        self.refresh_zone_info()
        return bool(self.get_parameter("humidistat", "acoilSettings", "inputs"))

    def is_heat_mode(self) -> int:
        """
        Refresh the cached zone information and return the heat mode.

        inputs:
            None
        returns:
            (int) heat mode, 1=enabled, 0=disabled.
        """
        return int(self._is_mode(tc.ThermostatCommonZone.HEAT_MODE))

    def is_cool_mode(self) -> int:
        """
        Refresh the cached zone information and return the cool mode.

        inputs:
            None
        returns:
            (int): cool mode, 1=enabled, 0=disabled.
        """
        return int(self._is_mode(tc.ThermostatCommonZone.COOL_MODE))

    def is_dry_mode(self) -> int:
        """
        Refresh the cached zone information and return the dry mode.

        inputs:
            None
        returns:
            (int): dry mode, 1=enabled, 0=disabled.
        """
        return int(self._is_mode(tc.ThermostatCommonZone.DRY_MODE))

    def is_fan_mode(self) -> int:
        """
        Refresh the cached zone information and return the fan mode.

        inputs:
            None
        returns:
            (int): fan mode, 1=enabled, 0=disabled.
        """
        return int(self._is_mode(tc.ThermostatCommonZone.FAN_MODE))

    def is_auto_mode(self) -> int:
        """
        Refresh the cached zone information and return the auto mode.

        inputs:
            None
        returns:
            (int): auto mode, 1=enabled, 0=disabled.
        """
        return int(self._is_mode(tc.ThermostatCommonZone.AUTO_MODE))

    def is_eco_mode(self) -> int:
        """
        Refresh the cached zone information and return the eco mode.

        inputs:
            None
        returns:
            (int): eco mode, 1=enabled, 0=disabled.
        """
        return int(self.get_parameter("energy_save", "reportedInitialSettings"))

    def is_off_mode(self) -> int:
        """
        Refresh the cached zone information and return the off mode.

        inputs:
            None
        returns:
            (int): off mode, 1=enabled, 0=disabled.
        """
        return int(
            self.get_system_switch_position()
            == self.system_switch_position[tc.ThermostatCommonZone.OFF_MODE]
        )

    def is_heating(self):
        """Return 1 if heating relay is active, else 0."""
        return int(
            self.is_heat_mode()
            and self.is_power_on()
            and self.get_heat_setpoint_raw() > self.get_display_temp()
        )

    def is_cooling(self):
        """Return 1 if cooling relay is active, else 0."""
        return int(
            self.is_cool_mode()
            and self.is_power_on()
            and self.get_cool_setpoint_raw() < self.get_display_temp()
        )

    def is_drying(self):
        """Return 1 if drying relay is active, else 0."""
        return int(
            self.is_dry_mode()
            and self.is_power_on()
            and self.get_cool_setpoint_raw() < self.get_display_temp()
        )

    def is_auto(self):
        """Return 1 if auto relay is active, else 0."""
        return int(
            self.is_auto_mode()
            and self.is_power_on()
            and (
                self.get_cool_setpoint_raw() < self.get_display_temp()
                or self.get_heat_setpoint_raw() > self.get_display_temp()
            )
        )

    def is_eco(self):
        """Return 1 if eco relay is active, else 0."""
        return int(
            self.is_eco_mode()
            and self.is_power_on()
            and (
                self.get_cool_setpoint_raw() < self.get_display_temp()
                or self.get_heat_setpoint_raw() > self.get_display_temp()
            )
        )

    def is_fanning(self) -> int:
        """Return 1 if fan relay is active, else 0."""
        return int(self.is_fan_on() and self.is_power_on())

    def is_power_on(self) -> int:
        """Return 1 if power relay is active, else 0."""
        self.refresh_zone_info()
        return int(self.get_parameter("power", "reportedCondition", default_val=0))

    def is_fan_on(self) -> int:
        """Return 1 if fan relay is active, else 0."""
        if self.is_power_on():
            fan_speed = self.get_parameter("fan_speed", "reportedCondition")
            if fan_speed is None:
                return 0  # no fan_speed key, return 0
            else:
                # Handle both string and numeric fan_speed values
                fan_is_on = False
                if isinstance(fan_speed, str):
                    # String values: "auto" or any non-"off" value indicates fan is on
                    # This catch-all approach handles any string fan speed modes
                    fan_is_on = fan_speed == "auto" or fan_speed != "off"
                elif isinstance(fan_speed, (int, float)):
                    # Numeric values: greater than 0 indicates fan is on
                    fan_is_on = fan_speed > 0
                # For unexpected types, fan_is_on remains False (fan off)
                # fan_speed_text check below provides additional validation

                return int(
                    fan_is_on
                    or self.get_parameter("fan_speed_text", "more", "reportedCondition")
                    != "off"
                )
        else:
            return 0

    def is_defrosting(self) -> int:
        """Return 1 if defrosting is active, else 0."""
        self.refresh_zone_info()
        return int(self.get_parameter("defrost", "status_display", "reportedCondition"))

    def is_standby(self) -> int:
        """Return 1 if standby is active, else 0."""
        self.refresh_zone_info()
        return int(self.get_parameter("standby", "status_display", "reportedCondition"))

    def get_wifi_strength(self) -> float:  # noqa R0201
        """Return the wifi signal strength in dBm.

        rssi is sometimes reported in the reportedCondition dict,
        rssi is always reported in the rssi dict.
        rssi dict can be empty if unit is off.
        """
        self.refresh_zone_info()
        return float(self.get_parameter("rssi", "rssi", None, util.BOGUS_INT))

    def get_wifi_status(self) -> bool:  # noqa R0201
        """Return the wifi connection status."""
        raw_wifi = self.get_wifi_strength()
        if isinstance(raw_wifi, (float, int)):
            return raw_wifi >= util.MIN_WIFI_DBM
        else:
            return False

    def get_battery_voltage(self) -> float:  # noqa R0201
        """Return the battery voltage in volts.

        This tstat is on line power so any valid response
        from tstat returns line power value.
        """
        return 120.0 if self.get_wifi_status() else 0.0

    def get_battery_status(self) -> bool:  # noqa R0201
        """Return the battery status.

        For this tstat any positive number returns True.
        """
        return self.get_battery_voltage() > 0.0

    def get_heat_setpoint_raw(self) -> float:  # used
        """
        Refresh the cached zone information and return the heat setpoint.

        inputs:
            None
        returns:
            (float): heating set point in °F.
        """
        self.refresh_zone_info()
        # if power is off then sp_heat may be missing
        return util.c_to_f(
            self.get_parameter("sp_heat", "reportedCondition", default_val=-1)
        )

    def get_heat_setpoint(self) -> str:
        """Return heat setpoint with units as a string."""
        return util.temp_value_with_units(self.get_heat_setpoint_raw())

    def get_schedule_heat_sp(self) -> float:  # used
        """
        Return the schedule heat setpoint.

        inputs:
            None
        returns:
            (float): scheduled heating set point in °F.
        """
        return float(kumocloudv3_config.MAX_HEAT_SETPOINT)  # max heat set point allowed

    def get_schedule_cool_sp(self) -> float:
        """
        Return the schedule cool setpoint.

        inputs:
            None
        returns:
            (float): scheduled cooling set point in °F.
        """
        return kumocloudv3_config.MIN_COOL_SETPOINT  # min cool set point allowed

    def get_cool_setpoint_raw(self) -> float:
        """
        Return the cool setpoint.

        inputs:
            None
        returns:
            (float): cooling set point in °F.
        """
        self.refresh_zone_info()
        # if power is off then sp_heat may be missing
        return util.c_to_f(
            self.get_parameter("sp_cool", "reportedCondition", default_val=-1)
        )

    def get_cool_setpoint(self) -> str:
        """Return cool setpoint with units as a string."""
        return util.temp_value_with_units(self.get_cool_setpoint_raw())

    def get_is_invacation_hold_mode(self) -> bool:  # used
        """
        Return the
          'IsInVacationHoldMode' setting.

        inputs:
            None
        returns:
            (booL): True if is in vacation hold mode.
        """
        return False  # no schedule, hold not implemented

    def get_vacation_hold(self) -> bool:
        """
        Return the
        VacationHold setting.

        inputs:
            None
        returns:
            (bool): True if vacation hold is set.
        """
        return False  # no schedule, hold not implemented

    def get_system_switch_position(self) -> Union[int, str]:  # used
        """
        Return the system switch position.

        inputs:
            None
        returns:
            (int or str) current mode for unit, should match value
                  in self.system_switch_position
        """
        self.refresh_zone_info()
        # first check if power is on
        # if power is off then operation_mode key may be missing.
        if not self.is_power_on():
            return self.system_switch_position[tc.ThermostatCommonZone.OFF_MODE]
        else:
            return self.get_parameter("operation_mode", "reportedCondition")

    def set_heat_setpoint(self, temp: int) -> None:
        """
        Set a new heat setpoint.

        This will also attempt to turn the thermostat to 'Heat'
        inputs:
            temp(int): desired temperature in F
        returns:
            None
        """
        # TODO needs implementation for v3 API
        del temp
        util.log_msg(
            "WARNING: this method not implemented yet for this thermostat type",
            mode=util.BOTH_LOG,
            func_name=1,
        )

    def set_cool_setpoint(self, temp: int) -> None:
        """
        Set a new cool setpoint.

        This will also attempt to turn the thermostat to 'Cool'
        inputs:
            temp(int): desired temperature in °F.
        returns:
            None
        """
        # TODO needs implementation for v3 API
        del temp
        util.log_msg(
            "WARNING: this method not implemented yet for this thermostat type",
            mode=util.BOTH_LOG,
            func_name=1,
        )

    def refresh_zone_info(self, force_refresh=False):
        """
        Refresh zone info from KumoCloud v3 API.

        inputs:
            force_refresh(bool): if True, ignore expiration timer.
        returns:
            None, zone_data is refreshed.
        """
        now_time = time.time()
        # refresh if past expiration date or force_refresh option
        if force_refresh or (
            now_time >= (self.last_fetch_time + self.fetch_interval_sec)
        ):
            try:
                # Clear cache to force fresh data
                self.Thermostat._cache_expires_at = 0
                self.Thermostat._cached_sites = None
                self.Thermostat._cached_zones = None
                self.Thermostat._cached_devices = None

                self.last_fetch_time = now_time
                # refresh device object
                self.zone_info = self.Thermostat.get_all_metadata(self.zone_number)

            except Exception as exc:
                util.log_msg(
                    f"WARNING: Kumocloud v3 refresh failed: {exc}",
                    mode=util.BOTH_LOG,
                    func_name=1,
                )


if __name__ == "__main__":
    # verify environment
    env.get_python_version()
    # No need to show pykumo version since we're not using it
    print("Using KumoCloud v3 API implementation")

    # get zone override
    api.uip = api.UserInputs(argv_list=None, thermostat_type=kumocloudv3_config.ALIAS)
    zone_number = api.uip.get_user_inputs(api.uip.zone_name, api.input_flds.zone)

    _, Zone = tc.thermostat_basic_checkout(
        kumocloudv3_config.ALIAS, zone_number, ThermostatClass, ThermostatZone
    )

    tc.print_select_data_from_all_zones(
        kumocloudv3_config.ALIAS,
        kumocloudv3_config.get_available_zones(),
        ThermostatClass,
        ThermostatZone,
        display_wifi=True,
        display_battery=True,
    )

    # measure thermostat response time
    if kumocloudv3_config.check_response_time:
        MEASUREMENTS = 30
        meas_data = Zone.measure_thermostat_repeatability(
            MEASUREMENTS,
            func=Zone.get_display_temp,  # Use a simple method for testing
            measure_response_time=True,
        )
        ppp = pprint.PrettyPrinter(indent=4)
        ppp.pprint(meas_data)
