# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A FastAPI-based streaming chat API that interfaces with OpenAI's Agents SDK. Features real-time SSE streaming, security guardrails (input/output moderation via OpenAI Moderation API), and an MLflow-based LLM-as-a-judge evaluation framework.

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
├── api/
│   ├── routes.py        # /health, /chat endpoints with SSE streaming
│   └── middleware.py    # Correlation ID middleware
├── models/
│   ├── request.py       # ChatRequest validation
│   └── response.py      # StreamChunk, ErrorResponse models
└── services/
    ├── chat_service.py  # OpenAI Agents SDK integration, streaming
    ├── guardrails.py    # Input/output moderation with retry logic
    └── logging_service.py

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

**Evaluation**: Uses MLflow 3.8.1 GenAI features throughout. `mlflow.genai.evaluate()` runs scorers and creates traces with assessments. Datasets are registered via `mlflow.genai.datasets.create_dataset` + `merge_records` (not `log_artifact`). The memory write eval uses a two-phase approach because `Runner.run_sync()` (asyncio) deadlocks inside `genai_evaluate()`'s worker threads — Phase 1 runs the agent with autolog disabled, Phase 2 runs scorer-only `genai_evaluate()` with pre-computed outputs. Security datasets use `expected_behavior: "block"|"allow"` to compute block rate and false positive rate.

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

Current: Features 001 (Core API) and 002 (Eval Framework) complete, 003 (Security Guardrails) complete.

Future: Memory retrieval (004), Weather tool (005), Voice (006), Edge client (007), Google integrations (008).

Each feature follows: spec → plan → tasks → implementation → eval coverage.
