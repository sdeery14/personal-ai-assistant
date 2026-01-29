# Implementation Plan: Core Streaming Chat API

**Branch**: `001-streaming-chat-api` | **Date**: 2026-01-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-streaming-chat-api/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Enable basic chat interaction where users send text messages via HTTP and receive streamed responses from an LLM. System provides structured logging with correlation IDs, graceful error handling, and token tracking. This is the foundational feature - stateless, single-container, no memory/tools/auth.

**Technical Approach**: FastAPI server with SSE streaming, OpenAI Agents SDK for LLM integration, structured JSON logging, Docker container for runtime, pytest for verification.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI 0.109+, openai-agents (latest), Pydantic 2.x, structlog
**Storage**: N/A (stateless, no persistence)
**Testing**: pytest, pytest-asyncio, httpx (async client for testing)
**Target Platform**: Docker container (Linux-based), single-container deployment
**Project Type**: Single project (backend API only, no frontend)
**Performance Goals**: First chunk within 2s (p95), stream responses up to 2000 tokens without interruption
**Constraints**: <30s request timeout, <3s first-chunk latency (p95), stateless requests
**Scale/Scope**: Single user, development-focused, ~500 LOC initial implementation

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

| Principle                          | Requirement                                    | Status      | Notes                                                               |
| ---------------------------------- | ---------------------------------------------- | ----------- | ------------------------------------------------------------------- |
| **I. Clarity over Cleverness**     | Simple modules, explicit I/O, typed signatures | ✅ PASS     | Single-purpose endpoint, Pydantic models, type hints required       |
| **II. Evaluation-First Behavior**  | Tests before implementation, golden suite      | ⚠️ DEFERRED | Golden tests in Feature 002; pytest tests required for this feature |
| **III. Tool Safety**               | Allowlisted, schema-validated tools            | ✅ PASS     | No tools in this feature (explicitly out of scope)                  |
| **IV. Privacy by Default**         | Redacted logs, env var secrets, minimal data   | ✅ PASS     | API keys in env, structlog redaction, stateless (no data retention) |
| **V. Consistent UX**               | Three-part error messages, no guessing         | ✅ PASS     | Error responses: what happened + why + what to do                   |
| **VI. Performance & Cost Budgets** | Timeouts, token tracking, degradation          | ✅ PASS     | 30s timeout, token logging, OpenAI rate limits respected            |
| **VII. Observability**             | Structured logs, correlation IDs, debuggable   | ✅ PASS     | structlog with JSON, correlation ID per request, error context      |

**Gate Result**: ✅ **PASS** - 6 of 7 principles satisfied (Evaluation-First partially deferred as planned)

**Justification for Deferral**: Principle II (Evaluation-First) golden test suite is explicitly scoped to Feature 002 per vision.md roadmap. This feature includes deterministic pytest tests for streaming behavior, error handling, and observability - satisfying the spirit of testing requirements at appropriate scope.

## Project Structure

### Documentation (this feature)

```text
specs/001-streaming-chat-api/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── chat-api.yaml    # OpenAPI spec for /chat endpoint
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── api/
│   ├── __init__.py
│   ├── routes.py          # FastAPI route definitions (/chat endpoint)
│   └── middleware.py      # Logging, correlation ID injection
├── models/
│   ├── __init__.py
│   ├── request.py         # ChatRequest, validation
│   └── response.py        # StreamChunk, ChatResponse
├── services/
│   ├── __init__.py
│   ├── chat_service.py    # OpenAI Agents SDK integration, streaming logic
│   └── logging_service.py # structlog configuration, redaction
├── config.py              # Environment variables, settings
└── main.py                # FastAPI app initialization, startup/shutdown

tests/
├── unit/
│   ├── test_models.py     # Pydantic model validation
│   ├── test_logging.py    # Redaction, correlation IDs
│   └── test_config.py     # Environment variable loading
├── integration/
│   ├── test_chat_endpoint.py      # SSE streaming, error handling
│   └── test_observability.py      # End-to-end log verification
└── conftest.py            # Pytest fixtures, mocks

Dockerfile                 # Single-stage Python 3.11 image
.env.example              # Template for environment variables
requirements.txt          # Python dependencies (pinned versions)
README.md                 # Setup and run instructions
```

**Structure Decision**: Single project structure selected. Backend-only API service with no frontend, no separate apps/packages. Follows standard Python project layout with src/ for application code and tests/ mirroring structure. Docker provides consistent runtime environment.

## Complexity Tracking

> **No violations detected - section intentionally empty**

All constitutional principles are satisfied or appropriately deferred. No complexity justifications needed.

---

## Phase Outputs Summary

### Phase 0: Research ✅

**File**: [research.md](research.md)

**Decisions Made**:

- FastAPI `StreamingResponse` with async generators for SSE
- OpenAI SDK chat completions with `stream=True`
- structlog with redaction processors for JSON logging
- Docker single-stage (`python:3.11-slim`) for runtime
- pytest + httpx + pytest-asyncio for async testing

**All technical unknowns resolved.**

### Phase 1: Design ✅

**Files Created**:

- [data-model.md](data-model.md) - Entities (ChatRequest, StreamChunk, ChatResponse, RequestLog) with Pydantic validation
- [contracts/chat-api.yaml](contracts/chat-api.yaml) - OpenAPI 3.1 specification for `/chat` endpoint
- [quickstart.md](quickstart.md) - Setup guide for Docker and local development

**Constitution Check (Post-Design)**: ✅ **PASS**

All design decisions align with constitutional principles:

- **Clarity**: Single-purpose models with explicit validation (Pydantic)
- **Privacy**: Redaction patterns defined in data-model.md, API keys never logged
- **Observability**: RequestLog schema includes correlation_id, timestamps, event types
- **UX**: ErrorResponse schema enforces three-part format (error, detail, correlation_id)
- **Performance**: Timeout and token limits baked into ChatRequest validation

**Agent Context Updated**: GitHub Copilot instructions updated with Python 3.11 + FastAPI stack

---

## Implementation Checklist

**Pre-Implementation** (verify before starting tasks):

- [x] Specification approved and clarified
- [x] Constitution Check passed
- [x] All technical decisions documented in research.md
- [x] Data models defined with validation rules
- [x] API contract (OpenAPI) generated
- [x] Quickstart guide written

**Next Command**: `/speckit.tasks` to generate implementation task list

---

## Key Files Reference

| File                                               | Purpose                                 | Status                      |
| -------------------------------------------------- | --------------------------------------- | --------------------------- |
| [spec.md](spec.md)                                 | Feature specification with user stories | ✅ Complete                 |
| [plan.md](plan.md)                                 | This file - implementation plan         | ✅ Complete                 |
| [research.md](research.md)                         | Technology decisions and patterns       | ✅ Complete                 |
| [data-model.md](data-model.md)                     | Entity definitions and validation       | ✅ Complete                 |
| [contracts/chat-api.yaml](contracts/chat-api.yaml) | OpenAPI specification                   | ✅ Complete                 |
| [quickstart.md](quickstart.md)                     | Developer setup guide                   | ✅ Complete                 |
| tasks.md                                           | Implementation task breakdown           | ⏳ Pending `/speckit.tasks` |

---

**Planning Complete**: All Phase 0 and Phase 1 deliverables generated. Ready to proceed to task breakdown.
