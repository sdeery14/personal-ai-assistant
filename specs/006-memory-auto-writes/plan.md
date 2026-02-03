# Implementation Plan: Memory v2 – Automatic Writes

**Branch**: `006-memory-auto-writes` | **Date**: February 3, 2026 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-memory-auto-writes/spec.md`

## Summary

Enable the assistant to automatically extract and persist important information from conversations. The agent decides what to remember during response generation via `save_memory` and `delete_memory` tools. Persistence happens asynchronously (never blocks the conversation). Includes episode summarization for meaningful conversations, duplicate prevention via semantic similarity, and MLflow evaluation coverage for extraction quality.

**Technical Approach**: The agent itself drives extraction decisions via tools — no separate extraction LLM call needed. `save_memory` applies confidence thresholds (>=0.7 auto-save, 0.5-0.7 confirm with user, <0.5 discard). `delete_memory` supports soft-delete with two-step confirmation. Both tools return immediately; actual DB writes use `asyncio.create_task()` for fire-and-forget persistence. Episode summarization triggers after response persistence when message count thresholds are met.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI, OpenAI Agents SDK, asyncpg, pgvector, Redis, tiktoken, MLflow
**Storage**: Postgres (pgvector), Redis (rate limiting, caching)
**Testing**: pytest (unit), integration tests against Docker services
**Target Platform**: Linux/Windows development, Docker for services
**Project Type**: Single (backend API + evaluation harness)
**Performance Goals**:

- Memory write latency: <500ms p95 for extraction + persistence (SC-004)
- Extraction precision: >=85% (SC-001)
- Extraction recall: >=70% (SC-002)

**Constraints**:

- Extraction decisions happen during response generation; persistence is async (FR-017)
- Must reuse Feature 004 retrieval infrastructure (memory_service, embedding_service)
- Must reuse Feature 003 guardrails for content safety
- Must integrate with Feature 002 eval framework
- Must fail closed on write errors (FR-016)
- Knowledge graph / entity relationships explicitly out of scope (Feature 007)

**Scale/Scope**:

- 1 new database migration (extend memory_items, add audit table)
- 2 new Agent tools (save_memory, delete_memory)
- 1 new service (memory_write_service)
- New config settings for write thresholds and rate limits
- Memory write golden dataset for evaluation

## Constitution Check

_GATE: Must pass before implementation._

- **I. Clarity over Cleverness**: Agent-driven extraction via tools follows existing patterns. No hidden extraction pipeline — the agent makes explicit decisions.

- **II. Evaluation-First Behavior**: Memory write golden dataset with precision/recall/false-positive metrics. Regression gating integrated with MLflow.

- **III. Tool Safety and Correctness**: `save_memory` has confidence thresholds preventing low-quality writes. `delete_memory` requires confirmation. Both enforce user_id scoping. Rate limits prevent spam.

- **IV. Privacy by Default**: Per-user scoping on all writes. Audit trail via memory_write_events. Soft-delete preserves reversibility. No raw content in logs.

- **V. Consistent UX**: Agent acknowledges memories naturally when useful. Asks confirmation for uncertain extractions. Users can correct/delete via conversation.

- **VI. Performance and Cost Budgets**: Async persistence avoids blocking conversation. Duplicate detection prevents memory store pollution. Rate limits (10/conversation, 25/hour) control costs.

- **VII. Observability and Debuggability**: All writes logged with correlation_id, confidence, processing_time. Audit table tracks create/supersede/delete operations.

- **VIII. Reproducible Environments**: All dependencies in pyproject.toml. Migration-based schema changes. Docker compose for services.

**GATE STATUS**: PASSED

## Project Structure

### Documentation (this feature)

```text
specs/006-memory-auto-writes/
├── spec.md              # Feature specification (approved)
├── plan.md              # This file
├── tasks.md             # Task breakdown
└── checklists/
    └── requirements.md  # Quality checklist
