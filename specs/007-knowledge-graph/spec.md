# Feature Specification: Knowledge Graph

**Feature Branch**: `007-knowledge-graph`
**Created**: 2026-02-05
**Status**: Draft
**Input**: User description: "Enable structured relationship tracking between entities mentioned in conversations."

> **Related Documents:**
>
> - [vision.md](../../vision.md) – Feature 007 in roadmap, Memory Architecture section
> - [006-memory-auto-writes/spec.md](../006-memory-auto-writes/spec.md) – Memory extraction patterns this builds on

---

## Clarifications

### Session 2026-02-05

- Q: How do we handle entity disambiguation (e.g., two people named "John")? → A: **Conservative merging** — entities with same name+type+user are considered the same. Different contexts create separate entities. Complex merging deferred to Feature 008.

- Q: What confidence threshold for automatic entity creation? → A: **Same as memory writes** — ≥0.7 auto-create, 0.5-0.7 create with lower confidence flag, <0.5 skip.

- Q: Should entities link to memory items or be separate? → A: **Separate but connected** — entities are distinct from memory items, but MENTIONED_IN relationships can link entities to episode memories.

- Q: How do we handle entity mentions vs. entity creation? → A: **Implicit extraction** — entity extraction happens automatically during message processing (like memory writes), not via explicit tool calls.

- Q: How do we handle pronouns ("he", "that project")? → A: **Skip in MVP** — only extract explicit named entities. Pronoun/coreference resolution is deferred.

- Q: Should relationships be directional or bidirectional? → A: **Stored as directional** — but symmetric relationships (WORKS_WITH) can be queried bidirectionally by the tool.

---

## Feature Overview

### Goal

Enable the assistant to understand and track relationships between entities (people, projects, tools, concepts) mentioned in conversations, allowing for relationship-based queries that vector search cannot answer well.

### Building on Memory v2

Memory v2 established automatic extraction and persistence of facts, preferences, and decisions. The Knowledge Graph extends this with:

- **Entity extraction**: Identifying people, projects, tools, and concepts from conversations
- **Relationship tracking**: Capturing how entities relate to each other (USES, PREFERS, WORKS_ON, etc.)
- **Graph-based retrieval**: A new tool for relationship queries ("What tools do I use for project X?")
- **Provenance**: Every entity and relationship links back to source messages

### User Capability

> "The assistant understands how things I mention relate to each other."

### Non-Goals

This feature explicitly does **not** include:

- **Complex entity merging**: Sophisticated deduplication across sessions (deferred to Feature 008)
- **Cross-user graph connections**: Graph data is strictly per-user
- **Automatic graph cleanup/consolidation**: No background pruning or merging
- **Inference/reasoning over graph**: No transitive relationship inference
- **Graph visualization**: No UI for exploring the graph

---

## User Scenarios & Testing

### User Story 1 – Entity Extraction (Priority: P1)

As a user, when I mention people, projects, or tools in conversation, the assistant automatically tracks them as entities so it can understand my context better.

**Why this priority**: Entity extraction is foundational—without entities, there's no graph.

**Independent Test**: Mention "I'm using FastAPI for project Phoenix with my colleague Sarah" and verify entities are created for FastAPI (tool), Phoenix (project), and Sarah (person).

**Acceptance Scenarios**:

1. **Given** the user says "I'm working on project Apollo", **When** the message is processed, **Then** an entity of type `project` named "Apollo" is created with provenance to the source message.

2. **Given** the user mentions "I switched from React to Vue", **When** the message is processed, **Then** entities for both React and Vue (type: `tool`) are created or retrieved if existing.

3. **Given** the user says "My manager Dave approved the budget", **When** the message is processed, **Then** an entity of type `person` named "Dave" is created with context "manager".

4. **Given** an entity with the same name and type already exists, **When** a new mention is processed, **Then** the existing entity is reused (no duplicate created).

---

### User Story 2 – Relationship Tracking (Priority: P1)

As a user, I want the assistant to understand how things I mention relate to each other, so it has better context for future conversations.

**Why this priority**: Relationships are the core value of a knowledge graph over a flat memory store.

**Independent Test**: Say "I use TypeScript for the Phoenix project" and verify a USES relationship is created between the user and TypeScript, and a relationship between Phoenix and TypeScript.

