"""
Weather API module for outdoor temperature and humidity data.

This module provides functions to fetch outdoor weather data using zip codes.
"""

# built-in imports
from typing import Dict, Optional

# third-party imports
import requests

# local imports
from src import environment as env
from src import utilities as util


class WeatherError(Exception):
    """Exception raised for weather API errors."""

    pass


def get_outdoor_weather(
    zip_code: str, api_key: Optional[str] = None
) -> Dict[str, float | str]:
    """
    Get outdoor temperature and humidity data for a given zip code.

    This function uses the OpenWeatherMap API to fetch current weather data.
    If no API key is provided, it loads the configured key. If no configured
    key exists, it returns mock data for testing.

    Args:
        zip_code (str): The zip code for which to fetch weather data
        api_key (str, optional): OpenWeatherMap API key

    Returns:
        Dict[str, float | str]: Dictionary containing:
            - outdoor_temp: Temperature in Fahrenheit
            - outdoor_humidity: Relative humidity in %
            - outdoor_conditions: Weather conditions description
            - data_source: Source of the data

    Raises:
        WeatherError: If API call fails or invalid zip code
    """
    if not zip_code or not isinstance(zip_code, str):
        raise WeatherError("Invalid zip code provided")

    if api_key is None:
        api_key = get_weather_api_key()

    # If no API key provided, return mock data for testing
    if not api_key:
        util.log_msg(
            f"No weather API key provided, returning mock data for zip {zip_code}",
            mode=util.BOTH_LOG,
            func_name=1,
        )
        return {
            "zip_code": zip_code,
            "outdoor_temp": -999.0,
            "outdoor_humidity": -999.0,
            "outdoor_conditions": "Missing API Key",
            "data_source": "mock",
        }

    try:
        # OpenWeatherMap API endpoint
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "zip": f"{zip_code},US",
            "appid": api_key,
            "units": "imperial",  # Fahrenheit
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        weather_data = response.json()

        return {
            "zip_code": zip_code,
            "outdoor_temp": float(weather_data["main"]["temp"]),
            "outdoor_humidity": float(weather_data["main"]["humidity"]),
            "outdoor_conditions": weather_data["weather"][0]["description"].title(),
            "data_source": "OpenWeatherMap",
        }

    except requests.exceptions.RequestException as e:
        util.log_msg(
            f"Weather API request failed: {e}", mode=util.BOTH_LOG, func_name=1
        )
        raise WeatherError(f"Failed to fetch weather data: {e}")
    except (KeyError, ValueError) as e:
        util.log_msg(
            f"Weather API response parsing failed: {e}", mode=util.BOTH_LOG, func_name=1
        )
        raise WeatherError(f"Invalid weather data format: {e}")
    except Exception as e:
        util.log_msg(f"Weather API general error: {e}", mode=util.BOTH_LOG, func_name=1)
        raise WeatherError(f"Failed to fetch weather data: {e}")


def get_weather_api_key() -> Optional[str]:
    """
    Get the OpenWeatherMap API key from the configured environment sources.

    Returns:
        str or None: API key if configured, otherwise None.
    """
    result = env.get_env_variable("OPENWEATHER_API_KEY", default="")
    return result["value"] or None


def format_weather_display(weather_data: Dict[str, float | str]) -> str:
    """
    Format weather data for display in thermostat reporting.

    Args:
        weather_data (dict): Weather data dictionary from get_outdoor_weather()

    Returns:
        str: Formatted weather string for display
    """
    if not weather_data:
        return "outdoor: N/A"

    zip_code = weather_data.get("zip_code", "N/A")
    temp = weather_data.get("outdoor_temp", "N/A")
    humidity = weather_data.get("outdoor_humidity", "N/A")
    conditions = weather_data.get("outdoor_conditions", "N/A")

    return f"outdoor({zip_code}): {temp:.1f}°F, {humidity:.0f}%RH ({conditions})"
