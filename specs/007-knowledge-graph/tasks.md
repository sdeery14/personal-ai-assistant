# Tasks: Knowledge Graph (Feature 007)

**Input**: Design documents from `/specs/007-knowledge-graph/`
**Prerequisites**: plan.md, spec.md

**Organization**: Tasks are grouped by phase. Each task maps to spec requirements (FR/SC) where applicable.

## Format: `[ID] [P?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

---

## Phase 1: Database Schema

- [ ] T001 [P] Create migration file `migrations/006_knowledge_graph.sql`
- [ ] T002 Create `entities` table with all columns (id, user_id, name, canonical_name, type, aliases, description, embedding, confidence, mention_count, timestamps, soft delete)
- [ ] T003 Add CHECK constraints for entity type enum and confidence range
- [ ] T004 Add unique constraint on (user_id, canonical_name, type) for non-deleted entities
- [ ] T005 Create `entity_relationships` table with all columns
- [ ] T006 Add CHECK constraints for relationship_type enum and confidence range
- [ ] T007 Add foreign key references to entities, messages, conversations
- [ ] T008 [P] Create index `idx_entities_user_id` (partial: deleted_at IS NULL)
- [ ] T009 [P] Create index `idx_entities_user_type` for type filtering
- [ ] T010 [P] Create index `idx_entities_canonical_name` for dedup lookups
- [ ] T011 [P] Create index `idx_entities_embedding` using ivfflat for vector search
- [ ] T012 [P] Create index `idx_relationships_user_id`
- [ ] T013 [P] Create index `idx_relationships_source` for graph traversal
- [ ] T014 [P] Create index `idx_relationships_target` for reverse traversal
- [ ] T015 [P] Create index `idx_relationships_type` for relationship filtering
- [ ] T016 Verify migration applies cleanly to fresh database
- [ ] T017 Verify migration applies cleanly to existing database with data

**Checkpoint**: Schema deployed — entities and relationships tables exist with indexes. ⏳

---

## Phase 2: Models & Configuration

### Pydantic Models

- [ ] T018 [P] Create `src/models/graph.py`
- [ ] T019 Define `EntityType` enum (person, project, tool, concept, organization)
- [ ] T020 Define `RelationshipType` enum (USES, PREFERS, DECIDED, WORKS_ON, WORKS_WITH, KNOWS, DEPENDS_ON, MENTIONED_IN, PART_OF)
- [ ] T021 Define `Entity` Pydantic model with all fields
- [ ] T022 Define `Relationship` Pydantic model with all fields
- [ ] T023 Define `GraphQueryRequest` model (query, entity_type filter, relationship_type filter, limit)
- [ ] T024 Define `GraphQueryResponse` model (entities, relationships, metadata)
- [ ] T025 Define `EntityCreateRequest` model for tool input validation
- [ ] T026 Define `RelationshipCreateRequest` model for tool input validation

### Configuration

- [ ] T027 [P] Add `graph_entity_confidence_threshold` to Settings (default: 0.7)
- [ ] T028 [P] Add `graph_max_entities_per_conversation` to Settings (default: 20)
- [ ] T029 [P] Add `graph_max_relationships_per_conversation` to Settings (default: 30)
- [ ] T030 [P] Add `graph_max_entities_per_day` to Settings (default: 100)

**Checkpoint**: Models and config ready for service layer. ⏳

---

## Phase 3: Graph Service (Core CRUD)

- [ ] T031 Create `src/services/graph_service.py`
- [ ] T032 Implement `normalize_entity_name()` — lowercase, strip whitespace, handle common variations
- [ ] T033 Implement `get_entity_by_canonical_name()` — lookup existing entity
- [ ] T034 Implement `create_entity()` — insert new entity with embedding generation
- [ ] T035 Implement `get_or_create_entity()` — find existing or create new (FR-001)
- [ ] T036 Implement `update_entity_mention()` — increment mention_count, update last_mentioned_at
- [ ] T037 Implement `get_entity_by_id()` — fetch single entity
- [ ] T038 Implement `search_entities()` — search by name pattern, type, user_id
- [ ] T039 Implement `soft_delete_entity()` — set deleted_at timestamp

### Relationship CRUD

- [ ] T040 Implement `create_relationship()` — insert new relationship (FR-002)
- [ ] T041 Implement `get_existing_relationship()` — check for duplicate relationship
- [ ] T042 Implement `reinforce_relationship()` — increase confidence of existing relationship
- [ ] T043 Implement `get_or_create_relationship()` — find existing or create new
- [ ] T044 Implement `get_entity_relationships()` — get all relationships for an entity
- [ ] T045 Implement `get_relationships_by_type()` — filter by relationship type
- [ ] T046 Implement `soft_delete_relationship()` — set deleted_at timestamp

