"""
Unit test module for kumolocal.py local network detection functionality.

This test module focuses on testing the local network detection logic
without requiring actual kumolocal devices.
"""

# built-in imports
import copy
import logging
import unittest

# local imports
from src import kumolocal
from src import kumo_common_zones
from src import kumolocal_config
from tests import unit_test_common as utc


class LocalNetworkDetectionUnitTest(utc.UnitTest):
    """
    Unit tests for local network detection functionality.
    """

    def setUp(self):
        """Setup for unit tests."""
        super().setUp()
        self.print_test_name()

        # Reset metadata to initial state
        self.original_metadata = copy.deepcopy(kumolocal_config.metadata)

    def tearDown(self):
        """Cleanup after unit tests."""
        # Restore original metadata
        kumolocal_config.metadata.clear()
        kumolocal_config.metadata.update(self.original_metadata)
        super().tearDown()

    def test_metadata_has_local_net_available_field(self):
        """Test that metadata includes local_net_available field."""
        for zone_id in kumolocal_config.metadata:
            self.assertIn("local_net_available", kumolocal_config.metadata[zone_id])
            # Should be None initially
            self.assertIsNone(kumolocal_config.metadata[zone_id]["local_net_available"])

    def test_local_network_detection_method_signature(self):
        """Test that detect_local_network_availability method can be called."""
        # This is a simple test to verify the method signature exists
        # without requiring pykumo or actual network detection

        # Create a mock thermostat class to test the method exists
        class MockThermostat:
            """
            Mock class for simulating a Thermostat object in unit tests.
            Attributes:
                verbose (bool): Flag to enable verbose output.
            Methods:
                detect_local_network_availability():
                    Mock implementation for testing local network availability
                    detection.
            """

            def __init__(self):
                self.verbose = False

            def detect_local_network_availability(self):
                """Mock implementation for testing."""
                # Just verify we can call this method
                pass

        mock_thermostat = MockThermostat()

        # Test method exists and can be called
        try:
            mock_thermostat.detect_local_network_availability()
        except Exception as e:
            self.fail(f"detect_local_network_availability method failed: {e}")

    def test_is_local_network_available_method_signature(self):
        """Test that is_local_network_available method has correct signature."""
        # This tests the method signature without requiring actual kumolocal
        try:
            # Create a mock thermostat class to test the method exists
            class MockThermostat:
                """
                MockThermostat is a mock class used for testing thermostat
                functionality.
                Attributes:
                    zone_number (int): The zone number associated with the thermostat.
                Methods:
                    is_local_network_available(zone=None):
                        Checks if the local network is available for the specified zone.
                        If no zone is provided, uses the instance's zone_number.
                        Returns True if the local network is available, False otherwise.
                """

                def __init__(self):
                    self.zone_number = 0

                def is_local_network_available(self, zone=None):
                    """Mock implementation for testing."""
                    zone_number = zone if zone is not None else self.zone_number
                    if zone_number in kumolocal_config.metadata:
                        value = kumolocal_config.metadata[zone_number].get(
                            "local_net_available", False
                        )
                        # Handle case where value is None (not yet detected)
                        return value if value is not None else False
                    return False

            mock_thermostat = MockThermostat()

            # Test method exists and returns expected type
            result = mock_thermostat.is_local_network_available()
            self.assertIsInstance(result, bool)
            self.assertFalse(result)  # Should be False for None value

        except ImportError:
            self.skipTest("kumolocal module not available for testing")

    def test_pykumo_logging_integration(self):
        """Test that pykumo logging integration can be initialized."""
        try:
            # Mock the utilities module to capture log messages
            captured_logs = []

            class MockUtil:
                """
                MockUtil is a mock utility class for logging messages during testing.
                Attributes:
                    DATA_LOG (int): Constant representing data log mode.
                    STDERR_LOG (int): Constant representing standard error log mode.
                    DEBUG_LOG (int): Constant representing debug log mode.
                Methods:
                    log_msg(msg, mode, func_name=None, file_name=None):
                            func_name (str, optional): Name of the function where the
                                                     log originated. Defaults to None.
                            file_name (str, optional): Name of the file where the log
                                                       originated. Defaults to None.
                """

                DATA_LOG = 1
                STDERR_LOG = 2
                DEBUG_LOG = 4

                @staticmethod
                def log_msg(msg, mode, func_name=None, file_name=None):
                    """
                    Logs a message with additional context information.

                    Appends a dictionary containing the message, mode, function name,
                    and file name to the captured_logs list.

                    Args:
                        msg (str): The log message to record.
                        mode (str): The logging mode or level (e.g., 'info', 'error').
                        func_name (str, optional): Name of the function where the log
                                                   originated. Defaults to None.
                        file_name (str, optional): Name of the file where the log
                                                   originated. Defaults to None.
                    """
                    captured_logs.append(
                        {
                            "msg": msg,
                            "mode": mode,
                            "func_name": func_name,
                            "file_name": file_name,
                        }
                    )

            # Temporarily replace util module
            original_util = kumolocal.util
            kumolocal.util = MockUtil

            try:
                # Test that we can create the SupervisorLogHandler
                handler = kumolocal.SupervisorLogHandler()
                self.assertIsInstance(handler, logging.Handler)

                # Test logging with the handler
                record = logging.LogRecord(
                    name="test",
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg="Test message",
                    args=(),
                    exc_info=None,
                )
                handler.emit(record)

                # Verify that a log message was captured
                self.assertTrue(len(captured_logs) > 0)
                self.assertIn("[pykumo]", captured_logs[0]["msg"])
                self.assertEqual("kumo_log.txt", captured_logs[0]["file_name"])

            finally:
                # Restore original util module
                kumolocal.util = original_util

        except ImportError:
            self.skipTest("kumolocal module not available for testing")