```

### Source Code (repository root)

```text
src/
├── config.py                      # MODIFIED: Add memory write config settings
├── main.py                        # MODIFIED: Drain pending writes on shutdown
├── models/
│   └── memory.py                  # MODIFIED: Add EPISODE type, write models
├── services/
│   ├── chat_service.py            # MODIFIED: Register new tools, system prompt, episode trigger
│   ├── memory_write_service.py    # NEW: Create/delete/supersede memories, duplicate detection, episodes
│   ├── memory_service.py          # (no changes - reuse existing)
│   ├── redis_service.py           # MODIFIED: Add write rate limit methods
│   ├── conversation_service.py    # (no changes - reuse existing)
│   └── embedding_service.py       # (no changes - reuse existing)
└── tools/
    ├── query_memory.py            # (no changes - reuse existing)
    ├── save_memory.py             # NEW: Agent tool for memory writes
    └── delete_memory.py           # NEW: Agent tool for memory deletion

migrations/
└── 005_memory_auto_writes.sql     # NEW: Extend memory_items, add audit table

eval/
├── memory_write_golden_dataset.json  # NEW: Extraction quality test cases
├── memory_write_judge.py             # NEW: Precision/recall judge
├── dataset.py                        # MODIFIED: Load write dataset
├── runner.py                         # MODIFIED: Write evaluation flow
├── models.py                         # MODIFIED: Write eval models
└── __main__.py                       # MODIFIED: Route write datasets

tests/
├── unit/
│   ├── test_memory_write_service.py  # NEW: Write service unit tests
│   ├── test_save_memory_tool.py      # NEW: Save tool unit tests
│   ├── test_delete_memory_tool.py    # NEW: Delete tool unit tests
│   └── test_memory_write_judge.py    # NEW: Write judge unit tests
└── integration/
    └── test_memory_writes.py         # NEW: End-to-end write tests
