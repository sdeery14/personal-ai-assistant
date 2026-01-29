# Data Model: Core Streaming Chat API

**Phase**: 1 (Design)
**Date**: 2026-01-28
**Purpose**: Define entities, validation rules, and data flow for stateless chat API

---

## Entities

### 1. ChatRequest

**Purpose**: Represents an incoming user message with validation

**Fields**:

- `message` (str, required): User's text input
  - **Validation**: Non-empty, max 8000 characters (OpenAI context window safety margin)
  - **Example**: `"What is the capital of France?"`
- `model` (str, optional): OpenAI model identifier
  - **Default**: `"gpt-4"` (configurable via environment)
  - **Validation**: Must be in allowlist: `["gpt-4", "gpt-3.5-turbo"]`
  - **Example**: `"gpt-3.5-turbo"`
- `max_tokens` (int, optional): Maximum tokens in response
  - **Default**: `2000`
  - **Validation**: Range [1, 4000]
  - **Example**: `1000`

**Validation Rules**:

- `message` must not be empty after stripping whitespace
- `message` must not exceed character limit to prevent token overflow
- `model` must be from approved list (security constraint)

**Relationships**: None (stateless, no persistence)

**Pydantic Model**:

```python
from pydantic import BaseModel, Field, field_validator

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    model: str = Field(default="gpt-4")
    max_tokens: int = Field(default=2000, ge=1, le=4000)

    @field_validator('message')
    def message_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Message cannot be empty or whitespace only')
        return v.strip()

    @field_validator('model')
    def model_allowed(cls, v):
        allowed = ["gpt-4", "gpt-3.5-turbo"]
        if v not in allowed:
            raise ValueError(f'Model must be one of {allowed}')
        return v
```

---

### 2. StreamChunk

**Purpose**: Individual piece of streamed response (SSE event)

**Fields**:

- `content` (str, required): Text fragment from LLM
  - **Example**: `"The capital"`
- `sequence` (int, required): Zero-indexed chunk number
  - **Example**: `0`, `1`, `2`...
- `is_final` (bool, required): True if this is the last chunk
  - **Example**: `false`, `false`, ... `true`
- `correlation_id` (str, required): Request tracking ID (UUID4)
  - **Example**: `"550e8400-e29b-41d4-a716-446655440000"`

**Validation Rules**:

- `correlation_id` must be valid UUID4 format
- `sequence` must be non-negative
- `is_final=True` must only appear once per stream

**Relationships**: Linked to parent request via `correlation_id`

**Pydantic Model**:

```python
from pydantic import BaseModel, UUID4

class StreamChunk(BaseModel):
    content: str
    sequence: int = Field(ge=0)
    is_final: bool
    correlation_id: UUID4
```

---

### 3. ChatResponse

**Purpose**: Metadata about completed response (logged, not streamed)

**Fields**:

- `correlation_id` (str, required): Matches request tracking ID
- `status` (str, required): `"success"` | `"error"` | `"timeout"`
- `total_tokens` (int, optional): Prompt + completion tokens (if available)
  - **Example**: `150`
- `duration_ms` (int, required): Request processing time in milliseconds
  - **Example**: `2345`
- `model_used` (str, required): Actual model that processed request
  - **Example**: `"gpt-4"`
- `error_message` (str, optional): Present only if `status="error"`
  - **Example**: `"OpenAI API rate limit exceeded"`

**Validation Rules**:

- `status` must be one of the three enum values
- `error_message` required if `status="error"`
- `total_tokens` omitted if error occurred before completion

**Relationships**: Logged alongside `RequestLog`, linked by `correlation_id`

**Pydantic Model**:

```python
from pydantic import BaseModel, UUID4, field_validator
from typing import Optional, Literal

class ChatResponse(BaseModel):
    correlation_id: UUID4
    status: Literal["success", "error", "timeout"]
    total_tokens: Optional[int] = None
    duration_ms: int = Field(ge=0)
    model_used: str
    error_message: Optional[str] = None

    @field_validator('error_message')
    def error_message_if_failed(cls, v, values):
        if values.get('status') == 'error' and not v:
            raise ValueError('error_message required when status is error')
        return v
```

