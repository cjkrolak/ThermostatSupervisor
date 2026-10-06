"""
Integration tests for weather functionality with thermostat reporting.
"""

# built-in imports
import inspect
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

# third-party imports

# local imports
from src import blink_config
from src import emulator_config
from src import thermostat_api as api
from src import thermostat_common as tc
from src import utilities as util
from src import weather
from tests import unit_test_common as utc


class TestWeatherIntegration(utc.UnitTest):
    """Test weather integration with thermostat reporting."""

    def test_print_select_data_from_all_zones_signature(self):
        """Test that the function signature includes outdoor weather parameter."""

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

    def test_blink_zone_zip_codes(self):
        """Verify Blink zones use the requested location-specific zip codes."""
        for zone in list(range(7)) + list(range(14, 21)):
            with self.subTest(zone=zone):
                self.assertEqual(blink_config.metadata[zone]["zip_code"], "55760")
        for zone in range(7, 14):
            with self.subTest(zone=zone):
                self.assertEqual(blink_config.metadata[zone]["zip_code"], "55378")

    def test_zone_weather_uses_zone_zip_and_global_fallback(self):
        """Use zone overrides while retaining defaults for other thermostat types."""
        self.assertEqual(tc._get_zone_zip_code("blink", 7), "55378")
        self.assertEqual(tc._get_zone_zip_code("blink", 0), "55760")
        self.assertEqual(tc._get_zone_zip_code("emulator", 0), "55378")

        zone_objects = []
        for zone in (0, 7):
            zone_object = MagicMock()
            zone_object.zone_name = f"zone {zone}"
            zone_object.get_display_temp.return_value = 70.0
            zone_objects.append((object(), zone_object))

        def weather_for_zip(zip_code, _api_key):
            return {
                "zip_code": zip_code,
                "outdoor_temp": 68.5,
                "outdoor_humidity": 45.0,
                "outdoor_conditions": "Sunny",
            }

        with (
            patch.object(
                tc, "create_thermostat_instance", side_effect=zone_objects
            ),
            patch.object(weather, "get_weather_api_key", return_value=None),
            patch.object(
                weather, "get_outdoor_weather", side_effect=weather_for_zip
            ) as mock_get_weather,
            patch("builtins.print") as mock_print,
        ):
            tc.print_select_data_from_all_zones(
                "blink",
                [0, 7],
                object,
                object,
                display_wifi=False,
                display_battery=False,
            )

        self.assertEqual(
            [call.args[0] for call in mock_get_weather.call_args_list],
            ["55760", "55378"],
        )
        output = "\n".join(call.args[0] for call in mock_print.call_args_list)
        self.assertIn(
            "zone: 0, name: zone 0, temp: 70.0 °F, outdoor(55760)", output
        )
        self.assertIn(
            "zone: 7, name: zone 7, temp: 70.0 °F, outdoor(55378)", output
        )

    @patch("src.weather.get_outdoor_weather")
    @patch("src.weather.get_weather_api_key")
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
        expected = "outdoor(N/A): 68.5°F, 45%RH (Sunny)"
        self.assertEqual(formatted, expected)

    def test_config_integration(self):
        """Test that thermostat configurations properly include zip codes."""

        # Check that our modified configs have zip codes
        emulator_config_api = api.SUPPORTED_THERMOSTATS.get("emulator", {})
        self.assertIn("zip_code", emulator_config_api)
        self.assertEqual(emulator_config_api["zip_code"], "55378")

        honeywell_config_api = api.SUPPORTED_THERMOSTATS.get("honeywell", {})
        self.assertIn("zip_code", honeywell_config_api)
        self.assertEqual(honeywell_config_api["zip_code"], "55378")


if __name__ == "__main__":
    util.log_msg.debug = True  # type: ignore[attr-defined]
    unittest.main(verbosity=2)
