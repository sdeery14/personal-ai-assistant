# Tasks: Memory v2 – Automatic Writes

**Input**: Design documents from `/specs/006-memory-auto-writes/`
**Prerequisites**: plan.md, spec.md

**Organization**: Tasks are grouped by phase. Each task maps to spec requirements (FR/SC) where applicable.

## Format: `[ID] [P?] [US?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[US]**: Which user story this task belongs to (US1-US6)
- Include exact file paths in descriptions

---

## Phase 1: Database Schema Extension

**Purpose**: Extend memory_items table and create audit table for write operations.

- [ ] T001 Create migrations/005_memory_auto_writes.sql with ALTER TABLE memory_items ADD COLUMN IF NOT EXISTS for: source_conversation_id (UUID FK conversations), confidence (FLOAT DEFAULT 1.0), superseded_by (UUID FK memory_items), status (VARCHAR DEFAULT 'active')
- [ ] T002 In migrations/005_memory_auto_writes.sql: DROP existing type CHECK constraint on memory_items, recreate with 'episode' added to allowed values (fact, preference, decision, note, episode) [FR-002]
- [ ] T003 In migrations/005_memory_auto_writes.sql: CREATE TABLE IF NOT EXISTS memory_write_events (id UUID PK, memory_item_id UUID FK, user_id VARCHAR NOT NULL, operation VARCHAR CHECK IN create/supersede/delete, confidence FLOAT, extraction_type VARCHAR, before_content TEXT, after_content TEXT, correlation_id UUID, processing_time_ms INT, created_at TIMESTAMPTZ) [FR-011]
- [ ] T004 In migrations/005_memory_auto_writes.sql: CREATE INDEX IF NOT EXISTS idx_memory_write_events_user ON memory_write_events(user_id) and idx_memory_write_events_memory ON memory_write_events(memory_item_id) and idx_memory_items_superseded_by ON memory_items(superseded_by) WHERE superseded_by IS NOT NULL
- [ ] T005 Verify migration runs idempotently: `docker compose up -d` and confirm schema changes applied without data loss

**Checkpoint**: Schema extended — memory_items has new columns, audit table exists.

---

## Phase 2: Models & Config

**Purpose**: Extend data models and add configuration settings for memory writes.

### Models

- [ ] T006 [P] Add EPISODE = "episode" to MemoryType enum in src/models/memory.py [FR-002]
- [ ] T007 [P] Add optional fields to MemoryItem in src/models/memory.py: source_conversation_id (Optional[UUID]), confidence (float, default=1.0), superseded_by (Optional[UUID]), status (str, default="active") [FR-004, FR-013]
- [ ] T008 Create MemoryWriteRequest model in src/models/memory.py: user_id (str), content (str, max 2000), type (MemoryType), confidence (float 0-1, default=0.8), source_message_id (Optional[UUID]), source_conversation_id (Optional[UUID]), importance (float 0-1, default=0.5) [FR-001, FR-004]
- [ ] T009 [P] Create MemoryDeleteRequest model in src/models/memory.py: user_id (str), query (str), reason (Optional[str]) [FR-008]
- [ ] T010 [P] Create MemoryWriteResponse model in src/models/memory.py: success (bool), memory_id (Optional[UUID]), action (str: created/duplicate_skipped/rate_limited/queued/confirm_needed/discarded), message (str)
- [ ] T011 [P] Create MemoryWriteEvent model in src/models/memory.py: id (UUID), memory_item_id (Optional[UUID]), user_id (str), operation (str), confidence (Optional[float]), extraction_type (Optional[str]), before_content (Optional[str]), after_content (Optional[str]), correlation_id (Optional[UUID]), processing_time_ms (Optional[int]), created_at (datetime) [FR-011]

### Config

- [ ] T012 Add memory write config to src/config.py: memory_write_rate_per_conversation (int=10), memory_write_rate_per_hour (int=25), memory_duplicate_threshold (float=0.92), episode_user_message_threshold (int=8), episode_total_message_threshold (int=15), memory_write_confidence_auto (float=0.7), memory_write_confidence_confirm (float=0.5) [FR-001, FR-006, FR-010, FR-012]

**Checkpoint**: Models and config ready for service layer.

---

## Phase 3: Redis Rate Limiting Extensions

**Purpose**: Add write-specific rate limiting to support FR-012.

