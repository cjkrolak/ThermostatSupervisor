"""
Weather API module for outdoor temperature and humidity data.

This module provides functions to fetch outdoor weather data using zip codes.
"""

# built-in imports
import os
from typing import Dict, Optional, Union

# third-party imports
import requests

# local imports
from src import utilities as util


class WeatherError(Exception):
    """Exception raised for weather API errors."""

    pass


def get_outdoor_weather(
    zip_code: str, api_key: Optional[str] = None
) -> Dict[str, Union[float, str]]:
    """
    Get outdoor temperature and humidity data for a given zip code.

    This function uses the OpenWeatherMap API to fetch current weather data.
    If no API key is provided, it returns mock data for testing.

    Args:
        zip_code (str): The zip code for which to fetch weather data
        api_key (str, optional): OpenWeatherMap API key

    Returns:
        Dict[str, Union[float, str]]: Dictionary containing:
            - outdoor_temp: Temperature in Fahrenheit
            - outdoor_humidity: Relative humidity in %
            - outdoor_conditions: Weather conditions description
            - data_source: Source of the data

    Raises:
        WeatherError: If API call fails or invalid zip code
    """
    if not zip_code or not isinstance(zip_code, str):
        raise WeatherError("Invalid zip code provided")

    # If no API key provided, return mock data for testing
    if not api_key:
        util.log_msg(
            f"No weather API key provided, returning mock data for zip {zip_code}",
            mode=util.BOTH_LOG,
            func_name=1,
        )
        return {
            "outdoor_temp": -999.0,
            "outdoor_humidity": -999.0,
            "outdoor_conditions": "Missing API Key",
            "data_source": "mock",
        }

    try:
        # OpenWeatherMap API endpoint
        url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            "zip": f"{zip_code},US",
            "appid": api_key,
            "units": "imperial",  # Fahrenheit
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        weather_data = response.json()

        return {
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
    Get weather API key from environment variables.

    Returns:
        str or None: API key if found in environment variables
    """
    return os.environ.get("WEATHER_API_KEY")


def format_weather_display(weather_data: Dict[str, Union[float, str]]) -> str:
    """
    Format weather data for display in thermostat reporting.

    Args:
        weather_data (dict): Weather data dictionary from get_outdoor_weather()

    Returns:
        str: Formatted weather string for display
    """
    if not weather_data:
        return "outdoor: N/A"

    temp = weather_data.get("outdoor_temp", "N/A")
    humidity = weather_data.get("outdoor_humidity", "N/A")
    conditions = weather_data.get("outdoor_conditions", "N/A")

    return f"outdoor: {temp:.1f}°F, {humidity:.0f}%RH ({conditions})"
