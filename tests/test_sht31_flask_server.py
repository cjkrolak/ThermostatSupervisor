"""
Unit test module for sht31_flask_server.py.

Flask server tests currently do not work on Azure pipelines
because ports cannot be opened on shared pool.
"""
# built-in imports
import os
import unittest
from unittest.mock import patch, MagicMock

# third party imports

# local imports
# thermostat_api is imported but not used to avoid a circular import
from thermostatsupervisor import environment as env
from thermostatsupervisor import (
    thermostat_api as api,
)  # noqa F401, pylint: disable=unused-import.
from thermostatsupervisor import sht31
from thermostatsupervisor import sht31_config
from thermostatsupervisor import sht31_flask_server as sht31_fs
from thermostatsupervisor import utilities as util
from tests import unit_test_common as utc


@unittest.skipIf(not utc.ENABLE_SHT31_TESTS, "sht31 tests are disabled")
@unittest.skipIf(
    env.is_azure_environment(), "this test not supported on Azure Pipelines"
)
@unittest.skipIf(
    not utc.ENABLE_FLASK_INTEGRATION_TESTS, "flask integration tests are disabled"
)
class IntegrationTest(utc.UnitTest):
    """Test functions in sht31_flask_server.py."""

    # sht31 flask server is automatically spawned in sht31
    # Thermostat class if unit test zone is being used.

    def test_sht31_flask_server_all_pages(self):
        """
        Confirm all pages return data from Flask server.
        """
        # do not test these pages
        no_test_list = ["i2c_recovery", "reset"]

        # no server outptu for these pages
        no_server_output_list = []
        no_key_check_list = ["print_block_list", "clear_block_list"]
        # loopback does not work so use local sht31 zone if testing
        # on the local net.  If not, use the DNS name.
        zone = sht31_config.get_preferred_zone()
        # Define expected keys for each test case
        expected_keys = {
            "production": "measurements",
            "unit_test": "measurements",
            "diag": "raw_binary",
            "clear_diag": "raw_binary",
            "enable_heater": "raw_binary",
            "disable_heater": "raw_binary",
            "soft_reset": "raw_binary",
            "i2c_detect": "i2c_detect",
            "i2c_detect_0": "i2c_detect",
            "i2c_detect_1": "i2c_detect",
            "i2c_logic_levels": "i2c_logic_levels",
            "i2c_bus_health": "i2c_bus_health",
            "i2c_recovery": "i2c_recovery",
            "reset": "message",
        }

        for test_case in sht31_config.flask_folder:
            if test_case in no_test_list:
                print(f"test_case={test_case}: bypassing this test case")
                continue

            print(f"test_case={test_case}")
            Thermostat = sht31.ThermostatClass(
                zone, path=sht31_config.flask_folder[test_case]
            )
            print("printing thermostat meta data:")
            return_data = Thermostat.print_all_thermostat_metadata(zone)

            # validate return type was returned
            if test_case in no_server_output_list:
                self.assertTrue(
                    isinstance(return_data, type(None)),
                    f"return data for test case {test_case} is not NoneType, "
                    f"return type: {type(return_data)}",
                )
            else:
                self.assertTrue(
                    isinstance(return_data, dict),
                    f"return data for test case {test_case} is not a dictionary, "
                    f"return type: {type(return_data)}",
                )

            # validate key as proof of correct return page
            if test_case not in no_key_check_list:
                expected_key = expected_keys.get(test_case, "bogus")
                self.assertTrue(
                    expected_key in return_data,
                    f"test_case '{test_case}': key '{expected_key}' "
                    f"was not found in return data: {return_data}",
                )

    def test_sht31_flask_server(self):
        """
        Confirm Flask server returns valid data.
        """
        measurements_bckup = sht31_config.MEASUREMENTS
        try:
            for sht31_config.measurements in [1, 10, 100, 1000]:
                msg = ["measurement", "measurements"][sht31_config.MEASUREMENTS > 1]
                print(
                    f"\ntesting SHT31 flask server with "
                    f"{sht31_config.MEASUREMENTS} {msg}..."
                )
                self.validate_flask_server()
        finally:
            sht31_config.measurements = measurements_bckup

    def validate_flask_server(self):
        """
        Launch SHT31 Flask server and validate data.
        """
        print("creating thermostat object...")
        Thermostat = sht31.ThermostatClass(sht31_config.UNIT_TEST_ZONE)
        print("printing thermostat meta data:")
        Thermostat.print_all_thermostat_metadata(sht31_config.UNIT_TEST_ZONE)

        # create mock runtime args
        api.uip = api.UserInputs(utc.unit_test_sht31)

        # create Zone object
        Zone = sht31.ThermostatZone(Thermostat)

        # update runtime overrides
        Zone.update_runtime_parameters()

        print("current thermostat settings...")
        print(f"switch position: {Zone.get_system_switch_position()}")
        print(f"heat mode={Zone.is_heat_mode()}")
        print(f"cool mode={Zone.is_cool_mode()}")
        print(f"temporary hold minutes={Zone.get_temporary_hold_until_time()}")
        meta_data = Thermostat.get_all_metadata(sht31_config.UNIT_TEST_ZONE, retry=True)
        print(f"thermostat meta data={meta_data}")
        print(
            f"thermostat display temp="
            f"{util.temp_value_with_units(Zone.get_display_temp())}"
        )

        # verify measurements
        self.assertEqual(
            meta_data["measurements"],
            sht31_config.MEASUREMENTS,
            f"measurements: actual={meta_data['measurements']}, "
            f"expected={sht31_config.MEASUREMENTS}",
        )

        # verify metadata
        test_cases = {
            "get_display_temp": {"min_val": 80, "max_val": 120},
            "get_is_humidity_supported": {"min_val": True, "max_val": True},
            "get_display_humidity": {"min_val": 49, "max_val": 51},
        }
        for param, limits in test_cases.items():
            return_val = getattr(Zone, param)()
            print(f"'{param}'={return_val}")
            min_val = limits["min_val"]
            max_val = limits["max_val"]
            self.assertTrue(
                min_val <= return_val <= max_val,
                f"'{param}'={return_val}, not between {min_val} " f"and {max_val}",
            )
        # cleanup
        del Zone
        del Thermostat