### Unit Tests

- [ ] T047 [P] Create `tests/unit/test_graph_service.py`
- [ ] T048 Test `normalize_entity_name()` with various inputs
- [ ] T049 Test `get_or_create_entity()` creates new entity
- [ ] T050 Test `get_or_create_entity()` returns existing entity
- [ ] T051 Test `create_relationship()` with valid entities
- [ ] T052 Test `get_or_create_relationship()` reinforces existing
- [ ] T053 Test user_id scoping in all queries (SC-001)

**Checkpoint**: Graph service CRUD operations complete with tests. ⏳

---

## Phase 4: Entity Extraction Tool

### Save Entity Tool

- [ ] T054 Create `src/tools/save_entity.py`
- [ ] T055 Define tool function signature with proper typing
- [ ] T056 Implement input validation (name required, type must be valid enum)
- [ ] T057 Implement user_id extraction from context (FR-003, SC-001)
- [ ] T058 Implement rate limiting check (max entities per conversation)
- [ ] T059 Call `graph_service.get_or_create_entity()` for persistence
- [ ] T060 Return structured response (created vs existing, entity details)
- [ ] T061 Add logging for entity extraction events
- [ ] T062 Register tool with OpenAI Agents SDK

### Unit Tests

- [ ] T063 [P] Create `tests/unit/test_save_entity_tool.py`
- [ ] T064 Test tool creates new entity successfully
- [ ] T065 Test tool returns existing entity on duplicate
- [ ] T066 Test tool validates entity type enum
- [ ] T067 Test tool enforces rate limits
- [ ] T068 Test tool requires user_id in context

**Checkpoint**: Entity extraction tool complete with tests. ⏳

---

## Phase 5: Relationship Extraction Tool

### Save Relationship Tool

- [ ] T069 Create `src/tools/save_relationship.py`
- [ ] T070 Define tool function signature with proper typing
- [ ] T071 Implement input validation (source required, relationship_type required)
- [ ] T072 Implement entity resolution (find or create source/target entities)
- [ ] T073 Implement user_id extraction from context (SC-001)
- [ ] T074 Implement rate limiting check (max relationships per conversation)
- [ ] T075 Call `graph_service.get_or_create_relationship()` for persistence
- [ ] T076 Return structured response (created vs reinforced, relationship details)
- [ ] T077 Add logging for relationship extraction events
- [ ] T078 Register tool with OpenAI Agents SDK

### Unit Tests

- [ ] T079 [P] Create `tests/unit/test_save_relationship_tool.py`
- [ ] T080 Test tool creates new relationship successfully
- [ ] T081 Test tool reinforces existing relationship
- [ ] T082 Test tool validates relationship type enum
- [ ] T083 Test tool creates missing entities automatically
- [ ] T084 Test tool enforces rate limits
- [ ] T085 Test tool requires user_id in context

**Checkpoint**: Relationship extraction tool complete with tests. ⏳

---

## Phase 6: Graph Query Tool

### Query Graph Tool

- [ ] T086 Create `src/tools/query_graph.py`
- [ ] T087 Define tool function signature (query, entity_type filter, relationship_type filter)
- [ ] T088 Implement query parsing (extract entity names, relationship intent)
- [ ] T089 Implement entity search by name/type
- [ ] T090 Implement relationship traversal from matched entities
- [ ] T091 Implement response formatting (entities with relationships, provenance)
- [ ] T092 Add user_id scoping to ALL queries (SC-001)
- [ ] T093 Add logging for graph query events
- [ ] T094 Register tool with OpenAI Agents SDK

### Graph Service Query Methods

- [ ] T095 Implement `search_entities_by_embedding()` — semantic entity search
- [ ] T096 Implement `get_related_entities()` — traverse relationships from entity
- [ ] T097 Implement `find_paths()` — find relationship paths between entities (optional)

### Unit Tests

- [ ] T098 [P] Create `tests/unit/test_query_graph_tool.py`
- [ ] T099 Test tool returns entities matching query
- [ ] T100 Test tool returns relationships for matched entities
- [ ] T101 Test tool filters by entity_type
- [ ] T102 Test tool filters by relationship_type
- [ ] T103 Test tool enforces user_id scoping

**Checkpoint**: Graph query tool complete with tests. ⏳

---

## Phase 7: Chat Service Integration

### System Prompt

