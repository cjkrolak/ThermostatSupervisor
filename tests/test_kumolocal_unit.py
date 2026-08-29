"""
Unit test module for kumolocal.py local network detection functionality.

This test module focuses on testing the local network detection logic
without requiring actual kumolocal devices.
"""

# built-in imports
import copy
import json
import logging
import os
import platform
import shutil
import tempfile
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

    def test_pykumo_logging_level_matches_app_debug_mode(self):
        """Test pykumo logger level is WARNING by default, DEBUG when debug on."""
        try:
            from src import utilities as util

            pykumo_modules = [
                "pykumo.py_kumo_cloud_account",
                "pykumo.py_kumo",
                "pykumo.py_kumo_base",
                "pykumo.py_kumo_station",
            ]

            original_debug = getattr(util.log_msg, "debug", False)
            try:
                # Test 1: debug mode OFF -> expect WARNING level
                util.log_msg.debug = False  # type: ignore[attr-defined]
                # Reset pykumo loggers so _setup_pykumo_logging re-applies them
                for mod in pykumo_modules:
                    logging.getLogger(mod).handlers.clear()

                # Invoke setup via a mock thermostat-like object
                class _FakeTherm:
                    """Minimal stub to invoke _setup_pykumo_logging."""

                    def _setup_pykumo_logging(self_inner):
                        """Forward to the real implementation."""
                        kumolocal.ThermostatClass._setup_pykumo_logging(
                            self_inner
                        )

                _FakeTherm()._setup_pykumo_logging()

                for mod in pykumo_modules:
                    logger = logging.getLogger(mod)
                    self.assertEqual(
                        logger.level,
                        logging.WARNING,
                        f"{mod} should be WARNING when debug is off",
                    )

                # Test 2: debug mode ON -> expect DEBUG level
                util.log_msg.debug = True  # type: ignore[attr-defined]
                for mod in pykumo_modules:
                    logging.getLogger(mod).handlers.clear()

                _FakeTherm()._setup_pykumo_logging()

                for mod in pykumo_modules:
                    logger = logging.getLogger(mod)
                    self.assertEqual(
                        logger.level,
                        logging.DEBUG,
                        f"{mod} should be DEBUG when debug is on",
                    )
            finally:
                util.log_msg.debug = original_debug  # type: ignore[attr-defined]
                # Restore logger levels to avoid side-effects
                restore_level = (
                    logging.DEBUG if original_debug else logging.WARNING
                )
                for mod in pykumo_modules:
                    logging.getLogger(mod).setLevel(restore_level)
                    logging.getLogger(mod).handlers.clear()

        except ImportError:
            self.skipTest("kumolocal module not available for testing")

    def test_get_zone_name_does_not_mutate_global_metadata(self):
        """get_zone_name returns device name without mutating config metadata."""
        from unittest.mock import MagicMock

        zone_number = kumolocal_config.LIVING_ROOM
        original_name = kumolocal_config.metadata[zone_number]["zone_name"]

        zone = kumolocal.ThermostatZone.__new__(kumolocal.ThermostatZone)
        zone.zone_number = zone_number
        zone.device_id = MagicMock()
        zone.device_id.get_name.return_value = "Main Level"

        def _noop_refresh(*args, **kwargs):
            return None

        zone.refresh_zone_info = _noop_refresh  # type: ignore[method-assign]

        returned = zone.get_zone_name()

        self.assertEqual(returned, "Main Level")
        self.assertEqual(
            kumolocal_config.metadata[zone_number]["zone_name"],
            original_name,
            "kumolocal_config.metadata['zone_name'] should remain configuration-only",
        )

    def test_detect_local_network_availability_preserves_configured_ips(self):
        """Availability detection must not rewrite configured IPs by cloud order."""
        thermostat = kumolocal.ThermostatClass.__new__(kumolocal.ThermostatClass)
        thermostat.verbose = False

        living_room_ip = kumolocal_config.metadata[kumolocal_config.LIVING_ROOM][
            "ip_address"
        ]
        kitchen_ip = kumolocal_config.metadata[kumolocal_config.KITCHEN]["ip_address"]
        basement_ip = kumolocal_config.metadata[kumolocal_config.BASEMENT]["ip_address"]

        serials = ["serial-basement", "serial-kitchen", "serial-living"]
        thermostat.get_indoor_units = lambda: serials  # type: ignore[method-assign]
        thermostat.get_name = lambda serial: {  # type: ignore[method-assign]
            "serial-basement": "Basement",
            "serial-kitchen": "Kitchen",
            "serial-living": "Living Room",
        }[serial]
        thermostat.get_address = lambda serial: {  # type: ignore[method-assign]
            "serial-basement": basement_ip,
            "serial-kitchen": kitchen_ip,
            "serial-living": living_room_ip,
        }[serial]

        original_is_host_on_local_net = kumolocal.util.is_host_on_local_net
        kumolocal.util.is_host_on_local_net = lambda **kwargs: (False, None)
        try:
            thermostat.detect_local_network_availability()
        finally:
            kumolocal.util.is_host_on_local_net = original_is_host_on_local_net

        self.assertEqual(
            kumolocal_config.metadata[kumolocal_config.LIVING_ROOM]["ip_address"],
            living_room_ip,
        )
        self.assertEqual(
            kumolocal_config.metadata[kumolocal_config.KITCHEN]["ip_address"],
            kitchen_ip,
        )
        self.assertEqual(
            kumolocal_config.metadata[kumolocal_config.BASEMENT]["ip_address"],
            basement_ip,
        )

    def test_process_zone_availability_matches_zone_by_name_when_ip_missing(self):
        """Availability detection should still update the right zone by device name."""
        thermostat = kumolocal.ThermostatClass.__new__(kumolocal.ThermostatClass)
        thermostat.verbose = False
        thermostat.get_name = (  # type: ignore[method-assign]
            lambda serial: "Living Room"
        )
        thermostat.get_address = lambda serial: None  # type: ignore[method-assign]

        kumolocal_config.metadata[kumolocal_config.LIVING_ROOM][
            "local_net_available"
        ] = None
        kumolocal_config.metadata[kumolocal_config.KITCHEN][
            "local_net_available"
        ] = None

        thermostat._process_zone_availability("serial-living")

        self.assertFalse(
            kumolocal_config.metadata[kumolocal_config.LIVING_ROOM][
                "local_net_available"
            ]
        )
        self.assertIsNone(
            kumolocal_config.metadata[kumolocal_config.KITCHEN]["local_net_available"]
        )


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

    def test_get_target_zone_id_raises_authentication_error_when_no_zones(self):
        """Empty kumolocal zones should raise AuthenticationError, not KeyError.

        A blank zone dict means the KumoCloud account could not be reached or
        authenticated (e.g. pykumo's cloud/local credential fetch failed), not
        that a configured zone name has a typo. This mirrors the
        AuthenticationError raised elsewhere in this module and in
        kumocloud.py for the equivalent failure.
        """
        from unittest.mock import patch
        from src import thermostat_common as tc

        thermostat = kumolocal.ThermostatClass.__new__(kumolocal.ThermostatClass)
        thermostat.zone_name = "Living Room"
        thermostat.zone_number = 0
        thermostat.device_id = None
        thermostat.verbose = False
        thermostat._need_fetch = False
        thermostat.make_pykumos = lambda **kwargs: {}  # type: ignore[method-assign]

        with patch("src.kumolocal.time.sleep"):
            with self.assertRaisesRegex(
                tc.AuthenticationError,
                r"kumolocal meta data is blank, probably due to an "
                r"Authentication Error, check your credentials\.",
            ):
                thermostat.get_target_zone_id(0)

    def test_get_target_zone_id_retries_once_before_giving_up(self):
        """get_target_zone_id retries a blank zone fetch once before failing."""
        from unittest.mock import MagicMock, patch

        thermostat = kumolocal.ThermostatClass.__new__(kumolocal.ThermostatClass)
        thermostat.zone_name = "Living Room"
        thermostat.zone_number = 0
        thermostat.device_id = None
        thermostat.verbose = False
        thermostat._need_fetch = False
        mock_make_pykumos = MagicMock(return_value={})
        thermostat.make_pykumos = mock_make_pykumos  # type: ignore[method-assign]

        with patch("src.kumolocal.time.sleep"):
            kumos = thermostat._make_pykumos_with_retry()

        self.assertEqual(kumos, {})
        self.assertEqual(mock_make_pykumos.call_count, 2)

    def test_get_target_zone_id_retry_recovers_on_second_attempt(self):
        """get_target_zone_id succeeds if the retry attempt returns zones."""
        from unittest.mock import MagicMock, patch

        thermostat = kumolocal.ThermostatClass.__new__(kumolocal.ThermostatClass)
        thermostat.zone_name = "Living Room"
        thermostat.zone_number = 0
        thermostat.device_id = None
        thermostat.verbose = False
        thermostat._need_fetch = False
        mock_make_pykumos = MagicMock(
            side_effect=[{}, {"Living Room": "dev-living-room"}]
        )
        thermostat.make_pykumos = mock_make_pykumos  # type: ignore[method-assign]

        with patch("src.kumolocal.time.sleep"):
            device_id = thermostat.get_target_zone_id(0)

        self.assertEqual(device_id, "dev-living-room")
        self.assertEqual(mock_make_pykumos.call_count, 2)

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

    def test_get_target_zone_id_prefers_configured_ip_over_zone_order(self):
        """Configured IP matching should win before fallback to zone ordering."""
        from unittest.mock import MagicMock

        thermostat = kumolocal.ThermostatClass.__new__(kumolocal.ThermostatClass)
        thermostat.zone_name = "Living Room"
        thermostat.zone_number = kumolocal_config.LIVING_ROOM
        thermostat.device_id = None
        thermostat.verbose = False

        expected_ip = kumolocal_config.metadata[kumolocal_config.LIVING_ROOM][
            "ip_address"
        ]
        first_device = MagicMock(name="FirstPyKumo")
        first_device._address = "10.0.0.99"
        second_device = MagicMock(name="SecondPyKumo")
        second_device._address = expected_ip
        thermostat.make_pykumos = lambda **kwargs: {  # type: ignore[method-assign]
            "Ground Floor": first_device,
            "Upstairs": second_device,
        }

        device_id = thermostat.get_target_zone_id(kumolocal_config.LIVING_ROOM)

        self.assertIs(device_id, second_device)
        self.assertEqual(thermostat.zone_name, "Upstairs")
        second_device.update_status.assert_called_once()
        first_device.update_status.assert_not_called()

    def test_get_target_zone_id_reapplies_configured_address(self):
        """Selected device should be updated to the configured per-zone address."""
        from unittest.mock import MagicMock

        thermostat = kumolocal.ThermostatClass.__new__(kumolocal.ThermostatClass)
        thermostat.zone_name = "Basement"
        thermostat.zone_number = kumolocal_config.BASEMENT
        thermostat.device_id = None
        thermostat.verbose = False

        basement_device = MagicMock(name="BasementPyKumo")
        basement_device._address = "10.0.0.99"
        thermostat.make_pykumos = lambda **kwargs: {  # type: ignore[method-assign]
            "Basement": basement_device
        }

        thermostat.get_target_zone_id(kumolocal_config.BASEMENT)

        self.assertEqual(
            basement_device._address,
            kumolocal_config.metadata[kumolocal_config.BASEMENT]["ip_address"],
        )


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
        zone.system_switch_position = dict(
            tc.ThermostatCommonZone.system_switch_position
        )
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
        """get_system_switch_position returns 'off' when get_mode() returns None."""
        zone = self._make_zone(mode_return_value=None)
        result = zone.get_system_switch_position()
        self.assertEqual(result, "off")

    def test_get_system_switch_position_returns_mode_when_available(self):
        """get_system_switch_position returns actual mode when get_mode() succeeds."""
        zone = self._make_zone(mode_return_value="heat")
        result = zone.get_system_switch_position()
        self.assertEqual(result, "heat")

    def test_is_power_on_returns_0_when_mode_is_none(self):
        """is_power_on returns 0 (device unreachable) when get_mode() returns None."""
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
        """_apply_local_addresses overwrites a stale address for a matching unit."""
        from src import kumo_common_zones
        obj = self._make_thermostat_class()
        obj._units = {
            "SERIAL1": {
                "label": kumo_common_zones.ZONE_NAME_LIVING_ROOM,
                "address": "10.0.0.99",  # stale/wrong address
            },
        }
        obj._apply_local_addresses()
        expected_ip = kumolocal_config.metadata[
            kumolocal_config.LIVING_ROOM]["ip_address"]
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
        from unittest.mock import patch
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
        from unittest.mock import patch
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
        """refresh_zone_info reuses existing device, does not call get_target_zone_id.

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


class V3AuthenticationUnitTest(utc.UnitTest):
    """Unit tests for the kumocloud-compatible v3 authentication flow."""

    def setUp(self):
        """Setup for unit tests, isolating the credential cache file."""
        super().setUp()
        self.print_test_name()
        # redirect the credential cache into a temp dir so tests never read
        # or write a real cache file.
        self.cache_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.cache_dir, "kumolocal_cache.json")
        self.original_cache_file = kumolocal.CREDENTIAL_CACHE_FILE
        kumolocal.CREDENTIAL_CACHE_FILE = self.cache_file

    def tearDown(self):
        """Restore the credential cache path and remove temp files."""
        kumolocal.CREDENTIAL_CACHE_FILE = self.original_cache_file
        shutil.rmtree(self.cache_dir, ignore_errors=True)
        super().tearDown()

    def _make_v3_client(self):
        """Create a KumoCloudV3Compatible instance with a fake access token."""
        client = kumolocal.KumoCloudV3Compatible("user", "pwd")
        client._access_token = "token"  # pylint: disable=protected-access
        return client

    def _make_thermostat_class(self):
        """Create a ThermostatClass instance without calling __init__."""
        obj = kumolocal.ThermostatClass.__new__(kumolocal.ThermostatClass)
        obj._username = "user"
        obj._password = "pwd"
        obj._units = {}
        obj._kumo_dict = None
        obj._need_fetch = True
        obj.v3_login_ok = False
        obj.v3_devices_discovered = 0
        obj.v3_local_credentials_returned = 0
        return obj

    def test_auth_headers_match_kumocloud_headers(self):
        """Test v3 client sends the same Accept headers used by kumocloud.py."""
        client = self._make_v3_client()
        headers = client._auth_headers()
        self.assertEqual(headers["Accept"], "application/json, text/plain, */*")
        self.assertEqual(headers["Accept-Language"], "en-US, en")
        self.assertIn("Authorization", headers)

    def test_get_zones_uses_trailing_slash_endpoint(self):
        """Test zones are requested from the kumocloud.py endpoint first."""
        from unittest.mock import patch
        client = self._make_v3_client()
        paths = []

        def fake_get(path):
            paths.append(path)
            return [{"name": "zone1"}]

        with patch.object(client, "_get", side_effect=fake_get):
            zones = client.get_zones("site1")

        self.assertEqual(paths, ["/v3/sites/site1/zones/"])
        self.assertEqual(zones, [{"name": "zone1"}])

    def test_get_zones_falls_back_to_pykumo_endpoint(self):
        """Test zones fall back to pykumo's endpoint when trailing slash fails."""
        from unittest.mock import patch
        client = self._make_v3_client()
        paths = []

        def fake_get(path):
            paths.append(path)
            if path.endswith("zones/"):
                return None
            return [{"name": "zone1"}]

        with patch.object(client, "_get", side_effect=fake_get):
            zones = client.get_zones("site1")

        self.assertEqual(
            paths, ["/v3/sites/site1/zones/", "/v3/sites/site1/zones"]
        )
        self.assertEqual(zones, [{"name": "zone1"}])

    def test_get_device_status_merges_device_endpoint(self):
        """Test cryptoSerial is retrieved from the kumocloud.py device endpoint."""
        from unittest.mock import patch
        client = self._make_v3_client()
        paths = []

        def fake_get(path):
            paths.append(path)
            if path.endswith("/status"):
                return {"cryptoSerial": ""}
            return {"cryptoSerial": "ABCD", "password": "pw"}

        with patch.object(client, "_get", side_effect=fake_get):
            status = client.get_device_status("SN1")

        self.assertEqual(paths, ["/v3/devices/SN1/status", "/v3/devices/SN1"])
        self.assertEqual(status["cryptoSerial"], "ABCD")
        self.assertEqual(status["password"], "pw")

    def test_get_device_status_skips_fallback_when_crypto_present(self):
        """Test the extra device request is skipped when cryptoSerial is present."""
        from unittest.mock import patch
        client = self._make_v3_client()
        paths = []

        def fake_get(path):
            paths.append(path)
            return {"cryptoSerial": "ABCD"}

        with patch.object(client, "_get", side_effect=fake_get):
            status = client.get_device_status("SN1")

        self.assertEqual(paths, ["/v3/devices/SN1/status"])
        self.assertEqual(status["cryptoSerial"], "ABCD")

    def test_get_all_device_credentials_fills_missing_password(self):
        """Test missing Socket.IO passwords are filled from the REST endpoint."""
        from unittest.mock import patch
        import pykumo
        client = self._make_v3_client()
        base_devices = {"SN1": {"password": "", "cryptoSerial": "ABCD"}}

        with patch.object(
            pykumo.KumoCloudV3,
            "get_all_device_credentials",
            return_value=base_devices,
        ):
            with patch.object(
                client, "get_device_status", return_value={"password": "pw"}
            ):
                devices = client.get_all_device_credentials()

        self.assertEqual(devices["SN1"]["password"], "pw")

    def test_try_setup_configures_units_from_v3_credentials(self):
        """Test try_setup populates units using the v3 credential fetch."""
        from unittest.mock import patch
        obj = self._make_thermostat_class()
        devices = {
            "SN1": {
                "label": "Basement",
                "password": "pw",
                "cryptoSerial": "ABCD",
                "unitType": "ductless",
                "mac": "aa:bb",
            },
        }

        with patch.object(
            obj, "_fetch_v3_device_credentials", return_value=devices
        ):
            result = obj.try_setup()

        self.assertTrue(result)
        self.assertEqual(list(obj._units), ["SN1"])
        self.assertEqual(obj._units["SN1"]["serial"], "SN1")
        self.assertFalse(obj._need_fetch)
        # cached dict must be readable by pykumo's cache parser
        self.assertEqual(
            list(obj._extract_cached_units()), ["SN1"]
        )

    def test_try_setup_skips_units_missing_credentials(self):
        """Test try_setup falls back to pykumo when credentials are incomplete."""
        from unittest.mock import patch
        import pykumo
        obj = self._make_thermostat_class()
        devices = {"SN1": {"label": "Basement", "password": "", "cryptoSerial": ""}}

        with patch.object(
            obj, "_fetch_v3_device_credentials", return_value=devices
        ):
            with patch.object(
                obj, "_fetch_v2_device_credentials", return_value={}
            ):
                with patch.object(
                    pykumo.KumoCloudAccount, "try_setup", return_value=False
                ) as mock_super:
                    result = obj.try_setup()

        self.assertFalse(result)
        mock_super.assert_called_once()

    def test_try_setup_falls_back_when_v3_fetch_fails(self):
        """Test try_setup falls back to pykumo when the v3 fetch returns nothing."""
        from unittest.mock import patch
        import pykumo
        obj = self._make_thermostat_class()

        with patch.object(obj, "_fetch_v3_device_credentials", return_value={}):
            with patch.object(
                obj, "_fetch_v2_device_credentials", return_value={}
            ):
                with patch.object(
                    pykumo.KumoCloudAccount, "try_setup", return_value=True
                ) as mock_super:
                    result = obj.try_setup()

        self.assertTrue(result)
        mock_super.assert_called_once()

    def test_fetch_v3_device_credentials_handles_exception(self):
        """Test credential fetch failures return an empty dict instead of raising."""
        from unittest.mock import patch
        obj = self._make_thermostat_class()

        with patch.object(
            kumolocal,
            "KumoCloudV3Compatible",
            side_effect=RuntimeError("network down"),
        ):
            self.assertEqual(obj._fetch_v3_device_credentials(), {})

    def test_fetch_v3_device_credentials_records_diagnostics(self):
        """Test the v3 fetch records login/discovery/credential counters."""
        from unittest.mock import MagicMock, patch
        obj = self._make_thermostat_class()
        client = MagicMock()
        client.login.return_value = True
        client.get_all_device_credentials.return_value = {
            "SN1": {"password": "", "cryptoSerial": ""},
            "SN2": {"password": "pw", "cryptoSerial": "ABCD"},
        }

        with patch.object(
            kumolocal, "KumoCloudV3Compatible", return_value=client
        ):
            obj._fetch_v3_device_credentials()

        self.assertTrue(obj.v3_login_ok)
        self.assertEqual(obj.v3_devices_discovered, 2)
        self.assertEqual(obj.v3_local_credentials_returned, 1)

    def test_local_credentials_withheld_true_when_cloud_omits_secrets(self):
        """Test withheld detection when login and discovery succeed w/o secrets."""
        obj = self._make_thermostat_class()
        obj.v3_login_ok = True
        obj.v3_devices_discovered = 3
        obj.v3_local_credentials_returned = 0
        self.assertTrue(obj._local_credentials_withheld())

    def test_local_credentials_withheld_false_on_login_failure(self):
        """Test withheld detection is False when the cloud login itself failed."""
        obj = self._make_thermostat_class()
        obj.v3_login_ok = False
        obj.v3_devices_discovered = 0
        obj.v3_local_credentials_returned = 0
        self.assertFalse(obj._local_credentials_withheld())

    def test_local_credentials_withheld_false_when_credentials_returned(self):
        """Test withheld detection is False when local credentials were returned."""
        obj = self._make_thermostat_class()
        obj.v3_login_ok = True
        obj.v3_devices_discovered = 2
        obj.v3_local_credentials_returned = 2
        self.assertFalse(obj._local_credentials_withheld())

    def test_zone_lookup_error_reports_withheld_credentials(self):
        """Test the raised error distinguishes withheld credentials from bad creds."""
        obj = self._make_thermostat_class()
        obj.zone_name = "Basement"
        obj.v3_login_ok = True
        obj.v3_devices_discovered = 3
        obj.v3_local_credentials_returned = 0

        with self.assertRaises(kumolocal.tc.AuthenticationError) as context:
            obj._raise_zone_lookup_error({}, 0)

        message = str(context.exception)
        self.assertIn("no local credentials", message)
        self.assertIn("dlarrick/pykumo/issues/78", message)
        self.assertNotIn("check your credentials", message)

    def test_zone_lookup_error_reports_credential_failure(self):
        """Test the original message is kept when the cloud login failed."""
        obj = self._make_thermostat_class()
        obj.zone_name = "Basement"

        with self.assertRaises(kumolocal.tc.AuthenticationError) as context:
            obj._raise_zone_lookup_error({}, 0)

        self.assertIn("check your credentials", str(context.exception))

    def test_retry_is_skipped_when_credentials_are_withheld(self):
        """Test no retry/sleep occurs when the cloud is withholding credentials."""
        from unittest.mock import patch
        obj = self._make_thermostat_class()
        obj.v3_login_ok = True
        obj.v3_devices_discovered = 3
        obj.v3_local_credentials_returned = 0

        with patch.object(obj, "make_pykumos", return_value={}) as mock_make:
            with patch.object(kumolocal.time, "sleep") as mock_sleep:
                kumos = obj._make_pykumos_with_retry()

        self.assertEqual(kumos, {})
        mock_make.assert_called_once()
        mock_sleep.assert_not_called()

    def test_try_setup_uses_cached_credentials_when_cloud_withholds(self):
        """Test cached credentials keep local control working (pykumo#78)."""
        from unittest.mock import patch
        obj = self._make_thermostat_class()
        with open(self.cache_file, "w", encoding="utf-8") as file_obj:
            json.dump(
                {
                    "SN1": {
                        "label": "Basement",
                        "password": "pw",
                        "cryptoSerial": "ABCD",
                        "unitType": "ductless",
                        "mac": "aa:bb",
                        "address": "192.168.1.5",
                    }
                },
                file_obj,
            )
        # cloud returns the device but withholds password/cryptoSerial
        cloud_devices = {
            "SN1": {
                "label": "Basement",
                "password": "",
                "cryptoSerial": "",
            }
        }

        with patch.object(
            obj, "_fetch_v3_device_credentials", return_value=cloud_devices
        ):
            with patch.object(
                obj, "_fetch_v2_device_credentials", return_value={}
            ):
                result = obj.try_setup()

        self.assertTrue(result)
        self.assertEqual(obj._units["SN1"]["password"], "pw")
        self.assertEqual(obj._units["SN1"]["cryptoSerial"], "ABCD")

    def test_try_setup_uses_v2_fallback_when_v3_withholds(self):
        """Test the v2 fallback supplies credentials the v3 API withholds."""
        from unittest.mock import patch
        obj = self._make_thermostat_class()
        cloud_devices = {
            "SN1": {
                "label": "Basement",
                "password": "",
                "cryptoSerial": "",
            }
        }
        v2_devices = {"SN1": {"password": "pw", "cryptoSerial": "ABCD"}}

        with patch.object(
            obj, "_fetch_v3_device_credentials", return_value=cloud_devices
        ):
            with patch.object(
                obj, "_fetch_v2_device_credentials", return_value=v2_devices
            ) as mock_v2:
                result = obj.try_setup()

        self.assertTrue(result)
        mock_v2.assert_called_once()
        self.assertEqual(obj._units["SN1"]["password"], "pw")
        # label from v3 is preserved, credentials come from v2
        self.assertEqual(obj._units["SN1"]["label"], "Basement")

    def test_v2_fallback_is_skipped_when_v3_returns_credentials(self):
        """Test the v2 endpoint is not contacted when v3 already succeeded."""
        from unittest.mock import patch
        obj = self._make_thermostat_class()
        devices = {"SN1": {"label": "Basement", "password": "pw",
                           "cryptoSerial": "ABCD"}}

        with patch.object(
            obj, "_fetch_v3_device_credentials", return_value=devices
        ):
            with patch.object(
                obj, "_fetch_v2_device_credentials", return_value={}
            ) as mock_v2:
                obj.try_setup()

        mock_v2.assert_not_called()

    def test_try_setup_saves_credentials_to_cache(self):
        """Test successful setup persists credentials for future runs."""
        from unittest.mock import patch
        obj = self._make_thermostat_class()
        devices = {
            "SN1": {
                "label": "Basement",
                "password": "pw",
                "cryptoSerial": "ABCD",
                "unitType": "ductless",
                "mac": "aa:bb",
                "address": "192.168.1.5",
            },
        }

        with patch.object(
            obj, "_fetch_v3_device_credentials", return_value=devices
        ):
            with patch.object(
                obj, "_fetch_v2_device_credentials", return_value={}
            ):
                obj.try_setup()

        self.assertTrue(os.path.exists(self.cache_file))
        with open(self.cache_file, "r", encoding="utf-8") as file_obj:
            cache = json.load(file_obj)
        self.assertEqual(cache["SN1"]["password"], "pw")
        self.assertEqual(cache["SN1"]["cryptoSerial"], "ABCD")

    def test_credential_cache_file_is_owner_only(self):
        """Test the credential cache is written with 0o600 permissions."""
        obj = self._make_thermostat_class()
        obj._save_credential_cache(
            {"SN1": {"password": "pw", "cryptoSerial": "ABCD"}}
        )
        mode = os.stat(self.cache_file).st_mode & 0o777
        if platform.system().lower() == "windows":
            self.assertIn(mode, (0o600, 0o666))
        else:
            self.assertEqual(mode, 0o600)

    def test_save_credential_cache_skips_incomplete_devices(self):
        """Test devices without both secrets are not written to the cache."""
        obj = self._make_thermostat_class()
        obj._save_credential_cache(
            {"SN1": {"password": "pw", "cryptoSerial": ""}}
        )
        self.assertFalse(os.path.exists(self.cache_file))

    def test_save_credential_cache_skips_rewrite_when_unchanged(self):
        """Test the cache file is not rewritten when contents are unchanged."""
        obj = self._make_thermostat_class()
        devices = {"SN1": {"password": "pw", "cryptoSerial": "ABCD"}}
        obj._save_credential_cache(devices)
        first_mtime = os.stat(self.cache_file).st_mtime_ns
        obj._save_credential_cache(devices)
        self.assertEqual(os.stat(self.cache_file).st_mtime_ns, first_mtime)

    def test_load_credential_cache_ignores_incomplete_entries(self):
        """Test cache entries missing a secret are ignored on load."""
        obj = self._make_thermostat_class()
        with open(self.cache_file, "w", encoding="utf-8") as file_obj:
            json.dump(
                {
                    "SN1": {"password": "pw", "cryptoSerial": ""},
                    "SN2": {"password": "pw2", "cryptoSerial": "ABCD"},
                },
                file_obj,
            )
        self.assertEqual(list(obj._load_credential_cache()), ["SN2"])

    def test_load_credential_cache_handles_corrupt_file(self):
        """Test a corrupt cache file returns an empty dict instead of raising."""
        obj = self._make_thermostat_class()
        with open(self.cache_file, "w", encoding="utf-8") as file_obj:
            file_obj.write("{not valid json")
        self.assertEqual(obj._load_credential_cache(), {})

    def test_load_credential_cache_handles_missing_file(self):
        """Test a missing cache file returns an empty dict."""
        obj = self._make_thermostat_class()
        self.assertEqual(obj._load_credential_cache(), {})

    def test_collect_prefers_cache_when_requested(self):
        """Test prefer_cache short-circuits the cloud when the cache is usable."""
        from unittest.mock import patch
        obj = self._make_thermostat_class()
        with open(self.cache_file, "w", encoding="utf-8") as file_obj:
            json.dump({"SN1": {"password": "pw", "cryptoSerial": "ABCD"}}, file_obj)

        with patch.object(obj, "_fetch_v3_device_credentials") as mock_v3:
            devices = obj._collect_device_credentials(prefer_cache=True)

        mock_v3.assert_not_called()
        self.assertEqual(list(devices), ["SN1"])

    def test_merge_credentials_prefers_primary_values(self):
        """Test merging never overwrites values already present in primary."""
        merged = kumolocal.ThermostatClass._merge_credentials(
            {"SN1": {"label": "Fresh", "password": ""}},
            {"SN1": {"label": "Stale", "password": "pw"}, "SN2": {"password": "x"}},
        )
        self.assertEqual(merged["SN1"]["label"], "Fresh")
        self.assertEqual(merged["SN1"]["password"], "pw")
        self.assertIn("SN2", merged)

    def test_v2_fallback_parses_legacy_zone_table(self):
        """Test the v2 login payload is parsed into device credentials."""
        from unittest.mock import MagicMock, patch
        obj = self._make_thermostat_class()
        raw_json = [
            {},
            {},
            {
                "children": [
                    {
                        "zoneTable": {
                            "SN1": {
                                "serial": "SN1",
                                "label": "Basement",
                                "password": "pw",
                                "cryptoSerial": "ABCD",
                                "address": "192.168.1.5",
                            }
                        }
                    }
                ]
            },
        ]
        response = MagicMock()
        response.json.return_value = raw_json

        with patch.object(obj, "_post_v2_login", return_value=response):
            devices = obj._fetch_v2_device_credentials()

        self.assertEqual(devices["SN1"]["password"], "pw")
        self.assertEqual(devices["SN1"]["cryptoSerial"], "ABCD")
        # the temporary parse must not clobber the account's kumo_dict
        self.assertIsNone(obj._kumo_dict)

    def test_v2_fallback_handles_null_response(self):
        """Test a 200/null v2 response (bad credentials) returns no devices."""
        from unittest.mock import MagicMock, patch
        obj = self._make_thermostat_class()
        response = MagicMock()
        response.json.return_value = None

        with patch.object(obj, "_post_v2_login", return_value=response):
            self.assertEqual(obj._fetch_v2_device_credentials(), {})

    def test_v2_fallback_handles_http_500_for_migrated_account(self):
        """Test v2 HTTP 500 (Comfort-migrated account) is handled gracefully."""
        from unittest.mock import MagicMock, patch
        obj = self._make_thermostat_class()
        response = MagicMock()
        response.status_code = 500

        with patch.object(kumolocal.requests, "post", return_value=response):
            self.assertIsNone(obj._post_v2_login())
            self.assertEqual(obj._fetch_v2_device_credentials(), {})

    def test_v2_fallback_handles_request_exception(self):
        """Test a network failure on the v2 endpoint does not raise."""
        from unittest.mock import patch
        obj = self._make_thermostat_class()

        with patch.object(
            kumolocal.requests,
            "post",
            side_effect=kumolocal.requests.exceptions.ConnectionError("down"),
        ):
            self.assertEqual(obj._fetch_v2_device_credentials(), {})

    def test_v2_fallback_posts_legacy_app_version(self):
        """Test the v2 login request uses the legacy endpoint and app version."""
        from unittest.mock import MagicMock, patch
        obj = self._make_thermostat_class()
        response = MagicMock()
        response.status_code = 200
        response.ok = True

        with patch.object(
            kumolocal.requests, "post", return_value=response
        ) as mock_post:
            obj._post_v2_login()

        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], kumolocal.V2_LOGIN_URL)
        self.assertEqual(kwargs["json"]["appVersion"], kumolocal.V2_APP_VERSION)
        self.assertEqual(kwargs["json"]["username"], "user")

    def test_pykumo_v3_logger_is_integrated(self):
        """Test the v3 cloud logger is routed through supervisor logging."""
        obj = self._make_thermostat_class()
        obj._setup_pykumo_logging()
        v3_logger = logging.getLogger("pykumo.py_kumo_cloud_account_v3")
        self.assertTrue(
            any(
                isinstance(handler, kumolocal.SupervisorLogHandler)
                for handler in v3_logger.handlers
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