```

## Implementation Phases

### Phase 1: Database Schema Extension

**Objective**: Extend memory_items table and add audit table for memory write operations.

**Tasks**:

1. Create `migrations/005_memory_auto_writes.sql`:
   - Add columns to `memory_items`: source_conversation_id, confidence, superseded_by, status
   - Drop and recreate type CHECK to add 'episode'
   - Create `memory_write_events` audit table
   - Add index for supersession lookups

**Acceptance Criteria**:

- Migration runs idempotently (IF NOT EXISTS / ADD COLUMN IF NOT EXISTS)
- Existing memory_items data unaffected
- New columns have sensible defaults (confidence=1.0, status='active')

**Deliverables**:

- `migrations/005_memory_auto_writes.sql`

---

### Phase 2: Models & Config

**Objective**: Extend data models and add configuration for memory writes.

**Tasks**:

1. Add `EPISODE` to `MemoryType` enum in `src/models/memory.py`
2. Add new fields to `MemoryItem`: source_conversation_id, confidence, superseded_by, status
3. Create new models: `MemoryWriteRequest`, `MemoryDeleteRequest`, `MemoryWriteResponse`, `MemoryWriteEvent`
4. Add config settings to `src/config.py`: write rate limits, duplicate threshold, episode thresholds, confidence thresholds

**Acceptance Criteria**:

- All models validate correctly with Pydantic
- Config settings have sensible defaults matching spec
- Existing code unaffected by model additions

**Deliverables**:

- Modified `src/models/memory.py`
- Modified `src/config.py`

---

### Phase 3: Redis Rate Limiting Extensions

**Objective**: Add write-specific rate limiting to Redis service.

**Tasks**:

1. Add `check_write_rate_limit_conversation(conversation_id, limit)` to `redis_service.py`
2. Add `check_write_rate_limit_hourly(user_id, limit)` to `redis_service.py`
3. Graceful degradation if Redis unavailable (allow writes, log warning)

**Acceptance Criteria**:

- Per-conversation limit (10) enforced via Redis counter
- Per-user hourly limit (25) enforced via Redis counter with 3600s TTL
- Redis failure doesn't block memory writes

**Deliverables**:

- Modified `src/services/redis_service.py`
- Unit tests for new methods

---

### Phase 4: Memory Write Service

**Objective**: Core service for all memory write operations.

**Tasks**:

1. Create `src/services/memory_write_service.py` with `MemoryWriteService` class
2. Implement `create_memory()`: rate limit check → embedding → duplicate check → INSERT → audit event
3. Implement `delete_memory()`: search matches → soft-delete → audit event
4. Implement `supersede_memory()`: mark old superseded → create new → audit both
5. Implement `create_episode_summary()`: fetch messages → check threshold → OpenAI summarization → create EPISODE memory
6. Add background task management: `_pending_tasks` set, `schedule_write()`, `await_pending_writes()`
7. Implement duplicate detection: cosine similarity > 0.92 against existing active memories = skip

**Acceptance Criteria**:

- All write operations produce audit events in memory_write_events
- Duplicate detection prevents identical memories
- Rate limits enforced (10/conversation, 25/hour)
- Episode summarization only triggers above threshold (8+ user msgs OR 15+ total)
- Episode re-generation prevented via Redis flag
- Fail-closed: errors logged, conversation continues

**Deliverables**:

- `src/services/memory_write_service.py`
- Unit tests

---

### Phase 5: Agent Tools

**Objective**: Create save_memory and delete_memory tools following existing query_memory pattern.

**Tasks**:

1. Create `src/tools/save_memory.py`:
   - `@function_tool` with params: content, memory_type, confidence, importance
   - Confidence routing: >=0.7 queue write, 0.5-0.7 return "confirm_needed", <0.5 return "discarded"
   - Uses `schedule_write()` for async persistence
2. Create `src/tools/delete_memory.py`:
   - `@function_tool` with params: description, confirm
   - Two-step: `confirm=False` returns candidates, `confirm=True` executes deletion
3. Both tools extract user_id, correlation_id, conversation_id from ctx.context

**Acceptance Criteria**:

- Tools follow exact pattern of query_memory_tool (imports, ctx usage, error handling, JSON response)
- save_memory returns immediately (async persistence)
- delete_memory presents candidates before deleting
- Missing user_id returns error response (security)

**Deliverables**:

- `src/tools/save_memory.py`
- `src/tools/delete_memory.py`
- Unit tests for both

---

### Phase 6: Chat Service Integration

**Objective**: Register new tools, update system prompt, add episode trigger.

**Tasks**:

1. Add `MEMORY_WRITE_SYSTEM_PROMPT` constant with extraction guidelines:
   - What to save (facts, preferences, decisions)
   - What NOT to save (trivial, transient)
   - Confidence guidelines for the agent
   - Correction flow (delete old + save new)
2. Register `save_memory_tool` and `delete_memory_tool` in `_get_tools()`
3. Append `MEMORY_WRITE_SYSTEM_PROMPT` to instructions when DB available
4. Add `conversation_id` to context dict for tools
5. After response persistence, check message count and trigger episode summarization if threshold met
6. Update `src/main.py` lifespan shutdown to call `await_pending_writes()`

**Acceptance Criteria**:

- Agent receives memory write instructions in system prompt
- New tools available alongside existing query_memory and get_weather
- Context includes conversation_id for provenance
- Episode summarization fires asynchronously after qualifying conversations
- Pending writes drain on shutdown

**Deliverables**:

- Modified `src/services/chat_service.py`
- Modified `src/main.py`

---

### Phase 7: Evaluation Framework

**Objective**: Add memory write evaluation with golden dataset and MLflow integration.

**Tasks**:

1. Add eval models: `MemoryWriteTestCase`, `MemoryWriteEvalResult`, `MemoryWriteMetrics`
2. Create `eval/memory_write_judge.py` with precision/recall/false-positive evaluation
3. Create `eval/memory_write_golden_dataset.json` with 10-15 test cases
4. Add `load_memory_write_dataset()` to `eval/dataset.py`
5. Add `run_memory_write_evaluation()` to `eval/runner.py`
6. Update `eval/__main__.py` to route write datasets

**Acceptance Criteria**:

- `uv run python -m eval --dataset eval/memory_write_golden_dataset.json` runs successfully
- MLflow logs extraction_precision, extraction_recall, false_positive_rate
- Regression gate: precision >= 0.85, recall >= 0.70

**Deliverables**:

- `eval/memory_write_judge.py`
- `eval/memory_write_golden_dataset.json`
- Modified `eval/models.py`, `eval/dataset.py`, `eval/runner.py`, `eval/__main__.py`
- Unit tests for judge

---

### Phase 8: Tests & Validation

**Objective**: Comprehensive test coverage and manual validation.

**Unit Tests**:

- `test_memory_write_service.py`: create, duplicate, rate limit, delete, supersede, episode, fail-closed, cross-user
- `test_save_memory_tool.py`: confidence routing, missing user_id, response format
- `test_delete_memory_tool.py`: search mode, confirm mode, no matches
- `test_memory_write_judge.py`: precision/recall/false-positive calculations
- Extend `test_redis_service.py`: write rate limit methods

**Integration Tests**:

- `test_memory_writes.py`: save via chat, delete via chat, correction flow, rate limits, duplicate prevention, episode summarization

**Manual Validation**:

1. Start services: `docker compose -f docker/docker-compose.api.yml up -d --build`
2. Send conversation with facts: verify memories created in DB
3. Ask "what do you remember about me?": verify memories listed
4. Say "forget that I told you X": verify soft-delete
5. Say "actually I prefer Y now": verify supersession
6. Have 10+ turn conversation: verify episode summary created
7. Run eval: `uv run python -m eval --dataset eval/memory_write_golden_dataset.json --verbose`

---

## Implementation Sequence Summary

| Phase | Focus                     | Key Deliverable                     | Blocker       |
| ----- | ------------------------- | ----------------------------------- | ------------- |
| 1     | Database Schema           | Migration extending memory_items    | None          |
| 2     | Models & Config           | Write models, config settings       | None          |
| 3     | Redis Rate Limits         | Write-specific rate limiting        | None          |
| 4     | Memory Write Service      | Core create/delete/supersede/episode| Phase 1, 2, 3 |
| 5     | Agent Tools               | save_memory, delete_memory          | Phase 4       |
| 6     | Chat Service Integration  | Tools registered, episode trigger   | Phase 5       |
| 7     | Evaluation Framework      | Golden dataset, MLflow metrics      | Phase 6       |
| 8     | Tests & Validation        | Full coverage, manual checks        | Phase 7       |

**Critical Path**: (1 || 2 || 3) → 4 → 5 → 6 → 7 → 8

**Parallel Opportunities**:

- Phases 1, 2, 3 have no dependencies on each other — can all run in parallel
- Unit tests can be written alongside implementation in each phase

---

## Testing Strategy

### Test Pyramid

**Unit Tests** (70% of test effort):

- Memory write service: create, duplicate, rate limit, delete, supersede, episode, errors
- Tools: confidence routing, validation, response format
- Judge: precision/recall calculations
- Redis: write rate limit methods

**Integration Tests** (25% of test effort):

- End-to-end write via chat endpoint
- Correction and deletion flows
- Episode summarization trigger
- Rate limit enforcement

**Manual Validation** (5% of test effort):

- Response naturalness when acknowledging memories
- MLflow dashboard inspection
- Audit table verification

### Security Testing

**Critical — Cross-User Safety**:

- All write operations verify user_id matches
- Delete operations scoped by user_id
- Audit events include user_id
- Zero cross-user writes in security test suite (SC-008)

---

## Definition of Done

- [ ] All 8 phases completed
- [ ] All tests passing (unit + integration)
- [ ] Manual validation steps verified
- [ ] Memory write golden dataset with >=10 cases
- [ ] MLflow metrics logging functional
- [ ] Extraction Precision >= 85%
- [ ] Extraction Recall >= 70%
- [ ] False positive rate < 5%
- [ ] Zero cross-user memory writes
- [ ] Async persistence verified (writes don't block response)
- [ ] Code reviewed and merged
