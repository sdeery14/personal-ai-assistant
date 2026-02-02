# OpenWeatherMap API Integration Guide

**Last Updated**: 2026-02-01
**Feature**: 005-weather-lookup
**Purpose**: Document correct location parameter formats and API usage patterns for OpenWeatherMap

---

## API Overview

OpenWeatherMap provides two main API families for weather data:

1. **Current Weather API (v2.5)** - Simpler, supports city names directly (deprecated geocoding)
2. **One Call API (v3.0)** - Advanced, requires lat/lon coordinates

**For Feature 005, we use Current Weather API v2.5** due to its simpler location handling and free tier availability.

---

## Location Parameter Formats

### ✅ CORRECT: Formats That Work

#### 1. City Name Only

```
q=Boston
q=London
q=Seattle
q=Chicago
```

**Result**: Returns the most common/populous match globally.

#### 2. City + Country Code (Recommended)

```
q=Boston,US
q=London,GB
q=Paris,FR
q=Toronto,CA
```

**Result**: Narrows to the specific country using ISO 3166 country codes.

**Why Recommended**: Avoids ambiguity (e.g., Paris, France vs Paris, Texas).

#### 3. City + State + Country (US Only)

```
q=Boston,MA,US
q=Austin,TX,US
q=Portland,OR,US
```

**Result**: Specifies the exact US city by state.

**CRITICAL LIMITATION**: State codes are **only supported for US locations**. Using state codes for non-US cities will cause the API to fail.

#### 4. Latitude/Longitude Coordinates

```
lat=42.3601&lon=-71.0589  (Boston)
lat=51.5074&lon=-0.1278   (London)
```

**Result**: Most precise, works globally.

---

### ❌ INCORRECT: Formats That Fail

#### 1. State Abbreviation Without Country Code

```
q=Boston,MA          ❌ FAILS (missing country code)
q=Austin,TX          ❌ FAILS (missing country code)
```

**Error**: API interprets "MA" or "TX" as a country code, which doesn't exist.

#### 2. Non-US State/Province Codes

```
q=Toronto,ON,CA      ❌ FAILS (ON is province code, not supported)
q=Munich,BY,DE       ❌ FAILS (BY is state code, not supported)
q=Melbourne,VI,AU    ❌ FAILS (VI is state code, not supported)
```

**Why**: State/province codes are only supported for US locations.

#### 3. Full State Names

```
q=Boston,Massachusetts,US    ❌ FAILS (full names not supported)
q=Austin,Texas,US            ❌ FAILS (full names not supported)
```

**Why**: API expects 2-letter ISO codes, not full names.

---

## API Endpoint Structure

### Current Weather API (v2.5)

**Base URL**: `https://api.openweathermap.org/data/2.5/weather`

#### Required Parameters

| Parameter | Type   | Description                        |
| --------- | ------ | ---------------------------------- |
| `q`       | string | Location query (see formats above) |
| `appid`   | string | Your OpenWeatherMap API key        |

#### Optional Parameters

| Parameter | Type   | Default    | Description                                                      |
| --------- | ------ | ---------- | ---------------------------------------------------------------- |
| `units`   | string | `standard` | `standard` (Kelvin), `metric` (Celsius), `imperial` (Fahrenheit) |
| `lang`    | string | `en`       | Language code (e.g., `en`, `fr`, `es`)                           |

### Example API Calls

```bash
# City name only
https://api.openweathermap.org/data/2.5/weather?q=Boston&appid={API_KEY}&units=imperial

# City + country (recommended)
https://api.openweathermap.org/data/2.5/weather?q=Boston,US&appid={API_KEY}&units=imperial

# City + state + country (US only)
https://api.openweathermap.org/data/2.5/weather?q=Boston,MA,US&appid={API_KEY}&units=imperial

# Coordinates
https://api.openweathermap.org/data/2.5/weather?lat=42.3601&lon=-71.0589&appid={API_KEY}&units=imperial
```

---

## Response Structure

### Success Response (HTTP 200)

```json
{
  "coord": {
    "lon": -71.0589,
    "lat": 42.3601
  },
  "weather": [
    {
      "id": 800,
      "main": "Clear",
      "description": "clear sky",
      "icon": "01d"
    }
  ],
  "base": "stations",
  "main": {
    "temp": 282.55, // Current temperature
    "feels_like": 281.86, // Feels like temperature
    "temp_min": 280.37, // Min observed temp (city-wide)
    "temp_max": 284.26, // Max observed temp (city-wide)
    "pressure": 1023, // Atmospheric pressure (hPa)
    "humidity": 73 // Humidity (%)
  },
  "visibility": 10000, // Visibility (meters, max 10km)
  "wind": {
    "speed": 4.1, // Wind speed (default: m/s, imperial: mph)
    "deg": 80, // Wind direction (degrees)
    "gust": 5.7 // Wind gust (optional)
  },
  "clouds": {
    "all": 90 // Cloudiness (%)
  },
  "dt": 1560350645, // Data calculation time (Unix UTC)
  "sys": {
    "country": "US",
    "sunrise": 1560343627, // Sunrise time (Unix UTC)
    "sunset": 1560396563 // Sunset time (Unix UTC)
  },
  "timezone": -14400, // Timezone offset (seconds from UTC)
  "id": 4930956, // City ID
  "name": "Boston", // City name
  "cod": 200 // HTTP status code
}
```

