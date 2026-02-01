# Implementation Plan: Memory v1 – Read-Only Recall

**Branch**: `004-memory-v1-readonly-recall` | **Date**: February 1, 2026 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-memory-v1-readonly-recall/spec.md`

## Summary

Enable safe, read-only retrieval of relevant past information to ground assistant responses. This includes durable conversation persistence (Postgres), hybrid memory retrieval (keyword + semantic via pgvector), an explicit `query_memory` tool for the Agent, Redis-based rate limiting and session state, and MLflow evaluation coverage. The `memory_items` table is **read-only at runtime**—items are manually seeded for testing; automatic extraction is deferred to Memory v2.

**Technical Approach**: Store conversations and messages in Postgres with embeddings generated via OpenAI text-embedding-3-small. Expose a `query_memory` tool to the Agent that performs hybrid search (full-text + vector similarity) with Reciprocal Rank Fusion (RRF) scoring. Enforce per-user scoping, token budget limits, and fail-closed semantics. Rate limit memory queries via Redis. Log all retrievals with correlation IDs for audit.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI, OpenAI Agents SDK, asyncpg, pgvector, Redis, tiktoken, MLflow
**Storage**: Postgres (pgvector extension), Redis (session state, rate limiting, embedding cache)
**Testing**: pytest (unit), integration tests against Docker services
**Target Platform**: Linux/Windows development, Docker for Postgres/Redis/MLflow
**Project Type**: Single (backend API + evaluation harness)
**Performance Goals**:

- Memory retrieval: <200ms p95 for up to 10,000 memory items (SC-001)
- Embedding generation: cached in Redis (7d TTL) to reduce API calls
- Rate limiting: 10 queries/minute per user (soft degradation)

**Constraints**:

- **Read-only memory_items**: No automatic writes to memory_items table at runtime
- Must reuse Feature 003 guardrails for content safety
- Must integrate with Feature 002 eval framework (no new eval loops)
- Must fail closed on retrieval errors (never hallucinate memories)
- Privacy: log query hash, not raw query content

**Scale/Scope**:

- 3 new database tables (conversations, messages, memory_items)
- 1 new Agent tool (query_memory)
- 3 new services (conversation, embedding, memory retrieval)
- Redis keys for session state, rate limiting, embedding cache
- Memory golden dataset for evaluation

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

✅ **I. Clarity over Cleverness**: Clear separation between conversation persistence, embedding generation, and memory retrieval. Hybrid search uses standard RRF algorithm. Tool contract is explicit and typed.

✅ **II. Evaluation-First Behavior**: Memory golden dataset enables retrieval quality testing. Recall@5, Precision@5, latency, and token budget metrics with regression gating. Integrates with Feature 002 MLflow framework.

✅ **III. Tool Safety and Correctness**: `query_memory` tool is read-only with mandatory user_id scoping. Fail-closed on errors. Rate limited. No cross-user data access possible.

✅ **IV. Privacy by Default**: Query content hashed in logs, not stored raw. Per-user memory scoping enforced at database level. Audit trail via correlation_id.

✅ **V. Consistent UX**: Memory cited as advisory context ("Based on what you mentioned..."), never as authoritative fact. Empty results on errors, no hallucinated memories.

✅ **VI. Performance and Cost Budgets**: Embedding cache reduces API calls. Token budget (1000 default) limits memory injection size. p95 latency target <200ms.

✅ **VII. Observability and Debuggability**: All retrievals logged with correlation_id, query_hash, result_count, latency_ms. MLflow tracks retrieval metrics over time.

✅ **VIII. Reproducible Environments**: All dependencies declared in pyproject.toml. Docker compose for Postgres (pgvector), Redis, MLflow. Seed data via migrations/fixtures.

**GATE STATUS**: ✅ PASSED - All principles satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/004-memory-v1-readonly-recall/
├── spec.md              # Feature specification (approved)
├── plan.md              # This file
├── tasks.md             # Task breakdown (generated)
└── research.md          # Phase 0: Technical unknowns (if needed)
```

### Source Code (repository root)

