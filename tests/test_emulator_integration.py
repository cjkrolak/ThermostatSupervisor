"""
Integration test module for emulator.py.

This test requires connection to emulator thermostat.
"""
# built-in imports
import math
import unittest

# local imports
from thermostatsupervisor import emulator
from thermostatsupervisor import emulator_config
from thermostatsupervisor import utilities as util
from tests import unit_test_common as utc


class IntegrationTest(utc.IntegrationTest):
    """
    Test functions in emulator.py.
    """

    def setUpIntTest(self):
        """Setup common to integration tests."""
        self.setup_common()
        self.print_test_name()

        # emulator argv list must be valid settings
        self.unit_test_argv = [
            "supervise.py",  # module
            "emulator",  # thermostat type
            "0",  # zone
            "5",  # poll time in sec, this value violates min
            # cycle time for TCC if reverting temperature deviation
            "11",  # reconnect time in sec
            "2",  # tolerance
            "UNKNOWN_MODE",  # thermostat mode, no target
            "6",  # number of measurements
        ]
        self.mod = emulator
        self.mod_config = emulator_config


class FunctionalIntegrationTest(IntegrationTest, utc.FunctionalIntegrationTest):
    """
    Test functional performance of emulator.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()
        # test_GetMetaData input parameters
        self.trait_field = None
        self.metadata_field = "display_temp"
        self.metadata_type = float

    def test_deviation_functionality(self):
        """Test emulator deviation functionality for improved testability."""
        self.print_test_name()

        # Create thermostat zone instance
        Thermostat = self.mod.ThermostatClass(zone="0", verbose=False)
        Zone = self.mod.ThermostatZone(Thermostat, verbose=False)

        try:
            # Test 1: Initial state - no deviation data
            self.assertFalse(
                Zone.has_deviation_data(), "Should have no deviation data initially"
            )

            # Test 2: Create deviation file
            Zone.create_deviation_file()
            self.assertTrue(
                Zone.has_deviation_data(), "Should have deviation file after creation"
            )

            # Test 3: Set specific deviation values
            test_temp = 85.5
            test_humidity = 60.0
            test_heat_sp = 68.0
            test_cool_sp = 76.0

            Zone.set_deviation_value("display_temp", test_temp)
            Zone.set_deviation_value("display_humidity", test_humidity)
            Zone.set_deviation_value("heat_setpoint", test_heat_sp)
            Zone.set_deviation_value("cool_setpoint", test_cool_sp)

            # Test 4: Verify deviation values are returned
            self.assertTrue(
                Zone.has_deviation_data("display_temp"), "Should have temp deviation"
            )
            self.assertTrue(
                Zone.has_deviation_data("display_humidity"),
                "Should have humidity deviation",
            )
            self.assertTrue(
                Zone.has_deviation_data("heat_setpoint"),
                "Should have heat setpoint deviation",
            )
            self.assertTrue(
                Zone.has_deviation_data("cool_setpoint"),
                "Should have cool setpoint deviation",
            )

            self.assertEqual(
                Zone.get_display_temp(), test_temp, "Should return deviated temperature"
            )
            self.assertEqual(
                Zone.get_display_humidity(),
                test_humidity,
                "Should return deviated humidity",
            )
            self.assertEqual(
                Zone.get_heat_setpoint_raw(),
                test_heat_sp,
                "Should return deviated heat setpoint",
            )
            self.assertEqual(
                Zone.get_cool_setpoint_raw(),
                test_cool_sp,
                "Should return deviated cool setpoint",
            )

            # Test 5: Test individual value retrieval
            self.assertEqual(
                Zone.get_deviation_value("display_temp"),
                test_temp,
                "Should retrieve specific deviation value",
            )
            self.assertIsNone(
                Zone.get_deviation_value("nonexistent_key"),
                "Should return None for missing key",
            )
            self.assertEqual(
                Zone.get_deviation_value("nonexistent_key", "default"),
                "default",
                "Should return default for missing key",
            )

            # Test 6: Clear deviation data
            Zone.clear_deviation_data()
            self.assertFalse(
                Zone.has_deviation_data(),
                "Should have no deviation data after clearing",
            )

            # Test 7: Verify normal behavior is restored
            # Note: We can't compare exact values due to random noise,
            # but values should be in normal range
            current_temp = Zone.get_display_temp()
            current_humidity = Zone.get_display_humidity()

            # Values should be within normal variation range from base values
            temp_diff = abs(current_temp - Zone.get_parameter("display_temp"))
            humidity_diff = abs(
                current_humidity - Zone.get_parameter("display_humidity")
            )

            self.assertLessEqual(
                temp_diff,
                emulator_config.NORMAL_TEMP_VARIATION,
                "Temperature should be within normal variation "
                "after clearing deviation",
            )
            self.assertLessEqual(
                humidity_diff,
                emulator_config.NORMAL_HUMIDITY_VARIATION,
                "Humidity should be within normal variation after clearing deviation",
            )

        finally:
            # Cleanup: ensure deviation file is removed
            Zone.clear_deviation_data()


class SuperviseIntegrationTest(IntegrationTest, utc.SuperviseIntegrationTest):
    """
    Test supervise functionality of emulator.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()


class PerformanceIntegrationTest(IntegrationTest, utc.PerformanceIntegrationTest):
    """
    Test performance of emulator.py.
    """

    def setUp(self):
        super().setUp()
        self.setUpIntTest()
        # network timing measurement
        self.timeout_limit = 1
        self.timing_measurements = 30  # fast measurement

        # temperature and humidity repeatability measurements
        # data is uniform distribution, 1 std= (range)/sqrt(12)
        # adding 0.1 buffer to prevent false failures due to rounding, etc.
        self.temp_stdev_limit = (
            emulator_config.NORMAL_TEMP_VARIATION * 2 / math.sqrt(12) + 0.1
        )
        self.temp_repeatability_measurements = 100  # number of temp msmts.
        self.humidity_stdev_limit = (
            emulator_config.NORMAL_HUMIDITY_VARIATION * 2 / math.sqrt(12) + 0.1
        )
        self.humidity_repeatability_measurements = 100  # number of temp msmts.
        self.poll_interval_sec = 0.5  # delay between repeatability msmts


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