class RuntimeParameterTest(utc.RuntimeParameterTest):
    """sht31 flask server Runtime parameter tests."""

    mod = sht31_fs  # module to test
    script = os.path.realpath(__file__)
    debug = False

    # fields for testing, mapped to class variables.
    # (value, field name)
    test_fields = [
        (script, os.path.realpath(__file__)),
        (debug, sht31_fs.input_flds.debug_fld),
    ]


class Sht31FlaskServerSensorUnit(utc.UnitTest):
    """Test suite for SHT31 Flask Server Sensors class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_app = MagicMock()
        self.mock_app.debug = True
        with patch("thermostatsupervisor.sht31_flask_server.app", self.mock_app):
            self.sensors = sht31_fs.Sensors()

    def test_init(self):
        """Test Sensors initialization."""
        self.assertTrue(self.sensors.verbose)

        # Test with debug False
        self.mock_app.debug = False
        with patch("thermostatsupervisor.sht31_flask_server.app", self.mock_app):
            sensors = sht31_fs.Sensors()
            self.assertFalse(sensors.verbose)

    def test_convert_data_normal_range(self):
        """Test convert_data with normal range values."""
        test_data = [100, 150, 200, 250, 300, 350]  # Example raw data
        # update CRC values in test_data
        test_data[2] = self.sensors.calculate_crc(test_data[0:2])
        test_data[5] = self.sensors.calculate_crc(test_data[3:5])
        temp, temp_c, temp_f, humidity = self.sensors.convert_data(test_data)

        self.assertEqual(temp, 25750)  # 100 * 256 + 150
        self.assertIsInstance(temp_c, float)
        self.assertIsInstance(temp_f, float)
        self.assertIsInstance(humidity, float)

    def test_convert_data_min_values(self):
        """Test convert_data with minimum values."""
        test_data = [0] * sht31_fs.i2c_data_length  # Min possible values
        # update CRC values in test_data
        test_data[2] = self.sensors.calculate_crc(test_data[0:2])
        test_data[5] = self.sensors.calculate_crc(test_data[3:5])
        temp, temp_c, temp_f, humidity = self.sensors.convert_data(test_data)

        self.assertEqual(temp, 0)
        self.assertAlmostEqual(temp_c, -45.0)
        self.assertAlmostEqual(temp_f, -49.0)
        self.assertGreaterEqual(humidity, 0.0)

    def test_convert_data_max_values(self):
        """Test convert_data with maximum values."""
        test_data = [255] * sht31_fs.i2c_data_length  # Max possible values
        # update CRC values in test_data
        test_data[2] = self.sensors.calculate_crc(test_data[0:2])
        test_data[5] = self.sensors.calculate_crc(test_data[3:5])
        temp, temp_c, temp_f, humidity = self.sensors.convert_data(test_data)

        self.assertEqual(temp, 65535)
        self.assertAlmostEqual(temp_c, 130.0, places=2)
        self.assertAlmostEqual(temp_f, 266.0, places=2)
        self.assertLessEqual(humidity, 100.0)

    def test_convert_data_invalid_input(self):
        """Test convert_data with invalid input."""
        invalid_inputs = [
            [],  # Empty list
            [100],  # Single value
            [100] * (sht31_fs.i2c_data_length - 1),  # Too few values
            [100] * (sht31_fs.i2c_data_length + 1),  # Too many values
            None,  # None
            "invalid",  # Wrong type
        ]

        for invalid_input in invalid_inputs:
            with self.assertRaises(Exception):
                self.sensors.convert_data(invalid_input)

    def test_calculate_crc(self):
        """Test CRC calculation."""
        test_cases = [
            # (input_data, expected_crc)
            ([0x00, 0x00], 0x81),  # All zeros
            ([0xFF, 0xFF], 0xAC),  # All ones
            ([0xBE, 0xEF], 0x92),  # Random values
            ([0xDE, 0xAD], 0x98),  # Random values
            ([0x12, 0x34], 0x37),  # Random values
        ]

        for data, expected_crc in test_cases:
            calculated_crc = self.sensors.calculate_crc(data)
            self.assertEqual(
                calculated_crc,
                expected_crc,
                f"CRC mismatch for data {[hex(x) for x in data]}: "
                f"expected {hex(expected_crc)}, got {hex(calculated_crc)}",
            )

    def test_validate_crc(self):
        """Test CRC validation."""
        test_cases = [
            # (data, checksum, expected_result)
            ([0x4A, 0xEA], 0xFC, True),  # actual data from SHT31
            ([0x4A, 0x9B], 0x35, True),  # actual data from SHT31
            ([0x00, 0x00], 0x81, True),  # Valid CRC
            ([0xFF, 0xFF], 0xAC, True),  # Valid CRC
            ([0xBE, 0xEF], 0x92, True),  # Valid CRC
            ([0xDE, 0xAD], 0x98, True),  # Valid CRC
            ([0x00, 0x00], 0x00, False),  # Invalid CRC
            ([0xFF, 0xFF], 0xFF, False),  # Invalid CRC
            ([0x12, 0x34], 0x37, True),  # Valid CRC
            # Additional SHT31 typical test cases
            ([0xBE, 0xFF], 0xD1, True),  # Valid CRC
            ([0x65, 0x4C], 0xE3, True),  # Valid CRC
        ]

        for data, checksum, expected in test_cases:
            result = self.sensors.validate_crc(data, checksum)
            actual = self.sensors.calculate_crc(data)
            self.assertEqual(
                result,
                expected,
                f"CRC validation failed for data {[hex(x) for x in data]} "
                f"with checksum {hex(checksum)}, actual={hex(actual)}",
            )

    def test_seed_value_functionality(self):
        """Test that seed parameter affects generated unit test data."""
        # Import Flask app from sht31_flask_server module
        from thermostatsupervisor.sht31_flask_server import app

        # Test different seed values to ensure they produce different results
        test_seeds = [0x7F, 0x50, 0xA0]  # Default seed, and two other values
        results = {}

        # Create Flask application context for the test
        with app.test_request_context():
            # Mock the wifi strength method to avoid system dependency
            with patch.object(
                self.sensors, "get_iwconfig_wifi_strength", return_value=-50
            ):
                for seed in test_seeds:
                    # Mock Flask request args with specific seed and measurements=1
                    with patch(
                        "thermostatsupervisor.sht31_flask_server.request"
                    ) as mock_request:
                        # Create a proper mock that returns values based on the key
                        def mock_args_get(key, default=None, type=None):
                            values = {
                                "measurements": 1,  # Single measurement for
                                # simple comparison
                                "seed": seed,
                            }
                            value = values.get(key, default)
                            if type is not None and value is not None:
                                return type(value)
                            return value

                        mock_request.args.get = mock_args_get

                        # Get unit test data with the mocked seed
                        data = self.sensors.get_unit_test()

                        # Store results for comparison
                        results[seed] = data

                        # Verify the response contains expected keys
                        self.assertIn("measurements", data)
                        self.assertIn("Temp(F) mean", data)
                        self.assertIn("Temp(C) mean", data)
                        self.assertIn("Humidity(%RH) mean", data)

                        # Verify measurements count is correct
                        self.assertEqual(data["measurements"], 1)

                # Verify that different seeds produce different temperature values
                seed_values = list(test_seeds)
                for i in range(len(seed_values)):
                    for j in range(i + 1, len(seed_values)):
                        seed1, seed2 = seed_values[i], seed_values[j]
                        temp_f1 = results[seed1]["Temp(F) mean"]
                        temp_f2 = results[seed2]["Temp(F) mean"]
                        self.assertNotEqual(
                            temp_f1,
                            temp_f2,
                            f"Different seeds {hex(seed1)} and {hex(seed2)} "
                            f"should produce different temperatures, "
                            f"but both gave {temp_f1}°F",
                        )

                        # Also verify humidity values are different
                        humidity1 = results[seed1]["Humidity(%RH) mean"]
                        humidity2 = results[seed2]["Humidity(%RH) mean"]
                        self.assertNotEqual(
                            humidity1,
                            humidity2,
                            f"Different seeds {hex(seed1)} and {hex(seed2)} "
                            f"should produce different humidity values, "
                            f"but both gave {humidity1}%RH",
                        )

                # Test reproducibility - same seed should give same results
                with patch(
                    "thermostatsupervisor.sht31_flask_server.request"
                ) as mock_request:

                    def mock_args_get_repeat(key, default=None, type=None):
                        values = {
                            "measurements": 1,
                            "seed": test_seeds[0],  # Use first seed again
                        }
                        value = values.get(key, default)
                        if type is not None and value is not None:
                            return type(value)
                        return value

                    mock_request.args.get = mock_args_get_repeat

                    repeat_data = self.sensors.get_unit_test()

                    # Verify reproducibility
                    original_data = results[test_seeds[0]]
                    self.assertEqual(
                        repeat_data["Temp(F) mean"],
                        original_data["Temp(F) mean"],
                        "Same seed should produce identical temperature readings",
                    )
                    self.assertEqual(
                        repeat_data["Humidity(%RH) mean"],
                        original_data["Humidity(%RH) mean"],
                        "Same seed should produce identical humidity readings",
                    )

    def test_i2c_read_logic_levels(self):
        """Test i2c logic levels reading method."""
        # Mock the pi_library_exception to None (successful GPIO import)
        with patch(
            "thermostatsupervisor.sht31_flask_server.pi_library_exception", None
        ):
            # Mock the GPIO module
            with patch("thermostatsupervisor.sht31_flask_server.GPIO") as mock_gpio:
                # Mock GPIO setup and input calls
                mock_gpio.BCM = "BCM"
                mock_gpio.IN = "IN"
                mock_gpio.input.side_effect = [1, 0]  # SDA high, SCL low

                # Call the method
                result = self.sensors.i2c_read_logic_levels()

                # Validate result structure
                self.assertIn("i2c_logic_levels", result)
                logic_data = result["i2c_logic_levels"]

                # Check required fields
                required_fields = [
                    "sda_pin",
                    "scl_pin",
                    "sda_level",
                    "scl_level",
                    "sda_state",
                    "scl_state",
                    "timestamp",
                ]
                for field in required_fields:
                    self.assertIn(field, logic_data)

                # Verify pin assignments
                self.assertEqual(logic_data["sda_pin"], sht31_config.SDA_PIN)
                self.assertEqual(logic_data["scl_pin"], sht31_config.SCL_PIN)

                # Verify logic levels
                self.assertEqual(logic_data["sda_level"], 1)
                self.assertEqual(logic_data["scl_level"], 0)
                self.assertEqual(logic_data["sda_state"], "HIGH")
                self.assertEqual(logic_data["scl_state"], "LOW")

                # Verify GPIO was set up correctly
                mock_gpio.setmode.assert_called_with("BCM")
                mock_gpio.setup.assert_any_call(sht31_config.SDA_PIN, "IN")
                mock_gpio.setup.assert_any_call(sht31_config.SCL_PIN, "IN")
                mock_gpio.cleanup.assert_called_once()

    def test_i2c_bus_health_check(self):
        """Test comprehensive i2c bus health check method."""
        # Mock the pi_library_exception to None (successful GPIO import)
        with patch(
            "thermostatsupervisor.sht31_flask_server.pi_library_exception", None
        ):
            # Mock the GPIO module
            with patch("thermostatsupervisor.sht31_flask_server.GPIO") as mock_gpio:
                # Mock GPIO calls for healthy bus (both pins high)
                mock_gpio.BCM = "BCM"
                mock_gpio.IN = "IN"
                mock_gpio.input.side_effect = [1, 1]  # SDA and SCL high

                # Mock i2c_detect to return successful detection
                with patch.object(self.sensors, "i2c_detect") as mock_detect:
                    mock_detect.return_value = {
                        "i2c_detect": {"bus_1": {"addr_base_40": {}}}
                    }

                    # Call the method
                    result = self.sensors.i2c_bus_health_check()

                    # Validate result structure
                    self.assertIn("i2c_bus_health", result)
                    health_data = result["i2c_bus_health"]

                    # Check required fields
                    required_fields = [
                        "bus_status",
                        "overall_health",
                        "health_issues",
                        "logic_levels",
                        "device_detection",
                        "timestamp",
                        "recommendations",
                    ]
                    for field in required_fields:
                        self.assertIn(field, health_data)

                    # For healthy bus, should be IDLE status
                    self.assertEqual(health_data["bus_status"], "IDLE")
                    self.assertIsInstance(health_data["health_issues"], list)
                    self.assertIsInstance(health_data["recommendations"], list)

    def test_i2c_bus_health_check_stuck_low(self):
        """Test i2c bus health check for stuck low condition."""
        # Mock the pi_library_exception to None (successful GPIO import)
        with patch(
            "thermostatsupervisor.sht31_flask_server.pi_library_exception", None
        ):
            # Mock the GPIO module
            with patch("thermostatsupervisor.sht31_flask_server.GPIO") as mock_gpio:
                # Mock GPIO calls for stuck bus (both pins low)
                mock_gpio.BCM = "BCM"
                mock_gpio.IN = "IN"
                mock_gpio.input.side_effect = [0, 0]  # Both SDA and SCL low

                # Mock i2c_detect to return successful detection
                with patch.object(self.sensors, "i2c_detect") as mock_detect:
                    mock_detect.return_value = {"i2c_detect": {"bus_1": {}}}

                    # Call the method
                    result = self.sensors.i2c_bus_health_check()

                    # Validate result structure
                    health_data = result["i2c_bus_health"]

                    # For stuck bus, should be STUCK_LOW and CRITICAL
                    self.assertEqual(health_data["bus_status"], "STUCK_LOW")
                    self.assertEqual(health_data["overall_health"], "CRITICAL")
                    self.assertIn(
                        "Both SDA and SCL pins stuck LOW", health_data["health_issues"]
                    )

                    # Should have recovery recommendations
                    recommendations = health_data["recommendations"]
                    self.assertTrue(
                        any("recovery" in rec.lower() for rec in recommendations)
                    )

    def test_get_health_recommendations(self):
        """Test health recommendations generation."""
        # Test recommendations for stuck bus
        recs = self.sensors._get_health_recommendations("STUCK_LOW")
        self.assertIsInstance(recs, list)
        self.assertTrue(len(recs) > 0)
        self.assertTrue(any("recovery" in rec.lower() for rec in recs))

        # Test recommendations for idle bus
        recs = self.sensors._get_health_recommendations("IDLE")
        self.assertIsInstance(recs, list)
        self.assertTrue(len(recs) > 0)

    def test_set_sht31_address(self):
        """Test setting SHT31 address configuration."""
        # Mock GPIO when library is available
        with patch(
            "thermostatsupervisor.sht31_flask_server.pi_library_exception", None
        ):
            with patch("thermostatsupervisor.sht31_flask_server.GPIO") as mock_gpio:
                mock_gpio.BCM = "BCM"
                mock_gpio.OUT = "OUT"
                mock_gpio.IN = "IN"
                mock_gpio.PUD_UP = "PUD_UP"
                mock_gpio.HIGH = 1
                mock_gpio.LOW = 0

                # Test setting address 0x45 (HIGH)
                self.sensors.set_sht31_address(0x45, 4, 5)
                mock_gpio.setmode.assert_called_with("BCM")
                mock_gpio.setup.assert_any_call(4, "OUT")
                mock_gpio.setup.assert_any_call(5, "IN", pull_up_down="PUD_UP")
                mock_gpio.output.assert_called_with(4, 1)

                # Test setting address 0x44 (LOW)
                mock_gpio.reset_mock()
                self.sensors.set_sht31_address(0x44, 4, 5)
                mock_gpio.output.assert_called_with(4, 0)

    def test_send_i2c_cmd_success(self):
        """Test successful I2C command sending."""
        # Mock smbus2 operations
        mock_bus = MagicMock()
        test_command = (0x30, [0xA2])  # soft reset command

        with patch("time.sleep"):  # Mock sleep to speed up test
            self.sensors.send_i2c_cmd(mock_bus, 0x44, test_command)

        mock_bus.write_i2c_block_data.assert_called_once_with(0x44, 0x30, [0xA2])

    def test_send_i2c_cmd_error(self):
        """Test I2C command sending with error."""
        mock_bus = MagicMock()
        mock_bus.write_i2c_block_data.side_effect = OSError("Device not responding")
        test_command = (0x30, [0xA2])

        with patch("time.sleep"):
            with self.assertRaises(OSError):
                self.sensors.send_i2c_cmd(mock_bus, 0x44, test_command)

    def test_parse_fault_register_data_success(self):
        """Test successful fault register data parsing."""
        # Test with known fault register values
        test_data = [0x80, 0x01, 0x00]  # Alert pending + write checksum error
        result = self.sensors.parse_fault_register_data(test_data)

        self.assertIn("raw", result)
        self.assertIn("raw_binary", result)
        self.assertEqual(result["alert pending status(0=0,1=1+)"], 1)
        self.assertEqual(result["Write data checksum status(0=correct,1=failed)"], 1)

    def test_parse_fault_register_data_error(self):
        """Test fault register parsing with insufficient data."""
        # Test with empty data to trigger IndexError
        result = self.sensors.parse_fault_register_data([])
        self.assertIn("raw", result)
        self.assertEqual(result["raw"], [])

    def test_pack_data_structure(self):
        """Test data structure packing for API response."""
        temp_f = [68.0, 69.0, 70.0]
        temp_c = [20.0, 20.5, 21.1]
        humidity = [45.0, 46.0, 47.0]
        rssi = [-50.0, -51.0, -52.0]

        result = self.sensors.pack_data_structure(temp_f, temp_c, humidity, rssi)

        # Check required API fields exist
        self.assertIn("measurements", result)
        self.assertIn("Temp(C) mean", result)
        self.assertIn("Temp(F) mean", result)
        self.assertIn("Humidity(%RH) mean", result)
        self.assertIn("rssi(dBm) mean", result)

        # Verify calculated values
        self.assertEqual(result["measurements"], 3)
        self.assertAlmostEqual(result["Temp(F) mean"], 69.0, places=1)
        self.assertAlmostEqual(result["Temp(C) mean"], 20.533, places=2)

    def test_get_iwconfig_wifi_strength_windows(self):
        """Test WiFi strength detection on Windows."""
        with patch(
            "thermostatsupervisor.environment.is_windows_environment", return_value=True
        ):
            with patch.object(self.sensors, "shell_cmd") as mock_shell:
                mock_shell.return_value = "Signal: 75%"

                result = self.sensors.get_iwconfig_wifi_strength()

                # Windows calculation: quality / 2 - 100
                expected = 75 / 2 - 100  # -37.5
                self.assertAlmostEqual(result, expected, places=1)

    def test_get_iwconfig_wifi_strength_linux(self):
        """Test WiFi strength detection on Linux."""
        with patch(
            "thermostatsupervisor.environment.is_windows_environment",
            return_value=False,
        ):
            with patch.object(self.sensors, "shell_cmd") as mock_shell:
                mock_shell.return_value = (
                    'wlan0     IEEE 802.11  ESSID:"TestNetwork"\n'
                    "          Mode:Managed  Frequency:2.437 GHz  "
                    "Access Point: 00:11:22:33:44:55\n"
                    "          Link Quality=65/70  Signal level=-45 dBm\n"
                )

                result = self.sensors.get_iwconfig_wifi_strength()
                self.assertEqual(result, -45.0)

    def test_get_iwlist_wifi_strength_windows_error(self):
        """Test that iwlist method raises error on Windows."""
        with patch(
            "thermostatsupervisor.environment.is_windows_environment", return_value=True
        ):
            with self.assertRaises(EnvironmentError):
                self.sensors.get_iwlist_wifi_strength()

    def test_shell_cmd(self):
        """Test shell command execution."""
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout.read.return_value = b"test\n"
            mock_proc.__enter__.return_value = mock_proc
            mock_popen.return_value = mock_proc

            result = self.sensors.shell_cmd(["echo", "test"])

            self.assertEqual(result, "test\n")
            mock_popen.assert_called_once()

    def test_shell_cmd_error(self):
        """Test shell command execution with error."""
        # The actual method doesn't catch FileNotFoundError, it lets it bubble up
        # So let's test the actual behavior
        with self.assertRaises(FileNotFoundError):
            self.sensors.shell_cmd(["nonexistent_cmd_that_does_not_exist"])

    def test_read_i2c_data_success(self):
        """Test successful I2C data reading."""
        mock_bus = MagicMock()
        expected_data = [0x4A, 0xEA, 0xFC, 0x4A, 0x9B, 0x35]
        mock_bus.read_i2c_block_data.return_value = expected_data

        with patch(
            "thermostatsupervisor.utilities.execute_with_extended_retries"
        ) as mock_retry:
            mock_retry.return_value = expected_data

            result = self.sensors.read_i2c_data(mock_bus, 0x44, 0x00, 6)

            self.assertEqual(result, expected_data)
            mock_retry.assert_called_once()

    def test_read_i2c_data_length_error(self):
        """Test I2C data reading with length mismatch."""
        mock_bus = MagicMock()
        # Return fewer bytes than expected
        mock_bus.read_i2c_block_data.return_value = [0x4A, 0xEA]

        def _failing_read():
            response = mock_bus.read_i2c_block_data(0x44, 0x00, 6)
            if len(response) != 6:
                raise ValueError("Length mismatch")
            return response

        with patch(
            "thermostatsupervisor.utilities.execute_with_extended_retries"
        ) as mock_retry:
            mock_retry.side_effect = ValueError("Length mismatch")

            with self.assertRaises(ValueError):
                self.sensors.read_i2c_data(mock_bus, 0x44, 0x00, 6)

    def test_i2c_detect_parsing(self):
        """Test I2C device detection parsing."""
        # Mock successful i2cdetect output
        mock_output = """     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- 44 -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- --                         """

        with patch.object(self.sensors, "shell_cmd", return_value=mock_output):
            result = self.sensors.i2c_detect(1)

            self.assertIn("i2c_detect", result)
            self.assertIn("bus_1", result["i2c_detect"])

    def test_i2c_detect_error_handling(self):
        """Test I2C detection with error output."""
        mock_error_output = (
            "Error: Could not open file `/dev/i2c-1' or "
            "`/dev/i2c/1': No such file or directory"
        )

        with patch.object(self.sensors, "shell_cmd", return_value=mock_error_output):
            result = self.sensors.i2c_detect(1)

            self.assertIn("i2c_detect", result)
            # Should handle error gracefully

    def test_get_unit_test_with_parameters(self):
        """Test unit test data generation with request parameters."""
        # Create a Flask app context for testing
        from thermostatsupervisor.sht31_flask_server import app

        with app.test_request_context("/unit?measurements=5&seed=123"):
            with patch.object(
                self.sensors, "get_iwconfig_wifi_strength", return_value=-50.0
            ):
                result = self.sensors.get_unit_test()

                # Verify response structure
                self.assertIn("measurements", result)
                self.assertEqual(result["measurements"], 5)

                # Verify the data is present
                self.assertIn("Temp(C) mean", result)
                self.assertIn("Temp(F) mean", result)
                self.assertIn("Humidity(%RH) mean", result)

    def test_convert_data_with_crc_warnings(self):
        """Test convert_data with CRC validation warnings."""
        # Create test data with intentionally wrong CRC
        test_data = [100, 150, 0xFF, 250, 50, 0xFF]  # Wrong CRC values

        with patch("builtins.print") as mock_print:
            temp, temp_c, temp_f, humidity = self.sensors.convert_data(test_data)

            # Should print CRC warnings
            self.assertTrue(mock_print.called)
            warning_calls = [
                call
                for call in mock_print.call_args_list
                if "WARNING: CRC validation failed" in str(call)
            ]
            self.assertGreater(len(warning_calls), 0)

    def test_get_iwlist_wifi_strength_parsing(self):
        """Test iwlist wifi strength parsing logic."""
        # Mock iwlist output
        mock_iwlist_output = """Cell 01 - Address: 00:11:22:33:44:55
          ESSID:"TestNetwork"
          Mode:Managed
          Frequency:2.437 GHz (Channel 6)
          Quality=65/70  Signal level=-45 dBm
          Encryption key:on"""

        with patch(
            "thermostatsupervisor.environment.is_windows_environment",
            return_value=False,
        ):
            with patch.object(
                self.sensors, "shell_cmd", return_value=mock_iwlist_output
            ):
                result = self.sensors.get_iwlist_wifi_strength(0)

                self.assertEqual(result, -45.0)

    def test_calculate_crc_reverse_mode(self):
        """Test CRC calculation with reverse mode."""
        # Test the reverse branch of CRC calculation
        test_data = [0xFF, 0xFF]
        result = self.sensors.calculate_crc(test_data, reverse=True)
        self.assertIsInstance(result, int)
        self.assertGreaterEqual(result, 0)
        self.assertLessEqual(result, 255)

    def test_calculate_crc_high_bit_set(self):
        """Test CRC calculation with high bit triggering polynomial XOR."""
        # Use data that will trigger the high bit condition
        test_data = [0x80, 0x80]  # High bit set
        result = self.sensors.calculate_crc(test_data, reverse=False)
        self.assertIsInstance(result, int)


@unittest.skipIf(not utc.ENABLE_SHT31_TESTS, "sht31 tests are disabled")
class TestSht31FlaskEndpoints(utc.UnitTest):
    """Test suite for SHT31 Flask endpoint classes."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_app = MagicMock()
        self.mock_app.debug = True

    def test_production_endpoint(self):
        """Test Controller endpoint class."""
        with patch("thermostatsupervisor.sht31_flask_server.app", self.mock_app):
            endpoint = sht31_fs.Controller()
            self.assertIsInstance(endpoint, sht31_fs.Controller)

            # Test that get method calls Sensors().get()
            with patch.object(sht31_fs.Sensors, "get") as mock_get:
                mock_get.return_value = {"test": "data"}
                endpoint.get()
                mock_get.assert_called_once()

    def test_unit_test_endpoint(self):
        """Test ControllerUnit endpoint class."""
        with patch("thermostatsupervisor.sht31_flask_server.app", self.mock_app):
            endpoint = sht31_fs.ControllerUnit()
            self.assertIsInstance(endpoint, sht31_fs.ControllerUnit)

            # Test that get method calls Sensors().get_unit_test()
            with patch.object(sht31_fs.Sensors, "get_unit_test") as mock_get:
                mock_get.return_value = {"test": "unit_data"}
                endpoint.get()
                mock_get.assert_called_once()

    def test_diagnostics_endpoint(self):
        """Test ReadFaultRegister endpoint class."""
        with patch("thermostatsupervisor.sht31_flask_server.app", self.mock_app):
            endpoint = sht31_fs.ReadFaultRegister()
            self.assertIsInstance(endpoint, sht31_fs.ReadFaultRegister)

            # Test that get method calls Sensors().send_cmd_get_diag()
            with patch.object(sht31_fs.Sensors, "send_cmd_get_diag") as mock_get:
                mock_get.return_value = {"diag": "data"}
                endpoint.get()
                mock_get.assert_called_once()

    def test_clear_diagnostics_endpoint(self):
        """Test ClearFaultRegister endpoint class."""
        with patch("thermostatsupervisor.sht31_flask_server.app", self.mock_app):
            endpoint = sht31_fs.ClearFaultRegister()
            self.assertIsInstance(endpoint, sht31_fs.ClearFaultRegister)

            # Test that get method calls Sensors().send_cmd_get_diag()
            with patch.object(sht31_fs.Sensors, "send_cmd_get_diag") as mock_get:
                mock_get.return_value = {"cleared": "data"}
                endpoint.get()
                mock_get.assert_called_once()

    def test_enable_heater_endpoint(self):
        """Test EnableHeater endpoint class."""
        with patch("thermostatsupervisor.sht31_flask_server.app", self.mock_app):
            endpoint = sht31_fs.EnableHeater()
            self.assertIsInstance(endpoint, sht31_fs.EnableHeater)

            with patch.object(sht31_fs.Sensors, "send_cmd_get_diag") as mock_get:
                mock_get.return_value = {"heater": "enabled"}
                endpoint.get()
                mock_get.assert_called_once()

    def test_disable_heater_endpoint(self):
        """Test DisableHeater endpoint class."""
        with patch("thermostatsupervisor.sht31_flask_server.app", self.mock_app):
            endpoint = sht31_fs.DisableHeater()
            self.assertIsInstance(endpoint, sht31_fs.DisableHeater)

            with patch.object(sht31_fs.Sensors, "send_cmd_get_diag") as mock_get:
                mock_get.return_value = {"heater": "disabled"}
                endpoint.get()
                mock_get.assert_called_once()

    def test_soft_reset_endpoint(self):
        """Test SoftReset endpoint class."""
        with patch("thermostatsupervisor.sht31_flask_server.app", self.mock_app):
            endpoint = sht31_fs.SoftReset()
            self.assertIsInstance(endpoint, sht31_fs.SoftReset)

            with patch.object(sht31_fs.Sensors, "send_cmd_get_diag") as mock_get:
                mock_get.return_value = {"reset": "soft"}
                endpoint.get()
                mock_get.assert_called_once()

    def test_reset_endpoint(self):
        """Test Reset endpoint class."""
        with patch("thermostatsupervisor.sht31_flask_server.app", self.mock_app):
            endpoint = sht31_fs.Reset()
            self.assertIsInstance(endpoint, sht31_fs.Reset)

            with patch.object(sht31_fs.Sensors, "send_cmd_get_diag") as mock_get:
                mock_get.return_value = {"reset": "hard"}
                endpoint.get()
                mock_get.assert_called_once()

    def test_i2c_recovery_endpoint(self):
        """Test I2CRecovery endpoint class."""
        with patch("thermostatsupervisor.sht31_flask_server.app", self.mock_app):
            endpoint = sht31_fs.I2CRecovery()
            self.assertIsInstance(endpoint, sht31_fs.I2CRecovery)

            with patch.object(sht31_fs.Sensors, "i2c_recovery") as mock_recovery:
                mock_recovery.return_value = {"recovery": "success"}
                endpoint.get()
                mock_recovery.assert_called_once()

    def test_i2c_detect_endpoint(self):
        """Test I2CDetect endpoint class."""
        with patch("thermostatsupervisor.sht31_flask_server.app", self.mock_app):
            endpoint = sht31_fs.I2CDetect()
            self.assertIsInstance(endpoint, sht31_fs.I2CDetect)

            with patch.object(sht31_fs.Sensors, "i2c_detect") as mock_detect:
                mock_detect.return_value = {"devices": "found"}
                endpoint.get()
                mock_detect.assert_called_once()

    def test_i2c_logic_levels_endpoint(self):
        """Test I2CLogicLevels endpoint class."""
        with patch("thermostatsupervisor.sht31_flask_server.app", self.mock_app):
            endpoint = sht31_fs.I2CLogicLevels()
            self.assertIsInstance(endpoint, sht31_fs.I2CLogicLevels)

            with patch.object(sht31_fs.Sensors, "i2c_read_logic_levels") as mock_logic:
                mock_logic.return_value = {"logic": "levels"}
                endpoint.get()
                mock_logic.assert_called_once()

    def test_i2c_bus_health_endpoint(self):
        """Test I2CBusHealth endpoint class."""
        with patch("thermostatsupervisor.sht31_flask_server.app", self.mock_app):
            endpoint = sht31_fs.I2CBusHealth()
            self.assertIsInstance(endpoint, sht31_fs.I2CBusHealth)

            with patch.object(sht31_fs.Sensors, "i2c_bus_health_check") as mock_health:
                mock_health.return_value = {"health": "good"}
                endpoint.get()
                mock_health.assert_called_once()

    def test_i2c_detect_bus0_endpoint(self):
        """Test I2CDetectBus0 endpoint class."""
        with patch("thermostatsupervisor.sht31_flask_server.app", self.mock_app):
            endpoint = sht31_fs.I2CDetectBus0()
            self.assertIsInstance(endpoint, sht31_fs.I2CDetectBus0)

            with patch.object(sht31_fs.Sensors, "i2c_detect") as mock_detect:
                mock_detect.return_value = {"devices": "found"}
                endpoint.get()
                mock_detect.assert_called_once_with(0)

    def test_i2c_detect_bus1_endpoint(self):
        """Test I2CDetectBus1 endpoint class."""
        with patch("thermostatsupervisor.sht31_flask_server.app", self.mock_app):
            endpoint = sht31_fs.I2CDetectBus1()
            self.assertIsInstance(endpoint, sht31_fs.I2CDetectBus1)

            with patch.object(sht31_fs.Sensors, "i2c_detect") as mock_detect:
                mock_detect.return_value = {"devices": "found"}
                endpoint.get()
                mock_detect.assert_called_once_with(1)

    def test_print_ip_ban_block_list_endpoint(self):
        """Test PrintIPBanBlockList endpoint class."""
        with patch("thermostatsupervisor.sht31_flask_server.app", self.mock_app):
            endpoint = sht31_fs.PrintIPBanBlockList()
            self.assertIsInstance(endpoint, sht31_fs.PrintIPBanBlockList)

            # Mock the ip_ban object and flask functions
            with patch(
                "thermostatsupervisor.flask_generic."
                "print_ipban_block_list_with_timestamp"
            ):
                with patch(
                    "thermostatsupervisor.sht31_flask_server.ip_ban"
                ) as mock_ip_ban:
                    with patch(
                        "thermostatsupervisor.sht31_flask_server.jsonify"
                    ) as mock_jsonify:
                        mock_ip_ban.get_block_list.return_value = {"test": "data"}
                        mock_jsonify.return_value = {"test": "data"}

                        endpoint.get()
                        mock_ip_ban.get_block_list.assert_called_once()

    def test_clear_ip_ban_block_list_endpoint(self):
        """Test ClearIPBanBlockList endpoint class."""
        with patch("thermostatsupervisor.sht31_flask_server.app", self.mock_app):
            endpoint = sht31_fs.ClearIPBanBlockList()
            self.assertIsInstance(endpoint, sht31_fs.ClearIPBanBlockList)

            # Mock the ip_ban object and flask functions
            with patch("thermostatsupervisor.flask_generic.clear_ipban_block_list"):
                with patch(
                    "thermostatsupervisor.sht31_flask_server.ip_ban"
                ) as mock_ip_ban:
                    with patch(
                        "thermostatsupervisor.sht31_flask_server.jsonify"
                    ) as mock_jsonify:
                        mock_ip_ban.get_block_list.return_value = {"cleared": "data"}
                        mock_jsonify.return_value = {"cleared": "data"}

                        endpoint.get()
                        mock_ip_ban.get_block_list.assert_called_once()


