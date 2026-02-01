"""Weather tool for Agent integration (Feature 005)."""

from agents import function_tool

from src.models.weather import WeatherResponse
from src.services.weather_service import WeatherService


def _format_current_weather(response: WeatherResponse) -> str:
    """Format current weather as readable text."""
    if not response.current:
        return ""

    current = response.current
    lines = [
        f"Current weather in {current.location}:",
        f"  Temperature: {current.temperature_f}°F ({current.temperature_c}°C)",
        f"  Feels like: {current.feels_like_f}°F ({current.feels_like_c}°C)",
        f"  Conditions: {current.conditions.description}",
        f"  Humidity: {current.humidity}%",
        f"  Wind: {current.wind_speed_mph} mph",
    ]
    return "\n".join(lines)


def _format_forecast(response: WeatherResponse) -> str:
    """Format forecast as readable text."""
    if not response.forecast:
        return ""

    lines = ["\nForecast:"]
    for day in response.forecast:
        lines.append(
            f"  {day.date.strftime('%A, %b %d')}: "
            f"High {day.high_f}°F ({day.high_c}°C), "
            f"Low {day.low_f}°F ({day.low_c}°C), "
            f"{day.conditions.description}, "
            f"{day.precipitation_chance}% chance of precipitation"
        )
    return "\n".join(lines)


def _format_weather_response(response: WeatherResponse) -> str:
    """Format complete weather response as readable text.

    Args:
        response: WeatherResponse from weather service

    Returns:
        Human-readable weather information
    """
    if response.error:
        return response.error

    parts = []

    # Add current weather
    current_text = _format_current_weather(response)
    if current_text:
        parts.append(current_text)

    # Add forecast
    forecast_text = _format_forecast(response)
    if forecast_text:
        parts.append(forecast_text)

    if not parts:
        return "No weather data available."

    result = "\n".join(parts)

    # Add cache indicator for debugging (optional)
    if response.cached:
        result += "\n\n(Data from cache)"

    return result


@function_tool
async def get_weather(
    location: str,
    include_forecast: bool = False,
    forecast_days: int = 0,
) -> str:
    """Get current weather and optional forecast for a location.

    Args:
        location: City name, optionally with state/country (e.g., "Boston, MA" or "London, UK").
                  Can also be coordinates (e.g., "40.7128, -74.0060").
        include_forecast: Whether to include multi-day forecast.
        forecast_days: Number of forecast days (1-7, only used if include_forecast=True).

    Returns:
        Weather information as formatted text, or an error message if the request fails.
    """
    # Validate location
    if not location or not location.strip():
        return "Please specify a location to get weather information."

    # Clamp forecast days to valid range
    if include_forecast and forecast_days < 1:
        forecast_days = 3  # Default to 3 days if forecast requested but no days specified
    forecast_days = max(0, min(7, forecast_days))

    # Get weather data
    service = WeatherService()
    try:
        response = await service.get_weather(
            location=location.strip(),
            include_forecast=include_forecast,
            forecast_days=forecast_days,
        )
        return _format_weather_response(response)
    finally:
        await service.close()


# Export the tool for registration
get_weather_tool = get_weather