- [ ] T013 Implement `async def check_write_rate_limit_conversation(conversation_id: str, limit: int = 10) -> tuple[bool, int]` in src/services/redis_service.py using key pattern `memory_write:conv:{conversation_id}`, no TTL (conversation-scoped) [FR-012]
- [ ] T014 Implement `async def check_write_rate_limit_hourly(user_id: str, limit: int = 25) -> tuple[bool, int]` in src/services/redis_service.py using key pattern `memory_write:hourly:{user_id}`, TTL 3600s [FR-012]
- [ ] T015 Add graceful degradation for both methods: Redis unavailable → return (True, -1), log warning

### Tests

- [ ] T016 [P] Create test_check_write_rate_limit_conversation_allows() in tests/unit/test_redis_service.py — mock Redis, verify returns (True, remaining)
- [ ] T017 [P] Create test_check_write_rate_limit_conversation_blocks() in tests/unit/test_redis_service.py — exceed limit, verify returns (False, 0)
- [ ] T018 [P] Create test_check_write_rate_limit_hourly_allows() in tests/unit/test_redis_service.py — under limit
- [ ] T019 [P] Create test_check_write_rate_limit_hourly_blocks() in tests/unit/test_redis_service.py — exceed limit
- [ ] T020 [P] Create test_write_rate_limit_redis_unavailable() in tests/unit/test_redis_service.py — mock error, verify graceful degradation

**Checkpoint**: Write rate limiting ready.

---

## Phase 4: Memory Write Service

**Purpose**: Core service for creating, deleting, and superseding memories.

### Service Implementation

- [ ] T021 Create src/services/memory_write_service.py with MemoryWriteService class (instantiates EmbeddingService, MemoryService, RedisService, gets Settings)
- [ ] T022 [US1] Implement `async def create_memory(request: MemoryWriteRequest, correlation_id: UUID) -> MemoryWriteResponse` — check rate limits → generate embedding → check duplicate → INSERT memory_items → INSERT memory_write_events → return response [FR-001, FR-004, FR-011]
- [ ] T023 [US1] Implement duplicate detection in create_memory(): generate embedding for new content, query memory_items WHERE user_id = request.user_id AND status = 'active' with cosine similarity > config.memory_duplicate_threshold (0.92), skip if match found [FR-014]
- [ ] T024 [US3] Implement `async def delete_memory(user_id: str, query: str, correlation_id: UUID) -> list[dict]` — call MemoryService.hybrid_search() with query → soft-delete matching memories (UPDATE status='deleted', deleted_at=NOW()) → INSERT memory_write_events → return deleted items [FR-008, FR-009]
- [ ] T025 [US3] Implement `async def supersede_memory(old_memory_id: UUID, new_request: MemoryWriteRequest, correlation_id: UUID) -> MemoryWriteResponse` — UPDATE old memory SET status='superseded', superseded_by=new_id → INSERT new memory → INSERT two audit events [FR-007, FR-013]
- [ ] T026 [US4] Implement `async def create_episode_summary(conversation_id: UUID, user_id: str, correlation_id: UUID) -> Optional[MemoryWriteResponse]` — fetch messages via ConversationService → check threshold (8+ user msgs OR 15+ total) → check Redis flag `episode:generated:{conversation_id}` → call OpenAI completion with summarization prompt → create EPISODE memory → set Redis flag → return [FR-010]
- [ ] T027 Add user_id scoping to ALL write queries: every INSERT and UPDATE includes WHERE user_id = $N [FR-015]
- [ ] T028 Add fail-closed error handling: wrap all DB operations in try/except, log error with correlation_id, return failure response [FR-016]

### Background Task Management

- [ ] T029 Add module-level `_pending_tasks: set[asyncio.Task]` to memory_write_service.py
- [ ] T030 Implement `schedule_write(coro)` — create task, add to _pending_tasks, register done callback for cleanup [FR-017]
- [ ] T031 Implement `async def await_pending_writes(timeout: float = 5.0)` — asyncio.wait on _pending_tasks with timeout, for shutdown

### Tests

- [ ] T032 [P] Create tests/unit/test_memory_write_service.py with test_create_memory_success() — mock DB + embedding, verify INSERT called and audit event created
- [ ] T033 [P] Add test_create_memory_duplicate_detected() — mock semantic search returning high similarity, verify skip and "duplicate_skipped" response
- [ ] T034 [P] Add test_create_memory_rate_limited_conversation() — mock Redis at limit, verify "rate_limited" response
- [ ] T035 [P] Add test_create_memory_rate_limited_hourly() — mock Redis hourly at limit, verify rejection
- [ ] T036 [P] Add test_delete_memory_success() — mock search returning match, verify soft-delete UPDATE and audit event
- [ ] T037 [P] Add test_delete_memory_no_match() — mock search returning empty, verify no changes
- [ ] T038 [P] Add test_supersede_memory_creates_chain() — verify old marked superseded, new created, both audited
- [ ] T039 [P] Add test_create_memory_db_error_fail_closed() — mock DB exception, verify failure response and error logged
- [ ] T040 [P] Add test_episode_summary_below_threshold() — mock 3 messages, verify None returned
- [ ] T041 [P] Add test_episode_summary_generated() — mock 10+ messages, verify EPISODE memory created
- [ ] T042 [P] Add test_episode_summary_already_generated() — mock Redis flag set, verify no duplicate
- [ ] T043 [P] Add test_cross_user_write_blocked() — attempt delete with mismatched user_id, verify rejection [SC-008]

