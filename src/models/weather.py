"""Weather data models for Feature 005."""

from datetime import date as date_type
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WeatherCondition(BaseModel):
    """Weather condition description."""

    description: str = Field(..., description="Weather condition (e.g., 'partly cloudy')")
    icon: str = Field(..., description="Weather icon code from provider")


class CurrentWeather(BaseModel):
    """Current weather conditions for a location."""

    location: str = Field(..., description="Location name")
    temperature_f: float = Field(..., description="Temperature in Fahrenheit")
    temperature_c: float = Field(..., description="Temperature in Celsius")
    feels_like_f: float = Field(..., description="Feels like temperature in Fahrenheit")
    feels_like_c: float = Field(..., description="Feels like temperature in Celsius")
    humidity: int = Field(..., ge=0, le=100, description="Humidity percentage")
    conditions: WeatherCondition = Field(..., description="Weather conditions")
    wind_speed_mph: float = Field(..., ge=0, description="Wind speed in mph")
    timestamp: datetime = Field(..., description="Data timestamp")


class ForecastDay(BaseModel):
    """Weather forecast for a single day."""

    date: date_type = Field(..., description="Forecast date")
    high_f: float = Field(..., description="High temperature in Fahrenheit")
    high_c: float = Field(..., description="High temperature in Celsius")
    low_f: float = Field(..., description="Low temperature in Fahrenheit")
    low_c: float = Field(..., description="Low temperature in Celsius")
    conditions: WeatherCondition = Field(..., description="Expected conditions")
    precipitation_chance: int = Field(
        ..., ge=0, le=100, description="Precipitation probability percentage"
    )


class WeatherResponse(BaseModel):
    """Complete weather response with current conditions and/or forecast."""

    current: Optional[CurrentWeather] = Field(
        None, description="Current weather conditions"
    )
    forecast: list[ForecastDay] = Field(
        default_factory=list, description="Multi-day forecast"
    )
    cached: bool = Field(False, description="Whether response came from cache")
    error: Optional[str] = Field(None, description="Error message if request failed")

    @property
    def success(self) -> bool:
        """Check if response contains weather data."""
        return self.error is None and (self.current is not None or len(self.forecast) > 0)
