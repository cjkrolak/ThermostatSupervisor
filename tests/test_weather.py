"""
Unit tests for weather module.
"""

import unittest
from unittest.mock import patch, MagicMock

import requests

from src import utilities as util
from src import weather
from tests import unit_test_common as utc


class TestWeather(utc.UnitTest):
    """Test functions in weather.py."""

    @patch("src.weather.env.get_env_variable")
    def test_get_weather_api_key(self, mock_get_env_variable):
        """Test that the API key is read through the environment helper."""
        mock_get_env_variable.return_value = {
            "value": "test_key",
            "source": "supervisor-env.txt",
        }

        result = weather.get_weather_api_key()

        self.assertEqual(result, "test_key")
        mock_get_env_variable.assert_called_once_with(
            "OPENWEATHER_API_KEY", default=""
        )

        mock_get_env_variable.return_value = {
            "value": "",
            "source": "default",
        }

        with patch("src.weather.env.get_env_variable", return_value={"value": ""}):
            result = weather.get_weather_api_key()

        self.assertIsNone(result)

    def test_mask_weather_api_key_in_log_messages(self):
        """Test weather API keys and app IDs are redacted in logs."""
        raw_message = (
            "OPENWEATHER_API_KEY=super-secret-weather-key; "
            "api_key=another-secret; appid=top-secret-app-id"
        )

        sanitized = util._sanitize_log_message(raw_message)

        self.assertNotIn("super-secret-weather-key", sanitized)
        self.assertNotIn("another-secret", sanitized)
        self.assertNotIn("top-secret-app-id", sanitized)
        self.assertIn("OPENWEATHER_API_KEY=******", sanitized)
        self.assertIn("api_key=******", sanitized)
        self.assertIn("appid=******", sanitized)

    @patch("src.weather.util.log_msg")
    @patch("src.weather.get_weather_api_key", return_value=None)
    def test_get_outdoor_weather_no_api_key(
        self, mock_get_weather_api_key, mock_log_msg
    ):
        """Test a missing configured API key returns mock data."""
        result = weather.get_outdoor_weather("12345")

        mock_get_weather_api_key.assert_called_once_with()
        mock_log_msg.assert_called_once()
        self.assertIsInstance(result, dict)
        self.assertIn("outdoor_temp", result)
        self.assertIn("outdoor_humidity", result)
        self.assertIn("outdoor_conditions", result)
        self.assertEqual(result["data_source"], "mock")
        self.assertEqual(result["outdoor_temp"], -999.0)
        self.assertEqual(result["outdoor_humidity"], -999.0)
        self.assertEqual(result["outdoor_conditions"], "Missing API Key")

    def test_get_outdoor_weather_invalid_zip(self):
        """Test get_outdoor_weather with invalid zip code."""
        with self.assertRaises(weather.WeatherError):
            weather.get_outdoor_weather("")

        with self.assertRaises(weather.WeatherError):
            weather.get_outdoor_weather(None)  # type: ignore[arg-type]

    @patch("requests.get")
    def test_get_outdoor_weather_with_api_key(self, mock_get):
        """Test get_outdoor_weather with API key."""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "main": {"temp": 75.5, "humidity": 60},
            "weather": [{"description": "partly cloudy"}],
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = weather.get_outdoor_weather("12345", "test_api_key")

        self.assertEqual(result["outdoor_temp"], 75.5)
        self.assertEqual(result["outdoor_humidity"], 60.0)
        self.assertEqual(result["outdoor_conditions"], "Partly Cloudy")
        self.assertEqual(result["data_source"], "OpenWeatherMap")

    @patch("src.weather.util.log_msg")
    @patch("requests.get")
    def test_get_outdoor_weather_api_error(self, mock_get, mock_log_msg):
        """Test an HTTP request error raises a weather error."""
        mock_get.side_effect = requests.exceptions.RequestException("API Error")

        with self.assertRaises(weather.WeatherError):
            weather.get_outdoor_weather("12345", "test_api_key")

        mock_log_msg.assert_called_once()

    def test_format_weather_display(self):
        """Test format_weather_display function."""
        weather_data = {
            "outdoor_temp": 75.5,
            "outdoor_humidity": 60.0,
            "outdoor_conditions": "Partly Cloudy",
        }

        result = weather.format_weather_display(weather_data)
        expected = "outdoor(N/A): 75.5°F, 60%RH (Partly Cloudy)"
        self.assertEqual(result, expected)

    def test_format_weather_display_empty(self):
        """Test format_weather_display with empty data."""
        result = weather.format_weather_display({})
        self.assertEqual(result, "outdoor: N/A")

        result = weather.format_weather_display(None)  # type: ignore[arg-type]
        self.assertEqual(result, "outdoor: N/A")


if __name__ == "__main__":
    util.log_msg.debug = True  # type: ignore[attr-defined]
    unittest.main(verbosity=2)