```text
src/
├── config.py                # MODIFIED: Add memory config (TOKEN_BUDGET, MIN_RELEVANCE, etc.)
├── models/
│   ├── request.py           # MODIFIED: Add user_id, conversation_id to ChatRequest
│   ├── response.py          # (no changes)
│   └── memory.py            # NEW: MemoryItem, MemoryQueryRequest, MemoryQueryResponse
├── services/
│   ├── chat_service.py      # MODIFIED: Attach query_memory tool, persist conversations
│   ├── conversation_service.py  # NEW: Conversation/message CRUD, persistence
│   ├── embedding_service.py # NEW: OpenAI embedding generation with caching
│   ├── memory_service.py    # NEW: Hybrid retrieval, RRF fusion, token budget
│   ├── redis_service.py     # NEW: Session state, rate limiting, embedding cache
│   ├── guardrails.py        # (no changes - reuse existing)
│   └── logging_service.py   # MODIFIED: Add memory retrieval logging
├── api/
│   ├── routes.py            # MODIFIED: Pass user_id to chat service
│   └── middleware.py        # (no changes)
└── tools/
    └── query_memory.py      # NEW: Agent tool definition for memory queries

migrations/
├── 001_create_conversations.sql  # NEW: conversations table
├── 002_create_messages.sql       # NEW: messages table with pgvector
├── 003_create_memory_items.sql   # NEW: memory_items table with pgvector
└── 004_seed_test_memories.sql    # NEW: Test data for manual seeding

docker/
├── docker-compose.api.yml       # MODIFIED: Add Postgres, Redis services
├── docker-compose.mlflow.yml    # (no changes)
└── init-pgvector.sql            # NEW: Enable pgvector extension

eval/
├── memory_golden_dataset.json   # NEW: Memory retrieval test cases
├── dataset.py                   # MODIFIED: Load memory dataset, validate schema
├── runner.py                    # MODIFIED: Compute memory metrics, MLflow logging
├── memory_judge.py              # NEW: Memory retrieval quality judge
└── models.py                    # MODIFIED: Add MemoryMetrics model

tests/
├── unit/
│   ├── test_memory_service.py       # NEW: Hybrid retrieval, RRF, token budget
│   ├── test_embedding_service.py    # NEW: Embedding generation, caching
│   ├── test_conversation_service.py # NEW: Conversation persistence
│   ├── test_redis_service.py        # NEW: Rate limiting, session state
│   └── test_memory_dataset.py       # NEW: Dataset schema validation
└── integration/
    ├── test_chat_endpoint.py        # MODIFIED: Add memory-grounded response tests
    ├── test_memory_retrieval.py     # NEW: End-to-end retrieval tests
    └── test_memory_eval.py          # NEW: Memory eval run verification
```

## Implementation Phases

### Phase 0: Infrastructure Setup

**Objective**: Set up Postgres with pgvector, Redis, and verify existing features functional.

**Tasks**:

1. Add Postgres service to docker-compose with pgvector extension
2. Add Redis service to docker-compose
3. Create database initialization script (enable pgvector)
4. Verify Feature 001 (streaming API) and Feature 003 (guardrails) functional
5. Add new dependencies to pyproject.toml (asyncpg, pgvector, redis, tiktoken)

**Acceptance Criteria**:

- `docker compose up` starts Postgres (pgvector enabled), Redis, and API
- `uv sync` installs all new dependencies
- Existing tests pass

**Deliverables**:

- Modified `docker/docker-compose.api.yml`
- New `docker/init-pgvector.sql`
- Modified `pyproject.toml`

---

### Phase 1: Database Schema & Migrations

**Objective**: Create conversations, messages, and memory_items tables with proper indexes.

**Tasks**:

1. Create `migrations/001_create_conversations.sql` with indexes
2. Create `migrations/002_create_messages.sql` with pgvector embedding column, FTS index
3. Create `migrations/003_create_memory_items.sql` with pgvector, FTS, soft delete
4. Create `migrations/004_seed_test_memories.sql` with test data for a test user
5. Add migration runner to apply SQL scripts on startup

**Acceptance Criteria**:

- All tables created with correct schema matching spec
- pgvector indexes (ivfflat) created for embedding columns
- GIN indexes created for full-text search
- Test memories seeded for user_id="test-user"

**Deliverables**:

- Migration SQL files
- Migration runner script or startup hook

---

### Phase 2: Core Services - Embedding & Redis

**Objective**: Implement embedding generation with caching and Redis services.

**Tasks**:

1. Create `src/services/embedding_service.py`:
   - `async def generate_embedding(text: str) -> list[float]` - Call OpenAI text-embedding-3-small
   - `async def get_cached_embedding(content_hash: str) -> list[float] | None` - Check Redis cache
   - `async def cache_embedding(content_hash: str, embedding: list[float])` - Store in Redis (7d TTL)