---

### 4. RequestLog

**Purpose**: Structured log entry for observability (written by structlog)

**Fields**:

- `correlation_id` (str): UUID4 tracking ID
- `timestamp` (str): ISO8601 timestamp
  - **Example**: `"2026-01-28T14:32:10.123456Z"`
- `log_level` (str): `"INFO"` | `"ERROR"` | `"DEBUG"`
- `event` (str): Event type
  - **Examples**: `"request_received"`, `"response_complete"`, `"error_occurred"`
- `method` (str, optional): HTTP method (e.g., `"POST"`)
- `path` (str, optional): HTTP path (e.g., `"/chat"`)
- `duration_ms` (int, optional): For completion events
- `error_type` (str, optional): For error events (e.g., `"TimeoutError"`, `"OpenAIError"`)
- `message_preview` (str, optional): First 50 chars of user message (for context)

**Validation Rules**:

- All sensitive fields automatically redacted by structlog processor
- `correlation_id` present in all log entries for a request
- Timestamps in UTC

**Relationships**: Linked to `ChatResponse` by `correlation_id`

**Note**: Not a Pydantic model - emitted directly by structlog. Schema shown for documentation.

---

## State Transitions

### Request Lifecycle

```
[Client sends POST /chat]
    ↓
[Validate ChatRequest] → [Error: 400 Bad Request if validation fails]
    ↓
[Generate correlation_id (UUID4)]
    ↓
[Log: request_received]
    ↓
[Call OpenAI API with streaming=True]
    ↓
[Stream loop:]
    ├─→ [Receive chunk from OpenAI]
    ├─→ [Create StreamChunk with sequence number]
    ├─→ [Emit as SSE event: "data: {json}\n\n"]
    ├─→ [Log chunk metadata (no content)]
    └─→ [Repeat until stream complete or timeout]
    ↓
[Stream ends]
    ↓
[Log: response_complete with ChatResponse metadata]
    ↓
[Client receives final chunk with is_final=true]
```

**Error Paths**:

- **Validation Error** (before OpenAI call): Return 400 with error details
- **OpenAI API Error**: Stream error chunk with user-friendly message
- **Timeout**: Close stream, log timeout, return 504
- **Client Disconnect**: Log disconnect, stop OpenAI stream early

---

## Data Flow

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ POST /chat {"message": "..."}
       ↓
┌──────────────────────────────────────┐
│  FastAPI Route (/chat)               │
│  • Parse & validate ChatRequest      │
│  • Generate correlation_id           │
│  • Inject into logger context        │
└──────┬───────────────────────────────┘
       │
       ↓
┌──────────────────────────────────────┐
│  ChatService                         │
│  • Build OpenAI messages array       │
│  • Call completions.create(stream=True) │
└──────┬───────────────────────────────┘
       │ async generator
       ↓
┌──────────────────────────────────────┐
│  Stream Generator                    │
│  • async for chunk in openai_stream │
│  • Transform to StreamChunk          │
│  • Yield as SSE: "data: {json}\n\n"  │
└──────┬───────────────────────────────┘
       │ StreamingResponse
       ↓
┌─────────────┐
│   Client    │ (receives SSE events in real-time)
└─────────────┘

[Parallel logging to stdout]
┌──────────────────────────────────────┐
│  structlog                           │
│  • request_received                  │
│  • chunk_sent (metadata only)        │
│  • response_complete                 │
└──────────────────────────────────────┘
```

---

## Validation Summary

| Entity       | Key Validation                   | Error Response                             |
| ------------ | -------------------------------- | ------------------------------------------ |
| ChatRequest  | `message` non-empty, ≤8000 chars | 400 Bad Request with details               |
| ChatRequest  | `model` in allowlist             | 400 Bad Request with details               |
| ChatRequest  | `max_tokens` in [1, 4000]        | 400 Bad Request with details               |
| StreamChunk  | `correlation_id` valid UUID4     | Internal error (should never reach client) |
| ChatResponse | `error_message` if status=error  | N/A (logging only)                         |

---

**Phase 1 Complete**: Data models defined with validation rules. Ready to generate API contracts.