### Error Response (HTTP 404)

```json
{
  "cod": "404",
  "message": "city not found"
}
```

**Common Causes**:

- Invalid location format (e.g., `Boston,MA` without `US`)
- Non-existent city name
- State codes used for non-US cities

---

## Best Practices for Location Handling

### 1. Normalize User Input

When users provide location queries, normalize them before calling the API:

```python
def normalize_location(location: str) -> str:
    """Normalize location for OpenWeatherMap API."""
    # Remove extra whitespace
    location = location.strip()

    # Remove common problematic patterns
    # Remove "in" prefix: "in Boston" → "Boston"
    if location.lower().startswith("in "):
        location = location[3:]

    # Check for state abbreviations without country
    parts = [p.strip() for p in location.split(',')]

    if len(parts) == 2:
        city, state_or_country = parts
        # If second part looks like US state code (2 uppercase letters)
        if len(state_or_country) == 2 and state_or_country.isupper():
            # Check if it's a known US state code
            us_states = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', ...]  # full list
            if state_or_country in us_states:
                # Add US country code
                location = f"{city},{state_or_country},US"
            # else assume it's already a country code

    return location
```

### 2. Handle State Abbreviations

**DO**: Strip state abbreviations for non-US cities

```python
# Input: "Toronto, ON"
# Process: Strip "ON" → "Toronto,CA"
# API Call: q=Toronto,CA
```

**DO**: Keep state abbreviations for US cities but add country code

```python
# Input: "Boston, MA"
# Process: Add US → "Boston,MA,US"
# API Call: q=Boston,MA,US
```

### 3. Fallback Strategy

If the API returns 404:

1. Try removing state/province code: `Boston,MA,US` → `Boston,US`
2. Try with just city name: `Boston,US` → `Boston`
3. Inform user if all attempts fail

### 4. Caching Strategy

Cache responses by normalized location key:

- Cache key: `lowercase(location)|units` (e.g., `"boston,us|imperial"`)
- TTL: 10 minutes for current weather (weather doesn't change rapidly)
- Cache location normalization results separately to avoid repeated API calls for similar queries

---

## Error Handling

### HTTP Status Codes

| Code          | Meaning           | Action                                                     |
| ------------- | ----------------- | ---------------------------------------------------------- |
| 200           | Success           | Return data                                                |
| 400           | Bad Request       | Check parameters, return error to user                     |
| 401           | Unauthorized      | Invalid API key, fail closed                               |
| 404           | Not Found         | Location not found, try fallback or return error           |
| 429           | Too Many Requests | Rate limit exceeded, use cached data or retry with backoff |
| 500, 502, 503 | Server Error      | Retry with exponential backoff (max 3 attempts)            |

### Retry Logic

```python
def should_retry(status_code: int) -> bool:
    """Determine if API call should be retried."""
    # Retry on transient errors
    if status_code in [429, 500, 502, 503]:
        return True
    # Don't retry on client errors or permanent failures
    if status_code in [400, 401, 404]:
        return False
    return False
```

---

## Rate Limits & Quotas

### Free Tier

- **60 calls/minute**
- **1,000,000 calls/month**

### Optimization Tips

1. **Cache aggressively**: 10-minute TTL keeps you well under limits
2. **Normalize locations**: Avoid duplicate calls for equivalent queries
3. **Batch requests**: If checking multiple cities, space them out

---

## Testing Checklist

Use these test cases to validate location handling:

### ✅ Should Work

- [ ] `Boston` - City only
- [ ] `Boston,US` - City + country
- [ ] `Boston,MA,US` - City + state + country (US)
- [ ] `London,GB` - Non-US city + country
- [ ] `São Paulo,BR` - Non-ASCII characters
- [ ] `lat=42.3601&lon=-71.0589` - Coordinates

### ❌ Should Handle Gracefully

- [ ] `Boston,MA` - Missing country code (normalize to `Boston,MA,US` or strip to `Boston,US`)
- [ ] `Toronto,ON,CA` - Non-US state code (strip to `Toronto,CA`)
- [ ] `Atlantis` - Non-existent city (return 404 error)
- [ ] `` - Empty string (validate before API call)

---

## Implementation Summary

For Feature 005 weather service:

1. **Use Current Weather API v2.5** (`/data/2.5/weather`)
2. **Normalize location input**: Handle state codes appropriately
3. **Prefer `{city},{country}` format**: Most reliable for global use
4. **For US cities with agent-provided states**: Either strip state or ensure format is `{city},{state},US`
5. **Cache responses**: 10-minute TTL with normalized location keys
6. **Implement fallback**: Try without state code if initial call fails
7. **Set timeout**: 5 seconds maximum
8. **Retry transient errors**: 429, 500, 502, 503 (max 3 attempts with exponential backoff)

---

## References

- [Current Weather API Documentation](https://openweathermap.org/current)
- [Geocoding API Documentation](https://openweathermap.org/api/geocoding-api)
- [ISO 3166 Country Codes](https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes)
- [Weather Condition Codes](https://openweathermap.org/weather-conditions)
