# Implementation Plan: External Tool v1 – Weather Lookup

**Branch**: `005-weather-lookup` | **Date**: February 1, 2026 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-weather-lookup/spec.md`

## Summary

Introduce a safe, real-world external tool that allows the assistant to accurately report current weather conditions and forecasts. Uses OpenWeatherMap API with schema-validated requests, Redis caching, retry logic with exponential backoff, and clear error states. The tool is read-only and provides factual weather data without advice or recommendations.

**Technical Approach**: Create a `get_weather` Agent tool using the `@function_tool` decorator from OpenAI Agents SDK. The tool calls OpenWeatherMap API for current conditions and forecasts, caches responses in Redis (10min current, 30min forecast), implements retry logic for transient failures, and returns structured weather data. Reuses existing Redis infrastructure from Feature 004.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI, OpenAI Agents SDK, httpx (async HTTP), Redis
**External API**: OpenWeatherMap API (free tier: 60 calls/minute)
**Testing**: pytest (unit), integration tests against Docker services
**Target Platform**: Linux/Windows development, Docker for Redis
**Project Type**: Single (backend API)

**Performance Goals**:

- Weather response: <3s p95 (SC-001)
- Cache hit rate: >30% (SC-003)
- Error messages: 100% user-friendly (SC-005)

**Constraints**:

- Must NOT provide weather-based advice or recommendations (out of scope)
- Must reuse Feature 003 guardrails for content safety
- Must reuse Feature 004 Redis infrastructure for caching
- Must fail closed on API errors (return error message, not hallucinate weather)
- API key must not be logged

**Scale/Scope**:

- 1 new Agent tool (`get_weather`)
- 1 new service (`weather_service.py`)
- New Pydantic models for weather data
- Redis cache keys for weather responses
- Weather evaluation dataset for quality testing

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

✅ **I. Clarity over Cleverness**: Simple tool interface with clear parameters (location, forecast_days). Standard retry pattern. Well-defined response schema.

✅ **II. Evaluation-First Behavior**: Weather golden dataset enables response quality testing. Metrics for accuracy, latency, cache efficiency. Integrates with Feature 002 MLflow framework.

✅ **III. Tool Safety and Correctness**: `get_weather` tool is read-only external API call. Schema validation on requests and responses. Timeout enforcement (5s). No user data modification.

✅ **IV. Privacy by Default**: Location names are not PII (public city names). API key redacted from logs. Correlation_id for audit trail.

✅ **V. Consistent UX**: Weather data presented factually without advice. Clear error messages for failures. Consistent response format (temp in F with C in parentheses).

✅ **VI. Performance and Cost Budgets**: Redis cache reduces API calls. Rate limiting via existing infrastructure. Timeout prevents hanging requests.

✅ **VII. Observability and Debuggability**: All weather requests logged with correlation_id, location, latency_ms, cache_hit, success status.

✅ **VIII. Reproducible Environments**: OpenWeatherMap API key via environment variable. Mock responses for testing. Docker compose for Redis.

**GATE STATUS**: ✅ PASSED - All principles satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/005-weather-lookup/
├── spec.md              # Feature specification (approved)
├── plan.md              # This file
├── tasks.md             # Task breakdown (generated)
└── research.md          # Phase 0: Technical unknowns (if needed)
```

### Source Code (repository root)