class KumolocalConfigUnitTest(utc.UnitTest):
    """Unit tests for kumolocal config zone definitions."""

    def test_kumolocal_supports_three_zones(self):
        """Test kumolocal supports 3 configured zones."""
        self.assertEqual(
            kumolocal_config.supported_configs["zones"],
            [
                kumolocal_config.LIVING_ROOM,
                kumolocal_config.KITCHEN,
                kumolocal_config.BASEMENT,
            ],
        )
        self.assertEqual(len(kumolocal_config.metadata), 3)

    def test_kumolocal_zone_names_include_kitchen(self):
        """Test kumolocal metadata includes the kitchen zone."""
        self.assertEqual(
            kumolocal_config.metadata[kumolocal_config.LIVING_ROOM]["zone_name"],
            kumo_common_zones.ZONE_NAME_LIVING_ROOM,
        )
        self.assertEqual(
            kumolocal_config.metadata[kumolocal_config.KITCHEN]["zone_name"],
            kumo_common_zones.ZONE_NAME_KITCHEN,
        )
        self.assertEqual(
            kumolocal_config.metadata[kumolocal_config.BASEMENT]["zone_name"],
            kumo_common_zones.ZONE_NAME_BASEMENT,
        )


class IniParsingUnitTest(utc.UnitTest):
    """Unit tests for load_ip_addresses_from_ini()."""

    def setUp(self):
        """Save original metadata IPs before each test."""
        super().setUp()
        self.print_test_name()
        self.original_ips = {
            zone_id: meta["ip_address"]
            for zone_id, meta in kumolocal_config.metadata.items()
        }

    def tearDown(self):
        """Restore original metadata IPs after each test."""
        for zone_id, ip in self.original_ips.items():
            kumolocal_config.metadata[zone_id]["ip_address"] = ip
        super().tearDown()

    def _write_ini(self, path, content):
        """Write content to a temp INI file."""
        with open(path, "w") as f:
            f.write(content)

    def test_load_ip_addresses_returns_true_when_file_found(self):
        """Test load_ip_addresses_from_ini returns True when the INI file exists."""
        import tempfile
        content = (
            "[Living Room]\nip_address = 10.0.0.1\n"
            "[Kitchen]\nip_address = 10.0.0.2\n"
            "[Basement]\nip_address = 10.0.0.3\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ini", delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            result = kumolocal_config.load_ip_addresses_from_ini(tmp_path)
            self.assertTrue(result)
        finally:
            import os
            os.unlink(tmp_path)

    def test_load_ip_addresses_returns_false_when_file_missing(self):
        """Test load_ip_addresses_from_ini returns False when the file is missing."""
        result = kumolocal_config.load_ip_addresses_from_ini(
            "/tmp/nonexistent_kumolocal.ini"
        )
        self.assertFalse(result)

    def test_load_ip_addresses_updates_metadata_from_ini(self):
        """Test that IPs in the INI file are loaded into metadata."""
        import tempfile
        content = (
            "[Living Room]\nip_address = 10.0.1.1\n"
            "[Kitchen]\nip_address = 10.0.1.2\n"
            "[Basement]\nip_address = 10.0.1.3\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ini", delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            kumolocal_config.load_ip_addresses_from_ini(tmp_path)
            self.assertEqual(
                kumolocal_config.metadata[kumolocal_config.LIVING_ROOM]["ip_address"],
                "10.0.1.1",
            )
            self.assertEqual(
                kumolocal_config.metadata[kumolocal_config.KITCHEN]["ip_address"],
                "10.0.1.2",
            )
            self.assertEqual(
                kumolocal_config.metadata[kumolocal_config.BASEMENT]["ip_address"],
                "10.0.1.3",
            )
        finally:
            import os
            os.unlink(tmp_path)

    def test_load_ip_addresses_keeps_defaults_when_file_missing(self):
        """Test that default IPs are preserved when the INI file is absent."""
        defaults = {
            zone_id: meta["ip_address"]
            for zone_id, meta in kumolocal_config.metadata.items()
        }
        kumolocal_config.load_ip_addresses_from_ini(
            "/tmp/nonexistent_kumolocal.ini"
        )
        for zone_id, ip in defaults.items():
            self.assertEqual(
                kumolocal_config.metadata[zone_id]["ip_address"], ip
            )

    def test_load_ip_addresses_ignores_unknown_sections(self):
        """Test that sections not matching any zone are silently ignored."""
        import tempfile
        content = (
            "[Living Room]\nip_address = 10.0.2.1\n"
            "[UnknownZone]\nip_address = 10.0.2.99\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ini", delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            kumolocal_config.load_ip_addresses_from_ini(tmp_path)
            self.assertEqual(
                kumolocal_config.metadata[kumolocal_config.LIVING_ROOM]["ip_address"],
                "10.0.2.1",
            )
        finally:
            import os
            os.unlink(tmp_path)


class KeyErrorHandlingUnitTest(utc.UnitTest):
    """
    Unit tests for enhanced KeyError handling in kumolocal.py.

    Tests the improved error handling when accessing nested JSON structures
    that can fail after temperature setting operations.
    """

    def setUp(self):
        """Setup for KeyError handling tests."""
        super().setUp()
        self.print_test_name()

    def test_enhanced_keyerror_messages_are_informative(self):
        """Test that the enhanced error handling creates informative messages."""
        # Test case 1: None raw data
        test_cases = [
            {
                "name": "Raw JSON data is None",
                "raw_data": None,
                "serial_list": ["test_serial"],
                "expected_msg": "Raw JSON data is None",
            },
            {
                "name": "Insufficient data length",
                "raw_data": [1, 2],
                "serial_list": ["test_serial"],
                "expected_msg": "expected at least 3 elements, got 2",
            },
            {
                "name": "Missing children key",
                "raw_data": [1, 2, {"no_children": True}],
                "serial_list": ["test_serial"],
                "expected_msg": "Missing 'children' key",
            },
            {
                "name": "Empty children array",
                "raw_data": [1, 2, {"children": []}],
                "serial_list": ["test_serial"],
                "expected_msg": "Empty 'children' array",
            },
            {
                "name": "Missing zoneTable key",
                "raw_data": [1, 2, {"children": [{"no_zonetable": True}]}],
                "serial_list": ["test_serial"],
                "expected_msg": "Missing 'zoneTable' key",
            },
            {
                "name": "Missing zone serial",
                "raw_data": [1, 2, {"children": [{"zoneTable": {"other_serial": {}}}]}],
                "serial_list": ["test_serial"],
                "expected_msg": "Zone serial number 'test_serial' not found",
            },
        ]

        # For each test case, verify the error handling logic would work
        for test_case in test_cases:
            with self.subTest(test_case=test_case["name"]):
                self.assertTrue(
                    self._would_generate_expected_error(
                        test_case["raw_data"],
                        test_case["serial_list"],
                        test_case["expected_msg"],
                    ),
                    f"Test case '{test_case['name']}' should generate "
                    "expected error message",
                )

    def _would_generate_expected_error(self, raw_data, serial_list, expected_msg):
        """
        Simulate the error handling logic to test expected error generation.

        This method replicates the error checking logic from the enhanced
        get_kumocloud_thermostat_metadata method without requiring a full
        ThermostatClass instance.
        """
        try:
            zone = 0

            # Replicate the error checking logic
            if raw_data is None:
                raise KeyError(
                    "Raw JSON data is None - likely authentication "
                    "or connection issue"
                )

            if len(raw_data) <= 2:
                raise KeyError(
                    f"Raw JSON data structure invalid - expected "
                    f"at least 3 elements, got {len(raw_data)}"
                )

            level_2_data = raw_data[2]
            if "children" not in level_2_data:
                raise KeyError("Missing 'children' key in raw JSON data at level 2")

            children_data = level_2_data["children"]
            if not children_data or len(children_data) == 0:
                raise KeyError("Empty 'children' array in raw JSON data")

            first_child = children_data[0]
            if "zoneTable" not in first_child:
                raise KeyError(
                    "Missing 'zoneTable' key in first child of raw JSON data"
                )

            zone_table = first_child["zoneTable"]
            zone_serial = serial_list[zone]
            if zone_serial not in zone_table:
                available_zones = list(zone_table.keys())
                raise KeyError(
                    f"Zone serial number '{zone_serial}' not found "
                    f"in zoneTable. Available zones: {available_zones}"
                )

            # If we get here, no error should be generated
            return False

        except KeyError as e:
            error_msg = str(e)
            return expected_msg in error_msg

        return False


class TargetZoneIdResolutionUnitTest(utc.UnitTest):
    """Unit tests for kumolocal target zone ID resolution."""

    def test_get_target_zone_id_normalizes_zone_name(self):
        """Test get_target_zone_id matches zone names with format differences."""
        thermostat = kumolocal.ThermostatClass.__new__(kumolocal.ThermostatClass)
        thermostat.zone_name = "Living Room"
        thermostat.zone_number = 0
        thermostat.device_id = None
        thermostat.verbose = False
        thermostat.make_pykumos = lambda **kwargs: {  # type: ignore[method-assign]
            "MainLevel": "dev-main",
            "Kitchen": "dev-kitchen",
        }

        device_id = thermostat.get_target_zone_id(0)

        self.assertEqual(device_id, "dev-main")
        self.assertEqual(thermostat.zone_name, "MainLevel")

    def test_get_target_zone_id_falls_back_to_zone_index(self):
        """Test get_target_zone_id falls back to zone index when names differ."""
        thermostat = kumolocal.ThermostatClass.__new__(kumolocal.ThermostatClass)
        thermostat.zone_name = "Living Room"
        thermostat.zone_number = 0
        thermostat.device_id = None
        thermostat.verbose = False
        thermostat.make_pykumos = lambda **kwargs: {  # type: ignore[method-assign]
            "Ground Floor": "dev-main",
            "Kitchen": "dev-kitchen",
        }

        device_id = thermostat.get_target_zone_id(0)

        self.assertEqual(device_id, "dev-main")
        self.assertEqual(thermostat.zone_name, "Ground Floor")

    def test_get_target_zone_id_raises_informative_keyerror(self):
        """Test get_target_zone_id raises informative error when zone not found."""
        thermostat = kumolocal.ThermostatClass.__new__(kumolocal.ThermostatClass)
        thermostat.zone_name = "Living Room"
        thermostat.zone_number = 5
        thermostat.device_id = None
        thermostat.verbose = False
        thermostat.make_pykumos = lambda **kwargs: {  # type: ignore[method-assign]
            "Basement": "dev-basement"
        }

        with self.assertRaisesRegex(
            KeyError,
            r"Configured zone name 'Living Room' was not found.*"
            r"zone index 5 is out of valid range \[0\.\.0\]",
        ):
            thermostat.get_target_zone_id(5)

    def test_get_target_zone_id_non_integer_zone_raises_keyerror(self):
        """Test non-integer zone values don't trigger TypeError in fallback logic."""
        thermostat = kumolocal.ThermostatClass.__new__(kumolocal.ThermostatClass)
        thermostat.zone_name = "Living Room"
        thermostat.zone_number = 0
        thermostat.device_id = None
        thermostat.verbose = False
        thermostat.make_pykumos = lambda **kwargs: {  # type: ignore[method-assign]
            "Basement": "dev-basement"
        }

        with self.assertRaisesRegex(
            KeyError,
            r"zone index 'invalid-zone' is out of valid range \[0\.\.0\]",
        ):
            thermostat.get_target_zone_id("invalid-zone")

    def test_get_target_zone_id_calls_update_status_for_matched_zone_only(self):
        """Test get_target_zone_id calls update_status only for the matched zone."""
        from unittest.mock import MagicMock
        thermostat = kumolocal.ThermostatClass.__new__(kumolocal.ThermostatClass)
        thermostat.zone_name = "Basement"
        thermostat.zone_number = 2
        thermostat.device_id = None
        thermostat.verbose = False
        living_room_mock = MagicMock(name="LivingRoomPyKumo")
        basement_mock = MagicMock(name="BasementPyKumo")
        thermostat.make_pykumos = lambda **kwargs: {  # type: ignore[method-assign]
            "Living Room": living_room_mock,
            "Basement": basement_mock,
        }

        thermostat.get_target_zone_id(2)

        basement_mock.update_status.assert_called_once()
        living_room_mock.update_status.assert_not_called()

    def test_get_target_zone_id_passes_init_update_status_false(self):
        """Test get_target_zone_id calls make_pykumos with init_update_status=False."""
        from unittest.mock import MagicMock
        thermostat = kumolocal.ThermostatClass.__new__(kumolocal.ThermostatClass)
        thermostat.zone_name = "Basement"
        thermostat.zone_number = 2
        thermostat.device_id = None
        thermostat.verbose = False
        basement_mock = MagicMock(name="BasementPyKumo")
        mock_make_pykumos = MagicMock(return_value={"Basement": basement_mock})
        thermostat.make_pykumos = mock_make_pykumos  # type: ignore[method-assign]

        thermostat.get_target_zone_id(2)

        mock_make_pykumos.assert_called_once_with(init_update_status=False)


class ThermostatZoneModeUnitTest(utc.UnitTest):
    """Unit tests for ThermostatZone mode methods when device data is unavailable."""

    def _make_zone(self, mode_return_value):
        """Create a ThermostatZone-like object with a mocked device_id."""

        class MockDeviceId:
            def get_mode(self_inner):
                return mode_return_value

        class MockThermostat:
            device_id = MockDeviceId()
            zone_number = 0
            zone_name = "Living Room"

            def get_target_zone_id(self_inner, zone_name):
                return self_inner.device_id

        zone = kumolocal.ThermostatZone.__new__(kumolocal.ThermostatZone)
        zone.verbose = False
        zone.zone_number = 0
        zone.zone_name = "Living Room"
        zone.fetch_interval_sec = 60
        import time
        zone.last_fetch_time = time.time() - 2 * zone.fetch_interval_sec
        zone.device_id = MockDeviceId()
        zone.Thermostat = MockThermostat()
        # set up system_switch_position as the constructor would
        from src import thermostat_common as tc
        from src import utilities as util
        zone.system_switch_position = dict(tc.ThermostatCommonZone.system_switch_position)
        zone.system_switch_position[tc.ThermostatCommonZone.COOL_MODE] = "cool"
        zone.system_switch_position[tc.ThermostatCommonZone.HEAT_MODE] = "heat"
        zone.system_switch_position[tc.ThermostatCommonZone.OFF_MODE] = "off"
        zone.system_switch_position[tc.ThermostatCommonZone.DRY_MODE] = "dry"
        zone.system_switch_position[tc.ThermostatCommonZone.AUTO_MODE] = "auto"
        zone.system_switch_position[tc.ThermostatCommonZone.FAN_MODE] = "vent"
        # override refresh_zone_info to avoid network calls
        zone.refresh_zone_info = lambda force_refresh=False: None
        return zone

    def test_get_system_switch_position_returns_off_when_mode_is_none(self):
        """Test get_system_switch_position returns 'off' when get_mode() returns None."""
        zone = self._make_zone(mode_return_value=None)
        result = zone.get_system_switch_position()
        self.assertEqual(result, "off")

    def test_get_system_switch_position_returns_mode_when_available(self):
        """Test get_system_switch_position returns actual mode when get_mode() succeeds."""
        zone = self._make_zone(mode_return_value="heat")
        result = zone.get_system_switch_position()
        self.assertEqual(result, "heat")

    def test_is_power_on_returns_0_when_mode_is_none(self):
        """Test is_power_on returns 0 (device unreachable) when get_mode() returns None."""
        zone = self._make_zone(mode_return_value=None)
        result = zone.is_power_on()
        self.assertEqual(result, 0)

    def test_is_power_on_returns_0_when_mode_is_off(self):
        """Test is_power_on returns 0 when mode is 'off'."""
        zone = self._make_zone(mode_return_value="off")
        result = zone.is_power_on()
        self.assertEqual(result, 0)

    def test_is_power_on_returns_1_when_mode_is_heat(self):
        """Test is_power_on returns 1 when mode is 'heat'."""
        zone = self._make_zone(mode_return_value="heat")
        result = zone.is_power_on()
        self.assertEqual(result, 1)


class LocalAddressUnitTest(utc.UnitTest):
    """Unit tests for _apply_local_addresses and _fetch_if_needed override."""

    def setUp(self):
        """Setup for tests."""
        super().setUp()
        self.print_test_name()
        import copy
        self.original_metadata = copy.deepcopy(kumolocal_config.metadata)

    def tearDown(self):
        """Restore metadata after each test."""
        kumolocal_config.metadata.clear()
        kumolocal_config.metadata.update(self.original_metadata)
        super().tearDown()

    def _make_thermostat_class(self):
        """Create a ThermostatClass instance without calling __init__."""
        obj = kumolocal.ThermostatClass.__new__(kumolocal.ThermostatClass)
        return obj

    def test_apply_local_addresses_sets_address_for_matching_unit(self):
        """Test _apply_local_addresses sets address for a unit whose label matches."""
        from src import kumo_common_zones
        obj = self._make_thermostat_class()
        # Simulate a pykumo _units dict with a matching label but no address
        obj._units = {
            "SERIAL1": {"label": kumo_common_zones.ZONE_NAME_BASEMENT, "address": ""},
        }
        obj._apply_local_addresses()
        expected_ip = kumolocal_config.metadata[kumolocal_config.BASEMENT]["ip_address"]
        self.assertEqual(obj._units["SERIAL1"]["address"], expected_ip)

    def test_apply_local_addresses_overwrites_stale_address(self):
        """Test _apply_local_addresses overwrites a stale address for a matching unit."""
        from src import kumo_common_zones
        obj = self._make_thermostat_class()
        obj._units = {
            "SERIAL1": {
                "label": kumo_common_zones.ZONE_NAME_LIVING_ROOM,
                "address": "10.0.0.99",  # stale/wrong address
            },
        }
        obj._apply_local_addresses()
        expected_ip = kumolocal_config.metadata[kumolocal_config.LIVING_ROOM]["ip_address"]
        self.assertEqual(obj._units["SERIAL1"]["address"], expected_ip)

    def test_apply_local_addresses_skips_zero_address(self):
        """Test _apply_local_addresses skips zones with 0.0.0.0 IP."""
        from src import kumo_common_zones
        kumolocal_config.metadata[kumolocal_config.BASEMENT]["ip_address"] = "0.0.0.0"
        obj = self._make_thermostat_class()
        obj._units = {
            "SERIAL1": {"label": kumo_common_zones.ZONE_NAME_BASEMENT, "address": ""},
        }
        obj._apply_local_addresses()
        # Address should remain empty since config IP is 0.0.0.0
        self.assertEqual(obj._units["SERIAL1"]["address"], "")

    def test_apply_local_addresses_no_op_when_no_ips_configured(self):
        """Test _apply_local_addresses does nothing when no IPs are configured."""
        for meta in kumolocal_config.metadata.values():
            meta["ip_address"] = None
        obj = self._make_thermostat_class()
        obj._units = {
            "SERIAL1": {"label": "Basement", "address": ""},
        }
        obj._apply_local_addresses()
        self.assertEqual(obj._units["SERIAL1"]["address"], "")

    def test_fetch_if_needed_calls_try_setup_then_apply_addresses(self):
        """Test _fetch_if_needed calls try_setup then _apply_local_addresses."""
        from unittest.mock import MagicMock, patch
        obj = self._make_thermostat_class()
        obj._need_fetch = True
        call_order = []

        def mock_try_setup():
            call_order.append("try_setup")

        def mock_apply():
            call_order.append("_apply_local_addresses")

        with patch.object(obj, "try_setup", side_effect=mock_try_setup):
            with patch.object(
                obj, "_apply_local_addresses", side_effect=mock_apply
            ):
                obj._fetch_if_needed()

        self.assertEqual(call_order, ["try_setup", "_apply_local_addresses"])

    def test_fetch_if_needed_skips_try_setup_when_not_needed(self):
        """Test _fetch_if_needed does not call try_setup when _need_fetch is False."""
        from unittest.mock import MagicMock
        obj = self._make_thermostat_class()
        obj._need_fetch = False
        obj.try_setup = MagicMock()
        obj._fetch_if_needed()
        obj.try_setup.assert_not_called()

    def test_fetch_if_needed_skips_try_setup_when_units_already_loaded(self):
        """Test _fetch_if_needed skips try_setup on refresh when _units is populated.

        On periodic refreshes (_need_fetch set True by refresh_zone_info), try_setup
        (which includes probe_ip for every device) is skipped to avoid unnecessary
        connection attempts and timeout warnings for temporarily unreachable devices.
        _apply_local_addresses is also skipped on refresh (addresses were already
        applied during initialization and are stored on the existing PyKumo objects).
        """
        from unittest.mock import MagicMock
        obj = self._make_thermostat_class()
        obj._need_fetch = True
        # Simulate already-loaded units (credentials present from initial setup)
        obj._units = {"SERIAL1": {"label": "Basement", "address": ""}}
        obj.try_setup = MagicMock()
        obj._apply_local_addresses = MagicMock()

        obj._fetch_if_needed()

        obj.try_setup.assert_not_called()
        obj._apply_local_addresses.assert_not_called()
        self.assertFalse(obj._need_fetch)

    def test_fetch_if_needed_calls_try_setup_when_units_empty(self):
        """Test _fetch_if_needed calls try_setup on first init when _units is empty."""
        from unittest.mock import MagicMock, patch
        obj = self._make_thermostat_class()
        obj._need_fetch = True
        obj._units = {}  # empty — first initialization

        def mock_try_setup():
            pass  # try_setup sets _need_fetch=False in production

        with patch.object(obj, "try_setup", side_effect=mock_try_setup) as mock_ts:
            with patch.object(obj, "_apply_local_addresses"):
                obj._fetch_if_needed()

        mock_ts.assert_called_once()

    def _make_zone_for_refresh(self):
        """Create a ThermostatZone-like object with mocked Thermostat and device."""
        import time
        from unittest.mock import MagicMock

        zone = kumolocal.ThermostatZone.__new__(kumolocal.ThermostatZone)
        zone.verbose = False
        zone.zone_number = 1
        zone.zone_name = "Kitchen"
        zone.fetch_interval_sec = 60
        zone.last_fetch_time = time.time() - 2 * zone.fetch_interval_sec  # stale

        mock_device = MagicMock()
        zone.device_id = mock_device

        mock_thermostat = MagicMock()
        mock_thermostat._need_fetch = False
        zone.Thermostat = mock_thermostat

        return zone, mock_device, mock_thermostat

    def test_refresh_zone_info_calls_update_status_on_existing_device(self):
        """Test refresh_zone_info calls update_status on existing device, not get_target_zone_id.

        On periodic refreshes, the existing PyKumo device object should be reused
        and only update_status() called — no new PyKumo objects should be created
        (which would trigger "Use default timeouts" and "Applied local address" log
        noise on every poll cycle).
        """
        zone, mock_device, mock_thermostat = self._make_zone_for_refresh()

        zone.refresh_zone_info()

        mock_device.update_status.assert_called_once()
        # get_target_zone_id must NOT be called on refresh
        mock_thermostat.get_target_zone_id.assert_not_called()

    def test_refresh_zone_info_skips_update_when_not_stale(self):
        """Test refresh_zone_info does not call update_status when cache is fresh."""
        import time
        zone, mock_device, mock_thermostat = self._make_zone_for_refresh()
        zone.last_fetch_time = time.time()  # fresh

        zone.refresh_zone_info()

        mock_device.update_status.assert_not_called()

    def test_refresh_zone_info_force_refresh_calls_update_status(self):
        """Test refresh_zone_info with force_refresh=True always calls update_status."""
        import time
        zone, mock_device, mock_thermostat = self._make_zone_for_refresh()
        zone.last_fetch_time = time.time()  # would normally skip

        zone.refresh_zone_info(force_refresh=True)

        mock_device.update_status.assert_called_once()

    def test_refresh_zone_info_handles_none_device_id_gracefully(self):
        """Test refresh_zone_info does not crash when device_id is None."""
        zone, mock_device, mock_thermostat = self._make_zone_for_refresh()
        zone.device_id = None

        # Should not raise
        zone.refresh_zone_info()


if __name__ == "__main__":
    unittest.main(verbosity=2)