**Checkpoint**: Memory write service complete with full test coverage.

---

## Phase 5: Agent Tools

**Purpose**: Create save_memory and delete_memory tools following query_memory_tool pattern.

### save_memory Tool

- [ ] T044 [US1] Create src/tools/save_memory.py with `@function_tool async def save_memory_tool(ctx: RunContextWrapper, content: str, memory_type: str, confidence: float = 0.8, importance: float = 0.5) -> str` [FR-003]
- [ ] T045 [US1] Implement context extraction: user_id, correlation_id, conversation_id from ctx.context (matching query_memory_tool pattern)
- [ ] T046 [US1] Implement confidence routing: >= 0.7 → schedule_write() and return {"action": "queued"}, 0.5-0.7 → return {"action": "confirm_needed", "content": ...}, < 0.5 → return {"action": "discarded"} [FR-001, FR-006, FR-006a, FR-017]
- [ ] T047 [US1] Add user_id validation: if missing, return error JSON (matching query_memory_tool security pattern) [FR-015]
- [ ] T048 [US1] Add docstring with tool description for the Agent: when to use, confidence guidelines, memory types

### delete_memory Tool

- [ ] T049 [US3] Create src/tools/delete_memory.py with `@function_tool async def delete_memory_tool(ctx: RunContextWrapper, description: str, confirm: bool = False) -> str` [FR-003a]
- [ ] T050 [US3] Implement search mode (confirm=False): call MemoryService.hybrid_search() with description, return matching memories as candidates for agent to present [FR-008]
- [ ] T051 [US3] Implement delete mode (confirm=True): call schedule_write(write_service.delete_memory()) and return confirmation [FR-008, FR-009, FR-017]
- [ ] T052 [US3] Add user_id validation and error handling matching save_memory_tool pattern [FR-015]

### Tests

- [ ] T053 [P] [US1] Create tests/unit/test_save_memory_tool.py with test_high_confidence_queues_write() — confidence=0.9, verify "queued" response
- [ ] T054 [P] [US1] Add test_medium_confidence_returns_confirm() — confidence=0.6, verify "confirm_needed" response
- [ ] T055 [P] [US1] Add test_low_confidence_discards() — confidence=0.3, verify "discarded" response
- [ ] T056 [P] [US1] Add test_missing_user_id_returns_error() — empty context, verify error response
- [ ] T057 [P] [US1] Add test_invalid_memory_type_handled() — bad type string, verify graceful error
- [ ] T058 [P] [US3] Create tests/unit/test_delete_memory_tool.py with test_search_mode_returns_candidates() — confirm=False, verify candidates returned
- [ ] T059 [P] [US3] Add test_confirm_mode_executes_deletion() — confirm=True, verify schedule_write called
- [ ] T060 [P] [US3] Add test_no_matches_returns_message() — empty search results, verify informative response
- [ ] T061 [P] [US3] Add test_missing_user_id_returns_error() — empty context, verify error response

**Checkpoint**: Both tools implemented and tested.

---

## Phase 6: Chat Service Integration

**Purpose**: Register new tools, update system prompt, add episode trigger, drain writes on shutdown.

### System Prompt

- [ ] T062 [US2] Add MEMORY_WRITE_SYSTEM_PROMPT constant to src/services/chat_service.py with extraction guidelines: what to save (facts, preferences, decisions), what NOT to save (trivial info), confidence guidelines (0.7+/0.5-0.7/<0.5), correction flow (delete old + save new), acknowledgment guidance [FR-001, FR-005, FR-006]

### Tool Registration

- [ ] T063 Register save_memory_tool in _get_tools() of src/services/chat_service.py with try/except lazy loading (matching existing pattern) [FR-003]
- [ ] T064 Register delete_memory_tool in _get_tools() of src/services/chat_service.py with try/except lazy loading [FR-003a]
- [ ] T065 Append MEMORY_WRITE_SYSTEM_PROMPT to instructions when self._database_available is True (after existing MEMORY_SYSTEM_PROMPT append)

### Context & Episode Trigger

