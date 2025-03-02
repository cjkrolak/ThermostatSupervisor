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
        meta_data = Thermostat.get_all_metadata(sht31_config.UNIT_TEST_ZONE)
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


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
