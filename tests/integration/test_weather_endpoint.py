"""Integration tests for weather tool endpoint."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.models.weather import (
    CurrentWeather,
    ForecastDay,
    WeatherCondition,
    WeatherResponse,
)


@pytest.fixture
def mock_weather_response():
    """Create mock weather response for testing."""
    from datetime import datetime, timezone

    return WeatherResponse(
        current=CurrentWeather(
            location="Boston",
            temperature_f=72.5,
            temperature_c=22.5,
            feels_like_f=75.0,
            feels_like_c=23.9,
            humidity=65,
            conditions=WeatherCondition(description="partly cloudy", icon="02d"),
            wind_speed_mph=10.5,
            timestamp=datetime.now(timezone.utc),
        ),
        cached=False,
    )


@pytest.fixture
def mock_weather_error_response():
    """Create mock weather error response."""
    return WeatherResponse(
        error="I couldn't find weather data for 'Atlantis'. Please check the spelling or try a nearby city."
    )


@pytest.fixture
def mock_settings():
    """Mock settings for tests."""
    settings = MagicMock()
    settings.openai_api_key = "sk-test-key"
    settings.openai_model = "gpt-4"
    settings.max_tokens = 2000
    settings.timeout_seconds = 30
    settings.log_level = "INFO"
    settings.allowed_models_list = ["gpt-4", "gpt-3.5-turbo"]
    settings.openweathermap_api_key = "test-weather-key"
    settings.weather_api_base_url = "https://api.openweathermap.org/data/2.5"
    settings.weather_api_timeout = 5
    settings.weather_cache_ttl_current = 600
    settings.weather_cache_ttl_forecast = 1800

    with (
        patch("src.services.chat_service.get_settings", return_value=settings),
        patch("src.services.weather_service.get_settings", return_value=settings),
        patch("src.api.routes.get_settings", return_value=settings),
        patch("src.main.get_settings", return_value=settings),
        patch("src.config.get_settings", return_value=settings),
    ):
        yield settings


@pytest.fixture
def mock_request_settings():
    """Mock settings for request validation."""
    with patch("src.models.request.get_settings") as mock:
        settings = MagicMock()
        settings.openai_model = "gpt-4"
        settings.max_tokens = 2000
        settings.allowed_models_list = ["gpt-4", "gpt-3.5-turbo"]
        mock.return_value = settings
        yield settings


class TestWeatherToolRegistration:
    """Tests for weather tool registration with agent."""

    def test_weather_tool_is_registered(self):
        """Test that get_weather tool is properly defined."""
        from agents import FunctionTool

        from src.tools.get_weather import get_weather_tool

        assert isinstance(get_weather_tool, FunctionTool)
        assert get_weather_tool.name == "get_weather"

    def test_weather_tool_in_chat_service(self, mock_settings, mock_request_settings):
        """Test that weather specialist is available in chat service."""
        with (
            patch("src.services.redis_service.get_redis", return_value=None),
            patch("src.tools.query_memory.MemoryService"),
        ):
            from src.services.chat_service import ChatService

            service = ChatService()
            service._database_available = True
            service._conversation_service = MagicMock()

            agent = service.create_agent()
            tool_names = [t.name for t in agent.tools]
            assert "ask_weather_agent" in tool_names, "ask_weather_agent should be registered"


class TestWeatherEndpoint:
    """Tests for weather queries via chat endpoint."""

    @pytest.mark.asyncio
    async def test_weather_query_returns_data(
        self, mock_settings, mock_request_settings, mock_weather_response
    ):
        """Test that weather query returns formatted weather data (T051)."""
        # This tests the weather tool's formatting logic with a mock response
        from src.tools.get_weather import _format_weather_response

        result = _format_weather_response(mock_weather_response)

        # Verify response contains expected weather information
        assert "Boston" in result
        assert "72.5°F" in result
        assert "22.5°C" in result
        assert "partly cloudy" in result
        assert "65%" in result

    @pytest.mark.asyncio
    async def test_invalid_location_returns_friendly_error(
        self, mock_settings, mock_request_settings, mock_weather_error_response
    ):
        """Test that invalid location returns user-friendly error (T065)."""
        from src.tools.get_weather import _format_weather_response

        result = _format_weather_response(mock_weather_error_response)

        # Verify user-friendly error message
        assert "couldn't find" in result.lower()
        assert "Atlantis" in result

    @pytest.mark.asyncio
    async def test_weather_service_invalid_location(
        self, mock_settings, mock_request_settings
    ):
        """Test that WeatherService returns error for invalid location."""
        with (
            patch("src.services.redis_service.get_redis", return_value=None),
            patch("httpx.AsyncClient") as mock_client_class,
        ):
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_client.get.return_value = mock_response
            mock_client.is_closed = False
            mock_client_class.return_value = mock_client

            from src.services.weather_service import WeatherService

            service = WeatherService()
            service._client = mock_client

            result = await service.get_weather("Atlantis")

            assert result.success is False
            assert result.error is not None
            assert "couldn't find" in result.error.lower()

    @pytest.mark.asyncio
    async def test_weather_with_coordinates(
        self, mock_settings, mock_request_settings
    ):
        """Test that coordinate-based queries work correctly."""
        mock_api_response = {
            "name": "New York",
            "main": {
                "temp": 295.15,
                "feels_like": 296.15,
                "humidity": 55,
            },
            "weather": [{"description": "clear sky", "icon": "01d"}],
            "wind": {"speed": 3.5},
            "dt": 1706800000,
        }

        with (
            patch("src.services.redis_service.get_redis", return_value=None),
            patch("httpx.AsyncClient") as mock_client_class,
        ):
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_api_response
            mock_response.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client.is_closed = False
            mock_client_class.return_value = mock_client

            from src.services.weather_service import WeatherService

            service = WeatherService()
            service._client = mock_client

            result = await service.get_weather("40.7128, -74.0060")

            assert result.success is True
            assert result.current is not None
            # Verify coordinates were used (lat/lon params)
            call_args = mock_client.get.call_args
            params = call_args[1]["params"]
            assert "lat" in params
            assert "lon" in params

    @pytest.mark.asyncio
    async def test_empty_location_returns_error(
        self, mock_settings, mock_request_settings
    ):
        """Test that empty location returns appropriate error."""
        from src.tools.get_weather import _format_weather_response

        from src.services.weather_service import WeatherService

        with patch("src.services.redis_service.get_redis", return_value=None):
            service = WeatherService()
            result = await service.get_weather("")

            # Format the error response
            formatted = _format_weather_response(result)

            assert result.success is False
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_forecast_query_returns_multi_day_data(
        self, mock_settings, mock_request_settings
    ):
        """Test that forecast query returns multi-day forecast data (T074)."""
        from datetime import date

        from src.models.weather import ForecastDay, WeatherCondition, WeatherResponse
        from src.tools.get_weather import _format_weather_response

        # Create mock response with forecast
        mock_response = WeatherResponse(
            forecast=[
                ForecastDay(
                    date=date(2024, 2, 1),
                    high_f=75.0,
                    high_c=23.9,
                    low_f=55.0,
                    low_c=12.8,
                    conditions=WeatherCondition(description="sunny", icon="01d"),
                    precipitation_chance=10,
                ),
                ForecastDay(
                    date=date(2024, 2, 2),
                    high_f=72.0,
                    high_c=22.2,
                    low_f=52.0,
                    low_c=11.1,
                    conditions=WeatherCondition(description="partly cloudy", icon="02d"),
                    precipitation_chance=25,
                ),
                ForecastDay(
                    date=date(2024, 2, 3),
                    high_f=68.0,
                    high_c=20.0,
                    low_f=48.0,
                    low_c=8.9,
                    conditions=WeatherCondition(description="rain", icon="10d"),
                    precipitation_chance=80,
                ),
            ],
            cached=False,
        )

        result = _format_weather_response(mock_response)

        # Verify multi-day forecast is included
        assert "Forecast:" in result
        assert "75.0°F" in result
        assert "sunny" in result
        assert "partly cloudy" in result
        assert "rain" in result
        assert "80%" in result  # precipitation chance

    @pytest.mark.asyncio
    async def test_forecast_with_current_weather(
        self, mock_settings, mock_request_settings
    ):
        """Test combined current weather and forecast response."""
        from datetime import date, datetime, timezone

        from src.models.weather import (
            CurrentWeather,
            ForecastDay,
            WeatherCondition,
            WeatherResponse,
        )
        from src.tools.get_weather import _format_weather_response

        mock_response = WeatherResponse(
            current=CurrentWeather(
                location="Chicago",
                temperature_f=65.0,
                temperature_c=18.3,
                feels_like_f=63.0,
                feels_like_c=17.2,
                humidity=55,
                conditions=WeatherCondition(description="overcast", icon="04d"),
                wind_speed_mph=12.0,
                timestamp=datetime.now(timezone.utc),
            ),
            forecast=[
                ForecastDay(
                    date=date(2024, 2, 1),
                    high_f=70.0,
                    high_c=21.1,
                    low_f=50.0,
                    low_c=10.0,
                    conditions=WeatherCondition(description="cloudy", icon="03d"),
                    precipitation_chance=40,
                ),
            ],
            cached=False,
        )

        result = _format_weather_response(mock_response)

        # Verify both current and forecast are included
        assert "Current weather in Chicago" in result
        assert "65.0°F" in result
        assert "Forecast:" in result
        assert "70.0°F" in result
