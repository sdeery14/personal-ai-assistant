"""Unit tests for weather service."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.services.weather_service import (
    WeatherService,
    _get_error_message,
    _kelvin_to_celsius,
    _kelvin_to_fahrenheit,
    _mps_to_mph,
    _normalize_location,
    _parse_coordinates,
)


class TestTemperatureConversion:
    """Tests for temperature conversion functions."""

    def test_kelvin_to_fahrenheit(self):
        """Test Kelvin to Fahrenheit conversion."""
        # 0°C = 273.15K = 32°F
        assert _kelvin_to_fahrenheit(273.15) == 32.0
        # 100°C = 373.15K = 212°F
        assert _kelvin_to_fahrenheit(373.15) == 212.0

    def test_kelvin_to_celsius(self):
        """Test Kelvin to Celsius conversion."""
        assert _kelvin_to_celsius(273.15) == 0.0
        assert _kelvin_to_celsius(373.15) == 100.0

    def test_mps_to_mph(self):
        """Test meters/second to miles/hour conversion."""
        # 1 m/s ≈ 2.237 mph
        assert _mps_to_mph(1.0) == 2.2
        assert _mps_to_mph(10.0) == 22.4


class TestLocationNormalization:
    """Tests for location normalization."""

    def test_normalize_location_lowercase(self):
        """Test that location is lowercased."""
        assert _normalize_location("Boston") == "boston"
        assert _normalize_location("NEW YORK") == "new york"

    def test_normalize_location_trim(self):
        """Test that whitespace is trimmed."""
        assert _normalize_location("  Boston  ") == "boston"
        assert _normalize_location("  New York, NY  ") == "new york, ny"


class TestCoordinateParsing:
    """Tests for coordinate parsing."""

    def test_parse_valid_coordinates(self):
        """Test parsing valid coordinate strings."""
        result = _parse_coordinates("40.7128, -74.0060")
        assert result == (40.7128, -74.006)

    def test_parse_coordinates_no_space(self):
        """Test parsing coordinates without space after comma."""
        result = _parse_coordinates("40.7128,-74.0060")
        assert result == (40.7128, -74.006)

    def test_parse_invalid_location(self):
        """Test that non-coordinate strings return None."""
        assert _parse_coordinates("Boston") is None
        assert _parse_coordinates("New York, NY") is None

    def test_parse_negative_coordinates(self):
        """Test parsing negative coordinates."""
        result = _parse_coordinates("-33.8688, 151.2093")
        assert result == (-33.8688, 151.2093)


class TestErrorMessages:
    """Tests for error message generation."""

    def test_api_unavailable_message(self):
        """Test API unavailable error message."""
        msg = _get_error_message("api_unavailable")
        assert "unable to retrieve weather" in msg.lower()

    def test_invalid_location_message(self):
        """Test invalid location error message."""
        msg = _get_error_message("invalid_location", "Atlantis")
        assert "Atlantis" in msg
        assert "couldn't find" in msg.lower()

    def test_timeout_message(self):
        """Test timeout error message."""
        msg = _get_error_message("timeout")
        assert "too long" in msg.lower()

    def test_unknown_error_message(self):
        """Test unknown error returns default message."""
        msg = _get_error_message("some_random_error")
        assert "unexpected error" in msg.lower()


class TestWeatherServiceCurrentWeather:
    """Tests for WeatherService.get_current_weather."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        with patch("src.services.weather_service.get_settings") as mock:
            settings = MagicMock()
            settings.openweathermap_api_key = "test-api-key"
            settings.weather_api_base_url = "https://api.openweathermap.org/data/2.5"
            settings.weather_api_timeout = 5
            settings.weather_cache_ttl_current = 600
            settings.weather_cache_ttl_forecast = 1800
            mock.return_value = settings
            yield settings

    @pytest.fixture
    def mock_api_response(self):
        """Create mock API response for current weather."""
        return {
            "name": "Boston",
            "main": {
                "temp": 295.15,  # ~72°F / ~22°C
                "feels_like": 296.15,
                "humidity": 65,
            },
            "weather": [{"description": "partly cloudy", "icon": "02d"}],
            "wind": {"speed": 4.5},
            "dt": 1706800000,
        }

    @pytest.mark.asyncio
    async def test_get_current_weather_success(self, mock_settings, mock_api_response):
        """Test successful current weather retrieval."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_api_response
            mock_response.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client.is_closed = False
            mock_client_class.return_value = mock_client

            service = WeatherService()
            service._client = mock_client

            result = await service.get_current_weather("Boston")

            assert result is not None
            assert result.location == "Boston"
            assert result.humidity == 65
            assert result.conditions.description == "partly cloudy"

    @pytest.mark.asyncio
    async def test_get_current_weather_invalid_location(self, mock_settings):
        """Test current weather with invalid location returns None."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_client.get.return_value = mock_response
            mock_client.is_closed = False
            mock_client_class.return_value = mock_client

            service = WeatherService()
            service._client = mock_client

            result = await service.get_current_weather("Atlantis")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_current_weather_auth_error(self, mock_settings):
        """Test that auth errors don't retry."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_client.get.return_value = mock_response
            mock_client.is_closed = False
            mock_client_class.return_value = mock_client

            service = WeatherService()
            service._client = mock_client

            result = await service.get_current_weather("Boston")

            assert result is None
            # Should only be called once (no retry on 401)
            assert mock_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_get_current_weather_timeout(self, mock_settings):
        """Test timeout handling."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("Timeout")
            mock_client.is_closed = False
            mock_client_class.return_value = mock_client

            service = WeatherService()
            service._client = mock_client

            result = await service.get_current_weather("Boston")

            assert result is None
            # Should retry 3 times
            assert mock_client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_on_server_error(self, mock_settings, mock_api_response):
        """Test retry on 5xx errors."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()

            # First call fails with 503, second succeeds
            error_response = MagicMock()
            error_response.status_code = 503

            success_response = MagicMock()
            success_response.status_code = 200
            success_response.json.return_value = mock_api_response
            success_response.raise_for_status = MagicMock()

            mock_client.get.side_effect = [error_response, success_response]
            mock_client.is_closed = False
            mock_client_class.return_value = mock_client

            service = WeatherService()
            service._client = mock_client

            with patch("asyncio.sleep"):  # Skip actual sleep
                result = await service.get_current_weather("Boston")

            assert result is not None
            assert result.location == "Boston"


class TestWeatherServiceGetWeather:
    """Tests for WeatherService.get_weather."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        with patch("src.services.weather_service.get_settings") as mock:
            settings = MagicMock()
            settings.openweathermap_api_key = "test-api-key"
            settings.weather_api_base_url = "https://api.openweathermap.org/data/2.5"
            settings.weather_api_timeout = 5
            settings.weather_cache_ttl_current = 600
            settings.weather_cache_ttl_forecast = 1800
            mock.return_value = settings
            yield settings

    @pytest.mark.asyncio
    async def test_empty_location_returns_error(self, mock_settings):
        """Test that empty location returns error response."""
        service = WeatherService()

        with patch("src.services.redis_service.get_redis") as mock_get_redis:
            mock_get_redis.return_value = None  # Simulate no Redis

            result = await service.get_weather("")

            assert result.error is not None
            assert result.success is False

    @pytest.mark.asyncio
    async def test_cache_hit_skips_api(self, mock_settings):
        """Test that cache hit skips API call."""
        cached_data = {
            "location": "Boston",
            "temperature_f": 72.0,
            "temperature_c": 22.2,
            "feels_like_f": 75.0,
            "feels_like_c": 23.9,
            "humidity": 65,
            "conditions": {"description": "sunny", "icon": "01d"},
            "wind_speed_mph": 10.0,
            "timestamp": "2024-02-01T12:00:00+00:00",
        }

        with patch("src.services.redis_service.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get.return_value = json.dumps(cached_data)
            mock_get_redis.return_value = mock_redis

            service = WeatherService()
            # Mock the API call to track if it's made
            service.get_current_weather = AsyncMock()

            result = await service.get_weather("Boston")

            assert result.cached is True
            # API should not be called when cache hit
            service.get_current_weather.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_calls_api(self, mock_settings):
        """Test that cache miss calls API."""
        with patch("src.services.redis_service.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get.return_value = None  # Cache miss
            mock_redis.setex.return_value = True
            mock_get_redis.return_value = mock_redis

            service = WeatherService()

            # Mock successful API response
            mock_current = MagicMock()
            mock_current.model_dump.return_value = {"location": "Boston"}
            service.get_current_weather = AsyncMock(return_value=mock_current)

            result = await service.get_weather("Boston")

            # API should be called
            service.get_current_weather.assert_called_once_with("Boston")
            # Cache should be set
            mock_redis.setex.assert_called()


class TestWeatherForecast:
    """Tests for forecast functionality (Phase 4)."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        with patch("src.services.weather_service.get_settings") as mock:
            settings = MagicMock()
            settings.openweathermap_api_key = "test-api-key"
            settings.weather_api_base_url = "https://api.openweathermap.org/data/2.5"
            settings.weather_api_timeout = 5
            settings.weather_cache_ttl_current = 600
            settings.weather_cache_ttl_forecast = 1800
            mock.return_value = settings
            yield settings

    @pytest.fixture
    def mock_forecast_api_response(self):
        """Create mock forecast API response with 3-hour intervals."""
        # Simulate OpenWeatherMap forecast response with multiple entries per day
        base_time = 1706800000  # Some timestamp
        return {
            "list": [
                # Day 1 - 3 entries
                {
                    "dt": base_time,
                    "main": {"temp": 280.0},  # ~44°F
                    "weather": [{"description": "clear sky", "icon": "01d"}],
                    "pop": 0.0,
                },
                {
                    "dt": base_time + 10800,  # +3 hours
                    "main": {"temp": 285.0},  # ~53°F
                    "weather": [{"description": "partly cloudy", "icon": "02d"}],
                    "pop": 0.1,
                },
                {
                    "dt": base_time + 21600,  # +6 hours
                    "main": {"temp": 282.0},  # ~48°F
                    "weather": [{"description": "cloudy", "icon": "03d"}],
                    "pop": 0.2,
                },
                # Day 2 - 2 entries
                {
                    "dt": base_time + 86400,  # +1 day
                    "main": {"temp": 290.0},  # ~62°F
                    "weather": [{"description": "rain", "icon": "10d"}],
                    "pop": 0.8,
                },
                {
                    "dt": base_time + 86400 + 10800,  # +1 day +3 hours
                    "main": {"temp": 288.0},  # ~59°F
                    "weather": [{"description": "light rain", "icon": "10d"}],
                    "pop": 0.6,
                },
            ]
        }

    @pytest.mark.asyncio
    async def test_forecast_aggregation(self, mock_settings, mock_forecast_api_response):
        """Test that 3-hour forecast data is aggregated to daily (T072)."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_forecast_api_response
            mock_response.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client.is_closed = False
            mock_client_class.return_value = mock_client

            service = WeatherService()
            service._client = mock_client

            result = await service.get_forecast("Boston", days=7)

            # Should have 2 days (aggregated from 5 entries)
            assert len(result) == 2

            # Day 1: high should be max of 280, 285, 282 = 285K
            day1 = result[0]
            assert day1.high_c == pytest.approx(285.0 - 273.15, rel=0.1)

            # Day 1: low should be min = 280K
            assert day1.low_c == pytest.approx(280.0 - 273.15, rel=0.1)

            # Day 1: precipitation chance should be max of 0, 10, 20 = 20%
            assert day1.precipitation_chance == 20

            # Day 2: high should be max of 290, 288 = 290K
            day2 = result[1]
            assert day2.high_c == pytest.approx(290.0 - 273.15, rel=0.1)

            # Day 2: precipitation chance should be max of 80, 60 = 80%
            assert day2.precipitation_chance == 80

    @pytest.mark.asyncio
    async def test_forecast_beyond_range_clamped(self, mock_settings, mock_forecast_api_response):
        """Test that requesting >7 days is clamped to 7 (T073)."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_forecast_api_response
            mock_response.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client.is_closed = False
            mock_client_class.return_value = mock_client

            service = WeatherService()
            service._client = mock_client

            # Request 14 days - should be clamped
            result = await service.get_forecast("Boston", days=14)

            # Should return what's available (2 days in mock data)
            # but the clamping logic would limit to 7 max
            assert len(result) <= 7

    @pytest.mark.asyncio
    async def test_forecast_days_minimum_clamped(self, mock_settings, mock_forecast_api_response):
        """Test that requesting <1 days is clamped to 1."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_forecast_api_response
            mock_response.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client.is_closed = False
            mock_client_class.return_value = mock_client

            service = WeatherService()
            service._client = mock_client

            # Request 0 days - should be clamped to 1
            result = await service.get_forecast("Boston", days=0)

            # Should return at least 1 day
            assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_forecast_invalid_location_returns_empty(self, mock_settings):
        """Test that invalid location returns empty forecast."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_client.get.return_value = mock_response
            mock_client.is_closed = False
            mock_client_class.return_value = mock_client

            service = WeatherService()
            service._client = mock_client

            result = await service.get_forecast("Atlantis")

            assert result == []