2. Create `src/services/redis_service.py`:
   - `async def get_session(user_id: str, conversation_id: str) -> dict` - Get session state
   - `async def set_session(user_id: str, conversation_id: str, state: dict)` - Store with 24h TTL
   - `async def check_rate_limit(user_id: str, limit: int = 10) -> bool` - Increment and check
   - `async def get_rate_limit_remaining(user_id: str) -> int` - Return remaining quota
3. Add config values to `src/config.py`:
   - `REDIS_URL`, `EMBEDDING_CACHE_TTL`, `SESSION_TTL`, `MEMORY_RATE_LIMIT`

**Acceptance Criteria**:

- Embedding generation works and caches results in Redis
- Rate limiting increments counter and enforces 10/minute limit
- Session state stores and retrieves correctly
- Redis unavailability logs warning but doesn't fail requests

**Testing Requirements**:

- Unit tests: mock OpenAI API, mock Redis
- Test cache hit/miss behavior
- Test rate limit enforcement

**Deliverables**:

- `src/services/embedding_service.py`
- `src/services/redis_service.py`
- Modified `src/config.py`
- Unit tests

---

### Phase 3: Conversation Persistence (User Story 2)

**Objective**: Implement durable conversation and message storage.

**Tasks**:

1. Create `src/models/memory.py`:
   - `Conversation`, `Message`, `MemoryItem` Pydantic models
   - `MemoryQueryRequest`, `MemoryQueryResponse` models
2. Create `src/services/conversation_service.py`:
   - `async def get_or_create_conversation(user_id: str, conversation_id: str | None) -> Conversation`
   - `async def add_message(conversation_id: str, role: str, content: str, correlation_id: str) -> Message`
   - `async def get_conversation_messages(conversation_id: str, limit: int = 20) -> list[Message]`
3. Modify `src/services/chat_service.py`:
   - Create/retrieve conversation at start of request
   - Persist user message before processing
   - Persist assistant response after streaming completes
4. Modify `src/api/routes.py`:
   - Accept optional `user_id` and `conversation_id` in request
   - Pass to chat service

**Acceptance Criteria**:

- User messages persisted to Postgres with embeddings
- Assistant responses persisted after stream completes
- Conversations retrievable across sessions
- Database unavailable → fail closed with error response

**Testing Requirements**:

- Unit tests: mock database, test CRUD operations
- Integration tests: verify persistence across API restarts

**Deliverables**:

- `src/models/memory.py`
- `src/services/conversation_service.py`
- Modified `src/services/chat_service.py`
- Modified `src/api/routes.py`
- Unit + integration tests

---

### Phase 4: Memory Retrieval Service (User Story 4)

**Objective**: Implement hybrid retrieval with keyword search, semantic search, and RRF fusion.

**Tasks**:

1. Create `src/services/memory_service.py`:
   - `async def keyword_search(user_id: str, query: str, limit: int) -> list[tuple[MemoryItem, int]]` - FTS with ts_rank, return (item, rank)
   - `async def semantic_search(user_id: str, embedding: list[float], limit: int) -> list[tuple[MemoryItem, int]]` - Cosine similarity, return (item, rank)
   - `async def hybrid_search(user_id: str, query: str, limit: int, min_score: float) -> list[MemoryItem]` - Combine with RRF
   - `def rrf_fusion(keyword_results: list, semantic_results: list, k: int = 60) -> list[MemoryItem]` - RRF algorithm
   - `def enforce_token_budget(items: list[MemoryItem], budget: int = 1000) -> list[MemoryItem]` - Truncate to budget
2. Add logging in `src/services/logging_service.py`:
   - `log_memory_retrieval(correlation_id, query_hash, result_count, latency_ms, truncated)`

**Acceptance Criteria**:

- Keyword search returns results ranked by ts_rank
- Semantic search returns results ranked by cosine similarity
- RRF fusion correctly combines rankings (k=60)
- Token budget enforced (default 1000 tokens)
- All retrievals logged with correlation_id, query_hash (not raw query)
- Errors return empty results (fail closed)

**Testing Requirements**:

- Unit tests: test each search mode independently, test RRF algorithm, test token budget
- Test with various query types (keyword-heavy, semantic-heavy, mixed)

**Deliverables**:

- `src/services/memory_service.py`
- Modified `src/services/logging_service.py`
- Unit tests

---

### Phase 5: Query Memory Tool (User Story 3)

**Objective**: Expose `query_memory` tool to the Agent via OpenAI Agents SDK.

**Tasks**:

1. Create `src/tools/query_memory.py`:
   - Define tool schema matching spec contract
   - Implement tool function that calls memory_service.hybrid_search
   - Apply rate limiting via redis_service
   - Format results for Agent consumption
2. Modify `src/services/chat_service.py`:
   - Import and attach `query_memory` tool to Agent: `Agent(tools=[query_memory], ...)`
   - Update system prompt with memory usage guidance
3. Handle tool errors gracefully:
   - Rate limit exceeded → return empty results with flag
   - Database error → return empty results with error flag
   - Timeout → return empty results

**Acceptance Criteria**:

- Agent can invoke `query_memory` tool during conversation
- Tool returns formatted memory items with relevance scores
- Rate limiting enforced (10/minute per user)
- Tool errors return empty results, Agent continues without memory

**Testing Requirements**:

- Unit tests: mock memory_service, test tool invocation
- Integration tests: verify Agent uses tool appropriately

**Deliverables**:

- `src/tools/query_memory.py`
- Modified `src/services/chat_service.py`
- Unit + integration tests

---

### Phase 6: Memory-Grounded Responses (User Story 1)

**Objective**: Ensure retrieved memories are incorporated appropriately in responses.

**Tasks**:

1. Update Agent system prompt in `src/services/chat_service.py`:
   - Add memory usage guidance from spec
   - Instruct Agent to cite memories as advisory context
2. Verify guardrails apply to retrieved memories:
   - Output guardrails validate final response including memory-derived content
3. Test end-to-end memory-grounded responses:
   - Seed memory, send query, verify response references memory appropriately

**Acceptance Criteria**:

- Responses cite retrieved memories naturally ("Based on what you mentioned...")
- No hallucinated memories when retrieval returns empty
- Guardrails apply to memory-grounded responses
- Multiple relevant memories synthesized appropriately

**Testing Requirements**:

- Integration tests: seed memories, query, verify response quality
- Manual validation of response naturalness

**Deliverables**:

- Modified `src/services/chat_service.py` (system prompt)
- Integration tests

---

### Phase 7: Evaluation Integration (User Story 5)

**Objective**: Create memory golden dataset and integrate with MLflow eval framework.

**Tasks**:

1. Create `eval/memory_golden_dataset.json`:
   - 15-25 test cases covering recall, precision, cross-user safety
   - Cases with setup_memories, query, expected_retrievals, rubric
   - Include edge cases: no matches, multiple matches, semantic-only matches
2. Create `eval/memory_judge.py`:
   - Judge for retrieval quality (did correct memories surface?)
   - Judge for citation quality (did response cite appropriately?)
3. Modify `eval/models.py`:
   - Add `MemoryMetrics` model: recall_at_5, precision_at_5, latency_p50, latency_p95, token_compliance, cross_user_safety
4. Modify `eval/runner.py`:
   - Support `--dataset memory` flag
   - Compute memory-specific metrics
   - Log to MLflow
   - Implement regression gating (Recall@5 ≥ 80%, Precision@5 ≥ 70%, cross-user = 0)
5. Modify `eval/dataset.py`:
   - Add `load_memory_dataset()` function
   - Validate memory dataset schema

**Acceptance Criteria**:

- `uv run python -m eval --dataset memory` runs successfully
- MLflow logs: recall_at_5, precision_at_5, latency metrics, token compliance
- Regression gate fails if thresholds not met
- Cross-user safety test passes (zero cross-user retrievals)

**Testing Requirements**:

- Unit tests: dataset schema validation, metric computation
- Integration tests: full eval run with MLflow logging

**Deliverables**:

- `eval/memory_golden_dataset.json`
- `eval/memory_judge.py`
- Modified `eval/models.py`, `eval/runner.py`, `eval/dataset.py`
- Unit + integration tests

---

### Phase 8: Tests & Validation

**Objective**: Comprehensive test coverage and validation.

**Unit Test Coverage**:

- `test_memory_service.py`: keyword search, semantic search, RRF fusion, token budget
- `test_embedding_service.py`: generation, caching, cache hits/misses
- `test_conversation_service.py`: CRUD operations, persistence
- `test_redis_service.py`: rate limiting, session state
- `test_memory_dataset.py`: schema validation, expected structure

