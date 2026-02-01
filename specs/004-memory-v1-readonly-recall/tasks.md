# Tasks: Memory v1 – Read-Only Recall

**Input**: Design documents from `/specs/004-memory-v1-readonly-recall/`
**Prerequisites**: plan.md, spec.md

**Organization**: Tasks are grouped by phase and user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US5)
- Include exact file paths in descriptions

---

## Phase 0: Infrastructure Setup

**Purpose**: Set up Postgres with pgvector, Redis, and verify existing features functional.

- [x] T001 Add Postgres service with pgvector to docker/docker-compose.api.yml (image: pgvector/pgvector:pg16, port 5432, volume for persistence)
- [x] T002 [P] Add Redis service to docker/docker-compose.api.yml (image: redis:7-alpine, port 6379)
- [x] T003 Create docker/init-pgvector.sql with `CREATE EXTENSION IF NOT EXISTS vector;`
- [x] T004 Add new dependencies to pyproject.toml: asyncpg, pgvector, redis, tiktoken
- [x] T005 Run `uv sync` and verify all dependencies install correctly
- [x] T006 Verify Feature 001 streaming API functional: `docker compose up -d && curl http://localhost:8000/health`
- [x] T007 Verify Feature 003 guardrails functional: `uv run pytest tests/unit/test_guardrails.py -v`

**Checkpoint**: Infrastructure ready - Postgres, Redis, and existing features operational.

---

## Phase 1: Database Schema & Migrations

**Purpose**: Create database tables with proper indexes for conversations, messages, and memory items.

- [x] T008 Create migrations/ directory at repository root
- [x] T009 Create migrations/001_create_conversations.sql with conversations table schema per spec (id, user_id, title, created_at, updated_at) and indexes
- [x] T010 Create migrations/002_create_messages.sql with messages table schema per spec (id, conversation_id, role, content, embedding VECTOR(1536), correlation_id, created_at) and indexes (FK, ivfflat, GIN for FTS)
- [x] T011 Create migrations/003_create_memory_items.sql with memory_items table schema per spec (id, user_id, content, type, embedding, source_message_id, importance, created_at, expires_at, deleted_at) and indexes
- [x] T012 Create migrations/004_seed_test_memories.sql with 5-10 test memory items for user_id='test-user' covering all types (fact, preference, decision, note)
- [x] T013 Create src/database.py with async connection pool (asyncpg) and migration runner function
- [x] T014 Add database initialization to src/main.py lifespan: run migrations on startup
- [x] T015 Verify migrations run successfully: `docker compose up -d` and check tables exist via psql

**Checkpoint**: Database schema complete - all tables created with correct indexes.

---

## Phase 2: Core Services - Embedding & Redis

**Purpose**: Implement embedding generation with caching and Redis services for rate limiting and session state.

### Configuration

- [x] T016 Add memory config to src/config.py: REDIS_URL, POSTGRES_URL, EMBEDDING_MODEL (text-embedding-3-small), TOKEN_BUDGET (1000), MIN_RELEVANCE (0.3), MAX_RESULTS (10), MEMORY_RATE_LIMIT (10), EMBEDDING_CACHE_TTL (604800), SESSION_TTL (86400)

### Redis Service

