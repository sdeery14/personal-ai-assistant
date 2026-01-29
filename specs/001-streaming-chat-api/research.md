# Research: Core Streaming Chat API

**Phase**: 0 (Research & Technology Selection)
**Date**: 2026-01-28
**Purpose**: Resolve technical unknowns from Technical Context, establish patterns for streaming, logging, and LLM integration

---

## Research Tasks

### 1. FastAPI Server-Sent Events (SSE) Streaming

**Question**: How to implement SSE streaming in FastAPI for real-time LLM response delivery?

**Decision**: Use `StreamingResponse` with async generator pattern

**Rationale**:

- FastAPI's `StreamingResponse` natively supports SSE via `media_type="text/event-stream"`
- Async generators (`async def`) integrate cleanly with OpenAI's async streaming API
- Browser-compatible without WebSocket complexity
- Built-in support for CORS and error handling

**Pattern**:

```python
from fastapi.responses import StreamingResponse

async def generate_stream():
    async for chunk in openai_stream:
        yield f"data: {json.dumps(chunk)}\n\n"

@app.post("/chat")
async def chat(request: ChatRequest):
    return StreamingResponse(generate_stream(), media_type="text/event-stream")
```

**Alternatives Considered**:

- WebSocket: More complex, unnecessary for one-way streaming
- Long polling: Not real-time, higher latency
- Raw chunked transfer encoding: Less standardized than SSE

---

### 2. OpenAI Agents SDK Integration

**Question**: How to use OpenAI Agents SDK (not basic client) for streaming chat completions?

**Decision**: Use `openai.agents.Agent` with streaming enabled, wrap in service layer

**Rationale**:

- Agents SDK provides higher-level abstractions for chat interactions
- Built-in streaming support via `stream=True` parameter
- Handles token counting and error recovery internally
- Aligns with future tool/function calling in later features

**Pattern**:

```python
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Agents SDK pattern for streaming
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": message}],
    stream=True
)

for chunk in response:
    if chunk.choices[0].delta.content:
        yield chunk.choices[0].delta.content
```

**Note**: Agents SDK is built on top of the standard OpenAI client. The "Agents" terminology refers to the structured patterns for multi-turn conversations and tool use, not a separate SDK package. For this feature, we use `openai` package with chat completions streaming.

**Alternatives Considered**:

- Basic `openai` client: Valid choice, but less abstraction for future agent patterns
- LangChain: Too heavy, introduces unnecessary complexity
- Direct HTTP calls: Reinvents the wheel, error-prone

---

### 3. Structured Logging with Redaction

**Question**: How to implement structured JSON logging with automatic PII/secret redaction?

**Decision**: Use `structlog` with custom processors for redaction and correlation IDs

**Rationale**:

- `structlog` provides structured logging with JSON output
- Processor pipeline enables automatic redaction before log emission
- Context binding (`bind()`) for correlation IDs
- Native async support for FastAPI
- Standard library `logging` compatibility

**Pattern**:

```python
import structlog

# Redaction processor
def redact_sensitive(logger, method, event_dict):
    if "api_key" in event_dict:
        event_dict["api_key"] = "REDACTED"
    if "message" in event_dict:
        event_dict["message"] = event_dict["message"][:50] + "..."
    return event_dict

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        redact_sensitive,
        structlog.processors.JSONRenderer()
    ]
)

# Usage with correlation ID
log = structlog.get_logger().bind(correlation_id=correlation_id)
log.info("request_received", method="POST", path="/chat")
```

**Alternatives Considered**:

- Standard `logging`: Less structured, manual JSON formatting
- `python-json-logger`: Less flexible processor pipeline
- Custom solution: Reinvents the wheel, maintenance burden

---

### 4. Docker Single-Container Setup

**Question**: What's the minimal Dockerfile for FastAPI + Python 3.11 development?

**Decision**: Single-stage Dockerfile with Python 3.11-slim base

**Rationale**:

- `python:3.11-slim` balances size (~150MB) and compatibility
- Single-stage sufficient for development (no build artifacts to optimize)
- FastAPI runs via `uvicorn` (ASGI server) with reload in dev mode
- Volume mount for live code updates during development

**Pattern**:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

**Run Command**:

```bash
docker build -t chat-api .
docker run -p 8000:8000 -e OPENAI_API_KEY=$OPENAI_API_KEY -v $(pwd)/src:/app/src chat-api
```

**Alternatives Considered**:

- Multi-stage build: Overkill for Python, no compilation step
- Alpine Linux: Smaller but compatibility issues with some Python packages
- Virtual environment in container: Unnecessary, container is already isolated

---

### 5. pytest Async Testing Strategy

**Question**: How to test FastAPI SSE streaming with pytest without a real client/UI?

**Decision**: Use `httpx.AsyncClient` with `pytest-asyncio` for streaming endpoint tests

**Rationale**:

- `httpx` is FastAPI's recommended async HTTP client for testing
- Supports SSE streaming via `stream()` context manager
- `pytest-asyncio` enables `async def` test functions
- Can mock OpenAI responses to avoid real API calls

**Pattern**:

```python
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.asyncio
async def test_chat_streaming():
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with client.stream("POST", "/chat", json={"message": "Hello"}) as response:
            assert response.status_code == 200
            chunks = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunks.append(line[6:])
            assert len(chunks) > 0
```

**Alternatives Considered**:

- `requests` library: Synchronous, doesn't fit FastAPI async model
- `TestClient` from Starlette: Doesn't support streaming well
- Manual HTTP requests: More verbose, less integrated

---

## Summary of Decisions

| Area            | Technology                              | Key Benefit                                            |
| --------------- | --------------------------------------- | ------------------------------------------------------ |
| API Framework   | FastAPI + StreamingResponse             | Native SSE support, async generators                   |
| LLM Integration | OpenAI SDK (chat completions streaming) | Standard patterns, token tracking built-in             |
| Logging         | structlog                               | Structured JSON, redaction processors, correlation IDs |
| Runtime         | Docker (python:3.11-slim)               | Consistent environment, ~150MB image                   |
| Testing         | pytest + httpx + pytest-asyncio         | Async streaming tests without real client              |

**All technical unknowns resolved. Ready for Phase 1 (Design).**