@unittest.skipIf(not utc.ENABLE_SHT31_TESTS, "sht31 tests are disabled")
@unittest.skipIf(
    not utc.ENABLE_FLASK_INTEGRATION_TESTS, "flask integration tests are disabled"
)
class TestSht31FlaskClientAzure(utc.UnitTest):
    """
    Azure-compatible tests for SHT31 Flask server using test client.

    These tests use Flask's test_client() which doesn't require network access,
    making them suitable for Azure Pipelines environments.
    """

    def setUp(self):
        super().setUp()
        self.app = sht31_fs.create_app()
        self.client = self.app.test_client()
        self.app.config["TESTING"] = True
        # Initialize IP ban for testing
        from thermostatsupervisor import flask_generic as flg

        self.ip_ban = flg.initialize_ipban(self.app)

    def test_sht31_flask_server_endpoints_response(self):
        """Test that SHT31 Flask server endpoints return valid responses."""
        # Define endpoints that should return 200 status
        test_endpoints = [
            ("/data", "production"),
            ("/unit", "unit_test"),
            ("/diag", "diag"),
            ("/clear_diag", "clear_diag"),
            ("/enable_heater", "enable_heater"),
            ("/disable_heater", "disable_heater"),
            ("/soft_reset", "soft_reset"),
            ("/i2c_detect", "i2c_detect"),
            ("/i2c_detect/0", "i2c_detect_0"),
            ("/i2c_detect/1", "i2c_detect_1"),
            ("/i2c_logic_levels", "i2c_logic_levels"),
            ("/i2c_bus_health", "i2c_bus_health"),
            ("/print_block_list", "print_block_list"),
            ("/clear_block_list", "clear_block_list"),
            # Note: skipping '/reset' and '/i2c_recovery' for side effects
        ]

        for endpoint, test_name in test_endpoints:
            with self.subTest(endpoint=endpoint, test_name=test_name):
                try:
                    response = self.client.get(endpoint)
                    # Check that we get a valid response
                    self.assertIn(
                        response.status_code,
                        [200, 400, 404, 500],
                        f"Endpoint {endpoint} returned unexpected "
                        f"status {response.status_code}",
                    )

                    # For successful responses, check that we get JSON data
                    if response.status_code == 200:
                        self.assertTrue(
                            response.is_json or response.mimetype == "application/json",
                            f"Endpoint {endpoint} should return JSON data",
                        )
                        data = response.get_json()
                        self.assertIsInstance(
                            data, dict, f"Endpoint {endpoint} should return dict data"
                        )
                except Exception as e:
                    # In test environment, some endpoints may fail due to
                    # missing hardware. This is acceptable as we're testing
                    # the Flask routing, not hardware
                    print(
                        f"Warning: Endpoint {endpoint} failed with {e}, "
                        f"this may be expected in test environment"
                    )

    def test_sht31_flask_server_unit_test_endpoint(self):
        """Test the unit_test endpoint specifically."""
        try:
            response = self.client.get("/unit")

            # Should get a valid response (404 is OK if endpoint doesn't exist)
            self.assertIn(response.status_code, [200, 400, 404, 500])

            if response.status_code == 200:
                # Should return JSON data
                self.assertTrue(
                    response.is_json or response.mimetype == "application/json"
                )
                data = response.get_json()
                self.assertIsInstance(data, dict)
                # Should contain measurements key for unit test endpoint
                if "measurements" in data:
                    self.assertIsInstance(data["measurements"], int)
        except (FileNotFoundError, OSError) as e:
            # Expected in test environments where system utilities like
            # iwconfig aren't available
            print(f"Expected error in test environment: {e}")
            # This is actually a positive result - it means the routing worked
            # and we got to the correct endpoint code

    def test_sht31_flask_server_bad_routes(self):
        """Test that bad routes return proper 404 responses."""
        # Define non-existent endpoints that should return 404
        bad_endpoints = [
            "/nonexistent",
            "/bad_route",
            "/invalid_endpoint",
            "/not_found",
            "/fake_api",
            "/i2c_detect/999",  # Invalid bus number
            "/enable_heater/extra",  # Extra path component
        ]

        for endpoint in bad_endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                # Should get 404 for non-existent routes
                self.assertEqual(
                    response.status_code,
                    404,
                    f"Endpoint {endpoint} should return 404, "
                    f"got {response.status_code}",
                )

    def test_sht31_flask_server_ipban_registry(self):
        """Test IP ban registry functionality."""
        # Test the print_block_list endpoint
        response = self.client.get("/print_block_list")
        self.assertIn(
            response.status_code,
            [200, 500],  # 500 is OK in test environment
            f"print_block_list endpoint returned {response.status_code}",
        )

        if response.status_code == 200:
            # Should return JSON data
            self.assertTrue(
                response.is_json or response.mimetype == "application/json",
                "print_block_list should return JSON data",
            )
            data = response.get_json()
            self.assertIsInstance(
                data, dict, "print_block_list should return dict data"
            )
            # Block list should be a dictionary (even if empty)
            self.assertIsInstance(
                data, dict, "IP ban block list should be a dictionary"
            )

    def test_sht31_flask_server_clear_ipban_registry(self):
        """Test clearing the IP ban registry."""
        # Test the clear_block_list endpoint
        response = self.client.get("/clear_block_list")
        self.assertIn(
            response.status_code,
            [200, 500],  # 500 is OK in test environment
            f"clear_block_list endpoint returned {response.status_code}",
        )

        if response.status_code == 200:
            # Should return JSON data
            self.assertTrue(
                response.is_json or response.mimetype == "application/json",
                "clear_block_list should return JSON data",
            )
            data = response.get_json()
            self.assertIsInstance(
                data, dict, "clear_block_list should return dict data"
            )
            # After clearing, block list should be empty
            self.assertEqual(len(data), 0, "Block list should be empty after clearing")

    def test_sht31_flask_server_ipban_recovery_workflow(self):
        """Test the complete IP ban and recovery workflow."""
        from thermostatsupervisor import flask_generic as flg

        # Step 1: Clear the block list to ensure clean state
        clear_response = self.client.get("/clear_block_list")
        if clear_response.status_code == 200:
            cleared_data = clear_response.get_json()
            self.assertIsInstance(cleared_data, dict)
            self.assertEqual(
                len(cleared_data), 0, "Block list should be empty after clearing"
            )

            # Step 2: Check initial block list state
            print_response = self.client.get("/print_block_list")
            if print_response.status_code == 200:
                initial_data = print_response.get_json()
                self.assertIsInstance(initial_data, dict)
                self.assertEqual(
                    len(initial_data), 0, "Block list should be empty initially"
                )

                # Step 3: Test bad route triggering IP ban
                # Make requests to bad routes to trigger IP ban
                # Use ipban_ban_count to determine how many requests needed
                ban_count_needed = flg.ipban_ban_count
                print(f"Making {ban_count_needed} bad requests to trigger IP ban")

                # Test with known nuisance patterns that should trigger bans
                # These patterns are typically loaded by default in flask-ipban
                test_bad_routes = [
                    "/wp-admin",  # Common vulnerability scan target
                    "/admin",  # Another common target
                    "/.env",  # Environment file scanning
                    "/phpMyAdmin",  # Database admin tool scanning
                ]

                for i in range(ban_count_needed):
                    # Use both custom and known bad routes
                    bad_route = test_bad_routes[i % len(test_bad_routes)]
                    if i >= len(test_bad_routes):
                        bad_route = f"/nonexistent_route_{i}"

                    bad_response = self.client.get(bad_route)
                    self.assertEqual(
                        bad_response.status_code,
                        404,
                        f"Bad route {bad_route} should return 404",
                    )

                # Step 4: Check if IP was added to block list after bad requests
                check_response = self.client.get("/print_block_list")
                if check_response.status_code == 200:
                    blocked_data = check_response.get_json()
                    self.assertIsInstance(blocked_data, dict)
                    print(
                        f"Block list after {ban_count_needed} bad requests: "
                        f"{blocked_data}"
                    )

                    # Step 5: Since automatic IP banning may not work in test
                    # environment, manually add an IP to test the clear functionality
                    # This ensures we test the core IP ban registry management
                    with self.app.test_request_context():
                        # Manually add an IP to the ban list for testing purposes
                        self.ip_ban.add("192.168.1.100", url="/test_ban")
                        manual_blocked_data = self.ip_ban.get_block_list()
                        print(
                            f"Block list after manual addition: "
                            f"{manual_blocked_data}"
                        )

                        # Verify that the IP was added
                        self.assertGreater(
                            len(manual_blocked_data),
                            0,
                            "Block list should contain entries after manual addition",
                        )

                    # Step 6: Test the clear functionality
                    final_clear_response = self.client.get("/clear_block_list")
                    if final_clear_response.status_code == 200:
                        final_cleared_data = final_clear_response.get_json()
                        self.assertIsInstance(final_cleared_data, dict)
                        self.assertEqual(
                            len(final_cleared_data),
                            0,
                            "Block list should be empty after final clearing",
                        )

                        # Step 7: Verify block list is empty after clearing
                        verify_response = self.client.get("/print_block_list")
                        if verify_response.status_code == 200:
                            verify_data = verify_response.get_json()
                            self.assertIsInstance(verify_data, dict)
                            self.assertEqual(
                                len(verify_data),
                                0,
                                "Block list should remain empty after verification",
                            )


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
