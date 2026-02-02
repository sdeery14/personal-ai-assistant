"""Weather service for OpenWeatherMap API integration."""

import asyncio
import re
from datetime import date, datetime, timezone
from typing import Optional

import httpx
import structlog

from src.config import get_settings
from src.models.weather import (
    CurrentWeather,
    ForecastDay,
    WeatherCondition,
    WeatherResponse,
)

logger = structlog.get_logger(__name__)

# Coordinate pattern: "lat, lon" or "lat,lon"
COORDINATE_PATTERN = re.compile(r"^(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)$")


def _kelvin_to_fahrenheit(k: float) -> float:
    """Convert Kelvin to Fahrenheit."""
    return round((k - 273.15) * 9 / 5 + 32, 1)


def _kelvin_to_celsius(k: float) -> float:
    """Convert Kelvin to Celsius."""
    return round(k - 273.15, 1)


def _mps_to_mph(mps: float) -> float:
    """Convert meters per second to miles per hour."""
    return round(mps * 2.237, 1)


def _normalize_location(location: str) -> str:
    """Normalize location string for cache key consistency.

    Returns lowercase, trimmed string for cache key.
    Original location is used for API calls.
    """
    return location.strip().lower()


# US state abbreviations for location normalization
US_STATE_CODES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
    'DC',  # District of Columbia
}

# Common ISO 3166-1 alpha-2 country codes (not exhaustive, but covers major countries)
COMMON_COUNTRY_CODES = {
    'US', 'GB', 'UK', 'CA', 'AU', 'DE', 'FR', 'IT', 'ES', 'JP',
    'CN', 'IN', 'BR', 'MX', 'KR', 'RU', 'NL', 'BE', 'CH', 'AT',
    'SE', 'NO', 'DK', 'FI', 'PL', 'PT', 'IE', 'NZ', 'SG', 'HK',
    'TW', 'ZA', 'IL', 'AE', 'SA', 'EG', 'AR', 'CL', 'CO', 'PE',
    'TH', 'MY', 'ID', 'PH', 'VN', 'TR', 'GR', 'CZ', 'HU', 'RO',
}


def _normalize_location_for_api(location: str) -> str:
    """Normalize location for OpenWeatherMap API call.

    Handles state abbreviations correctly:
    - "Boston, MA" → "Boston,MA,US" (US state codes need country code)
    - "Toronto, ON" → "Toronto" (non-US state codes are stripped)
    - "London, UK" → "London,UK" (country codes preserved)
    - "Boston" → "Boston" (simple city names preserved)

    See: docs/guides/openweathermap-api.md for format details.
    """
    location = location.strip()

    # Don't modify coordinate queries
    if COORDINATE_PATTERN.match(location):
        return location

    # Split by comma
    parts = [p.strip() for p in location.split(',')]

    if len(parts) == 1:
        # Simple city name, return as-is
        return parts[0]

    if len(parts) == 2:
        city, second = parts
        second_upper = second.upper()

        # Check if second part is a US state code
        if second_upper in US_STATE_CODES:
            # Add US country code: "Boston,MA" → "Boston,MA,US"
            return f"{city},{second_upper},US"

        # Check if it's a known country code
        if second_upper in COMMON_COUNTRY_CODES:
            return f"{city},{second_upper}"

        # If it's a 2-letter code but not recognized, it's likely a province code
        # (e.g., "ON" for Ontario, "BC" for British Columbia)
        # Strip it and just use the city name
        if len(second) == 2:
            return city

        # For longer codes, also strip (e.g., full state/province names)
        return city

    if len(parts) == 3:
        city, state, country = parts
        country_upper = country.upper()

        # Already has country code
        if country_upper == 'US' and state.upper() in US_STATE_CODES:
            # Valid US format
            return f"{city},{state.upper()},{country_upper}"

        # Non-US with state code - strip state
        return f"{city},{country_upper}"

    # More than 3 parts - just use first part as city
    return parts[0]


def _parse_coordinates(location: str) -> tuple[float, float] | None:
    """Parse coordinates from location string.

    Returns (lat, lon) tuple if location is in coordinate format, None otherwise.
    """
    match = COORDINATE_PATTERN.match(location.strip())
    if match:
        return float(match.group(1)), float(match.group(2))
    return None


def _get_error_message(error_type: str, location: str | None = None) -> str:
    """Get user-friendly error message for error type."""
    messages = {
        "api_unavailable": "I'm unable to retrieve weather information right now. Please try again in a few minutes.",
        "invalid_location": f"I couldn't find weather data for '{location}'. Please check the spelling or try a nearby city.",
        "timeout": "The weather request took too long. Please try again.",
        "rate_limited": "Weather service is temporarily busy. Please try again in a moment.",
        "auth_error": "Weather service configuration error. Please contact support.",
        "unknown": "An unexpected error occurred while fetching weather data. Please try again.",
    }
    return messages.get(error_type, messages["unknown"])


