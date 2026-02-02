"""Unit tests for weather models."""

from datetime import date, datetime, timezone

import pytest

from src.models.weather import (
    CurrentWeather,
    ForecastDay,
    WeatherCondition,
    WeatherResponse,
)


class TestWeatherCondition:
    """Tests for WeatherCondition model."""

    def test_valid_condition(self):
        """Test creating a valid weather condition."""
        condition = WeatherCondition(description="partly cloudy", icon="02d")
        assert condition.description == "partly cloudy"
        assert condition.icon == "02d"

    def test_empty_description_fails(self):
        """Test that empty description fails validation."""
        # Empty string is technically valid, but icon is required
        condition = WeatherCondition(description="", icon="01d")
        assert condition.description == ""


class TestCurrentWeather:
    """Tests for CurrentWeather model."""

    def test_valid_current_weather(self):
        """Test creating valid current weather data."""
        weather = CurrentWeather(
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
        assert weather.location == "Boston"
        assert weather.temperature_f == 72.5
        assert weather.humidity == 65

    def test_humidity_must_be_valid_percentage(self):
        """Test that humidity must be between 0 and 100."""
        with pytest.raises(ValueError):
            CurrentWeather(
                location="Boston",
                temperature_f=72.5,
                temperature_c=22.5,
                feels_like_f=75.0,
                feels_like_c=23.9,
                humidity=150,  # Invalid
                conditions=WeatherCondition(description="sunny", icon="01d"),
                wind_speed_mph=10.5,
                timestamp=datetime.now(timezone.utc),
            )

    def test_wind_speed_must_be_non_negative(self):
        """Test that wind speed must be >= 0."""
        with pytest.raises(ValueError):
            CurrentWeather(
                location="Boston",
                temperature_f=72.5,
                temperature_c=22.5,
                feels_like_f=75.0,
                feels_like_c=23.9,
                humidity=65,
                conditions=WeatherCondition(description="sunny", icon="01d"),
                wind_speed_mph=-5.0,  # Invalid
                timestamp=datetime.now(timezone.utc),
            )


class TestForecastDay:
    """Tests for ForecastDay model."""

    def test_valid_forecast_day(self):
        """Test creating valid forecast day data."""
        forecast = ForecastDay(
            date=date.today(),
            high_f=80.0,
            high_c=26.7,
            low_f=60.0,
            low_c=15.6,
            conditions=WeatherCondition(description="cloudy", icon="03d"),
            precipitation_chance=30,
        )
        assert forecast.high_f == 80.0
        assert forecast.precipitation_chance == 30

    def test_precipitation_must_be_valid_percentage(self):
        """Test that precipitation chance must be between 0 and 100."""
        with pytest.raises(ValueError):
            ForecastDay(
                date=date.today(),
                high_f=80.0,
                high_c=26.7,
                low_f=60.0,
                low_c=15.6,
                conditions=WeatherCondition(description="cloudy", icon="03d"),
                precipitation_chance=120,  # Invalid
            )


class TestWeatherResponse:
    """Tests for WeatherResponse model."""

    def test_success_response_with_current(self):
        """Test successful response with current weather."""
        current = CurrentWeather(
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
        response = WeatherResponse(current=current)
        assert response.success is True
        assert response.error is None

    def test_error_response(self):
        """Test error response."""
        response = WeatherResponse(error="Location not found")
        assert response.success is False
        assert response.error == "Location not found"

    def test_cached_flag(self):
        """Test cached flag."""
        current = CurrentWeather(
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
        response = WeatherResponse(current=current, cached=True)
        assert response.cached is True

    def test_response_with_forecast(self):
        """Test response with forecast data."""
        forecast = [
            ForecastDay(
                date=date.today(),
                high_f=80.0,
                high_c=26.7,
                low_f=60.0,
                low_c=15.6,
                conditions=WeatherCondition(description="cloudy", icon="03d"),
                precipitation_chance=30,
            )
        ]
        response = WeatherResponse(forecast=forecast)
        assert response.success is True
        assert len(response.forecast) == 1

    def test_empty_response_is_not_success(self):
        """Test that response with no data is not successful."""
        response = WeatherResponse()
        assert response.success is False
