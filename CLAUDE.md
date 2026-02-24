# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A FastAPI-based streaming chat API that interfaces with OpenAI's Agents SDK, with a Next.js web frontend. Features real-time SSE streaming, security guardrails (input/output moderation via OpenAI Moderation API), an MLflow-based LLM-as-a-judge evaluation framework, and a web UI with authentication, conversation management, memory browsing, and knowledge graph exploration.

## Development Commands

### Docker Services (Required)

```bash
# Start MLflow tracking server
docker compose -f docker/docker-compose.mlflow.yml up -d

# Start Chat API (requires .env with OPENAI_API_KEY)
docker compose -f docker/docker-compose.api.yml up -d --env-file .env

# Rebuild after code changes
docker compose -f docker/docker-compose.api.yml up -d --build

# View logs
docker logs chat-api -f

# Stop services
docker compose -f docker/docker-compose.api.yml down
docker compose -f docker/docker-compose.mlflow.yml down
```

### Frontend Development (Next.js)

```bash
# Install dependencies
cd frontend && npm install

# Start development server (http://localhost:3000)
cd frontend && npm run dev

# Run unit tests (Vitest + React Testing Library)
cd frontend && npm test

# Run E2E tests (Playwright, requires dev server running)
cd frontend && npx playwright test

# Build for production
cd frontend && npm run build

# Start frontend + API with Docker
docker compose -f docker/docker-compose.frontend.yml up -d
```

### Testing & Evaluation

```bash
# Run all tests (against Docker services on localhost:8000)
uv run pytest tests/ -v

# Run only unit tests (no Docker needed, everything mocked)
uv run pytest tests/unit/ -v

# Run specific test file
uv run pytest tests/integration/test_chat_endpoint.py -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html

# Run MLflow evaluation suite (requires Docker services running)
uv run python -m eval

# Validate evaluation dataset only
uv run python -m eval --dry-run

# Run eval with verbose output
uv run python -m eval --verbose

# Run eval inside Docker (requires both API and MLflow stacks running)
docker compose -f docker/docker-compose.eval.yml run --rm eval --dataset eval/graph_extraction_golden_dataset.json --verbose

# Dry-run eval in Docker
docker compose -f docker/docker-compose.eval.yml run --rm eval --dry-run

# Rebuild eval container after code changes
docker compose -f docker/docker-compose.eval.yml build
```

### Dependency Management

This project uses `uv` (not pip). Never use `pip install`.

```bash
uv sync              # Install/sync dependencies
uv add <package>     # Add dependency
uv add --dev <pkg>   # Add dev dependency
uv run <command>     # Run in project environment
```

## Architecture

```
src/
├── main.py              # FastAPI app, lifespan, exception handlers
├── config.py            # Pydantic settings (env vars)
├── database.py          # asyncpg pool, migrations runner
├── api/
│   ├── routes.py        # /health, /chat endpoints with SSE streaming
│   ├── auth.py          # /auth/* endpoints (login, setup, refresh, status)
│   ├── admin.py         # /admin/* endpoints (user CRUD)
│   ├── conversations.py # /conversations/* endpoints
│   ├── memories.py      # /memories/* endpoints
│   ├── entities.py      # /entities/* endpoints
│   ├── dependencies.py  # Auth dependencies (get_current_user, require_admin)
│   └── middleware.py     # Correlation ID middleware
├── models/
│   ├── request.py       # ChatRequest validation
│   ├── response.py      # StreamChunk, ErrorResponse models
│   ├── user.py          # User, RefreshToken models
│   └── auth.py          # Auth request/response models
└── services/
    ├── chat_service.py  # OpenAI Agents SDK integration, streaming
    ├── auth_service.py  # JWT, password hashing, refresh tokens
    ├── user_service.py  # User CRUD operations
    ├── guardrails.py    # Input/output moderation with retry logic
    └── logging_service.py

frontend/                  # Next.js 15 App Router
├── src/
│   ├── app/
│   │   ├── (auth)/      # Login, setup pages (no sidebar)
│   │   ├── (main)/      # Chat, memory, knowledge, admin (with sidebar)
│   │   └── api/auth/    # Auth.js API route
│   ├── components/
│   │   ├── chat/        # ChatPanel, MessageBubble, ChatInput, etc.
│   │   ├── conversation/ # ConversationList, ConversationItem
│   │   ├── memory/      # MemoryCard, MemoryList
│   │   ├── knowledge/   # EntityDetail, EntityList
│   │   ├── layout/      # Header, Sidebar, ErrorBoundary
│   │   └── ui/          # Button, Input, Card, Dialog, Skeleton
│   ├── hooks/           # useChat, useConversations, useMemories, useEntities
│   ├── stores/          # Zustand chat-store
│   ├── lib/             # api-client, auth (Auth.js), chat-stream (SSE)
│   └── types/           # TypeScript interfaces

eval/
├── __main__.py          # CLI entry point (python -m eval)
├── runner.py            # Orchestrates eval flow, MLflow GenAI integration
├── mlflow_datasets.py   # MLflow Evaluation Dataset registration (get-or-create)
├── judge.py             # LLM-as-a-judge quality scorer
├── assistant.py         # Test client for assistant invocation
├── dataset.py           # Golden dataset loader/validator
└── models.py            # EvalResult, EvalRunMetrics

tests/
├── unit/                # Mock everything, no services needed
└── integration/         # Hit Docker services on localhost:8000
```