- [ ] T104 Add `GRAPH_EXTRACTION_SYSTEM_PROMPT` to chat_service.py
- [ ] T105 Include entity extraction guidance (when to extract, confidence levels)
- [ ] T106 Include relationship extraction guidance (patterns, types)
- [ ] T107 Include graph query guidance (when to use query_graph vs query_memory)

### Tool Registration

- [ ] T108 Import save_entity tool in chat_service._get_tools()
- [ ] T109 Import save_relationship tool in chat_service._get_tools()
- [ ] T110 Import query_graph tool in chat_service._get_tools()
- [ ] T111 Add graph system prompt to agent instructions when tools available

### Rate Limiting Integration

- [ ] T112 Add graph rate limit keys to redis_service.py
- [ ] T113 Implement `check_entity_rate_limit()` in redis_service.py
- [ ] T114 Implement `check_relationship_rate_limit()` in redis_service.py

**Checkpoint**: Chat service integrated with graph tools. ⏳

---

## Phase 8: Evaluation Framework

### Golden Dataset

- [ ] T115 Create `eval/graph_extraction_golden_dataset.json`
- [ ] T116 Add 5+ entity extraction test cases (various entity types)
- [ ] T117 Add 5+ relationship extraction test cases (various relationship types)
- [ ] T118 Add 5+ graph query test cases (relationship questions)
- [ ] T119 Add negative test cases (no entities to extract)

### Eval Runner Integration

- [ ] T120 Add graph extraction eval to runner.py
- [ ] T121 Implement entity extraction precision/recall metrics
- [ ] T122 Implement relationship extraction precision/recall metrics
- [ ] T123 Implement graph query relevance scoring

### Judge Scorer

- [ ] T124 Create `eval/graph_extraction_judge.py`
- [ ] T125 Implement entity extraction quality scorer
- [ ] T126 Implement relationship extraction quality scorer

**Checkpoint**: Evaluation framework complete for graph features. ⏳

---

## Phase 9: Integration Tests & Manual Validation

### Integration Tests

- [ ] T127 Create `tests/integration/test_knowledge_graph.py`
- [ ] T128 Test entity extraction E2E (send message → verify entity in DB)
- [ ] T129 Test relationship extraction E2E (send message → verify relationship in DB)
- [ ] T130 Test graph query E2E (create entities → query → verify response)
- [ ] T131 Test cross-user isolation (user A's entities not visible to user B)
- [ ] T132 Test entity deduplication (same name+type = same entity)
- [ ] T133 Test relationship reinforcement (same relationship = higher confidence)

### Manual Validation

- [ ] T134 Start services: `docker compose -f docker/docker-compose.api.yml up -d --build`
- [ ] T135 Send message: "I'm using FastAPI for project Phoenix" → verify entity extraction
- [ ] T136 Send message: "I work with Sarah on the backend" → verify relationship extraction
- [ ] T137 Ask "What tools do I use?" → verify graph query returns FastAPI
- [ ] T138 Ask "Who do I work with?" → verify graph query returns Sarah
- [ ] T139 Run eval: `uv run python -m eval --verbose`
- [ ] T140 Check MLflow at http://localhost:5000 — verify graph metrics logged

**Checkpoint**: Feature complete — tests pass, manual validation confirmed. ⏳

---

## Task Count Summary

| Phase | Description | Tasks |
|-------|-------------|-------|
| 1 | Database Schema | 17 |
| 2 | Models & Config | 13 |
| 3 | Graph Service | 23 |
| 4 | Entity Tool | 15 |
| 5 | Relationship Tool | 17 |
| 6 | Query Tool | 18 |
| 7 | Chat Integration | 11 |
| 8 | Evaluation | 12 |
| 9 | Integration & Validation | 14 |
| **Total** | | **140** |

---

## Critical Security Tasks

These tasks are security-critical and must not be skipped:

- T053: user_id scoping in graph service queries
- T057, T073, T092: user_id extraction from context in all tools
- T068, T085, T103: user_id validation tests
- T131: Cross-user isolation integration test

---

## Dependencies Between Phases

```
Phase 1 (Schema)
    ↓
Phase 2 (Models)
    ↓
Phase 3 (Graph Service)
    ↓
Phase 4 (Entity Tool) ──┬──→ Phase 7 (Integration)
    ↓                   │
Phase 5 (Relationship)──┤
    ↓                   │
Phase 6 (Query Tool) ───┘
                        ↓
                   Phase 8 (Eval)
                        ↓
                   Phase 9 (Validation)
```

Phases 4, 5, 6 can be partially parallelized after Phase 3 is complete.