**Acceptance Scenarios**:

1. **Given** the user says "I prefer Python over JavaScript", **When** the message is processed, **Then** a PREFERS relationship is created from user to Python with context indicating it's preferred over JavaScript.

2. **Given** the user says "Project Apollo uses PostgreSQL", **When** the message is processed, **Then** a USES relationship is created from Apollo entity to PostgreSQL entity.

3. **Given** the user says "Sarah works on the backend team", **When** the message is processed, **Then** a WORKS_ON relationship is created from Sarah entity to a team/group entity.

4. **Given** a relationship already exists, **When** it's mentioned again, **Then** the existing relationship is reinforced (confidence increased) rather than duplicated.

---

### User Story 3 – Graph-Based Retrieval (Priority: P1)

As a user, I can ask relationship questions that the assistant answers using the knowledge graph.

**Why this priority**: This is the user-facing value—being able to query relationships.

**Independent Test**: After establishing several entities and relationships, ask "What tools do I use for project X?" and verify the assistant uses the graph to answer.

**Acceptance Scenarios**:

1. **Given** entities and relationships exist for a project, **When** the user asks "What technologies am I using for project Phoenix?", **Then** the assistant queries the graph and lists related tools.

2. **Given** person entities exist, **When** the user asks "Who have I mentioned working with?", **Then** the assistant returns a list of people entities from the graph.

3. **Given** tool preferences exist, **When** the user asks "What are my preferred tools for backend development?", **Then** the assistant combines graph relationships with memory items.

4. **Given** no relevant entities exist, **When** the user asks a relationship question, **Then** the assistant acknowledges it doesn't have that information yet.

---

### User Story 4 – Provenance & Transparency (Priority: P2)

As a user, I want to know where the assistant learned about entities and relationships, so I can trust and correct the information.

**Acceptance Scenarios**:

1. **Given** an entity was extracted, **When** the user asks "How do you know about X?", **Then** the assistant can cite the source conversation/message.

2. **Given** a relationship was extracted incorrectly, **When** the user says "Actually, I don't use X anymore", **Then** the relationship is marked as inactive (soft delete).

---

## Entity Types

| Type | Description | Examples |
|------|-------------|----------|
| `person` | People mentioned (colleagues, friends, family) | "Dave", "my manager", "Sarah" |
| `project` | Projects, repositories, initiatives | "Phoenix", "the API rewrite" |
| `tool` | Tools, libraries, languages, services | "FastAPI", "PostgreSQL", "Docker" |
| `concept` | Abstract ideas, methodologies, topics | "microservices", "TDD", "agile" |
| `organization` | Companies, teams, groups | "Google", "the backend team" |

---

## Relationship Types

| Relationship | Description | Example |
|--------------|-------------|---------|
| `USES` | User/project uses a tool or technology | User → USES → FastAPI |
| `PREFERS` | User prefers X (optionally over Y) | User → PREFERS → Python |
| `DECIDED` | User made a decision about X | User → DECIDED → PostgreSQL |
| `WORKS_ON` | User/person works on project | User → WORKS_ON → Phoenix |
| `WORKS_WITH` | User works with person | User → WORKS_WITH → Sarah |
| `KNOWS` | User knows person | User → KNOWS → Dave |
| `DEPENDS_ON` | Project/tool depends on another | Phoenix → DEPENDS_ON → FastAPI |
| `MENTIONED_IN` | Entity mentioned in episode/memory | FastAPI → MENTIONED_IN → Episode123 |
| `PART_OF` | Entity is part of another | Sarah → PART_OF → Backend Team |

---

## Functional Requirements

### FR-001: Entity Storage

The system must store entities with:
- Unique ID (UUID)
- User ID (for scoping)
- Name (display name)
- Type (person, project, tool, concept, organization)
- Aliases (alternative names/references)
- Embedding (for semantic search)
- Confidence score (extraction confidence)
- Source message ID (provenance)
- Source conversation ID (provenance)
- Created/updated timestamps
- Soft delete support

### FR-002: Relationship Storage

