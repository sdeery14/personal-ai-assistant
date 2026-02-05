# Implementation Plan: Knowledge Graph (Feature 007)

**Created**: 2026-02-05
**Estimated Phases**: 6
**Dependencies**: Feature 006 (Memory v2) complete

---

## Overview

This plan implements a knowledge graph system that tracks entities (people, projects, tools) and relationships between them, enabling relationship-based queries that complement the existing vector-based memory retrieval.

### Architecture Approach

The Knowledge Graph follows patterns established in Memory v2:
- **Extraction during response generation**: Entity/relationship identification happens as part of the agent's response flow
- **Async persistence**: Database writes are fire-and-forget to not block responses
- **Agent tool for retrieval**: A `query_graph` tool allows the agent to answer relationship questions
- **User-scoped data**: All entities and relationships are strictly per-user

### Key Design Decisions

1. **Implicit extraction**: No explicit `extract_entity` tool — the agent identifies entities/relationships as part of normal processing, guided by system prompt
2. **Conservative deduplication**: Same name + type + user = same entity
3. **Directional storage**: Relationships stored with source→target direction
4. **Provenance required**: All graph elements link to source messages

---

## Phase 1: Database Schema

**Goal**: Create tables for entities and relationships with proper indexing.

### Deliverables

1. **Migration 006_knowledge_graph.sql**
   - `entities` table with all required columns
   - `entity_relationships` table
   - Indexes for user scoping, type filtering, name lookup
   - Vector index for entity embedding similarity

### Schema Design

```sql
-- entities table
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    canonical_name VARCHAR(255) NOT NULL,  -- lowercase, normalized for dedup
    type VARCHAR(20) NOT NULL,
    aliases TEXT[] DEFAULT '{}',
    description TEXT,
    embedding VECTOR(1536),
    confidence FLOAT DEFAULT 1.0,
    mention_count INTEGER DEFAULT 1,
    first_seen_message_id UUID REFERENCES messages(id),
    first_seen_conversation_id UUID REFERENCES conversations(id),
    last_mentioned_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT entities_type_check CHECK (type IN ('person', 'project', 'tool', 'concept', 'organization')),
    CONSTRAINT entities_confidence_check CHECK (confidence >= 0.0 AND confidence <= 1.0),
    UNIQUE(user_id, canonical_name, type) WHERE deleted_at IS NULL
);

-- entity_relationships table
CREATE TABLE entity_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    source_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    target_entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    relationship_type VARCHAR(30) NOT NULL,
    context TEXT,
    confidence FLOAT DEFAULT 1.0,
    source_message_id UUID REFERENCES messages(id),
    source_conversation_id UUID REFERENCES conversations(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT relationships_type_check CHECK (relationship_type IN (
        'USES', 'PREFERS', 'DECIDED', 'WORKS_ON', 'WORKS_WITH',
        'KNOWS', 'DEPENDS_ON', 'MENTIONED_IN', 'PART_OF'
    )),
    CONSTRAINT relationships_confidence_check CHECK (confidence >= 0.0 AND confidence <= 1.0)
);
```

### Indexes

- `idx_entities_user_id` — filter by user (partial: non-deleted)
- `idx_entities_user_type` — filter by user + type
- `idx_entities_canonical_name` — deduplication lookups
- `idx_entities_embedding` — vector similarity search
- `idx_relationships_user_id` — filter relationships by user
- `idx_relationships_source` — traverse from source entity
- `idx_relationships_target` — traverse to target entity
- `idx_relationships_type` — filter by relationship type

---

## Phase 2: Models & Services

**Goal**: Create Pydantic models and core service layer.

### Deliverables

1. **src/models/graph.py** — Pydantic models
   - `EntityType` enum
   - `RelationshipType` enum
   - `Entity` model
   - `Relationship` model
   - `GraphQueryRequest` / `GraphQueryResponse`

2. **src/services/graph_service.py** — Core CRUD operations
   - `get_or_create_entity()` — find existing or create new
   - `create_relationship()` — create with dedup check
   - `query_entities()` — find entities by criteria
   - `query_relationships()` — find relationships by criteria
   - `get_entity_relationships()` — get all relationships for an entity

3. **src/config.py** — Add graph-related settings
   - `graph_entity_confidence_threshold`
   - `graph_max_entities_per_conversation`
   - `graph_max_relationships_per_conversation`

---

## Phase 3: Entity Extraction

**Goal**: Enable automatic entity extraction from conversations.

### Approach

Entity extraction uses the same pattern as memory writes:
1. System prompt instructs the agent to identify entities
2. Agent calls `save_entity` tool when entities are detected
3. Tool validates and queues async persistence

### Deliverables

