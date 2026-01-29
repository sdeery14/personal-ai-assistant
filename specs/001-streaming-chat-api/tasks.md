# Tasks: Core Streaming Chat API

**Input**: Design documents from `/specs/001-streaming-chat-api/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Feature**: 001 - Core Streaming Chat API
**Goal**: Enable basic chat interaction with streamed LLM responses, structured logging, and error handling

**Tests**: pytest tests are REQUIRED per spec (deterministic tests for streaming, error handling, observability)

**Organization**: Tasks grouped by user story for independent implementation and testing

---

## Format: `- [ ] [ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (US1, US2, US3) - omitted for Setup/Foundational phases
- Include exact file paths in task descriptions

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Create project structure and install dependencies

- [ ] T001 Create project directory structure (src/, tests/, src/api/, src/models/, src/services/)
- [ ] T002 Create requirements.txt with pinned dependencies (fastapi==0.109.0, uvicorn[standard], openai, pydantic==2.5.0, structlog, pytest, pytest-asyncio, httpx)
- [ ] T003 [P] Create .env.example with environment variable template (OPENAI_API_KEY, OPENAI_MODEL, MAX_TOKENS, TIMEOUT_SECONDS, LOG_LEVEL)
- [ ] T004 [P] Create .gitignore (venv/, .env, __pycache__/, *.pyc, .pytest_cache/, htmlcov/)

**Checkpoint**: Project structure ready for implementation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Implement config.py with Pydantic settings (load env vars: OPENAI_API_KEY, OPENAI_MODEL, MAX_TOKENS, TIMEOUT_SECONDS, LOG_LEVEL)
- [ ] T006 [P] Implement structlog configuration in src/services/logging_service.py (JSON output, correlation ID binding, ISO timestamps, redaction processor for api_key fields)
- [ ] T007 [P] Create src/models/__init__.py with __all__ exports
- [ ] T008 [P] Create src/api/__init__.py with __all__ exports
- [ ] T009 [P] Create src/services/__init__.py with __all__ exports
- [ ] T010 Create tests/conftest.py with pytest fixtures (mock OpenAI client, test app instance)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Basic Message Exchange (Priority: P1) 🎯 MVP

**Goal**: User sends text message and receives streamed LLM response via SSE

**Independent Test**: Send "What is 2+2?" and verify streamed chunks are received with sequence numbers and is_final flag

### Implementation for User Story 1

- [ ] T011 [P] [US1] Create ChatRequest model in src/models/request.py (message: str, model: str, max_tokens: int, validation: non-empty, ≤8000 chars, model in allowlist)
- [ ] T012 [P] [US1] Create StreamChunk and ChatResponse models in src/models/response.py (content, sequence, is_final, correlation_id, status, duration_ms, total_tokens)
- [ ] T013 [US1] Implement ChatService.stream_completion in src/services/chat_service.py (OpenAI client, chat.completions.create with stream=True, async generator yielding chunks)
- [ ] T014 [US1] Create FastAPI app in src/main.py (app initialization, CORS middleware, startup/shutdown events)
- [ ] T015 [US1] Implement /chat endpoint in src/api/routes.py (POST handler, parse ChatRequest, generate correlation_id UUID4, call ChatService, return StreamingResponse with media_type="text/event-stream", yield SSE format "data: {json}\n\n")
- [ ] T016 [US1] Implement /health endpoint in src/api/routes.py (GET handler, return {"status": "healthy", "timestamp": ISO8601})
- [ ] T017 [US1] Write integration test in tests/integration/test_chat_endpoint.py (mock OpenAI, test streaming chunks received, verify sequence and is_final flag, use httpx.AsyncClient with stream())

**Checkpoint**: At this point, User Story 1 should stream responses successfully - testable with pytest

---

## Phase 4: User Story 2 - Error Handling and Feedback (Priority: P2)

**Goal**: Graceful error handling with user-friendly messages following constitutional UX principle (what happened + why + what to do)

**Independent Test**: Send empty message, invalid model, simulate OpenAI API error - verify appropriate error responses

### Implementation for User Story 2

- [ ] T018 [US2] Add Pydantic validation error handler in src/api/routes.py (catch RequestValidationError, return 400 with ErrorResponse: error, detail, correlation_id)
- [ ] T019 [US2] Add OpenAI API error handling in src/services/chat_service.py (try/except OpenAIError, stream error chunk with user-friendly message per constitution)
- [ ] T020 [US2] Add timeout handling in src/api/routes.py (asyncio.timeout(TIMEOUT_SECONDS) context manager, catch TimeoutError, return 504 with three-part error message)
- [ ] T021 [US2] Write unit tests in tests/unit/test_models.py (test ChatRequest validation: empty message, message >8000 chars, invalid model, max_tokens out of range)
- [ ] T022 [US2] Write integration test in tests/integration/test_chat_endpoint.py (test error scenarios: empty message → 400, invalid model → 400, mock OpenAI error → error chunk streamed)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - error handling validated

---

## Phase 5: User Story 3 - Request Observability (Priority: P3)

**Goal**: Every request logged with structured data (correlation IDs, timestamps, redacted content) enabling debugging

**Independent Test**: Send message and verify structured JSON logs with correlation_id, no PII/secrets exposed

### Implementation for User Story 3

- [ ] T023 [P] [US3] Implement correlation ID middleware in src/api/middleware.py (generate UUID4 per request, add to request.state, bind to structlog context, add X-Correlation-Id response header)
- [ ] T024 [US3] Add request lifecycle logging in src/api/routes.py (log request_received with correlation_id/method/path on entry, log response_complete with duration_ms/token_count/status on exit)
- [ ] T025 [US3] Add chunk metadata logging in src/services/chat_service.py (log chunk_sent events with sequence and timing, do NOT log content)
- [ ] T026 [US3] Add error context logging in error handlers (log error_occurred with correlation_id, error_type, message, recovery action)
- [ ] T027 [US3] Write tests in tests/unit/test_logging.py (test redaction processor removes api_key, test correlation_id binds correctly, test log format is JSON)
- [ ] T028 [US3] Write integration test in tests/integration/test_observability.py (capture logs, verify correlation_id present, verify no secrets in logs, verify timestamps in UTC ISO8601)

**Checkpoint**: All user stories should now be independently functional with full observability

---

## Phase 6: Docker & Deployment

**Purpose**: Containerize application for consistent runtime environment

- [ ] T029 Create Dockerfile (FROM python:3.11-slim, WORKDIR /app, COPY requirements.txt, RUN pip install, COPY src/, EXPOSE 8000, CMD uvicorn src.main:app --host 0.0.0.0 --port 8000)
- [ ] T030 Create README.md with setup instructions (prerequisites, .env setup, docker build/run commands, curl examples, troubleshooting)
- [ ] T031 Verify full workflow: docker build → docker run → curl /health → curl /chat → verify streaming → verify logs → pytest

**Checkpoint**: Feature 001 complete - streaming chat API runs in Docker with tests passing

---

## Dependencies & Execution Order

### Phase Dependencies

1. **Setup (Phase 1)**: No dependencies - start immediately
2. **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
3. **User Story 1 (Phase 3)**: Depends on Foundational - MVP implementation
4. **User Story 2 (Phase 4)**: Depends on Foundational + User Story 1 - builds on streaming endpoint
5. **User Story 3 (Phase 5)**: Depends on Foundational + User Stories 1 & 2 - observability layer
6. **Docker (Phase 6)**: Depends on all user stories complete

### Execution Strategy

**Recommended Order** (sequential, focused sessions):

```
Setup (T001-T004)
  ↓
Foundational (T005-T010) ← BLOCKING GATE
  ↓
User Story 1 (T011-T017) ← MVP MILESTONE
  ↓
Test & validate streaming works
  ↓
User Story 2 (T018-T022)
  ↓
Test & validate error handling
  ↓
User Story 3 (T023-T028)
  ↓
Test & validate observability
  ↓
Docker (T029-T031) ← DEPLOYMENT READY
```

### Parallel Opportunities

Within each phase, tasks marked **[P]** can run in parallel:

- **Setup**: T003 and T004 (different files)
- **Foundational**: T006-T009 (different modules)
- **US1 Implementation**: T011 and T012 (models)
- **US3 Observability**: T023 and T024 (different concerns)

---

## Implementation Notes

### Stop Conditions (Per User Request)

✅ **Stop when**:
- A streamed response can be verified via pytest (after T017)
- The API runs successfully in Docker (after T031)

### What to AVOID (Per User Request)

❌ **Do NOT**:
- Re-plan or redesign during implementation
- Add new architecture, tools, or abstractions not in plan.md
- Over-optimize or refactor prematurely
- Design for future features (no memory, tools, multi-user)
- Add documentation-only tasks (README.md is minimal setup only)

### Key Implementation Patterns (From research.md)

**FastAPI SSE Streaming**:
```python
async def generate_stream():
    async for chunk in openai_stream:
        yield f"data: {json.dumps(chunk_dict)}\n\n"

return StreamingResponse(generate_stream(), media_type="text/event-stream")
```

**OpenAI Streaming**:
```python
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": message}],
    stream=True
)
async for chunk in response:
    if chunk.choices[0].delta.content:
        yield chunk.choices[0].delta.content
```

**structlog Redaction**:
```python
def redact_sensitive(logger, method, event_dict):
    if "api_key" in event_dict:
        event_dict["api_key"] = "REDACTED"
    return event_dict
```

**pytest Async Streaming Test**:
```python
@pytest.mark.asyncio
async def test_chat_streaming():
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with client.stream("POST", "/chat", json={"message": "Hello"}) as response:
            chunks = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunks.append(json.loads(line[6:]))
            assert len(chunks) > 0
```

---

## Validation Checklist

Before marking feature complete:

- [ ] pytest tests/unit/ passes
- [ ] pytest tests/integration/ passes
- [ ] docker build succeeds
- [ ] docker run starts without errors
- [ ] curl http://localhost:8000/health returns {"status": "healthy"}
- [ ] curl POST /chat streams chunks with sequence numbers
- [ ] Empty message returns 400 error
- [ ] Invalid model returns 400 error
- [ ] Logs are JSON format with correlation_ids
- [ ] No API keys visible in logs
- [ ] README.md instructions work from scratch

---

**Total Tasks**: 31 tasks across 6 phases
**Estimated Effort**: 8-10 focused sessions (assuming 3-4 tasks per session)
**MVP Milestone**: After Phase 3 (Task T017) - basic streaming works
**Feature Complete**: After Phase 6 (Task T031) - Docker deployment ready
