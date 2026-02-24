# Implementation Plan: Prompt Registry

**Branch**: `012-prompt-registry` | **Date**: 2026-02-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/012-prompt-registry/spec.md`

## Summary

Migrate all 11 system prompt constants from hardcoded strings in `src/services/agents.py` to MLflow's Prompt Registry. Prompts become versioned, alias-addressable artifacts loaded at runtime via `mlflow.genai.load_prompt()` with built-in caching. Eval runs are tagged with prompt versions for lineage tracking. Bundled defaults provide fallback when the registry is unreachable.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: MLflow 3.10.0+ (already installed), FastAPI, OpenAI Agents SDK
**Storage**: MLflow Prompt Registry (backed by existing MLflow tracking server in Docker)
**Testing**: pytest (unit tests with mocked MLflow calls), MLflow eval (integration with real registry)
**Target Platform**: Linux server (Docker)
**Project Type**: Web application (backend API)
**Performance Goals**: Prompt loading adds <100ms latency to agent creation (cached). Cache TTL configurable (default 300s).
**Constraints**: No new infrastructure. No new database tables. Backward-compatible with existing eval framework.
**Scale/Scope**: 11 prompts, 2 aliases per prompt, ~5 files modified, ~3 files created.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 Gate

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Clarity over Cleverness | PASS | Single-responsibility `prompt_service.py` module with explicit inputs/outputs. No magic — prompts loaded by name, fallback behavior documented. |
| II. Evaluation-First Behavior | PASS | Prompt versions become versioned artifacts (stronger than before). Eval runs tagged with versions. Existing eval suite validates no regression. |
| III. Tool Safety and Correctness | N/A | No new tools introduced. Existing tools unchanged. |
| IV. Privacy by Default | PASS | Prompts contain system instructions, not user data. No PII stored in registry. Prompt content logged at DEBUG level only. |
| V. Consistent UX | PASS | No user-facing behavior changes. Prompts loaded transparently. Fallback ensures identical behavior when registry is down. |
| VI. Performance and Cost Budgets | PASS | Built-in MLflow caching (300s default TTL) eliminates per-request registry calls. Cache TTL is configurable. |
| VII. Observability and Debuggability | PASS | FR-010: Log prompt version + alias + correlation ID on every agent creation. Fallback usage logged as WARNING. |
| VIII. Reproducible Environments | PASS | No new dependencies. MLflow already in `pyproject.toml`. Auto-seeding ensures consistent registry state across environments. |

### Post-Phase 1 Gate

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Clarity over Cleverness | PASS | Three clean modules: `defaults.py` (data), `prompt_service.py` (logic), modified `agents.py` (consumption). Each has one purpose. |
| II. Evaluation-First Behavior | PASS | Unit tests mock MLflow calls. Integration tests verify seed + load cycle. Eval lineage tagging enables prompt-vs-quality correlation. |
| VI. Performance and Cost Budgets | PASS | MLflow's built-in cache handles TTL. No custom cache implementation needed. Startup seeding is O(11) calls, one-time. |
| VII. Observability and Debuggability | PASS | Structured logging for: seed results, each prompt load (version, alias, fallback status), cache hits/misses via MLflow internals. |

**No violations. No Complexity Tracking entries needed.**

## Project Structure

### Documentation (this feature)

```text
specs/012-prompt-registry/
├── plan.md              # This file
├── research.md          # Phase 0: MLflow API research, decisions
├── data-model.md        # Phase 1: MLflow entity descriptions
├── quickstart.md        # Phase 1: Developer usage guide
├── contracts/
│   └── prompt-service.md # Phase 1: Internal service interface
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── prompts/
│   ├── __init__.py          # NEW: Package init
│   └── defaults.py          # NEW: Bundled default prompt text + name mappings
├── services/
│   ├── prompt_service.py    # NEW: Registry load/seed/version logic
│   ├── agents.py            # MODIFIED: Replace constants with prompt_service calls
│   └── chat_service.py      # MODIFIED: Update re-exports for backward compat
├── config.py                # MODIFIED: Add PROMPT_CACHE_TTL_SECONDS, PROMPT_ALIAS
└── main.py                  # MODIFIED: Add seed_prompts() to lifespan startup

eval/
├── runner.py                # MODIFIED: Add prompt version tagging to mlflow.log_params()
└── __main__.py              # MODIFIED: (minimal) Pass prompt alias if --prompt-alias flag added

tests/
└── unit/
    ├── test_prompt_service.py  # NEW: Seed, load, fallback, version tracking
    └── test_prompt_defaults.py # NEW: Validate all defaults present and non-empty
```

**Structure Decision**: Backend-only changes within existing `src/` layout. New `src/prompts/` package for prompt data (defaults). New service module follows existing `src/services/` pattern. No frontend changes.

## Design Decisions

### D1: Use MLflow's built-in cache (not custom)

MLflow's `load_prompt(cache_ttl_seconds=N)` provides per-call caching. We pass `settings.prompt_cache_ttl_seconds` (default 300) to every load call. This eliminates the need for a custom in-memory cache, threading, or cache invalidation logic.

See [research.md](research.md#r4-caching-strategy) for details.

### D2: Bundled defaults as fallback AND seed source

The `src/prompts/defaults.py` module serves dual purpose:
1. **Seed source**: Content registered into MLflow on first startup
2. **Fallback**: Returned when MLflow is unreachable

This avoids duplication — the same content is used for both purposes.

### D3: Prompt loading in agent factories (not at module import time)

Current constants load at import time (Python module loading). Registry prompts load when `create_*_agent()` or `build_orchestrator_instructions()` is called. This means:
- No blocking MLflow calls during import
- Prompts are loaded fresh (within cache TTL) per agent creation
- Fallback works even if MLflow was down at import time

### D4: Backward-compatible re-exports

`chat_service.py` currently re-exports all prompt constants. To avoid breaking tests and eval code that import from `chat_service`, we'll replace the constant re-exports with lazy properties or functions that delegate to `prompt_service.load_prompt()`. Tests that import these for assertions will get the current registry content (or fallback default).

### D5: Eval lineage via mlflow.log_params()

Prompt versions are logged as MLflow run parameters (not tags) because:
- Params appear in the MLflow UI comparison table
- Params are filterable in search queries
- Format: `prompt.{name}` → `v{version}` (e.g., `prompt.orchestrator-base` → `v3`)

## Migration Path

### Phase 1: Foundation (no behavior change)
1. Create `src/prompts/defaults.py` with current prompt text
2. Create `src/services/prompt_service.py` with load/seed/version logic
3. Add config settings
4. Add unit tests for prompt_service

### Phase 2: Integration (swap to registry)
1. Add `seed_prompts()` to `main.py` lifespan
2. Modify `agents.py` to use `prompt_service.load_prompt()`
3. Update `chat_service.py` re-exports
4. Verify existing tests still pass

### Phase 3: Eval Lineage
1. Add prompt version tagging to `eval/runner.py`
2. Add `--prompt-alias` flag to eval CLI
3. Verify eval runs show prompt versions in MLflow UI

### Phase 4: Verification
1. Run full eval suite — compare results to pre-migration baseline
2. Verify fallback behavior (stop MLflow, confirm agent still works)
3. Verify alias swap (register new version, update alias, confirm agent uses it)