- [x] T017 Create src/services/redis_service.py with RedisService class and async connection pool
- [x] T018 Implement `async def get_session(user_id: str, conversation_id: str) -> dict | None` in redis_service.py - retrieve session hash
- [x] T019 Implement `async def set_session(user_id: str, conversation_id: str, state: dict)` in redis_service.py - store with SESSION_TTL
- [x] T020 Implement `async def check_rate_limit(user_id: str, limit: int) -> tuple[bool, int]` in redis_service.py - increment counter, return (allowed, remaining)
- [x] T021 Implement `async def get_cached_embedding(content_hash: str) -> list[float] | None` in redis_service.py
- [x] T022 Implement `async def cache_embedding(content_hash: str, embedding: list[float])` in redis_service.py with EMBEDDING_CACHE_TTL
- [x] T023 Add graceful degradation: Redis unavailable → log warning, return None/True (don't block requests)

### Embedding Service

- [x] T024 Create src/services/embedding_service.py with EmbeddingService class
- [x] T025 Implement `async def generate_embedding(text: str) -> list[float]` in embedding_service.py - call OpenAI text-embedding-3-small API
- [x] T026 Implement `async def get_embedding(text: str) -> list[float]` in embedding_service.py - check cache first, generate if miss, cache result
- [x] T027 Add query preprocessing: truncate to 8192 chars, compute content_hash (SHA256)
- [x] T028 Add graceful degradation: OpenAI API timeout → return None, log error

### Tests for Phase 2

- [x] T029 [P] Create tests/unit/test_redis_service.py with test_check_rate_limit_allows_under_limit() - mock Redis, verify returns (True, remaining)
- [x] T030 [P] Add test_check_rate_limit_blocks_over_limit() to tests/unit/test_redis_service.py - verify returns (False, 0) after limit exceeded
- [x] T031 [P] Add test_session_storage_and_retrieval() to tests/unit/test_redis_service.py - verify round-trip
- [x] T032 [P] Add test_redis_unavailable_graceful_degradation() to tests/unit/test_redis_service.py - mock connection error, verify no exception raised
- [x] T033 [P] Create tests/unit/test_embedding_service.py with test_generate_embedding_calls_openai() - mock OpenAI, verify API called
- [x] T034 [P] Add test_get_embedding_cache_hit() to tests/unit/test_embedding_service.py - mock cache hit, verify no API call
- [x] T035 [P] Add test_get_embedding_cache_miss() to tests/unit/test_embedding_service.py - mock cache miss, verify API called and result cached

**Checkpoint**: Core services ready - embedding generation and Redis operations functional.

---

## Phase 3: Conversation Persistence (User Story 2 - P1 MVP)

**Purpose**: Implement durable conversation and message storage.

### Models

- [x] T036 [US2] Create src/models/memory.py with Conversation Pydantic model (id, user_id, title, created_at, updated_at)
- [x] T037 [US2] Add Message Pydantic model to src/models/memory.py (id, conversation_id, role, content, embedding, correlation_id, created_at)
- [x] T038 [US2] Add MemoryItem Pydantic model to src/models/memory.py (id, user_id, content, type, relevance_score, source, created_at, importance)
- [x] T039 [US2] Add MemoryQueryRequest model to src/models/memory.py (user_id, query, limit, types, min_score)
- [x] T040 [US2] Add MemoryQueryResponse model to src/models/memory.py (items, total_count, query_embedding_ms, retrieval_ms, token_count, truncated)

### Conversation Service

- [x] T041 [US2] Create src/services/conversation_service.py with ConversationService class
- [x] T042 [US2] Implement `async def get_or_create_conversation(user_id: str, conversation_id: str | None) -> Conversation` in conversation_service.py
- [x] T043 [US2] Implement `async def add_message(conversation_id: UUID, role: str, content: str, correlation_id: UUID, embedding: list[float] | None) -> Message` in conversation_service.py
- [x] T044 [US2] Implement `async def get_conversation_messages(conversation_id: UUID, limit: int = 20) -> list[Message]` in conversation_service.py
- [x] T045 [US2] Add database error handling: connection failure → raise explicit exception (fail closed)

### Integration with Chat Service

- [x] T046 [US2] Modify src/models/request.py: add optional user_id and conversation_id fields to ChatRequest
- [x] T047 [US2] Modify src/api/routes.py POST /chat: extract user_id and conversation_id from request, pass to chat_service
- [x] T048 [US2] Modify src/services/chat_service.py: accept user_id and conversation_id parameters
- [x] T049 [US2] In chat_service.py stream_completion(): call get_or_create_conversation() at start
- [x] T050 [US2] In chat_service.py stream_completion(): persist user message with embedding before Agent processing
- [x] T051 [US2] In chat_service.py stream_completion(): accumulate assistant response, persist after streaming completes

### Tests for User Story 2

- [x] T052 [P] [US2] Create tests/unit/test_conversation_service.py with test_get_or_create_conversation_creates_new() - mock DB, verify INSERT called
- [x] T053 [P] [US2] Add test_get_or_create_conversation_returns_existing() to tests/unit/test_conversation_service.py - mock existing row, verify no INSERT
- [x] T054 [P] [US2] Add test_add_message_persists_correctly() to tests/unit/test_conversation_service.py - verify all fields stored
- [x] T055 [P] [US2] Add test_database_unavailable_raises_exception() to tests/unit/test_conversation_service.py - mock connection error, verify exception
- [x] T056 [US2] Create tests/integration/test_conversation_persistence.py with test_message_persisted_after_request() - send message, query DB, verify row exists
- [x] T057 [US2] Add test_conversation_survives_restart() to tests/integration/test_conversation_persistence.py - send message, restart container, verify data persists

**Checkpoint**: User Story 2 complete - conversations and messages persisted durably.

---

## Phase 4: Memory Retrieval Service (User Story 4 - P2)

**Purpose**: Implement hybrid retrieval with keyword search, semantic search, and RRF fusion.

### Memory Service

- [x] T058 [US4] Create src/services/memory_service.py with MemoryService class
- [x] T059 [US4] Implement `async def keyword_search(user_id: str, query: str, limit: int = 20) -> list[tuple[MemoryItem, int]]` in memory_service.py - FTS with ts_rank, return (item, rank)
- [x] T060 [US4] Implement `async def semantic_search(user_id: str, embedding: list[float], limit: int = 20) -> list[tuple[MemoryItem, int]]` in memory_service.py - cosine similarity via pgvector, return (item, rank)
- [x] T061 [US4] Implement `def rrf_fusion(keyword_results: list, semantic_results: list, k: int = 60) -> list[MemoryItem]` in memory_service.py - standard RRF algorithm
- [x] T062 [US4] Implement `def count_tokens(text: str) -> int` in memory_service.py - use tiktoken cl100k_base
- [x] T063 [US4] Implement `def enforce_token_budget(items: list[MemoryItem], budget: int) -> tuple[list[MemoryItem], bool]` in memory_service.py - return (truncated_items, was_truncated)
- [x] T064 [US4] Implement `async def hybrid_search(request: MemoryQueryRequest) -> MemoryQueryResponse` in memory_service.py - orchestrate full flow: embed query → parallel search → RRF → filter min_score → enforce budget
- [x] T065 [US4] Add mandatory user_id filtering in ALL queries (WHERE user_id = $1) - CRITICAL for security
- [x] T066 [US4] Add graceful degradation: database error → return empty MemoryQueryResponse with error logged

### Logging

- [x] T067 [US4] Add `log_memory_retrieval()` function to src/services/logging_service.py with fields: correlation_id, query_hash (SHA256, NOT raw query), result_count, latency_ms, truncated
- [x] T068 [US4] Call log_memory_retrieval() in memory_service.py hybrid_search() after retrieval completes

### Tests for User Story 4

- [x] T069 [P] [US4] Create tests/unit/test_memory_service.py with test_keyword_search_returns_ranked_results() - mock DB, verify ts_rank ordering
- [x] T070 [P] [US4] Add test_semantic_search_returns_ranked_results() to tests/unit/test_memory_service.py - mock DB, verify cosine similarity ordering
- [x] T071 [P] [US4] Add test_rrf_fusion_combines_rankings() to tests/unit/test_memory_service.py - provide known inputs, verify RRF scores correct
- [x] T072 [P] [US4] Add test_rrf_fusion_handles_disjoint_results() to tests/unit/test_memory_service.py - items only in one list still ranked
- [x] T073 [P] [US4] Add test_enforce_token_budget_truncates() to tests/unit/test_memory_service.py - verify items removed when over budget
- [x] T074 [P] [US4] Add test_enforce_token_budget_returns_truncated_flag() to tests/unit/test_memory_service.py - verify boolean flag
- [x] T075 [P] [US4] Add test_hybrid_search_enforces_user_id_filter() to tests/unit/test_memory_service.py - verify user_id in WHERE clause (CRITICAL)
- [x] T076 [P] [US4] Add test_hybrid_search_filters_by_min_score() to tests/unit/test_memory_service.py - verify low-score items excluded
- [x] T077 [P] [US4] Add test_database_error_returns_empty_response() to tests/unit/test_memory_service.py - mock error, verify empty response
- [x] T078 [US4] Create tests/integration/test_memory_retrieval.py with test_hybrid_search_returns_relevant_memories() - seed data, query, verify correct items returned

**Checkpoint**: User Story 4 complete - hybrid retrieval with RRF fusion operational.

---

## Phase 5: Query Memory Tool (User Story 3 - P2)

**Purpose**: Expose `query_memory` tool to the Agent via OpenAI Agents SDK.

### Tool Implementation

- [x] T079 [US3] Create src/tools/ directory
- [x] T080 [US3] Create src/tools/query_memory.py with tool function definition
- [x] T081 [US3] Define tool schema in query_memory.py matching spec: name="query_memory", parameters (query: str required, types: list[str] optional)
- [x] T082 [US3] Implement tool function: extract user_id from context, call memory_service.hybrid_search(), format response
- [x] T083 [US3] Add rate limiting check in tool function: call redis_service.check_rate_limit(), return empty if exceeded
- [x] T084 [US3] Format tool response per spec: memories array (content, type, relevance, context) + metadata (count, truncated)
- [x] T085 [US3] Handle tool errors: catch exceptions, return empty memories with error flag, log error

### Agent Integration

- [x] T086 [US3] Modify src/services/chat_service.py: import query_memory tool
- [x] T087 [US3] In chat_service.py create_agent(): attach tool via `Agent(tools=[query_memory], ...)`
- [x] T088 [US3] Add user_id to tool context so tool function can access it

### Tests for User Story 3

- [x] T089 [P] [US3] Create tests/unit/test_query_memory_tool.py with test_tool_calls_memory_service() - mock memory_service, verify hybrid_search called
- [x] T090 [P] [US3] Add test_tool_formats_response_correctly() to tests/unit/test_query_memory_tool.py - verify output matches spec schema
- [x] T091 [P] [US3] Add test_tool_rate_limit_returns_empty() to tests/unit/test_query_memory_tool.py - mock rate limit exceeded, verify empty response
- [x] T092 [P] [US3] Add test_tool_error_returns_empty_with_flag() to tests/unit/test_query_memory_tool.py - mock exception, verify graceful degradation
- [x] T093 [US3] Add test_agent_can_invoke_query_memory() to tests/integration/test_memory_retrieval.py - verify Agent tool invocation works

**Checkpoint**: User Story 3 complete - Agent can invoke query_memory tool.

---

## Phase 6: Memory-Grounded Responses (User Story 1 - P1 MVP)

**Purpose**: Ensure retrieved memories are incorporated appropriately in responses.

### System Prompt

- [x] T094 [US1] Create memory usage guidance text in src/services/chat_service.py matching spec (when to use memory, how to cite)
- [x] T095 [US1] Modify create_agent() in chat_service.py: append memory guidance to system prompt

### Guardrail Integration

- [x] T096 [US1] Verify output guardrails in src/services/guardrails.py apply to memory-grounded responses (no code changes expected, just verification)
- [x] T097 [US1] Add test case to verify guardrails check memory-derived content

### Tests for User Story 1

- [x] T098 [US1] Create tests/integration/test_memory_grounded_response.py with test_response_references_retrieved_memory() - seed memory, query, verify response mentions memory content
- [x] T099 [US1] Add test_response_cites_memory_naturally() to tests/integration/test_memory_grounded_response.py - verify phrasing like "Based on what you mentioned..."
- [x] T100 [US1] Add test_no_hallucinated_memories_when_empty() to tests/integration/test_memory_grounded_response.py - query with no matching memories, verify no fabricated references
- [x] T101 [US1] Add test_multiple_memories_synthesized() to tests/integration/test_memory_grounded_response.py - seed multiple relevant memories, verify response incorporates multiple

**Checkpoint**: User Story 1 complete - memory-grounded responses working end-to-end.

---

## Phase 7: Evaluation Integration (User Story 5 - P3)

**Purpose**: Create memory golden dataset and integrate with MLflow eval framework.

### Golden Dataset

- [x] T102 [US5] Create eval/memory_golden_dataset.json with version, description, and empty cases array
- [x] T103 [US5] Add 5 recall test cases to memory_golden_dataset.json: setup_memories, query, expected_retrievals, rubric
- [x] T104 [US5] Add 5 precision test cases to memory_golden_dataset.json: queries with multiple potential matches
- [x] T105 [US5] Add 3 edge case tests to memory_golden_dataset.json: no matches, semantic-only match, keyword-only match
- [x] T106 [US5] Add 2 cross-user security cases to memory_golden_dataset.json: verify user A cannot retrieve user B's memories

### Eval Models

- [x] T107 [US5] Add MemoryTestCase model to eval/models.py: id, setup_memories, query, expected_retrievals, rubric, user_id
- [x] T108 [US5] Add MemoryMetrics model to eval/models.py: recall_at_5, precision_at_5, latency_p50, latency_p95, token_compliance, cross_user_violations

### Dataset Loading

- [x] T109 [US5] Add `load_memory_dataset(filepath: str) -> list[MemoryTestCase]` function to eval/dataset.py
- [x] T110 [US5] Add schema validation in load_memory_dataset(): required fields (id, setup_memories, query, expected_retrievals)

### Memory Judge

- [x] T111 [US5] Create eval/memory_judge.py with MemoryJudge class
- [x] T112 [US5] Implement `def evaluate_recall(retrieved: list[str], expected: list[str], k: int = 5) -> float` in memory_judge.py
- [x] T113 [US5] Implement `def evaluate_precision(retrieved: list[str], expected: list[str], k: int = 5) -> float` in memory_judge.py
- [x] T114 [US5] Implement `def check_cross_user_violation(retrieved_user_ids: list[str], expected_user_id: str) -> bool` in memory_judge.py

### Runner Integration

- [x] T115 [US5] Modify eval/runner.py: add `--dataset memory` flag support
- [x] T116 [US5] In runner.py: implement memory eval flow - seed memories, run queries, collect results
- [x] T117 [US5] In runner.py: compute recall@5, precision@5 using memory_judge
- [x] T118 [US5] In runner.py: compute latency_p50, latency_p95 from retrieval timing
- [x] T119 [US5] In runner.py: compute token_compliance (% of retrievals within budget)
- [x] T120 [US5] In runner.py: log metrics to MLflow: `mlflow.log_metric("memory_recall_at_5", ...)`, etc.
- [x] T121 [US5] Implement regression gating in runner.py: exit code 1 if recall@5 < 0.80 OR precision@5 < 0.70 OR cross_user_violations > 0

### Tests for User Story 5

- [x] T122 [P] [US5] Create tests/unit/test_memory_dataset.py with test_load_memory_dataset_parses_json() - verify parsing works
- [x] T123 [P] [US5] Add test_memory_dataset_schema_validation() to tests/unit/test_memory_dataset.py - verify required fields checked
- [x] T124 [P] [US5] Add test_evaluate_recall_correct_calculation() to tests/unit/test_memory_judge.py - verify formula
- [x] T125 [P] [US5] Add test_evaluate_precision_correct_calculation() to tests/unit/test_memory_judge.py - verify formula
- [x] T126 [P] [US5] Add test_cross_user_violation_detected() to tests/unit/test_memory_judge.py - verify detection works
- [ ] T127 [US5] Create tests/integration/test_memory_eval.py with test_full_memory_eval_run() - run `python -m eval --dataset memory`, verify exit code and MLflow metrics

**Checkpoint**: User Story 5 complete - memory evaluation integrated with MLflow.

---

## Phase 8: Polish & Validation

**Purpose**: Final testing, validation, and cleanup.

### Additional Tests

- [ ] T128 [P] Add test_memory_logging_hashes_query() to tests/unit/test_logging.py - verify query_hash logged, not raw query
- [ ] T129 [P] Add test_memory_retrieval_includes_correlation_id() to tests/unit/test_memory_service.py - verify correlation_id in logs
- [ ] T130 [P] Add test_empty_memory_store_no_errors() to tests/integration/test_memory_retrieval.py - first-time user, verify graceful handling

### Validation

- [ ] T131 Start all services: `docker compose -f docker/docker-compose.api.yml up -d`
- [ ] T132 Verify Postgres pgvector: `docker exec postgres psql -U postgres -c "SELECT extname FROM pg_extension WHERE extname='vector'"`
- [ ] T133 Verify tables created: `docker exec postgres psql -U postgres -c "\dt"` - should show conversations, messages, memory_items
- [ ] T134 Run migrations including seed data: verify test-user has memory items
- [ ] T135 Test memory-grounded response manually:
      ```
      curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
        -d '{"message": "What package manager should I use?", "user_id": "test-user"}'
      ```
      Verify response references "uv over pip" preference
- [ ] T136 Run memory eval: `uv run python -m eval --dataset memory --verbose`
      Verify: Recall@5 ≥ 80%, Precision@5 ≥ 70%, exit code 0
- [ ] T137 Check MLflow UI at http://localhost:5000 - verify memory metrics logged
- [ ] T138 Verify log privacy: grep logs for test query text, expect no raw queries found
- [ ] T139 Run full test suite: `uv run pytest tests/ -v --cov=src --cov=eval` - verify ≥85% coverage on new code
- [ ] T140 Code review: verify user_id scoping in all queries, no cross-user data access possible

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 0 (Infrastructure)**: No dependencies - setup first
- **Phase 1 (Database)**: Depends on Phase 0 (needs Postgres running)
- **Phase 2 (Embedding + Redis)**: Depends on Phase 1 (needs tables for context)
- **Phase 3 (Conversation Persistence)**: Depends on Phase 2 (needs embedding service)
- **Phase 4 (Memory Retrieval)**: Depends on Phase 2 (needs embedding service) - CAN RUN PARALLEL WITH PHASE 3
- **Phase 5 (Query Memory Tool)**: Depends on Phase 3 AND Phase 4
- **Phase 6 (Memory-Grounded Responses)**: Depends on Phase 5
- **Phase 7 (Evaluation)**: Depends on Phase 6
- **Phase 8 (Validation)**: Depends on Phase 7

### User Story Dependencies

- **US2 (Conversation Persistence)**: Foundation - no story dependencies
- **US4 (Hybrid Retrieval)**: Foundation - no story dependencies, can parallel with US2
- **US3 (Query Memory Tool)**: Depends on US2 (needs conversation context) and US4 (needs retrieval)
- **US1 (Memory-Grounded Response)**: Depends on US3 (needs tool working)
- **US5 (Evaluation)**: Depends on US1 (needs full flow working)

### Parallel Opportunities Per Phase

**Phase 0**: T001, T002 can run in parallel (different services)

**Phase 1**: T009, T010, T011 can run in parallel (different SQL files)

**Phase 2**:
- T017-T023 (Redis) and T024-T028 (Embedding) can run in parallel
- All test tasks (T029-T035) can run in parallel

**Phase 3**: All test tasks (T052-T055) can run in parallel

**Phase 4**: All test tasks (T069-T077) can run in parallel

**Phase 5**: All test tasks (T089-T092) can run in parallel

**Phase 7**: T102-T106 (dataset cases) are sequential; T122-T126 (tests) can run in parallel

**Phase 8**: T128-T130 can run in parallel; T131-T140 should run sequentially (validation steps)

---

## Task Count Summary

| Phase | Description               | Tasks | Parallel |
| ----- | ------------------------- | ----- | -------- |
| 0     | Infrastructure Setup      | 7     | 2        |
| 1     | Database Schema           | 8     | 3        |
| 2     | Embedding + Redis         | 20    | 9        |
| 3     | Conversation Persistence  | 22    | 6        |
| 4     | Memory Retrieval          | 21    | 11       |
| 5     | Query Memory Tool         | 15    | 5        |
| 6     | Memory-Grounded Responses | 8     | 1        |
| 7     | Evaluation Integration    | 26    | 6        |
| 8     | Polish & Validation       | 13    | 3        |
| **Total** |                       | **140** | **46** |

### By User Story

- **US1 (Memory-Grounded Response)**: 8 tasks
- **US2 (Conversation Persistence)**: 22 tasks
- **US3 (Query Memory Tool)**: 15 tasks
- **US4 (Hybrid Retrieval)**: 21 tasks
- **US5 (Evaluation)**: 26 tasks
- **Infrastructure/Shared**: 48 tasks

### Test Tasks

- **Unit Tests**: 38 tasks
- **Integration Tests**: 12 tasks
- **Validation**: 10 tasks
- **Total Test/Validation**: 60 tasks (43% of all tasks)

---

## MVP Scope Recommendation

**Recommended MVP**: Complete Phases 0-6 (US1, US2, US3, US4)

**Rationale**:
- Delivers core user capability: memory-grounded responses
- Includes foundational infrastructure (Postgres, Redis, migrations)
- Full hybrid retrieval with RRF fusion
- Agent tool integration working
- Evaluation (Phase 7) can follow as fast-follow

**MVP Task Count**: 101 tasks (Phases 0-6)

**Post-MVP**: Phase 7 (Evaluation) + Phase 8 (Validation) = 39 tasks

---

## Critical Security Tasks

**MUST NOT SKIP - Cross-User Safety**:

- T065: Mandatory user_id filtering in ALL queries
- T075: Test user_id filter enforcement
- T106: Cross-user security test cases in dataset
- T114: Cross-user violation detection in judge
- T121: Regression gate on cross-user violations
- T140: Code review for user_id scoping

---

## Notes

- [P] tasks = different files, no dependencies - can run in parallel
- [Story] label maps task to specific user story (US1-US5)
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
- **memory_items table is READ-ONLY** - only seeded via migrations, never written at runtime
- Privacy critical: verify NO raw queries logged, only query_hash
