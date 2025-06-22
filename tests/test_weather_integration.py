"""
Integration tests for weather functionality with thermostat reporting.
"""
import unittest
from unittest.mock import patch
from thermostatsupervisor import thermostat_common as tc
from thermostatsupervisor import emulator_config
from thermostatsupervisor import weather


class TestWeatherIntegration(unittest.TestCase):
    """Test weather integration with thermostat reporting."""

    def test_print_select_data_from_all_zones_signature(self):
        """Test that the function signature includes outdoor weather parameter."""
        import inspect

        sig = inspect.signature(tc.print_select_data_from_all_zones)

        # Check that all expected parameters are present
        expected_params = [
            "thermostat_type",
            "zone_lst",
            "ThermostatClass",
            "ThermostatZone",
            "display_wifi",
            "display_battery",
            "display_outdoor_weather",
        ]

        actual_params = list(sig.parameters.keys())
        self.assertEqual(actual_params, expected_params)

        # Check that new parameter has correct default
        outdoor_weather_param = sig.parameters["display_outdoor_weather"]
        self.assertTrue(outdoor_weather_param.default)

    def test_emulator_config_has_zip_code(self):
        """Test that emulator config includes zip code."""
        zip_code = emulator_config.supported_configs.get("zip_code")
        self.assertIsNotNone(zip_code)
        self.assertIsInstance(zip_code, str)
        self.assertEqual(zip_code, "55378")

    @patch("thermostatsupervisor.weather.get_outdoor_weather")
    @patch("thermostatsupervisor.weather.get_weather_api_key")
    def test_weather_data_integration(self, mock_get_api_key, mock_get_weather):
        """Test weather data integration in thermostat reporting."""
        # Mock weather data
        mock_get_api_key.return_value = None  # No API key, should use mock data
        mock_get_weather.return_value = {
            "outdoor_temp": 68.5,
            "outdoor_humidity": 45.0,
            "outdoor_conditions": "Sunny",
            "data_source": "mock",
        }

        # Test weather display formatting
        weather_data = mock_get_weather.return_value
        formatted = weather.format_weather_display(weather_data)
        expected = "outdoor: 68.5°F, 45%RH (Sunny)"
        self.assertEqual(formatted, expected)

    def test_config_integration(self):
        """Test that thermostat configurations properly include zip codes."""
        from thermostatsupervisor import thermostat_api as api

        # Check that our modified configs have zip codes
        emulator_config_api = api.SUPPORTED_THERMOSTATS.get("emulator", {})
        self.assertIn("zip_code", emulator_config_api)
        self.assertEqual(emulator_config_api["zip_code"], "55378")

        honeywell_config_api = api.SUPPORTED_THERMOSTATS.get("honeywell", {})
        self.assertIn("zip_code", honeywell_config_api)
        self.assertEqual(honeywell_config_api["zip_code"], "55378")


if __name__ == "__main__":
    unittest.main()