class WeatherService:
    """Service for fetching weather data from OpenWeatherMap."""

    def __init__(self):
        self.settings = get_settings()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.settings.weather_api_timeout)
            )
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _call_api(
        self,
        endpoint: str,
        params: dict,
        max_retries: int = 3,
    ) -> dict | None:
        """Call OpenWeatherMap API with retry logic.

        Args:
            endpoint: API endpoint (e.g., 'weather', 'forecast')
            params: Query parameters
            max_retries: Maximum retry attempts

        Returns:
            API response dict or None on failure
        """
        if not self.settings.openweathermap_api_key:
            logger.error("weather_api_key_missing")
            return None

        url = f"{self.settings.weather_api_base_url}/{endpoint}"
        params["appid"] = self.settings.openweathermap_api_key

        client = await self._get_client()
        last_error = None

        for attempt in range(max_retries):
            try:
                response = await client.get(url, params=params)

                # Don't retry on client errors (4xx) except 429
                if response.status_code == 401:
                    logger.error("weather_api_auth_error")
                    return None
                if response.status_code == 404:
                    logger.debug("weather_location_not_found", params=params)
                    return None
                if response.status_code == 429:
                    # Rate limited - retry with backoff
                    wait_time = 2 ** attempt
                    logger.warning(
                        "weather_api_rate_limited",
                        attempt=attempt,
                        wait_seconds=wait_time,
                    )
                    await asyncio.sleep(wait_time)
                    continue

                # Retry on server errors (5xx)
                if response.status_code >= 500:
                    wait_time = 2 ** attempt
                    logger.warning(
                        "weather_api_server_error",
                        status_code=response.status_code,
                        attempt=attempt,
                        wait_seconds=wait_time,
                    )
                    await asyncio.sleep(wait_time)
                    continue

                response.raise_for_status()
                return response.json()

            except httpx.TimeoutException as e:
                last_error = e
                wait_time = 2 ** attempt
                logger.warning(
                    "weather_api_timeout",
                    attempt=attempt,
                    wait_seconds=wait_time,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)
                continue

            except httpx.HTTPError as e:
                last_error = e
                logger.error(
                    "weather_api_error",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                break

        logger.error(
            "weather_api_failed_after_retries",
            max_retries=max_retries,
            last_error=str(last_error) if last_error else None,
        )
        return None

    async def get_current_weather(self, location: str) -> CurrentWeather | None:
        """Get current weather for a location.

        Args:
            location: City name or coordinates

        Returns:
            CurrentWeather or None if not found/error
        """
        # Check for coordinate format
        coords = _parse_coordinates(location)
        if coords:
            params = {"lat": coords[0], "lon": coords[1]}
        else:
            # Normalize location for API (handles US state codes)
            normalized_location = _normalize_location_for_api(location)
            params = {"q": normalized_location}

        data = await self._call_api("weather", params)
        if not data:
            return None

        try:
            # Parse OpenWeatherMap response
            main = data.get("main", {})
            weather = data.get("weather", [{}])[0]
            wind = data.get("wind", {})

            temp_k = main.get("temp", 273.15)
            feels_k = main.get("feels_like", temp_k)

            return CurrentWeather(
                location=data.get("name", location),
                temperature_f=_kelvin_to_fahrenheit(temp_k),
                temperature_c=_kelvin_to_celsius(temp_k),
                feels_like_f=_kelvin_to_fahrenheit(feels_k),
                feels_like_c=_kelvin_to_celsius(feels_k),
                humidity=main.get("humidity", 0),
                conditions=WeatherCondition(
                    description=weather.get("description", "unknown"),
                    icon=weather.get("icon", ""),
                ),
                wind_speed_mph=_mps_to_mph(wind.get("speed", 0)),
                timestamp=datetime.fromtimestamp(data.get("dt", 0), tz=timezone.utc),
            )
        except Exception as e:
            logger.error(
                "weather_parse_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    async def get_forecast(
        self, location: str, days: int = 7
    ) -> list[ForecastDay]:
        """Get weather forecast for a location.

        Args:
            location: City name or coordinates
            days: Number of forecast days (1-7, clamped)

        Returns:
            List of ForecastDay objects
        """
        # Clamp days to valid range
        days = max(1, min(7, days))

        # Check for coordinate format
        coords = _parse_coordinates(location)
        if coords:
            params = {"lat": coords[0], "lon": coords[1]}
        else:
            # Normalize location for API (handles US state codes)
            normalized_location = _normalize_location_for_api(location)
            params = {"q": normalized_location}

        # OpenWeatherMap free tier returns 5-day/3-hour forecast
        data = await self._call_api("forecast", params)
        if not data:
            return []

        try:
            # Aggregate 3-hour data into daily forecasts
            daily_data: dict[date, dict] = {}

            for item in data.get("list", []):
                dt = datetime.fromtimestamp(item.get("dt", 0), tz=timezone.utc)
                day = dt.date()

                if day not in daily_data:
                    daily_data[day] = {
                        "temps": [],
                        "conditions": [],
                        "pop": [],  # probability of precipitation
                    }

                main = item.get("main", {})
                weather = item.get("weather", [{}])[0]

                daily_data[day]["temps"].append(main.get("temp", 273.15))
                daily_data[day]["conditions"].append(weather)
                daily_data[day]["pop"].append(item.get("pop", 0) * 100)

            # Convert to ForecastDay objects
            forecast = []
            sorted_days = sorted(daily_data.keys())[:days]

            for day in sorted_days:
                day_info = daily_data[day]
                temps = day_info["temps"]
                conditions = day_info["conditions"]
                pops = day_info["pop"]

                # Get most common condition
                if conditions:
                    # Use the condition from midday if available, else first
                    mid_idx = len(conditions) // 2
                    main_condition = conditions[mid_idx]
                else:
                    main_condition = {"description": "unknown", "icon": ""}

                high_k = max(temps) if temps else 273.15
                low_k = min(temps) if temps else 273.15

                forecast.append(
                    ForecastDay(
                        date=day,
                        high_f=_kelvin_to_fahrenheit(high_k),
                        high_c=_kelvin_to_celsius(high_k),
                        low_f=_kelvin_to_fahrenheit(low_k),
                        low_c=_kelvin_to_celsius(low_k),
                        conditions=WeatherCondition(
                            description=main_condition.get("description", "unknown"),
                            icon=main_condition.get("icon", ""),
                        ),
                        precipitation_chance=int(max(pops)) if pops else 0,
                    )
                )

            return forecast

        except Exception as e:
            logger.error(
                "weather_forecast_parse_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return []

    async def get_weather(
        self,
        location: str,
        include_forecast: bool = False,
        forecast_days: int = 0,
    ) -> WeatherResponse:
        """Get weather data for a location.

        Args:
            location: City name or coordinates
            include_forecast: Whether to include forecast
            forecast_days: Number of forecast days (1-7)

        Returns:
            WeatherResponse with current conditions and/or forecast
        """
        import time

        from src.services.redis_service import RedisService

        start_time = time.perf_counter()
        location = location.strip()

        if not location:
            return WeatherResponse(error=_get_error_message("invalid_location", ""))

        redis = RedisService()
        cache_key_location = _normalize_location(location)
        cached = False
        current = None
        forecast = []

        try:
            # Check cache for current weather
            cached_current = await redis.get_weather_cache(
                cache_key_location, "current"
            )
            if cached_current:
                current = CurrentWeather(**cached_current)
                cached = True
                logger.debug("weather_cache_hit", location=location, type="current")
            else:
                current = await self.get_current_weather(location)
                if current:
                    await redis.set_weather_cache(
                        cache_key_location,
                        "current",
                        current.model_dump(mode="json"),
                        self.settings.weather_cache_ttl_current,
                    )

            # Check cache for forecast if requested
            if include_forecast and forecast_days > 0:
                cache_key = f"forecast_{forecast_days}"
                cached_forecast = await redis.get_weather_cache(
                    cache_key_location, cache_key
                )
                if cached_forecast:
                    forecast = [ForecastDay(**f) for f in cached_forecast]
                    cached = True
                    logger.debug("weather_cache_hit", location=location, type="forecast")
                else:
                    forecast = await self.get_forecast(location, forecast_days)
                    if forecast:
                        await redis.set_weather_cache(
                            cache_key_location,
                            cache_key,
                            [f.model_dump(mode="json") for f in forecast],
                            self.settings.weather_cache_ttl_forecast,
                        )

            latency_ms = int((time.perf_counter() - start_time) * 1000)

            # Determine if we got valid data
            if current is None and not forecast:
                logger.warning(
                    "weather_request_failed",
                    location=location,
                    latency_ms=latency_ms,
                )
                return WeatherResponse(
                    error=_get_error_message("invalid_location", location)
                )

            logger.info(
                "weather_request_success",
                location=location,
                cached=cached,
                latency_ms=latency_ms,
                has_current=current is not None,
                forecast_days=len(forecast),
            )

            return WeatherResponse(
                current=current,
                forecast=forecast,
                cached=cached,
            )

        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(
                "weather_request_error",
                location=location,
                error=str(e),
                error_type=type(e).__name__,
                latency_ms=latency_ms,
            )
            return WeatherResponse(error=_get_error_message("unknown"))