The system must store relationships with:
- Unique ID (UUID)
- User ID (for scoping)
- Source entity ID
- Target entity ID (nullable for user-centric relationships)
- Relationship type (enum)
- Context/description (optional)
- Confidence score
- Source message ID (provenance)
- Created timestamp
- Soft delete support

### FR-003: Entity Extraction Tool

The agent must have access to an entity extraction capability that:
- Identifies entity mentions in user messages
- Determines entity type with confidence
- Creates or retrieves existing entities
- Links to source message for provenance
- Operates during response generation (not blocking)

### FR-004: Relationship Extraction

The system must extract relationships by:
- Analyzing sentences for relationship patterns
- Determining relationship type with confidence
- Creating bidirectional links where appropriate
- Reinforcing existing relationships on re-mention

### FR-005: Graph Query Tool

The agent must have a `query_graph` tool that:
- Accepts relationship-oriented queries
- Returns relevant entities and relationships
- Supports filtering by entity type and relationship type
- Returns provenance information
- Respects user scoping (never crosses user boundaries)

### FR-006: Retrieval Routing

The system should route queries appropriately:
- **Graph retrieval**: Relationship queries ("What tools do I use?")
- **Vector retrieval**: Narrative queries ("What did we discuss about the trip?")
- **Combined**: Complex queries needing both

---

## Technical Design

### Database Schema

```sql
-- Entities table
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('person', 'project', 'tool', 'concept', 'organization')),
    aliases TEXT[] DEFAULT '{}',
    description TEXT,
    embedding VECTOR(1536),
    confidence FLOAT DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    source_message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    source_conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    mention_count INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Relationships table
CREATE TABLE entity_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    source_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    target_entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    relationship_type VARCHAR(30) NOT NULL CHECK (relationship_type IN (
        'USES', 'PREFERS', 'DECIDED', 'WORKS_ON', 'WORKS_WITH',
        'KNOWS', 'DEPENDS_ON', 'MENTIONED_IN', 'PART_OF'
    )),
    context TEXT,
    confidence FLOAT DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    source_message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    source_conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
```

### Agent Tools

1. **`query_graph`**: Relationship-oriented queries
   - Input: query string, optional entity_type filter, optional relationship_type filter
   - Output: List of entities and relationships with provenance

2. Entity extraction is integrated into the response flow (similar to memory extraction)

### Extraction Strategy

Entity and relationship extraction follows the Memory v2 pattern:
- Extraction decisions happen during response generation
- Persistence happens asynchronously (fire-and-forget)
- Agent uses internal reasoning to identify extractable entities/relationships
- System prompt guides extraction behavior

---

## Security Considerations

### SC-001: User Scoping

All entity and relationship queries MUST include user_id filter. Cross-user graph access is a critical security violation.

### SC-002: Provenance Integrity

Source message references must be validated to ensure users can only link to their own messages.

### SC-003: Rate Limiting

Entity/relationship creation should respect similar rate limits as memory writes:
- Max 20 entities per conversation
- Max 50 relationships per conversation
- Burst and daily limits similar to memory

---

## Evaluation Criteria

### Graph Extraction Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Entity Precision | ≥80% | % of extracted entities that are valid |
| Entity Recall | ≥70% | % of mentioned entities that were extracted |
| Relationship Precision | ≥75% | % of extracted relationships that are correct |
| Relationship Recall | ≥60% | % of stated relationships that were extracted |

### Retrieval Quality

| Metric | Target | Description |
|--------|--------|-------------|
| Graph Query Relevance | ≥80% | Relevant entities returned for relationship queries |
| Provenance Accuracy | 100% | All graph elements link to valid source messages |

---

## Dependencies

- Feature 004: Memory v1 (query patterns, embedding service)
- Feature 006: Memory v2 (extraction patterns, async write infrastructure)
- PostgreSQL with pgvector extension (already deployed)

---

## Design Decisions (Resolved)

1. **Entity deduplication**: Same name + type + user_id = same entity. Context stored in aliases/description.
2. **Extraction approach**: Implicit during message processing (no separate tool call).
3. **Precision vs recall**: Favor precision (≥0.7 confidence threshold) — better to miss some than create noise.
4. **Pronouns**: Skip in MVP — only explicit named entities extracted.
5. **Relationship direction**: Stored as directional; symmetric types queryable both ways.