1. **src/tools/save_entity.py** — Agent tool for entity creation
   - Input: name, type, description (optional), confidence
   - Validates against existing entities (dedup)
   - Returns created/existing entity info

2. **src/services/graph_service.py** — Add extraction methods
   - `extract_and_save_entity()` — handles dedup logic
   - `normalize_entity_name()` — canonical name generation

3. **System prompt addition** (in chat_service.py)
   - Instructions for when to extract entities
   - Guidance on entity types and confidence

### Extraction Prompt Guidance

```
When users mention specific people, projects, tools, or organizations:
- Extract entities with save_entity tool
- Use appropriate type: person, project, tool, concept, organization
- Include context in description when helpful
- Confidence 0.9+ for explicit mentions ("I use FastAPI")
- Confidence 0.7-0.9 for implied mentions ("the backend framework we discussed")
```

---

## Phase 4: Relationship Extraction

**Goal**: Enable automatic relationship extraction between entities.

### Deliverables

1. **src/tools/save_relationship.py** — Agent tool for relationships
   - Input: source_entity (name or ID), target_entity, relationship_type, context
   - Validates entities exist (or creates them)
   - Handles relationship reinforcement (existing relationship = increase confidence)

2. **System prompt addition**
   - Instructions for identifying relationships
   - Guidance on relationship types

### Relationship Extraction Patterns

| Pattern | Relationship |
|---------|--------------|
| "I use X" | User → USES → X |
| "I prefer X over Y" | User → PREFERS → X |
| "Project uses X" | Project → USES → X |
| "I work with Sarah" | User → WORKS_WITH → Sarah |
| "I decided on X" | User → DECIDED → X |
| "X depends on Y" | X → DEPENDS_ON → Y |

---

## Phase 5: Graph Query Tool

**Goal**: Enable the agent to query the knowledge graph for relationship information.

### Deliverables

1. **src/tools/query_graph.py** — Agent retrieval tool
   - Input: query (natural language), entity_type filter, relationship_type filter
   - Returns relevant entities and relationships with provenance
   - Formats output for agent consumption

2. **src/services/graph_service.py** — Add query methods
   - `search_entities_by_name()` — fuzzy name matching
   - `get_related_entities()` — traverse relationships
   - `answer_relationship_query()` — high-level query processing

### Query Examples

```python
# "What tools do I use?"
query_graph(query="tools I use", relationship_type="USES", entity_type="tool")

# "Who do I work with?"
query_graph(query="people I work with", relationship_type="WORKS_WITH", entity_type="person")

# "What does project Phoenix use?"
query_graph(query="Phoenix dependencies", entity_type="tool")
```

---

## Phase 6: Integration & Testing

**Goal**: Wire everything together and ensure quality.

### Deliverables

1. **Chat service integration**
   - Add graph tools to agent
   - Add system prompt guidance
   - Wire extraction to conversation flow

2. **Unit tests**
   - `tests/unit/test_graph_service.py`
   - `tests/unit/test_save_entity_tool.py`
   - `tests/unit/test_save_relationship_tool.py`
   - `tests/unit/test_query_graph_tool.py`

3. **Integration tests**
   - `tests/integration/test_knowledge_graph.py`
   - Entity extraction E2E
   - Relationship extraction E2E
   - Graph query E2E

4. **Evaluation dataset**
   - `eval/graph_extraction_golden_dataset.json`
   - Test cases for entity extraction
   - Test cases for relationship extraction
   - Test cases for graph queries

5. **Eval runner integration**
   - Graph extraction precision/recall metrics
   - Graph query relevance scoring

---

## Rate Limiting

Following the Memory v2 pattern:

| Limit | Value | Rationale |
|-------|-------|-----------|
| Entities per conversation | 20 | Prevent runaway extraction |
| Relationships per conversation | 30 | Relationships ≤ entities squared |
| Entities per user per day | 100 | Daily cap |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Entity explosion (too many entities) | Conservative extraction + rate limits |
| Duplicate entities | Canonical name normalization + unique constraint |
| Relationship noise | High confidence threshold (0.7) |
| Query performance | Proper indexes + pagination |
| Cross-user data leaks | user_id in ALL queries (security-critical) |

---

## Success Criteria

1. **Functional**: Entity and relationship extraction works for common patterns
2. **Quality**: ≥80% entity precision, ≥75% relationship precision
3. **Performance**: Graph queries complete in <500ms
4. **Security**: Zero cross-user data access in tests
5. **Integration**: Graph tool available to agent, works alongside memory tools

---

## Out of Scope (Deferred)

- Pronoun/coreference resolution
- Complex entity merging across conversations
- Graph visualization
- Transitive relationship inference
- Background consolidation jobs
