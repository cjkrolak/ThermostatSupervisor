"""
Unit test module for kumocloud.py.

Tests core functionality with mocked pykumo library to achieve high code
coverage without requiring actual thermostat connections.
"""

# built-in imports
import logging
import time
import unittest
from unittest.mock import MagicMock, patch

# local imports
# conditionally import kumocloud module to handle missing pykumo dependency
try:
    from src import kumocloud
    from src import kumocloud_config
    import src.thermostat_common as tc

    kumocloud_import_error = None
except ImportError as ex:
    # pykumo library not available, tests will be skipped
    kumocloud = None
    kumocloud_config = None
    tc = None
    kumocloud_import_error = ex

from src import utilities as util
from tests import unit_test_common as utc


@unittest.skipIf(
    kumocloud_import_error,
    "kumocloud import failed, tests are disabled",
)
class SupervisorLogHandlerUnitTest(utc.UnitTest):
    """Test SupervisorLogHandler class."""

    def setUp(self):
        """Setup for unit tests."""
        super().setUp()
        self.print_test_name()

    def test_emit_debug_level(self):
        """Test emit() with DEBUG level log record."""
        handler = kumocloud.SupervisorLogHandler()  # type: ignore[union-attr]

        # Create a mock log record
        record = logging.LogRecord(
            name="pykumo.test",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=1,
            msg="Test debug message",
            args=(),
            exc_info=None,
        )

        with patch("src.utilities.log_msg") as mock_log:
            handler.emit(record)
            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            self.assertIn("pykumo", args[0])
            self.assertIn("Test debug message", args[0])
            self.assertEqual(
                kwargs["mode"], util.DEBUG_LOG + util.DATA_LOG
            )

    def test_emit_info_level(self):
        """Test emit() with INFO level log record."""
        handler = kumocloud.SupervisorLogHandler()  # type: ignore[union-attr]
        record = logging.LogRecord(
            name="pykumo.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test info message",
            args=(),
            exc_info=None,
        )

        with patch("src.utilities.log_msg") as mock_log:
            handler.emit(record)
            _, kwargs = mock_log.call_args
            self.assertEqual(kwargs["mode"], util.DATA_LOG)

    def test_emit_error_level(self):
        """Test emit() with ERROR level log record."""
        handler = kumocloud.SupervisorLogHandler()  # type: ignore[union-attr]
        record = logging.LogRecord(
            name="pykumo.test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Test error message",
            args=(),
            exc_info=None,
        )

        with patch("src.utilities.log_msg") as mock_log:
            handler.emit(record)
            _, kwargs = mock_log.call_args
            self.assertEqual(
                kwargs["mode"], util.DATA_LOG + util.STDERR_LOG
            )

    def test_emit_exception_handling(self):
        """Test emit() handles exceptions gracefully."""
        handler = kumocloud.SupervisorLogHandler()
        record = logging.LogRecord(
            name="pykumo.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Mock log_msg to raise an exception
        with patch(
            "src.utilities.log_msg",
            side_effect=Exception("Log error")
        ):
            # Mock handleError to verify it's called
            with patch.object(handler, "handleError") as mock_handle_error:
                handler.emit(record)
                mock_handle_error.assert_called_once_with(record)


@unittest.skipIf(
    kumocloud_import_error,
    "kumocloud import failed, tests are disabled",
)
class ThermostatClassUnitTest(utc.UnitTest):
    """Test ThermostatClass methods."""

    def setUp(self):
        """Setup for unit tests."""
        super().setUp()
        self.print_test_name()

    @patch("src.kumocloud.pykumo.KumoCloudAccount.__init__")
    @patch.object(kumocloud.ThermostatClass, "_setup_pykumo_logging")
    def test_init_success(self, _mock_logging, mock_kumo_init):
        """Test successful ThermostatClass initialization."""
        assert kumocloud is not None  # Type narrowing for patch.object
        mock_kumo_init.return_value = None

        with patch.dict(
            "os.environ",
            {"KUMO_USERNAME": "test_user", "KUMO_PASSWORD": "test_pass"}
        ):
            tstat = kumocloud.ThermostatClass(zone=0, verbose=False)
            self.assertEqual(tstat.zone_number, 0)
            self.assertEqual(tstat.thermostat_type, kumocloud_config.ALIAS)
            _mock_logging.assert_called_once()
            mock_kumo_init.assert_called_once()

    @patch("src.kumocloud.pykumo.KumoCloudAccount.__init__")
    # type: ignore[union-attr]
    @patch.object(kumocloud.ThermostatClass, "_setup_pykumo_logging")
    def test_init_missing_credentials(self, _mock_logging, mock_kumo_init):
        """Test initialization with missing credentials."""
        mock_kumo_init.return_value = None

        with patch.dict("os.environ", {}, clear=True):
            tstat = kumocloud.ThermostatClass(zone=0, verbose=False)
            self.assertIn("MISSING", tstat.kc_uname)
            self.assertIn("MISSING", tstat.kc_pwd)

    def test_setup_pykumo_logging_success(self):
        """Test _setup_pykumo_logging() configures loggers correctly."""
        with patch(
            "src.kumocloud.pykumo.KumoCloudAccount.__init__"
        ), patch.dict(
            "os.environ",
            {"KUMO_USERNAME": "test", "KUMO_PASSWORD": "test"}
        ):
            # Mock logging.getLogger
            mock_logger = MagicMock()
            mock_logger.handlers = []

            with patch(
                "logging.getLogger", return_value=mock_logger
            ) as mock_get_logger:
                kumocloud.ThermostatClass(zone=0, verbose=False)

                # Verify getLogger was called for pykumo modules
                self.assertGreater(mock_get_logger.call_count, 0)
                # Verify handler was added
                self.assertGreater(mock_logger.addHandler.call_count, 0)

    def test_setup_pykumo_logging_exception(self):
        """Test _setup_pykumo_logging() handles exceptions."""
        with patch(
            "src.kumocloud.pykumo.KumoCloudAccount.__init__"
        ), patch.dict(
            "os.environ",
            {"KUMO_USERNAME": "test", "KUMO_PASSWORD": "test"}
        ):
            # Mock logging.getLogger to raise an exception
            with patch(
                "logging.getLogger", side_effect=Exception("Logger error")
            ), patch("src.utilities.log_msg") as mock_log:
                # Should not raise exception, just log it
                kumocloud.ThermostatClass(zone=0, verbose=False)
                # Verify error was logged
                self.assertTrue(any(
                    "Failed to setup logging" in str(call)
                    for call in mock_log.call_args_list
                ))

    @patch("src.kumocloud.pykumo.KumoCloudAccount.__init__")
    # type: ignore[union-attr]
    @patch.object(kumocloud.ThermostatClass, "_setup_pykumo_logging")
    def test_get_target_zone_id(self, _mock_logging, mock_kumo_init):
        """Test get_target_zone_id() returns zone parameter."""
        mock_kumo_init.return_value = None

        with patch.dict(
            "os.environ",
            {"KUMO_USERNAME": "test", "KUMO_PASSWORD": "test"}
        ):
            tstat = kumocloud.ThermostatClass(zone=0, verbose=False)
            self.assertEqual(tstat.get_target_zone_id(5), 5)
            self.assertEqual(tstat.get_target_zone_id("TestZone"), "TestZone")

    @patch("src.kumocloud.pykumo.KumoCloudAccount.__init__")
    # type: ignore[union-attr]
    @patch.object(kumocloud.ThermostatClass, "_setup_pykumo_logging")
    def test_get_zone_index_from_name_success(
        self, _mock_logging, mock_kumo_init
    ):
        """Test get_zone_index_from_name() with valid zone name."""
        mock_kumo_init.return_value = None

        with patch.dict(
            "os.environ",
            {"KUMO_USERNAME": "test", "KUMO_PASSWORD": "test"}
        ):
            tstat = kumocloud.ThermostatClass(zone=0, verbose=False)
            # Use actual zone name from config
            tstat.zone_name = kumocloud_config.metadata[0]["zone_name"]
            zone_index = tstat.get_zone_index_from_name()
            self.assertEqual(zone_index, 0)

    @patch("src.kumocloud.pykumo.KumoCloudAccount.__init__")
    # type: ignore[union-attr]
    @patch.object(kumocloud.ThermostatClass, "_setup_pykumo_logging")
    def test_get_zone_index_from_name_invalid(
        self, _mock_logging, mock_kumo_init
    ):
        """Test get_zone_index_from_name() with invalid zone name."""
        mock_kumo_init.return_value = None

        with patch.dict(
            "os.environ",
            {"KUMO_USERNAME": "test", "KUMO_PASSWORD": "test"}
        ):
            tstat = kumocloud.ThermostatClass(zone=0, verbose=False)
            tstat.zone_name = "NonExistentZone"
            with self.assertRaises(ValueError) as context:
                tstat.get_zone_index_from_name()
            self.assertIn("NonExistentZone", str(context.exception))
            self.assertIn("not found", str(context.exception))

    @patch("src.kumocloud.pykumo.KumoCloudAccount.__init__")
    # type: ignore[union-attr]
    @patch.object(kumocloud.ThermostatClass, "_setup_pykumo_logging")
    def test_get_serial_number_list_success(
        self, _mock_logging, mock_kumo_init
    ):
        """Test _get_serial_number_list() returns serial numbers."""
        mock_kumo_init.return_value = None

        with patch.dict(
            "os.environ",
            {"KUMO_USERNAME": "test", "KUMO_PASSWORD": "test"}
        ):
            tstat = kumocloud.ThermostatClass(zone=0, verbose=False)
            mock_serials = {"SERIAL001": {}, "SERIAL002": {}}
            tstat.get_indoor_units = MagicMock(return_value=mock_serials)

            result = tstat._get_serial_number_list()  # type: ignore[attr-defined]
            self.assertEqual(result, ["SERIAL001", "SERIAL002"])

    @patch("src.kumocloud.pykumo.KumoCloudAccount.__init__")
    # type: ignore[union-attr]
    @patch.object(kumocloud.ThermostatClass, "_setup_pykumo_logging")
    def test_get_serial_number_list_with_retry(
        self, _mock_logging, mock_kumo_init
    ):
        """Test _get_serial_number_list() retries on UnboundLocalError."""
        mock_kumo_init.return_value = None

        with patch.dict(
            "os.environ",
            {"KUMO_USERNAME": "test", "KUMO_PASSWORD": "test"}
        ):
            tstat = kumocloud.ThermostatClass(zone=0, verbose=False)
            mock_serials = {"SERIAL001": {}}

            # First call raises UnboundLocalError, second succeeds
            tstat.get_indoor_units = MagicMock(
                side_effect=[UnboundLocalError(), mock_serials]
            )

            with patch("time.sleep"):  # Speed up test
                result = tstat._get_serial_number_list()  # type: ignore[attr-defined]
                self.assertEqual(result, ["SERIAL001"])
                self.assertEqual(tstat.get_indoor_units.call_count, 2)

    @patch("src.kumocloud.pykumo.KumoCloudAccount.__init__")
    # type: ignore[union-attr]
    @patch.object(kumocloud.ThermostatClass, "_setup_pykumo_logging")
    def test_validate_and_populate_metadata_success(
        self, _mock_logging, mock_kumo_init
    ):
        """Test _validate_and_populate_metadata() populates metadata."""
        mock_kumo_init.return_value = None

        with patch.dict(
            "os.environ",
            {"KUMO_USERNAME": "test", "KUMO_PASSWORD": "test"}
        ):
            tstat = kumocloud.ThermostatClass(zone=0, verbose=False)
            serial_list = ["SERIAL001", "SERIAL002"]

            # type: ignore[attr-defined]
            tstat._validate_and_populate_metadata(serial_list)

            # Verify metadata was populated
            self.assertEqual(
                kumocloud_config.metadata[0]["serial_number"], "SERIAL001"
            )
            self.assertEqual(
                kumocloud_config.metadata[1]["serial_number"], "SERIAL002"
            )

    @patch("src.kumocloud.pykumo.KumoCloudAccount.__init__")
    # type: ignore[union-attr]
    @patch.object(kumocloud.ThermostatClass, "_setup_pykumo_logging")
    def test_validate_and_populate_metadata_empty_list(
        self, _mock_logging, mock_kumo_init
    ):
        """Test _validate_and_populate_metadata() with empty list."""
        mock_kumo_init.return_value = None

        with patch.dict(
            "os.environ",
            {"KUMO_USERNAME": "test", "KUMO_PASSWORD": "test"}
        ):
            tstat = kumocloud.ThermostatClass(zone=0, verbose=False)

            with self.assertRaises(tc.AuthenticationError) as context:
                tstat._validate_and_populate_metadata([])  # type: ignore[attr-defined]
            self.assertIn("Authentication Error", str(context.exception))

    @patch("src.kumocloud.pykumo.KumoCloudAccount.__init__")
    # type: ignore[union-attr]
    @patch.object(kumocloud.ThermostatClass, "_setup_pykumo_logging")
    def test_get_zone_data_all_zones(self, _mock_logging, mock_kumo_init):
        """Test _get_zone_data() with zone=None returns all zones."""
        mock_kumo_init.return_value = None

        with patch.dict(
            "os.environ",
            {"KUMO_USERNAME": "test", "KUMO_PASSWORD": "test"}
        ):
            tstat = kumocloud.ThermostatClass(zone=0, verbose=False)
            mock_raw_json = [None, None, {"all_zones": "data"}, None]
            tstat.get_raw_json = MagicMock(return_value=mock_raw_json)

            result = tstat._get_zone_data(None, [])  # type: ignore[attr-defined]
            self.assertEqual(result, {"all_zones": "data"})

    @patch("src.kumocloud.pykumo.KumoCloudAccount.__init__")
    # type: ignore[union-attr]
    @patch.object(kumocloud.ThermostatClass, "_setup_pykumo_logging")
    def test_get_zone_data_specific_zone_by_index(
        self, _mock_logging, mock_kumo_init
    ):
        """Test _get_zone_data() with integer zone index."""
        mock_kumo_init.return_value = None

        with patch.dict(
            "os.environ",
            {"KUMO_USERNAME": "test", "KUMO_PASSWORD": "test"}
        ):
            tstat = kumocloud.ThermostatClass(zone=0, verbose=False)
            mock_zone_data = {"zone0": "data"}
            mock_raw_json = [
                None,
                None,
                {
                    "children": [
                        {"zoneTable": {"SERIAL001": mock_zone_data}}
                    ]
                },
                None
            ]
            tstat.get_raw_json = MagicMock(return_value=mock_raw_json)
            serial_list = ["SERIAL001"]

            result = tstat._get_zone_data(0, serial_list)  # type: ignore[attr-defined]
            self.assertEqual(result, mock_zone_data)
            self.assertEqual(tstat.serial_number, "SERIAL001")

    @patch("src.kumocloud.pykumo.KumoCloudAccount.__init__")
    # type: ignore[union-attr]
    @patch.object(kumocloud.ThermostatClass, "_setup_pykumo_logging")
    def test_get_zone_data_specific_zone_by_name(
        self, _mock_logging, mock_kumo_init
    ):
        """Test _get_zone_data() with string zone name."""
        mock_kumo_init.return_value = None

        with patch.dict(
            "os.environ",
            {"KUMO_USERNAME": "test", "KUMO_PASSWORD": "test"}
        ):
            tstat = kumocloud.ThermostatClass(zone=0, verbose=False)
            zone_name = kumocloud_config.metadata[1]["zone_name"]
            tstat.get_zone_index_from_name = MagicMock(return_value=1)

            mock_zone_data = {"zone1": "data"}
            mock_raw_json = [
                None,
                None,
                {
                    "children": [
                        {
                            "zoneTable": {
                                "SERIAL001": {},
                                "SERIAL002": mock_zone_data
                            }
                        }
                    ]
                },
                None
            ]
            tstat.get_raw_json = MagicMock(return_value=mock_raw_json)
            serial_list = ["SERIAL001", "SERIAL002"]

            # type: ignore[attr-defined]
            result = tstat._get_zone_data(zone_name, serial_list)
            self.assertEqual(result, mock_zone_data)
            self.assertEqual(tstat.serial_number, "SERIAL002")

    @patch("src.kumocloud.pykumo.KumoCloudAccount.__init__")
    # type: ignore[union-attr]
    @patch.object(kumocloud.ThermostatClass, "_setup_pykumo_logging")
    def test_get_zone_data_invalid_index(self, _mock_logging, mock_kumo_init):
        """Test _get_zone_data() with invalid zone index."""
        mock_kumo_init.return_value = None

        with patch.dict(
            "os.environ",
            {"KUMO_USERNAME": "test", "KUMO_PASSWORD": "test"}
        ):
            tstat = kumocloud.ThermostatClass(zone=0, verbose=False)
            mock_raw_json = [
                None,
                None,
                {"children": [{"zoneTable": {}}]},
                None
            ]
            tstat.get_raw_json = MagicMock(return_value=mock_raw_json)
            serial_list = ["SERIAL001"]

            with self.assertRaises(IndexError) as context:
                tstat._get_zone_data(5, serial_list)
            self.assertIn("Invalid Zone", str(context.exception))

    @patch("src.kumocloud.pykumo.KumoCloudAccount.__init__")
    # type: ignore[union-attr]
    @patch.object(kumocloud.ThermostatClass, "_setup_pykumo_logging")
    def test_get_metadata_without_retry(self, _mock_logging, mock_kumo_init):
        """Test get_metadata() without retry option."""
        mock_kumo_init.return_value = None

        with patch.dict(
            "os.environ",
            {"KUMO_USERNAME": "test", "KUMO_PASSWORD": "test"}
        ):
            tstat = kumocloud.ThermostatClass(zone=0, verbose=False)
            mock_zone_data = {"temp": 72, "mode": "heat"}

            # type: ignore[attr-defined]
            tstat._get_serial_number_list = MagicMock(
                return_value=["SERIAL001"]
            )
            # type: ignore[attr-defined]
            tstat._validate_and_populate_metadata = MagicMock()
            # type: ignore[attr-defined]
            tstat._get_zone_data = MagicMock(
                return_value=mock_zone_data
            )

            # Test without parameter (returns all)
            result = tstat.get_metadata(zone=0)
            self.assertEqual(result, mock_zone_data)

            # Test with specific parameter
            result = tstat.get_metadata(zone=0, parameter="temp")
            self.assertEqual(result, 72)

    @patch("src.kumocloud.pykumo.KumoCloudAccount.__init__")
    # type: ignore[union-attr]
    @patch.object(kumocloud.ThermostatClass, "_setup_pykumo_logging")
    def test_get_metadata_with_retry(self, _mock_logging, mock_kumo_init):
        """Test get_metadata() with retry option."""
        mock_kumo_init.return_value = None

        with patch.dict(
            "os.environ",
            {"KUMO_USERNAME": "test", "KUMO_PASSWORD": "test"}
        ):
            tstat = kumocloud.ThermostatClass(zone=0, verbose=False)
            tstat.thermostat_type = "KumoCloud"
            tstat.zone_name = "TestZone"

            mock_zone_data = {"temp": 72}
            # type: ignore[attr-defined]
            tstat._get_serial_number_list = MagicMock(
                return_value=["SERIAL001"]
            )
            # type: ignore[attr-defined]
            tstat._validate_and_populate_metadata = MagicMock()
            # type: ignore[attr-defined]
            tstat._get_zone_data = MagicMock(
                return_value=mock_zone_data
            )

            with patch(
                "src.utilities.execute_with_extended_retries"
            ) as mock_retry:
                mock_retry.return_value = mock_zone_data

                result = tstat.get_metadata(zone=0, retry=True)

                mock_retry.assert_called_once()
                call_kwargs = mock_retry.call_args[1]
                self.assertEqual(call_kwargs["thermostat_type"], "KumoCloud")
                self.assertEqual(call_kwargs["zone_name"], "TestZone")
                self.assertEqual(call_kwargs["number_of_retries"], 5)
                self.assertEqual(result, mock_zone_data)

    @patch("src.kumocloud.pykumo.KumoCloudAccount.__init__")
    # type: ignore[union-attr]
    @patch.object(kumocloud.ThermostatClass, "_setup_pykumo_logging")
    def test_get_all_metadata(self, _mock_logging, mock_kumo_init):
        """Test get_all_metadata() delegates to get_metadata()."""
        mock_kumo_init.return_value = None

        with patch.dict(
            "os.environ",
            {"KUMO_USERNAME": "test", "KUMO_PASSWORD": "test"}
        ):
            tstat = kumocloud.ThermostatClass(zone=0, verbose=False)
            tstat.get_metadata = MagicMock(return_value={"test": "data"})

            result = tstat.get_all_metadata(zone=1, retry=True)

            tstat.get_metadata.assert_called_once_with(1, retry=True)
            self.assertEqual(result, {"test": "data"})

    @patch("src.kumocloud.pykumo.KumoCloudAccount.__init__")
    # type: ignore[union-attr]
    @patch.object(kumocloud.ThermostatClass, "_setup_pykumo_logging")
    def test_print_all_thermostat_metadata(
        self, _mock_logging, mock_kumo_init
    ):
        """Test print_all_thermostat_metadata() calls parent method."""
        mock_kumo_init.return_value = None

        with patch.dict(
            "os.environ",
            {"KUMO_USERNAME": "test", "KUMO_PASSWORD": "test"}
        ):
            tstat = kumocloud.ThermostatClass(zone=0, verbose=False)
            tstat.exec_print_all_thermostat_metadata = MagicMock()
            tstat.get_all_metadata = MagicMock(return_value={})

            tstat.print_all_thermostat_metadata(zone=0)

            tstat.exec_print_all_thermostat_metadata.assert_called_once()


@unittest.skipIf(
    kumocloud_import_error,
    "kumocloud import failed, tests are disabled",
)
class ThermostatZoneUnitTest(utc.UnitTest):
    """Test ThermostatZone methods."""

    def setUp(self):
        """Setup for unit tests."""
        super().setUp()
        self.print_test_name()

        # Create mock thermostat object
        self.mock_thermostat = MagicMock()
        self.mock_thermostat.device_id = "test_device"
        self.mock_thermostat.zone_number = 0
        self.mock_thermostat.get_all_metadata.return_value = {
            "label": "TestZone",
            "reportedCondition": {
                "room_temp": 21.0,  # 21°C = ~69.8°F
                "power": 1,
                "operation_mode": 1,
                "sp_heat": 20.0,
                "sp_cool": 25.0,
                "fan_speed": 2,
            },
            "reportedInitialSettings": {
                "energy_save": 0,
            }
        }

    def test_init_success(self):
        """Test successful ThermostatZone initialization."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        self.assertEqual(zone.zone_number, 0)
        self.assertEqual(zone.thermostat_type, kumocloud_config.ALIAS)
        self.assertIsNotNone(zone.zone_info)

    def test_get_parameter_simple_key(self):
        """Test get_parameter() with simple key."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        result = zone.get_parameter("label")
        self.assertEqual(result, "TestZone")

    def test_get_parameter_with_parent_key(self):
        """Test get_parameter() with parent_key."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        result = zone.get_parameter("room_temp", "reportedCondition")
        self.assertEqual(result, 21.0)

    def test_get_parameter_with_grandparent_key(self):
        """Test get_parameter() with grandparent_key."""
        self.mock_thermostat.get_all_metadata.return_value = {
            "label": "TestZone",
            "acoilSettings": {
                "inputs": {
                    "humidistat": True
                }
            }
        }

        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        result = zone.get_parameter(
            "humidistat", "inputs", "acoilSettings"
        )
        self.assertTrue(result)

    def test_get_parameter_with_default(self):
        """Test get_parameter() returns default on KeyError."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        result = zone.get_parameter(
            "nonexistent", default_val="default_value"
        )
        self.assertEqual(result, "default_value")

    def test_get_parameter_key_error_no_default(self):
        """Test get_parameter() raises KeyError when no default."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with self.assertRaises(KeyError):
            zone.get_parameter("nonexistent")

    def test_get_zone_name(self):
        """Test get_zone_name() returns zone label."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "refresh_zone_info"):
            result = zone.get_zone_name()
            self.assertEqual(result, "TestZone")

    def test_get_display_temp(self):
        """Test get_display_temp() returns temperature in Fahrenheit."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "refresh_zone_info"):
            temp = zone.get_display_temp()
            # 21°C should be approximately 69.8°F
            self.assertAlmostEqual(temp, 69.8, places=1)

    def test_get_display_humidity_not_supported(self):
        """Test get_display_humidity() when humidity not supported."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(
            zone, "get_is_humidity_supported", return_value=False
        ):
            result = zone.get_display_humidity()
            self.assertIsNone(result)

    def test_get_is_humidity_supported_true(self):
        """Test get_is_humidity_supported() returns True."""
        self.mock_thermostat.get_all_metadata.return_value = {
            "label": "TestZone",
            "acoilSettings": {
                "inputs": {
                    "humidistat": True
                }
            }
        }

        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "refresh_zone_info"):
            result = zone.get_is_humidity_supported()
            self.assertTrue(result)

    def test_get_is_humidity_supported_false(self):
        """Test get_is_humidity_supported() returns False."""
        self.mock_thermostat.get_all_metadata.return_value = {
            "label": "TestZone",
            "acoilSettings": {
                "inputs": {
                    "humidistat": False
                }
            }
        }

        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "refresh_zone_info"):
            result = zone.get_is_humidity_supported()
            self.assertFalse(result)

    def test_is_heat_mode(self):
        """Test is_heat_mode() returns correct value."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "_is_mode", return_value=True):
            result = zone.is_heat_mode()
            self.assertEqual(result, 1)

    def test_is_cool_mode(self):
        """Test is_cool_mode() returns correct value."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "_is_mode", return_value=False):
            result = zone.is_cool_mode()
            self.assertEqual(result, 0)

    def test_is_dry_mode(self):
        """Test is_dry_mode() returns correct value."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "_is_mode", return_value=True):
            result = zone.is_dry_mode()
            self.assertEqual(result, 1)

    def test_is_fan_mode(self):
        """Test is_fan_mode() returns correct value."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "_is_mode", return_value=True):
            result = zone.is_fan_mode()
            self.assertEqual(result, 1)

    def test_is_auto_mode(self):
        """Test is_auto_mode() returns correct value."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "_is_mode", return_value=False):
            result = zone.is_auto_mode()
            self.assertEqual(result, 0)

    def test_is_eco_mode(self):
        """Test is_eco_mode() returns correct value."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "refresh_zone_info"):
            result = zone.is_eco_mode()
            self.assertEqual(result, 0)

    def test_is_off_mode(self):
        """Test is_off_mode() returns correct value."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "_is_mode", return_value=True):
            result = zone.is_off_mode()
            self.assertEqual(result, 1)

    def test_is_heating_active(self):
        """Test is_heating() when heating is active."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "is_heat_mode", return_value=1), \
             patch.object(zone, "is_power_on", return_value=1), \
             patch.object(zone, "get_heat_setpoint_raw", return_value=75.0), \
             patch.object(zone, "get_display_temp", return_value=70.0):
            result = zone.is_heating()
            self.assertEqual(result, 1)

    def test_is_heating_inactive(self):
        """Test is_heating() when heating is inactive."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "is_heat_mode", return_value=1), \
             patch.object(zone, "is_power_on", return_value=1), \
             patch.object(zone, "get_heat_setpoint_raw", return_value=70.0), \
             patch.object(zone, "get_display_temp", return_value=75.0):
            result = zone.is_heating()
            self.assertEqual(result, 0)

    def test_is_cooling_active(self):
        """Test is_cooling() when cooling is active."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "is_cool_mode", return_value=1), \
             patch.object(zone, "is_power_on", return_value=1), \
             patch.object(zone, "get_cool_setpoint_raw", return_value=70.0), \
             patch.object(zone, "get_display_temp", return_value=75.0):
            result = zone.is_cooling()
            self.assertEqual(result, 1)

    def test_is_cooling_inactive(self):
        """Test is_cooling() when cooling is inactive."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "is_cool_mode", return_value=1), \
             patch.object(zone, "is_power_on", return_value=1), \
             patch.object(zone, "get_cool_setpoint_raw", return_value=75.0), \
             patch.object(zone, "get_display_temp", return_value=70.0):
            result = zone.is_cooling()
            self.assertEqual(result, 0)

    def test_is_drying_active(self):
        """Test is_drying() when drying is active."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "is_dry_mode", return_value=1), \
             patch.object(zone, "is_power_on", return_value=1), \
             patch.object(zone, "get_cool_setpoint_raw", return_value=70.0), \
             patch.object(zone, "get_display_temp", return_value=75.0):
            result = zone.is_drying()
            self.assertEqual(result, 1)

    def test_is_auto_active(self):
        """Test is_auto() when auto mode is active."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "is_auto_mode", return_value=1), \
             patch.object(zone, "is_power_on", return_value=1), \
             patch.object(zone, "get_cool_setpoint_raw", return_value=70.0), \
             patch.object(zone, "get_heat_setpoint_raw", return_value=68.0), \
             patch.object(zone, "get_display_temp", return_value=75.0):
            result = zone.is_auto()
            self.assertEqual(result, 1)

    def test_is_eco_active(self):
        """Test is_eco() when eco mode is active."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "is_eco_mode", return_value=1), \
             patch.object(zone, "is_power_on", return_value=1), \
             patch.object(zone, "get_cool_setpoint_raw", return_value=70.0), \
             patch.object(zone, "get_heat_setpoint_raw", return_value=68.0), \
             patch.object(zone, "get_display_temp", return_value=75.0):
            result = zone.is_eco()
            self.assertEqual(result, 1)

    def test_is_fanning_active(self):
        """Test is_fanning() when fan is active."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "is_fan_on", return_value=1), \
             patch.object(zone, "is_power_on", return_value=1):
            result = zone.is_fanning()
            self.assertEqual(result, 1)

    def test_is_power_on_true(self):
        """Test is_power_on() returns 1 when power is on."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "refresh_zone_info"):
            result = zone.is_power_on()
            self.assertEqual(result, 1)

    def test_is_power_on_false(self):
        """Test is_power_on() returns 0 when power is off."""
        self.mock_thermostat.get_all_metadata.return_value = {
            "label": "TestZone",
            "reportedCondition": {
                "power": 0
            }
        }

        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "refresh_zone_info"):
            result = zone.is_power_on()
            self.assertEqual(result, 0)

    def test_is_fan_on_with_fan_speed(self):
        """Test is_fan_on() when fan speed is positive."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "is_power_on", return_value=1):
            result = zone.is_fan_on()
            self.assertEqual(result, 1)

    def test_is_fan_on_power_off(self):
        """Test is_fan_on() when power is off."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "is_power_on", return_value=0):
            result = zone.is_fan_on()
            self.assertEqual(result, 0)

    def test_is_fan_on_no_fan_speed_key(self):
        """Test is_fan_on() when fan_speed key is missing."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        # Mock get_parameter to return None for fan_speed
        with patch.object(zone, "is_power_on", return_value=1), \
             patch.object(
                 zone, "get_parameter", return_value=None
             ) as mock_get_param:
            result = zone.is_fan_on()
            self.assertEqual(result, 0)
            # Verify get_parameter was called for fan_speed
            mock_get_param.assert_called_with(
                "fan_speed", "reportedCondition"
            )

    def test_is_defrosting(self):
        """Test is_defrosting() returns correct value."""
        self.mock_thermostat.get_all_metadata.return_value = {
            "label": "TestZone",
            "reportedCondition": {
                "status_display": {
                    "defrost": 1
                }
            }
        }

        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "refresh_zone_info"):
            result = zone.is_defrosting()
            self.assertEqual(result, 1)

    def test_is_standby(self):
        """Test is_standby() returns correct value."""
        self.mock_thermostat.get_all_metadata.return_value = {
            "label": "TestZone",
            "reportedCondition": {
                "status_display": {
                    "standby": 1
                }
            }
        }

        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "refresh_zone_info"):
            result = zone.is_standby()
            self.assertEqual(result, 1)

    def test_get_wifi_strength(self):
        """Test get_wifi_strength() returns rssi value."""
        self.mock_thermostat.get_all_metadata.return_value = {
            "label": "TestZone",
            "rssi": {
                "rssi": -45.0
            }
        }

        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "refresh_zone_info"):
            result = zone.get_wifi_strength()
            self.assertEqual(result, -45.0)

    def test_get_wifi_status_good(self):
        """Test get_wifi_status() returns True for good signal."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "get_wifi_strength", return_value=-50.0):
            result = zone.get_wifi_status()
            self.assertTrue(result)

    def test_get_wifi_status_weak(self):
        """Test get_wifi_status() returns False for weak signal."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "get_wifi_strength", return_value=-120.0):
            result = zone.get_wifi_status()
            self.assertFalse(result)

    def test_get_wifi_status_invalid(self):
        """Test get_wifi_status() handles invalid wifi strength."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "get_wifi_strength", return_value="invalid"):
            result = zone.get_wifi_status()
            self.assertFalse(result)

    def test_get_battery_voltage_online(self):
        """Test get_battery_voltage() when online."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "get_wifi_status", return_value=True):
            result = zone.get_battery_voltage()
            self.assertEqual(result, 120.0)

    def test_get_battery_voltage_offline(self):
        """Test get_battery_voltage() when offline."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "get_wifi_status", return_value=False):
            result = zone.get_battery_voltage()
            self.assertEqual(result, 0.0)

    def test_get_battery_status_online(self):
        """Test get_battery_status() when online."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "get_battery_voltage", return_value=120.0):
            result = zone.get_battery_status()
            self.assertTrue(result)

    def test_get_battery_status_offline(self):
        """Test get_battery_status() when offline."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "get_battery_voltage", return_value=0.0):
            result = zone.get_battery_status()
            self.assertFalse(result)

    def test_get_heat_setpoint_raw(self):
        """Test get_heat_setpoint_raw() returns temperature in F."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "refresh_zone_info"):
            temp = zone.get_heat_setpoint_raw()
            # 20°C should be 68°F
            self.assertAlmostEqual(temp, 68.0, places=1)

    def test_get_heat_setpoint_raw_missing(self):
        """Test get_heat_setpoint_raw() when sp_heat is missing."""
        self.mock_thermostat.get_all_metadata.return_value = {
            "label": "TestZone",
            "reportedCondition": {
                "power": 0
                # sp_heat missing
            }
        }

        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "refresh_zone_info"):
            temp = zone.get_heat_setpoint_raw()
            # Should return conversion of -1°C
            self.assertLess(temp, 32.0)

    def test_get_heat_setpoint(self):
        """Test get_heat_setpoint() returns string with units."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "get_heat_setpoint_raw", return_value=68.0):
            result = zone.get_heat_setpoint()
            self.assertIsInstance(result, str)
            self.assertIn("68", result)

    def test_get_schedule_heat_sp(self):
        """Test get_schedule_heat_sp() returns max heat setpoint."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        result = zone.get_schedule_heat_sp()
        self.assertEqual(result, float(kumocloud_config.MAX_HEAT_SETPOINT))

    def test_get_schedule_cool_sp(self):
        """Test get_schedule_cool_sp() returns min cool setpoint."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        result = zone.get_schedule_cool_sp()
        self.assertEqual(result, kumocloud_config.MIN_COOL_SETPOINT)

    def test_get_cool_setpoint_raw(self):
        """Test get_cool_setpoint_raw() returns temperature in F."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "refresh_zone_info"):
            temp = zone.get_cool_setpoint_raw()
            # 25°C should be 77°F
            self.assertAlmostEqual(temp, 77.0, places=1)

    def test_get_cool_setpoint(self):
        """Test get_cool_setpoint() returns string with units."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "get_cool_setpoint_raw", return_value=77.0):
            result = zone.get_cool_setpoint()
            self.assertIsInstance(result, str)
            self.assertIn("77", result)

    def test_get_is_invacation_hold_mode(self):
        """Test get_is_invacation_hold_mode() returns False."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        result = zone.get_is_invacation_hold_mode()
        self.assertFalse(result)

    def test_get_vacation_hold(self):
        """Test get_vacation_hold() returns False."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        result = zone.get_vacation_hold()
        self.assertFalse(result)

    def test_get_system_switch_position_power_off(self):
        """Test get_system_switch_position() when power is off."""
        self.mock_thermostat.get_all_metadata.return_value = {
            "label": "TestZone",
            "reportedCondition": {
                "power": 0
            }
        }

        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "refresh_zone_info"), \
             patch.object(zone, "is_power_on", return_value=0):
            result = zone.get_system_switch_position()
            self.assertEqual(result, 16)  # OFF_MODE value

    def test_get_system_switch_position_power_on(self):
        """Test get_system_switch_position() when power is on."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch.object(zone, "refresh_zone_info"), \
             patch.object(zone, "is_power_on", return_value=1):
            result = zone.get_system_switch_position()
            self.assertEqual(result, 1)  # operation_mode from mock data

    def test_set_heat_setpoint_not_implemented(self):
        """Test set_heat_setpoint() logs warning."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch("src.utilities.log_msg") as mock_log:
            zone.set_heat_setpoint(70)
            # Verify warning was logged
            self.assertTrue(any(
                "not implemented" in str(call)
                for call in mock_log.call_args_list
            ))

    def test_set_cool_setpoint_not_implemented(self):
        """Test set_cool_setpoint() logs warning."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        with patch("src.utilities.log_msg") as mock_log:
            zone.set_cool_setpoint(75)
            # Verify warning was logged
            self.assertTrue(any(
                "not implemented" in str(call)
                for call in mock_log.call_args_list
            ))

    def test_refresh_zone_info_not_expired(self):
        """Test refresh_zone_info() does not refresh if not expired."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        # Set last fetch time to now
        zone.last_fetch_time = time.time()
        zone.Thermostat._need_fetch = False  # type: ignore[attr-defined]
        zone.Thermostat._fetch_if_needed = MagicMock()  # type: ignore[attr-defined]

        zone.refresh_zone_info(force_refresh=False)

        # Should not call _fetch_if_needed
        # type: ignore[attr-defined]
        zone.Thermostat._fetch_if_needed.assert_not_called()

    def test_refresh_zone_info_expired(self):
        """Test refresh_zone_info() refreshes when expired."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        # Set last fetch time to past
        zone.last_fetch_time = time.time() - 2 * zone.fetch_interval_sec
        zone.Thermostat._need_fetch = False  # type: ignore[attr-defined]
        zone.Thermostat._fetch_if_needed = MagicMock()  # type: ignore[attr-defined]

        zone.refresh_zone_info(force_refresh=False)

        # Should call _fetch_if_needed
        # type: ignore[attr-defined]
        zone.Thermostat._fetch_if_needed.assert_called_once()

    def test_refresh_zone_info_force_refresh(self):
        """Test refresh_zone_info() with force_refresh=True."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        # Set last fetch time to now (not expired)
        zone.last_fetch_time = time.time()
        zone.Thermostat._need_fetch = False  # type: ignore[attr-defined]
        zone.Thermostat._fetch_if_needed = MagicMock()  # type: ignore[attr-defined]

        zone.refresh_zone_info(force_refresh=True)

        # Should call _fetch_if_needed even though not expired
        # type: ignore[attr-defined]
        zone.Thermostat._fetch_if_needed.assert_called_once()

    def test_refresh_zone_info_with_unbound_local_error(self):
        """Test refresh_zone_info() handles UnboundLocalError."""
        zone = kumocloud.ThermostatZone(
            self.mock_thermostat, verbose=False
        )

        zone.last_fetch_time = time.time() - 2 * zone.fetch_interval_sec
        zone.Thermostat._need_fetch = False  # type: ignore[attr-defined]
        zone.Thermostat._fetch_if_needed = MagicMock(  # type: ignore[attr-defined]
            side_effect=UnboundLocalError("Test error")
        )

        with patch("src.utilities.log_msg") as mock_log:
            zone.refresh_zone_info(force_refresh=False)
            # Verify warning was logged
            self.assertTrue(any(
                "timeout" in str(call).lower()
                for call in mock_log.call_args_list
            ))


if __name__ == "__main__":
    util.log_msg.debug = True  # type: ignore[attr-defined]
    unittest.main(verbosity=2)