- [ ] T066 Add "conversation_id" to context dict in stream_completion() (line ~184): `context["conversation_id"] = str(conversation.id) if conversation else None` [FR-004]
- [ ] T067 [US4] After response persistence in stream_completion() (line ~244): add episode summarization check — count messages, if threshold met (8+ user OR 15+ total) and not already generated, fire-and-forget create_episode_summary() via schedule_write() [FR-010, FR-017]
- [ ] T068 In episode check: use Redis key `episode:generated:{conversation_id}` to prevent re-triggering [FR-010]

### Shutdown

- [ ] T069 Update src/main.py lifespan shutdown: import and call await_pending_writes(timeout=5.0) to drain background tasks before exit

**Checkpoint**: Chat service fully integrated with memory write capabilities.

---

## Phase 7: Evaluation Framework

**Purpose**: Add extraction quality evaluation with golden dataset and MLflow integration.

### Models

- [ ] T070 [P] [US6] Add MemoryWriteTestCase model to eval/models.py: id (str), conversation (list[dict] of role/content), user_id (str, default="eval-user"), expected_writes (list[dict] with content_keywords/type/should_write), expected_deletes (list[str]), rubric (str)
- [ ] T071 [P] [US6] Add MemoryWriteEvalResult model to eval/models.py: case_id, conversation_summary, actual_writes (list[dict]), actual_deletes (list[str]), precision (float), recall (float), false_positive_count (int), latency_ms (int), error (Optional[str])
- [ ] T072 [P] [US6] Add MemoryWriteMetrics model to eval/models.py: total_cases, extraction_precision, extraction_recall, false_positive_rate, latency_p50, latency_p95, error_cases, overall_passed (precision >= 0.85 AND recall >= 0.70) [SC-001, SC-002, SC-007]

### Judge

- [ ] T073 [US6] Create eval/memory_write_judge.py with MemoryWriteJudge class
- [ ] T074 [US6] Implement evaluate_extraction_precision(actual_writes, expected_writes) -> float — fraction of actual writes that match expected [SC-001]
- [ ] T075 [US6] Implement evaluate_extraction_recall(actual_writes, expected_writes) -> float — fraction of expected writes found in actual [SC-002]
- [ ] T076 [US6] Implement count_false_positives(actual_writes, expected_writes) -> int — writes that don't match any expected [SC-007]

### Dataset

- [ ] T077 [US6] Create eval/memory_write_golden_dataset.json with version, description, and 10-15 cases covering: fact extraction, preference extraction, decision extraction, trivial message (no write), correction/supersession, deletion request, duplicate content, low-confidence item, multi-fact message, episode summary
- [ ] T078 [US6] Add load_memory_write_dataset(path) function to eval/dataset.py with Pydantic validation
- [ ] T079 [US6] Add is_memory_write_dataset(path) detection function to eval/dataset.py (check for "memory_write" in filename)

### Runner

- [ ] T080 [US6] Add run_memory_write_evaluation() function to eval/runner.py following run_memory_evaluation() pattern: load dataset → for each case send conversation → query DB for actual writes → judge → compute metrics → log to MLflow
- [ ] T081 [US6] Add MemoryWriteEvaluationResult dataclass and format_memory_write_summary() to eval/runner.py
- [ ] T082 [US6] Implement regression gating in run_memory_write_evaluation(): FAIL if precision < 0.85 OR recall < 0.70 [SC-001, SC-002]

### CLI

- [ ] T083 [US6] Update eval/__main__.py: detect memory write dataset via is_memory_write_dataset(), route to run_memory_write_evaluation()

### Tests

- [ ] T084 [P] [US6] Create tests/unit/test_memory_write_judge.py with test_precision_all_correct() — all writes expected, verify 1.0
- [ ] T085 [P] [US6] Add test_precision_with_false_positives() — extra writes, verify < 1.0
- [ ] T086 [P] [US6] Add test_recall_all_found() — all expected found, verify 1.0
- [ ] T087 [P] [US6] Add test_recall_with_misses() — missing expected, verify < 1.0
- [ ] T088 [P] [US6] Add test_false_positive_count() — verify correct count of unwanted writes

**Checkpoint**: Evaluation framework complete — can measure extraction quality.

---

## Phase 8: Integration Tests & Validation

**Purpose**: End-to-end testing and manual verification.

### Integration Tests