### Key Patterns

**Streaming Flow**: Request → CorrelationIdMiddleware → `/chat` route → `ChatService.stream_completion()` → SSE chunks with `data: {json}\n\n` format

**Guardrails**: SDK decorators `@input_guardrail` / `@output_guardrail` wrap validation. Uses OpenAI Moderation API with exponential backoff retry. Fail-closed on API errors.

**Evaluation**: Uses MLflow 3.10.0 GenAI features with a unified two-phase pattern. All evals that invoke the production agent use: Phase 1 — manual prediction loop with `mlflow.openai.autolog(disable=True)` to prevent orphaned traces; Phase 2 — scorer-only `genai_evaluate()` with pre-computed outputs (no `predict_fn`), creating the only traces (with assessments). This two-phase split is required because `Runner.run_sync()` (asyncio) deadlocks inside `genai_evaluate()`'s worker threads. Datasets are registered via `mlflow.genai.datasets.create_dataset` + `merge_records`. Eval types:
- **Quality evals**: LLM judge scores response quality against rubrics
- **Security evals**: Use `expected_behavior: "block"|"allow"` to compute block rate and false positive rate
- **Memory retrieval eval**: Queries memory service directly (no agent), no two-phase needed
- **Memory write eval**: Phase 1 extracts `save_memory_tool`/`delete_memory_tool` calls from agent, Phase 2 runs precision/recall scorers + LLM judge. Metrics: extraction_precision, extraction_recall, false_positive_rate, judge_pass_rate
- **Weather eval**: Tests tool calling behavior with `weather_behavior_scorer`

## Testing Philosophy

- **pytest**: Test code logic, error handling, control flow. Mock all OpenAI/LLM API calls. Fast, deterministic, cheap.
- **MLflow eval**: Test AI behavior, output quality, guardrail effectiveness. Real API calls. Slow, non-deterministic, expensive.

Never mock the entire SDK/Runner in pytest. If you need to test SDK integration behavior, that belongs in MLflow eval.

## Environment Variables

Required: `OPENAI_API_KEY`

Optional: `OPENAI_MODEL` (default: gpt-4o), `MAX_TOKENS` (default: 2000), `TIMEOUT_SECONDS` (default: 30), `LOG_LEVEL` (default: INFO)

## API Endpoints

- `GET /health` - Returns `{"status": "healthy", "timestamp": "..."}`
- `POST /chat` - SSE streaming. Body: `{"message": "...", "model": null, "max_tokens": null}`

## Feature Roadmap Context

See `vision.md` for the full roadmap. Completed: 001–013. Next: 014 (Eval Dashboard UI).

When a feature, idea, or capability is deferred or declared out of scope during any phase (specify, clarify, plan, implement), add it to the **Future Capabilities** section in `vision.md` so it is not lost.

## Spec-Kit Workflow

This project uses a spec-driven development process. Each feature goes through these phases:

1. **Specify** — Write feature spec from natural language description
2. **Clarify** — Resolve ambiguities in the spec (optional)
3. **Plan** — Technical architecture, data model, API contracts
4. **Tasks** — Break plan into dependency-ordered, independently testable tasks
5. **Analyze** — Cross-artifact consistency check (optional)
6. **Implement** — Execute tasks phase by phase

### How to Run

When the user asks to run a spec-kit phase, read the corresponding prompt file for detailed instructions:

| Phase | Prompt File |
|-------|-------------|
| Specify | `.github/prompts/speckit.specify.prompt.md` |
| Clarify | `.github/prompts/speckit.clarify.prompt.md` |
| Plan | `.github/prompts/speckit.plan.prompt.md` |
| Tasks | `.github/prompts/speckit.tasks.prompt.md` |
| Checklist | `.github/prompts/speckit.checklist.prompt.md` |
| Analyze | `.github/prompts/speckit.analyze.prompt.md` |
| Implement | `.github/prompts/speckit.implement.prompt.md` |

### Key Resources

- **Templates**: `.specify/templates/` (spec, plan, tasks, checklist templates)
- **Constitution**: `.specify/memory/constitution.md` (project principles, non-negotiable)
- **Scripts**: `.specify/scripts/powershell/` (branch creation, prerequisites, etc.)
- **Vision**: `vision.md` (guiding principles, memory architecture, feature roadmap)

### Conventions

- Feature branches: `NNN-short-name` (e.g., `008-web-frontend`)
- Spec artifacts go in: `specs/NNN-short-name/`
- Each feature produces: `spec.md`, `plan.md`, `tasks.md`, and optionally `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `checklists/`