```text
src/
├── config.py                # MODIFIED: Add weather config (API key, cache TTLs, timeout)
├── models/
│   ├── weather.py           # NEW: WeatherRequest, WeatherResponse, ForecastDay
│   └── ...
├── services/
│   ├── weather_service.py   # NEW: OpenWeatherMap integration, caching, retry logic
│   ├── redis_service.py     # MODIFIED: Add weather cache methods
│   ├── chat_service.py      # MODIFIED: Attach get_weather tool
│   └── logging_service.py   # MODIFIED: Add weather request logging
└── tools/
    ├── query_memory.py      # (existing)
    └── get_weather.py       # NEW: Agent tool definition for weather queries

eval/
├── weather_golden_dataset.json  # NEW: Weather query test cases
├── dataset.py                   # MODIFIED: Load weather dataset
├── runner.py                    # MODIFIED: Compute weather metrics
└── models.py                    # MODIFIED: Add WeatherMetrics model

tests/
├── unit/
│   ├── test_weather_service.py  # NEW: API calls, caching, retry logic
│   ├── test_weather_models.py   # NEW: Request/response validation
│   └── test_weather_tool.py     # NEW: Tool invocation, error handling
└── integration/
    ├── test_weather_endpoint.py # NEW: End-to-end weather queries
    └── test_weather_eval.py     # NEW: Weather eval run verification
```

## Implementation Phases

### Phase 0: Environment Setup

**Objective**: Configure OpenWeatherMap API access and verify existing infrastructure.

**Tasks**:

1. Sign up for OpenWeatherMap free tier API key
2. Add `OPENWEATHERMAP_API_KEY` to environment configuration
3. Add weather-related config to `src/config.py`:
   - `WEATHER_API_KEY`, `WEATHER_API_BASE_URL`
   - `WEATHER_CACHE_TTL_CURRENT` (default: 600s / 10 min)
   - `WEATHER_CACHE_TTL_FORECAST` (default: 1800s / 30 min)
   - `WEATHER_API_TIMEOUT` (default: 5s)
4. Verify Redis from Feature 004 is operational
5. Add httpx to dependencies (async HTTP client)

**Acceptance Criteria**:

- OpenWeatherMap API key configured and accessible
- `uv sync` installs httpx
- Existing Feature 004 functionality unaffected
- Redis caching operational

**Deliverables**:

- Modified `src/config.py`
- Modified `pyproject.toml`
- Updated `.env.example` with `OPENWEATHERMAP_API_KEY`

---

### Phase 1: Weather Models & Service

**Objective**: Implement weather data models and OpenWeatherMap API integration.

**Tasks**:

1. Create `src/models/weather.py`:
   ```python
   class WeatherCondition(BaseModel):
       description: str      # e.g., "partly cloudy"
       icon: str             # weather icon code

   class CurrentWeather(BaseModel):
       location: str
       temperature_f: float
       temperature_c: float
       feels_like_f: float
       feels_like_c: float
       humidity: int         # percentage
       conditions: WeatherCondition
       wind_speed_mph: float
       timestamp: datetime

   class ForecastDay(BaseModel):
       date: date
       high_f: float
       high_c: float
       low_f: float
       low_c: float
       conditions: WeatherCondition
       precipitation_chance: int  # percentage

   class WeatherResponse(BaseModel):
       current: CurrentWeather | None
       forecast: list[ForecastDay]
       cached: bool
       error: str | None
   ```

2. Create `src/services/weather_service.py`:
   - `async def get_current_weather(location: str) -> CurrentWeather`
   - `async def get_forecast(location: str, days: int = 7) -> list[ForecastDay]`
   - `async def get_weather(location: str, include_forecast: bool = False, forecast_days: int = 0) -> WeatherResponse`
   - Implement retry logic with exponential backoff (max 3 attempts)
   - Implement 5-second timeout per request
   - Handle API errors gracefully (return error message, not exception)

3. Add Redis cache methods to `src/services/redis_service.py`:
   - `async def get_weather_cache(location: str, query_type: str) -> dict | None`
   - `async def set_weather_cache(location: str, query_type: str, data: dict, ttl: int)`
   - Cache key format: `weather:{normalized_location}:{query_type}`

**Acceptance Criteria**:

- OpenWeatherMap current weather API called correctly
- OpenWeatherMap forecast API called correctly
- Response parsed into Pydantic models
- Retry logic works for transient failures (429, 500, 503)
- Immediate failure for auth errors (401)
- Timeout enforced at 5 seconds
- Results cached in Redis with appropriate TTLs