- [ ] T089 [US1] Create tests/integration/test_memory_writes.py with test_save_memory_via_chat() — send message with factual info, verify memory created in DB [FR-001]
- [ ] T090 [US3] Add test_delete_memory_via_chat() — create memory, send "forget that", verify soft-deleted [FR-008, FR-009]
- [ ] T091 [US3] Add test_correction_flow() — create memory, send correction, verify old superseded and new created [FR-007, FR-013]
- [ ] T092 Add test_rate_limit_enforcement() — send rapid memory-creating messages, verify rate limit kicks in [FR-012]
- [ ] T093 Add test_duplicate_prevention() — send same fact twice, verify only one memory created [FR-014]
- [ ] T094 [US4] Add test_episode_summarization() — send 10+ messages, verify episode summary created [FR-010]
- [ ] T095 Add test_cross_user_write_isolation() — verify user A cannot delete user B's memories [FR-015, SC-008]
- [ ] T096 Add test_async_write_does_not_block_response() — time the response, verify write latency doesn't add to response time [FR-017]

### Manual Validation

- [ ] T097 Start services: `docker compose -f docker/docker-compose.api.yml up -d --build`
- [ ] T098 Send factual message: "I'm a vegetarian" → verify memory created in memory_items table and memory_write_events has audit entry
- [ ] T099 Ask "what do you remember about me?" → verify assistant lists saved memories with sources
- [ ] T100 Say "forget that I'm a vegetarian" → verify soft-delete (deleted_at set, status='deleted')
- [ ] T101 Say "actually I prefer Python over TypeScript" → verify old preference superseded, new created
- [ ] T102 Have 10+ turn conversation → verify episode summary created as EPISODE memory
- [ ] T103 Run eval: `uv run python -m eval --dataset eval/memory_write_golden_dataset.json --verbose`
- [ ] T104 Run full test suite: `uv run pytest tests/ -v` — all tests pass
- [ ] T105 Check MLflow at http://localhost:5000 — verify extraction metrics logged

**Checkpoint**: Feature complete — all tests pass, manual validation confirmed.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Schema)**: No dependencies
- **Phase 2 (Models)**: No dependencies — CAN RUN PARALLEL WITH PHASE 1
- **Phase 3 (Redis)**: No dependencies — CAN RUN PARALLEL WITH PHASE 1, 2
- **Phase 4 (Write Service)**: Depends on Phase 1 (schema), Phase 2 (models), Phase 3 (Redis)
- **Phase 5 (Tools)**: Depends on Phase 4 (write service)
- **Phase 6 (Chat Integration)**: Depends on Phase 5 (tools)
- **Phase 7 (Evaluation)**: Depends on Phase 6 (full flow working)
- **Phase 8 (Integration Tests)**: Depends on Phase 6 (full flow working)

### Parallel Opportunities Per Phase

**Phases 1, 2, 3**: All independent — can run in parallel

**Phase 4**: T032-T043 (unit tests) can all run in parallel

**Phase 5**: T053-T061 (unit tests) can all run in parallel

**Phase 7**: T070-T072 (models), T084-T088 (judge tests) can run in parallel

---

## Task Count Summary

| Phase | Description               | Tasks | Parallel |
| ----- | ------------------------- | ----- | -------- |
| 1     | Database Schema           | 5     | 0        |
| 2     | Models & Config           | 7     | 5        |
| 3     | Redis Rate Limits         | 8     | 5        |
| 4     | Memory Write Service      | 24    | 12       |
| 5     | Agent Tools               | 18    | 9        |
| 6     | Chat Integration          | 8     | 0        |
| 7     | Evaluation Framework      | 19    | 8        |
| 8     | Integration & Validation  | 17    | 0        |
| **Total** |                       | **106** | **39** |

### By User Story

- **US1 (Automatic Fact Extraction)**: 12 tasks
- **US2 (Memory Write Observability)**: 1 task (system prompt)
- **US3 (Memory Correction/Deletion)**: 10 tasks
- **US4 (Episode Summarization)**: 4 tasks
- **US6 (Evaluation)**: 19 tasks
- **Infrastructure/Shared**: 60 tasks

### Test Tasks

- **Unit Tests**: 30 tasks
- **Integration Tests**: 8 tasks
- **Validation**: 9 tasks
- **Total Test/Validation**: 47 tasks (44% of all tasks)

---

## Critical Security Tasks

**MUST NOT SKIP — Cross-User Safety**:

- T027: user_id scoping in ALL write queries
- T043: Cross-user write test
- T047, T052, T056, T061: user_id validation in tools
- T095: Cross-user isolation integration test
- SC-008: Zero unauthorized cross-user writes

---

## Notes

- [P] tasks = different files, no dependencies — can run in parallel
- [US] label maps task to specific user story
- Commit after each phase or logical group
- Stop at any checkpoint to validate independently
- Episode summarization uses same model as chat (no separate model needed)
- Async persistence via asyncio.create_task — drain on shutdown