**Integration Test Coverage**:

- `test_memory_retrieval.py`: end-to-end hybrid search
- `test_chat_endpoint.py`: memory-grounded responses
- `test_memory_eval.py`: full eval run with metrics

**Validation Steps** (manual):

1. Start services: `docker compose -f docker/docker-compose.api.yml up -d`
2. Verify Postgres with pgvector: `docker exec -it postgres psql -c "SELECT * FROM pg_extension WHERE extname='vector'"`
3. Seed test memories: run migration 004
4. Test memory retrieval:
   ```bash
   curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
     -d '{"message": "What package manager should I use?", "user_id": "test-user"}'
   # Expected: Response references "uv over pip" preference
   ```
5. Run memory eval:
   ```bash
   uv run python -m eval --dataset memory --verbose
   # Expected: Recall@5 ≥ 80%, Precision@5 ≥ 70%
   ```
6. Check MLflow: http://localhost:5000 - verify memory metrics logged
7. Verify logs: check for `memory_retrieval` events with correlation_id, no raw queries

**Deliverables**:

- Complete test suite
- Validation checklist completed

---

## Implementation Sequence Summary

| Phase | Focus                   | Key Deliverable                   | Blocker       |
| ----- | ----------------------- | --------------------------------- | ------------- |
| 0     | Infrastructure          | Postgres + Redis in Docker        | None          |
| 1     | Database Schema         | Tables + migrations               | Phase 0       |
| 2     | Embedding + Redis       | Caching, rate limiting            | Phase 1       |
| 3     | Conversation Persistence| Message storage (US2)             | Phase 2       |
| 4     | Memory Retrieval        | Hybrid search + RRF (US4)         | Phase 2       |
| 5     | Query Memory Tool       | Agent tool integration (US3)      | Phase 3, 4    |
| 6     | Memory-Grounded Responses| End-to-end flow (US1)            | Phase 5       |
| 7     | Evaluation              | MLflow metrics + gating (US5)     | Phase 6       |
| 8     | Tests + Validation      | Coverage, manual verification     | Phase 7       |

**Critical Path**: Phase 0 → 1 → 2 → (3 || 4) → 5 → 6 → 7 → 8

**Parallel Opportunities**:

- Phase 3 (Conversation Persistence) and Phase 4 (Memory Retrieval) can run in parallel after Phase 2
- Unit tests can be written in parallel with implementation

---

## Testing Strategy

### Test Pyramid

**Unit Tests** (70% of test effort):

- Memory service: search algorithms, RRF fusion, token budget
- Embedding service: generation, caching logic
- Conversation service: CRUD, persistence
- Redis service: rate limiting, session state
- Dataset validation

**Integration Tests** (25% of test effort):

- End-to-end retrieval through API
- Memory-grounded response quality
- Eval run with MLflow logging

**Manual Validation** (5% of test effort):

- Response naturalness review
- MLflow dashboard inspection
- Log privacy compliance check

### Privacy Testing

**Critical**: Verify raw queries NEVER logged.

**Test Cases**:

- `test_memory_logging_hashes_query()` - Assert logs contain query_hash, not raw query
- `test_no_raw_content_in_logs()` - Grep logs for test query text, expect no matches
- Manual log inspection after test runs

### Performance Testing

**Targets** (per spec success criteria):

- SC-001: Retrieval <200ms p95
- Token budget: 100% compliance

**Approach**:

- Add latency logging to retrieval functions
- Run eval with `--verbose` to capture timing
- Review MLflow metrics for latency percentiles

---

## Next Steps

### Immediate Actions

1. **Review this plan**: Stakeholder approval before implementation begins
2. **Environment setup**: Add Postgres/Redis to docker-compose
3. **Create feature branch**: Already on `004-memory-v1-readonly-recall`
4. **Generate tasks**: Create `tasks.md` with detailed task breakdown

### Definition of Done

- [ ] All 8 phases completed
- [ ] All tests passing (unit + integration)
- [ ] Manual validation steps verified
- [ ] Memory golden dataset with ≥15 cases
- [ ] MLflow metrics logging functional
- [ ] Recall@5 ≥ 80%, Precision@5 ≥ 70%
- [ ] Zero cross-user retrievals
- [ ] Logs comply with privacy constraints (no raw queries)
- [ ] Code reviewed and merged to main