**Testing Requirements**:

- Unit tests: mock httpx responses, test parsing, test retry logic
- Test cache hit/miss behavior
- Test timeout handling
- Test error scenarios (invalid location, API down)

**Deliverables**:

- `src/models/weather.py`
- `src/services/weather_service.py`
- Modified `src/services/redis_service.py`
- Unit tests

---

### Phase 2: Weather Tool Integration

**Objective**: Expose `get_weather` tool to the Agent via OpenAI Agents SDK.

**Tasks**:

1. Create `src/tools/get_weather.py`:
   ```python
   from agents import function_tool

   @function_tool
   async def get_weather(
       location: str,
       include_forecast: bool = False,
       forecast_days: int = 0
   ) -> str:
       """
       Get current weather and optional forecast for a location.

       Args:
           location: City name, optionally with state/country (e.g., "Boston, MA" or "London, UK")
           include_forecast: Whether to include multi-day forecast
           forecast_days: Number of forecast days (1-7, only used if include_forecast=True)

       Returns:
           Weather information as formatted text
       """
   ```

2. Implement tool function:
   - Validate location parameter (non-empty string)
   - Call weather_service.get_weather()
   - Format response as human-readable text
   - Include both F and C temperatures
   - Handle errors with user-friendly messages

3. Modify `src/services/chat_service.py`:
   - Import and attach `get_weather` tool to Agent
   - Add system prompt guidance for weather tool usage

4. Add logging in `src/services/logging_service.py`:
   - `log_weather_request(correlation_id, location, cache_hit, latency_ms, success)`

**Acceptance Criteria**:

- Agent can invoke `get_weather` tool during conversation
- Tool returns formatted weather data
- Errors return user-friendly messages, not exceptions
- All requests logged with correlation_id

**System Prompt Guidance**:

```
You have access to a weather tool that can retrieve current conditions and forecasts.

When to use the weather tool:
- User asks about current weather in a location
- User asks about upcoming weather or forecasts
- User asks weather-related questions ("Is it raining?", "Should I bring an umbrella?")

When using weather data:
- Present facts without advice or recommendations
- If forecast requested beyond 7 days, explain the limitation
- If location is ambiguous, ask for clarification or note which location was used
- If weather cannot be retrieved, explain the issue and suggest trying again
```

**Testing Requirements**:

- Unit tests: mock weather_service, test tool invocation
- Test error message formatting
- Integration tests: verify Agent uses tool for weather queries

**Deliverables**:

- `src/tools/get_weather.py`
- Modified `src/services/chat_service.py`
- Modified `src/services/logging_service.py`
- Unit + integration tests

---

### Phase 3: Error Handling & Edge Cases (US3)

**Objective**: Implement robust error handling for all failure scenarios.

**Tasks**:

1. Implement error handling in weather_service:
   - **API unavailable**: Return "I'm unable to retrieve weather information right now. Please try again in a few minutes."
   - **Invalid location**: Return "I couldn't find weather data for '[location]'. Please check the spelling or try a nearby city."
   - **Incomplete data**: Return available data with note about missing fields
   - **Timeout**: Return "The weather request took too long. Please try again."
   - **Rate limited**: Return "Weather service is temporarily busy. Please try again in a moment."

2. Implement location normalization:
   - Trim whitespace
   - Handle common variations (e.g., "NYC" → "New York City")
   - Log normalized location for cache key consistency

3. Handle ambiguous locations:
   - If multiple matches possible, use first result and note which location
   - Example: "Springfield" → "Showing weather for Springfield, IL. There are multiple cities named Springfield."

4. Handle coordinate input:
   - Detect lat/lon format (e.g., "40.7128, -74.0060")
   - Pass coordinates to API directly

**Acceptance Criteria**:

- All error scenarios return user-friendly messages
- No technical jargon or stack traces exposed to user
- Ambiguous locations handled gracefully
- Coordinate input supported

**Testing Requirements**:

- Unit tests: test each error scenario
- Test location normalization
- Test coordinate parsing

**Deliverables**:

- Enhanced `src/services/weather_service.py`
- Unit tests for error scenarios

---

### Phase 4: Caching Optimization (US4)

**Objective**: Optimize cache behavior for cost efficiency and performance.

**Tasks**:

1. Implement cache key normalization:
   - Lowercase location
   - Remove extra whitespace
   - Standardize state/country abbreviations
   - Key format: `weather:{normalized_location}:{current|forecast}`

2. Implement cache-first retrieval:
   - Check cache before API call
   - Return cached data with `cached: true` flag
   - Log cache hit/miss

3. Implement graceful degradation:
   - If Redis unavailable, proceed directly to API
   - Log warning but don't fail request

4. Add cache metrics:
   - Track cache hit rate in logs
   - Include cache_hit in weather logging

**Acceptance Criteria**:

- Same location queries return cached data within TTL
- Cache hit rate logged for monitoring
- Redis unavailable doesn't break weather queries

**Testing Requirements**:

- Unit tests: test cache key normalization
- Test cache hit/miss scenarios
- Test Redis unavailability handling

**Deliverables**:

- Enhanced caching in `src/services/weather_service.py`
- Cache metrics logging
- Unit tests

---

### Phase 5: Evaluation Integration

**Objective**: Create weather evaluation dataset and integrate with MLflow.

**Tasks**:

1. Create `eval/weather_golden_dataset.json`:
   - 10-15 test cases covering:
     - Current weather queries (valid locations)
     - Forecast queries
     - Invalid locations (error handling)
     - Ambiguous locations
     - Edge cases (coordinates, international cities)
   - Each case: query, expected_behavior (success/error), expected_fields

2. Modify `eval/models.py`:
   - Add `WeatherMetrics` model:
     ```python
     class WeatherMetrics(BaseModel):
         success_rate: float      # % of queries returning weather data
         error_rate: float        # % of queries returning errors
         cache_hit_rate: float    # % of cache hits
         latency_p50: int         # ms
         latency_p95: int         # ms
         valid_response_rate: float  # % with required fields present
     ```

3. Modify `eval/runner.py`:
   - Support weather dataset detection
   - Compute weather-specific metrics
   - Log to MLflow

4. Modify `eval/dataset.py`:
   - Add `load_weather_dataset()` function
   - Validate weather dataset schema

**Acceptance Criteria**:

- `uv run python -m eval --dataset eval/weather_golden_dataset.json` runs successfully
- MLflow logs weather metrics
- Success rate ≥ 95% for valid locations
- Latency p95 < 3000ms

**Testing Requirements**:

- Unit tests: dataset schema validation
- Integration tests: full eval run

**Deliverables**:

- `eval/weather_golden_dataset.json`
- Modified `eval/models.py`, `eval/runner.py`, `eval/dataset.py`
- Unit + integration tests

---

### Phase 6: Testing & Validation

**Objective**: Comprehensive test coverage and manual validation.

**Unit Test Coverage**:

- `test_weather_service.py`: API calls, parsing, retry logic, caching
- `test_weather_models.py`: Pydantic validation, serialization
- `test_weather_tool.py`: Tool invocation, error handling, formatting

**Integration Test Coverage**:

- `test_weather_endpoint.py`: End-to-end weather queries via chat API
- `test_weather_eval.py`: Full eval run with metrics

**Validation Steps** (manual):

1. Start services: `docker compose -f docker/docker-compose.api.yml up -d`
2. Test current weather:
   ```bash
   curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
     -d '{"message": "What is the weather in Boston?", "user_id": "test-user"}'
   # Expected: Response includes temperature, conditions, humidity
   ```
