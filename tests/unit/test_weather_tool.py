"""Unit tests for weather tool.

Note: The @function_tool decorator from agents SDK wraps the function
in a FunctionTool object. We test the formatting helpers directly and
test the tool integration via the underlying WeatherService.
"""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.weather import (
    CurrentWeather,
    ForecastDay,
    WeatherCondition,
    WeatherResponse,
)
from src.tools.get_weather import (
    _format_current_weather,
    _format_forecast,
    _format_weather_response,
)
from src.services.weather_service import WeatherService


class TestFormatCurrentWeather:
    """Tests for current weather formatting."""

    def test_format_current_weather(self):
        """Test formatting current weather data."""
        response = WeatherResponse(
            current=CurrentWeather(
                location="Boston",
                temperature_f=72.5,
                temperature_c=22.5,
                feels_like_f=75.0,
                feels_like_c=23.9,
                humidity=65,
                conditions=WeatherCondition(description="sunny", icon="01d"),
                wind_speed_mph=10.5,
                timestamp=datetime.now(timezone.utc),
            )
        )

        result = _format_current_weather(response)

        assert "Boston" in result
        assert "72.5°F" in result
        assert "22.5°C" in result
        assert "sunny" in result
        assert "65%" in result

    def test_format_current_weather_no_data(self):
        """Test formatting when no current weather data."""
        response = WeatherResponse()

        result = _format_current_weather(response)

        assert result == ""


class TestFormatForecast:
    """Tests for forecast formatting."""

    def test_format_forecast(self):
        """Test formatting forecast data."""
        response = WeatherResponse(
            forecast=[
                ForecastDay(
                    date=date(2024, 2, 1),
                    high_f=80.0,
                    high_c=26.7,
                    low_f=60.0,
                    low_c=15.6,
                    conditions=WeatherCondition(description="cloudy", icon="03d"),
                    precipitation_chance=30,
                ),
                ForecastDay(
                    date=date(2024, 2, 2),
                    high_f=75.0,
                    high_c=23.9,
                    low_f=55.0,
                    low_c=12.8,
                    conditions=WeatherCondition(description="rainy", icon="10d"),
                    precipitation_chance=80,
                ),
            ]
        )

        result = _format_forecast(response)

        assert "Forecast:" in result
        assert "80.0°F" in result
        assert "26.7°C" in result
        assert "cloudy" in result
        assert "30%" in result
        assert "rainy" in result
        assert "80%" in result

    def test_format_forecast_no_data(self):
        """Test formatting when no forecast data."""
        response = WeatherResponse()

        result = _format_forecast(response)

        assert result == ""


class TestFormatWeatherResponse:
    """Tests for complete weather response formatting."""

    def test_format_success_response(self):
        """Test formatting successful response."""
        response = WeatherResponse(
            current=CurrentWeather(
                location="Boston",
                temperature_f=72.5,
                temperature_c=22.5,
                feels_like_f=75.0,
                feels_like_c=23.9,
                humidity=65,
                conditions=WeatherCondition(description="sunny", icon="01d"),
                wind_speed_mph=10.5,
                timestamp=datetime.now(timezone.utc),
            )
        )

        result = _format_weather_response(response)

        assert "Boston" in result
        assert "72.5°F" in result

    def test_format_error_response(self):
        """Test formatting error response."""
        response = WeatherResponse(error="Location not found")

        result = _format_weather_response(response)

        assert result == "Location not found"

    def test_format_cached_response(self):
        """Test that cached indicator is shown."""
        response = WeatherResponse(
            current=CurrentWeather(
                location="Boston",
                temperature_f=72.5,
                temperature_c=22.5,
                feels_like_f=75.0,
                feels_like_c=23.9,
                humidity=65,
                conditions=WeatherCondition(description="sunny", icon="01d"),
                wind_speed_mph=10.5,
                timestamp=datetime.now(timezone.utc),
            ),
            cached=True,
        )

        result = _format_weather_response(response)

        assert "cache" in result.lower()

    def test_format_empty_response(self):
        """Test formatting empty response."""
        response = WeatherResponse()

        result = _format_weather_response(response)

        assert "No weather data available" in result


class TestGetWeatherTool:
    """Tests for get_weather tool integration.

    Since @function_tool wraps the function, we test the service and
    formatting logic separately, and verify tool registration.
    """

    def test_tool_is_registered(self):
        """Test that get_weather tool is properly defined."""
        from src.tools.get_weather import get_weather_tool
        from agents import FunctionTool

        assert isinstance(get_weather_tool, FunctionTool)
        assert get_weather_tool.name == "get_weather"

    def test_format_response_success(self):
        """Test formatting a successful weather response."""
        response = WeatherResponse(
            current=CurrentWeather(
                location="Boston",
                temperature_f=72.5,
                temperature_c=22.5,
                feels_like_f=75.0,
                feels_like_c=23.9,
                humidity=65,
                conditions=WeatherCondition(description="sunny", icon="01d"),
                wind_speed_mph=10.5,
                timestamp=datetime.now(timezone.utc),
            )
        )

        result = _format_weather_response(response)

        assert "Boston" in result
        assert "72.5°F" in result
        assert "22.5°C" in result

    def test_format_response_error(self):
        """Test formatting an error response."""
        response = WeatherResponse(
            error="I couldn't find weather data for 'Atlantis'."
        )

        result = _format_weather_response(response)

        assert "couldn't find" in result.lower()

    @pytest.mark.asyncio
    async def test_weather_service_handles_empty_location(self):
        """Test that WeatherService returns error for empty location."""
        with patch("src.services.weather_service.get_settings") as mock_settings:
            settings = MagicMock()
            settings.openweathermap_api_key = "test-key"
            settings.weather_api_base_url = "https://api.openweathermap.org"
            settings.weather_api_timeout = 5
            settings.weather_cache_ttl_current = 600
            settings.weather_cache_ttl_forecast = 1800
            mock_settings.return_value = settings

            with patch("src.services.redis_service.get_redis") as mock_get_redis:
                mock_get_redis.return_value = None

                service = WeatherService()
                result = await service.get_weather("")

                assert result.error is not None
                assert result.success is False

    @pytest.mark.asyncio
    async def test_weather_service_handles_whitespace_location(self):
        """Test that WeatherService returns error for whitespace-only location."""
        with patch("src.services.weather_service.get_settings") as mock_settings:
            settings = MagicMock()
            settings.openweathermap_api_key = "test-key"
            settings.weather_api_base_url = "https://api.openweathermap.org"
            settings.weather_api_timeout = 5
            settings.weather_cache_ttl_current = 600
            settings.weather_cache_ttl_forecast = 1800
            mock_settings.return_value = settings

            with patch("src.services.redis_service.get_redis") as mock_get_redis:
                mock_get_redis.return_value = None

                service = WeatherService()
                result = await service.get_weather("   ")

                assert result.error is not None
                assert result.success is False
