"""
Unit tests for weather module.
"""

import unittest
from unittest.mock import patch, MagicMock
from thermostatsupervisor import weather


class TestWeather(unittest.TestCase):
    """Test functions in weather.py."""

    def test_get_weather_api_key(self):
        """Test get_weather_api_key function."""
        with patch.dict("os.environ", {"WEATHER_API_KEY": "test_key"}):
            result = weather.get_weather_api_key()
            self.assertEqual(result, "test_key")

        with patch.dict("os.environ", {}, clear=True):
            result = weather.get_weather_api_key()
            self.assertIsNone(result)

    def test_get_outdoor_weather_no_api_key(self):
        """Test get_outdoor_weather with no API key returns mock data."""
        result = weather.get_outdoor_weather("12345")

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
            weather.get_outdoor_weather(None)

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

    @patch("requests.get")
    def test_get_outdoor_weather_api_error(self, mock_get):
        """Test get_outdoor_weather with API error."""
        mock_get.side_effect = Exception("API Error")

        with self.assertRaises(weather.WeatherError):
            weather.get_outdoor_weather("12345", "test_api_key")

    def test_format_weather_display(self):
        """Test format_weather_display function."""
        weather_data = {
            "outdoor_temp": 75.5,
            "outdoor_humidity": 60.0,
            "outdoor_conditions": "Partly Cloudy",
        }

        result = weather.format_weather_display(weather_data)
        expected = "outdoor: 75.5°F, 60%RH (Partly Cloudy)"
        self.assertEqual(result, expected)

    def test_format_weather_display_empty(self):
        """Test format_weather_display with empty data."""
        result = weather.format_weather_display({})
        self.assertEqual(result, "outdoor: N/A")

        result = weather.format_weather_display(None)
        self.assertEqual(result, "outdoor: N/A")


if __name__ == "__main__":
    unittest.main()