3. Test forecast:
   ```bash
   curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
     -d '{"message": "What is the weather forecast for Chicago this week?", "user_id": "test-user"}'
   # Expected: Response includes multi-day forecast
   ```
4. Test invalid location:
   ```bash
   curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
     -d '{"message": "What is the weather in Atlantis?", "user_id": "test-user"}'
   # Expected: User-friendly error message
   ```
5. Test caching (make same query twice, verify second is faster)
6. Run weather eval:
   ```bash
   uv run python -m eval --dataset eval/weather_golden_dataset.json --verbose
   # Expected: Success rate ≥ 95%, latency p95 < 3000ms
   ```
7. Check MLflow: http://localhost:5000 - verify weather metrics logged
8. Verify logs: check for `weather_request` events with correlation_id, no API keys

**Deliverables**:

- Complete test suite
- Validation checklist completed

---

## Implementation Sequence Summary

| Phase | Focus                | Key Deliverable                | Blocker |
|-------|----------------------|--------------------------------|---------|
| 0     | Environment Setup    | API key, config, httpx         | None    |
| 1     | Models & Service     | Weather API integration        | Phase 0 |
| 2     | Tool Integration     | Agent get_weather tool         | Phase 1 |
| 3     | Error Handling       | Graceful failures (US3)        | Phase 2 |
| 4     | Caching              | Redis optimization (US4)       | Phase 2 |
| 5     | Evaluation           | MLflow metrics                 | Phase 3 |
| 6     | Testing & Validation | Coverage, manual verification  | Phase 5 |

**Critical Path**: Phase 0 → 1 → 2 → 3 → 5 → 6

**Parallel Opportunities**:

- Phase 3 (Error Handling) and Phase 4 (Caching) can run in parallel after Phase 2
- Unit tests can be written in parallel with implementation

---

## Testing Strategy

### Test Pyramid

**Unit Tests** (70% of test effort):

- Weather service: API calls, response parsing, retry logic
- Caching: hit/miss, TTL, Redis unavailability
- Tool: invocation, parameter validation, error formatting
- Models: validation, serialization

**Integration Tests** (25% of test effort):

- End-to-end weather queries through chat API
- Eval run with MLflow logging
- Cache behavior verification

**Manual Validation** (5% of test effort):

- Response quality review
- Error message clarity
- MLflow dashboard inspection

### Mock Strategy

For unit tests, mock:
- `httpx.AsyncClient` for API calls
- `RedisService` for caching
- Use fixture responses from OpenWeatherMap documentation

### Performance Testing

**Targets** (per spec success criteria):

- SC-001: Response <3s p95
- SC-003: Cache hit rate >30%

**Approach**:

- Add latency logging to weather requests
- Run eval with `--verbose` to capture timing
- Review MLflow metrics for latency percentiles

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| OpenWeatherMap API down | Retry logic + clear error message |
| Rate limit exceeded | Cache reduces calls; error message if hit |
| Invalid API key | Fail fast with clear error; don't retry |
| Network timeout | 5s timeout + retry; user-friendly message |
| Ambiguous location | Use first result + note which location |

---

## Next Steps

### Immediate Actions

1. **Review this plan**: Stakeholder approval before implementation begins
2. **Get OpenWeatherMap API key**: Sign up for free tier
3. **Create feature branch**: `git checkout -b 005-weather-lookup`
4. **Generate tasks**: Create `tasks.md` with detailed task breakdown

### Definition of Done

- [ ] All 6 phases completed
- [ ] All tests passing (unit + integration)
- [ ] Manual validation steps verified
- [ ] Weather golden dataset with ≥10 cases
- [ ] MLflow metrics logging functional
- [ ] Success rate ≥ 95% for valid locations
- [ ] Latency p95 < 3000ms
- [ ] Error messages 100% user-friendly
- [ ] No weather-based advice in responses
- [ ] Code reviewed and merged to main
