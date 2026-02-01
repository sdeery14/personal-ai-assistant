# Feature Specification: Memory v1 – Read-Only Recall

**Feature Branch**: `004-memory-v1-readonly-recall`
**Created**: 2026-02-01
**Status**: Draft
**Input**: User description: "Enable safe, read-only retrieval of relevant past information to ground assistant responses."

> **Related Documents:**
>
> - [vision.md](../../vision.md) – Feature 004 in roadmap
> - [vision-memory.md](../../vision-memory.md) – Memory v1 phase definition

---

## Feature Overview

### Goal

Enable the assistant to retrieve relevant past information from durable storage and use it as advisory context when answering user questions. This establishes the foundation for memory-grounded responses while maintaining strict safety boundaries.

### Clarification on "Read-Only"

This feature enables **read-only access to the curated memory store** (`memory_items` table). Conversation and message persistence—including embedding generation and Redis session state—is explicitly in-scope as foundational infrastructure required for future retrieval. The "read-only" constraint means that **automatic creation or modification of memory items is deferred to Memory v2**; the `memory_items` table is queried but never written to by the running system in this phase.

### User Capability

> "I can ask questions and the assistant can retrieve relevant past information when answering."

### Non-Goals

This feature explicitly does **not** include:

- **Automatic memory writes**: No summarization, insight extraction, or automatic persistence of memory items
- **Automatic memory item creation**: Memory items are manually seeded via migration, fixture, or admin script; automatic extraction from conversations is v2 scope
- **Background jobs**: No offline processing or scheduled tasks
- **Proactive behavior**: No unsolicited suggestions or notifications
- **Personalization logic**: No user modeling or preference learning
- **Cross-user memory**: Memory is strictly scoped per user

---

## User Scenarios & Testing

### User Story 1 – Memory-Grounded Response (Priority: P1) 🎯 MVP

As a user, when I ask a question that relates to something I've discussed before, the assistant retrieves relevant past context and uses it to provide a more informed answer.

**Why this priority**: This is the core capability. Without memory retrieval surfacing in responses, the feature delivers no value.

**Independent Test**: Store a fact ("I prefer uv over pip"), then ask "What package manager should I use?" and verify the response references the stored preference.

**Acceptance Scenarios**:

1. **Given** a memory item exists with content "User prefers uv over pip for Python dependency management", **When** the user asks "What package manager should I use for my Python project?", **Then** the assistant retrieves this memory and references the preference in its response.

2. **Given** multiple memory items exist for the user, **When** the user asks a question matching several memories, **Then** the assistant retrieves the most relevant items (up to token budget) and synthesizes them in the response.

3. **Given** no relevant memories exist for the query, **When** the user asks a question, **Then** the assistant responds normally without hallucinating past context, and no memory injection occurs.

4. **Given** a relevant memory is retrieved, **When** the assistant uses it in a response, **Then** the memory is cited as advisory context (e.g., "Based on what you mentioned previously...") rather than stated as authoritative fact.

---

### User Story 2 – Conversation Persistence (Priority: P1) 🎯 MVP

As a user, my conversations with the assistant are durably stored so they can be referenced in future sessions.

**Why this priority**: Without durable conversation storage, there's nothing to retrieve. This is foundational infrastructure.

**Independent Test**: Send a message, restart the API container, query the database, and verify the conversation and message are persisted.

**Acceptance Scenarios**:

1. **Given** a user sends a message to the assistant, **When** the message is processed, **Then** the conversation and message are persisted to Postgres with user ID, timestamp, and content.

2. **Given** a conversation exists from a previous session, **When** the user starts a new session, **Then** the previous conversation remains accessible for retrieval.

3. **Given** a streaming response completes, **When** the final chunk is sent, **Then** the assistant's response is persisted as a message linked to the conversation.

4. **Given** the database is unavailable, **When** a user sends a message, **Then** the request fails closed with an appropriate error (no silent data loss).

---

### User Story 3 – Memory Query Tool (Priority: P2)

As a developer, I can expose a memory query tool to the Agent that retrieves relevant memories based on the current conversation context.

**Why this priority**: The Agent needs an explicit tool to query memory. This enables the SDK's tool-calling pattern rather than implicit injection.

**Independent Test**: Invoke the memory query tool directly with a test query and verify it returns relevant memory items with scores and metadata.

**Acceptance Scenarios**:

1. **Given** the Agent is processing a user message, **When** the Agent determines memory context would be helpful, **Then** the Agent can invoke the `query_memory` tool with a search query.

2. **Given** the `query_memory` tool is invoked, **When** the tool executes, **Then** it returns a list of memory items with: content, type (`fact`/`preference`/`decision`/`note`), relevance score, source reference, and created timestamp.

3. **Given** the tool returns results, **When** the Agent incorporates them into the response, **Then** the total injected memory content respects the token budget (≤1000 tokens default).

4. **Given** the memory retrieval fails (timeout, database error), **When** the tool is invoked, **Then** the tool returns an empty result set with an error flag (fail closed), and the Agent proceeds without memory context.

---

### User Story 4 – Hybrid Retrieval (Priority: P2)

As a user, the assistant finds relevant memories using both keyword matching and semantic similarity, improving recall accuracy.

**Why this priority**: Single-mode retrieval (keyword-only or vector-only) has known limitations. Hybrid search improves both precision and recall.

**Independent Test**: Store memories with varying keyword overlap, query with a semantically-similar but lexically-different phrase, and verify both keyword and semantic matches are returned.

**Acceptance Scenarios**:

1. **Given** a memory with exact keyword match, **When** a query contains those keywords, **Then** the memory is retrieved with high relevance score.

2. **Given** a memory with semantic similarity but no keyword overlap (e.g., memory: "I enjoy hiking in the mountains", query: "outdoor activities"), **When** the query is executed, **Then** the memory is retrieved via vector similarity.

3. **Given** both keyword and semantic matches exist, **When** results are merged, **Then** the final ranking combines both signals using reciprocal rank fusion (RRF) or similar.

4. **Given** a query with no matches, **When** retrieval executes, **Then** an empty result set is returned (no forced matches).

---

### User Story 5 – Memory Evaluation Coverage (Priority: P3)

As a developer, I can run memory retrieval evaluations to measure quality and detect regressions.

**Why this priority**: Evaluation coverage ensures retrieval quality doesn't degrade over time. This builds on the Feature 002 eval framework.

**Independent Test**: Run `python -m eval --dataset memory` and verify Recall@K, Precision, and latency metrics are logged to MLflow.

**Acceptance Scenarios**:

1. **Given** a memory golden dataset exists with queries and expected retrievals, **When** the eval suite runs, **Then** each case is evaluated for retrieval correctness.

2. **Given** the eval completes, **When** viewing MLflow results, **Then** metrics include: Recall@5, Precision@5, retrieval latency (p50, p95), and token budget compliance.

3. **Given** retrieval quality falls below threshold (e.g., Recall@5 < 80%), **When** the eval suite completes, **Then** the overall result is FAIL with clear metric breakdown.

---

### Edge Cases

- **Empty memory store**: First-time user with no memories – assistant should respond normally without errors.
- **Token budget exceeded**: Query returns many relevant memories – truncate to budget with relevance-based prioritization.
- **Database timeout**: Postgres or Redis unavailable – fail closed, log error, respond without memory context.
- **Malicious memory content**: If a stored memory contains adversarial content, retrieval should not bypass guardrails.
- **Very long query**: User sends extremely long message – truncate query for embedding, log warning.
- **Concurrent requests**: Multiple requests from same user – each retrieval is independent (no race conditions).

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST persist all conversations and messages to Postgres with user ID, correlation ID, and timestamps.
- **FR-002**: System MUST support typed memory items: `fact`, `preference`, `decision`, `note`.
- **FR-003**: System MUST provide a `query_memory` tool callable by the Agent via OpenAI Agents SDK.
- **FR-004**: System MUST implement hybrid retrieval combining keyword search (full-text) and semantic search (pgvector).
- **FR-005**: System MUST enforce per-user memory scoping – users can only retrieve their own memories.
- **FR-006**: System MUST respect a configurable token budget for memory injection (default: 1000 tokens).
- **FR-007**: System MUST fail closed on retrieval errors – return empty results, never hallucinate.
- **FR-008**: System MUST log all memory retrievals with correlation ID, query hash, result count, and latency.
- **FR-009**: System MUST generate embeddings for stored messages using OpenAI text-embedding-3-small.
- **FR-010**: System MUST store session state (last N messages, current context) in Redis for fast access.

### Key Entities

- **Conversation**: A logical grouping of messages between a user and the assistant. Has user_id, created_at, updated_at, and optional title.
- **Message**: A single turn in a conversation. Has role (user/assistant/system), content, embedding vector, timestamp, and correlation_id.
- **MemoryItem**: A typed, curated piece of information. Has content, type (`fact`/`preference`/`decision`/`note`), source_message_id, importance score, created_at, and optional expires_at.
- **User**: The authenticated user. Has user_id and any auth metadata. (Authentication implementation deferred – assume user_id is available.)

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: Memory retrieval returns relevant results within 200ms (p95) for queries against stores with up to 10,000 memory items.
- **SC-002**: Recall@5 ≥ 80% on the memory golden dataset (correct memory appears in top 5 results).
- **SC-003**: Precision@5 ≥ 70% on the memory golden dataset (≥70% of returned memories are relevant).
- **SC-004**: Zero false cross-user retrievals in security test suite.
- **SC-005**: Memory-grounded responses cite source appropriately (qualitative eval via judge).
- **SC-006**: Token budget compliance: 100% of memory injections respect configured limit.

---

## Data Model

### Tables

#### `conversations`

| Column     | Type         | Constraints             | Description                     |
| ---------- | ------------ | ----------------------- | ------------------------------- |
| id         | UUID         | PRIMARY KEY             | Unique conversation identifier  |
| user_id    | VARCHAR(255) | NOT NULL, INDEX         | User who owns this conversation |
| title      | VARCHAR(500) | NULLABLE                | Optional conversation title     |
| created_at | TIMESTAMPTZ  | NOT NULL, DEFAULT NOW() | Creation timestamp              |
| updated_at | TIMESTAMPTZ  | NOT NULL, DEFAULT NOW() | Last update timestamp           |

**Indexes**: `idx_conversations_user_id` on (user_id), `idx_conversations_updated_at` on (updated_at DESC)

---

#### `messages`

| Column          | Type         | Constraints                     | Description                      |
| --------------- | ------------ | ------------------------------- | -------------------------------- |
| id              | UUID         | PRIMARY KEY                     | Unique message identifier        |
| conversation_id | UUID         | NOT NULL, FK → conversations.id | Parent conversation              |
| role            | VARCHAR(20)  | NOT NULL                        | 'user', 'assistant', or 'system' |
| content         | TEXT         | NOT NULL                        | Message content                  |
| embedding       | VECTOR(1536) | NULLABLE                        | text-embedding-3-small vector    |
| correlation_id  | UUID         | NOT NULL, INDEX                 | Request correlation ID           |
| created_at      | TIMESTAMPTZ  | NOT NULL, DEFAULT NOW()         | Creation timestamp               |

**Indexes**:

- `idx_messages_conversation_id` on (conversation_id)
- `idx_messages_embedding` using ivfflat on (embedding vector_cosine_ops) with (lists = 100)
- `idx_messages_content_fts` using gin on (to_tsvector('english', content))

---

#### `memory_items`

| Column            | Type         | Constraints                | Description                              |
| ----------------- | ------------ | -------------------------- | ---------------------------------------- |
| id                | UUID         | PRIMARY KEY                | Unique memory item identifier            |
| user_id           | VARCHAR(255) | NOT NULL, INDEX            | User who owns this memory                |
| content           | TEXT         | NOT NULL                   | Memory content (human-readable)          |
| type              | VARCHAR(20)  | NOT NULL                   | 'fact', 'preference', 'decision', 'note' |
| embedding         | VECTOR(1536) | NOT NULL                   | Semantic embedding                       |
| source_message_id | UUID         | NULLABLE, FK → messages.id | Message this was derived from            |
| importance        | FLOAT        | NOT NULL, DEFAULT 0.5      | Importance score 0.0-1.0                 |
| created_at        | TIMESTAMPTZ  | NOT NULL, DEFAULT NOW()    | Creation timestamp                       |
| expires_at        | TIMESTAMPTZ  | NULLABLE                   | Optional expiration                      |
| deleted_at        | TIMESTAMPTZ  | NULLABLE                   | Soft delete timestamp                    |

**Indexes**:

- `idx_memory_items_user_id` on (user_id) WHERE deleted_at IS NULL
- `idx_memory_items_embedding` using ivfflat on (embedding vector_cosine_ops) with (lists = 100)
- `idx_memory_items_content_fts` using gin on (to_tsvector('english', content))
- `idx_memory_items_type` on (user_id, type) WHERE deleted_at IS NULL

---

### Redis Keys

| Key Pattern                           | Type   | TTL | Description                                   |
| ------------------------------------- | ------ | --- | --------------------------------------------- |
| `session:{user_id}:{conversation_id}` | Hash   | 24h | Session state (last N messages, current goal) |
| `rate_limit:{user_id}`                | String | 60s | Rate limiting counter                         |
| `embedding_cache:{content_hash}`      | String | 7d  | Cached embeddings to reduce API calls         |

---

## Memory Retrieval API

### Internal Service Interface

```
MemoryQueryRequest:
  user_id: str           # Required: scoped retrieval
  query: str             # The search query (user message or derived)
  limit: int = 10        # Max results to return
  types: list[str] | None  # Filter by memory type (optional)
  min_score: float = 0.3   # Minimum relevance threshold

MemoryQueryResponse:
  items: list[MemoryItem]
  total_count: int
  query_embedding_ms: int   # Time to generate query embedding
  retrieval_ms: int         # Time for database retrieval
  token_count: int          # Estimated tokens in returned content
  truncated: bool           # Whether results were truncated for budget
```

### MemoryItem Response Schema

```
MemoryItem:
  id: str
  content: str
  type: "fact" | "preference" | "decision" | "note"
  relevance_score: float    # Combined score from hybrid retrieval
  source: str | None        # Reference to source message if available
  created_at: datetime
  importance: float
```

---

## Agent Integration

### Memory Query Tool Contract

The Agent is exposed a tool named `query_memory` with the following schema:

```
Tool: query_memory
Description: "Retrieve relevant memories from the user's past conversations and stored context. Use this when the user's question may relate to something discussed previously or when personalization would improve the response."

Parameters:
  query: string (required)
    Description: "Search query to find relevant memories. Should capture the semantic intent of what context would be helpful."

  types: array[string] (optional)
    Description: "Filter to specific memory types"
    Enum: ["fact", "preference", "decision", "note"]

Returns:
  memories: array
    - content: string      # The memory content
    - type: string         # Memory type
    - relevance: number    # 0.0-1.0 relevance score
    - context: string      # Brief source context

  metadata:
    count: number          # Number of memories returned
    truncated: boolean     # Whether more results were available
```

### Agent System Prompt Addition

The Agent's system prompt should include guidance on memory usage:

```
You have access to a memory query tool that can retrieve relevant information from past conversations with this user.

When to use memory:
- User references something discussed previously ("like I mentioned", "remember when")
- User asks about their preferences or past decisions
- Personalization would improve the response quality

When using retrieved memories:
- Treat memories as advisory context, not authoritative fact
- Cite memory sources naturally (e.g., "Based on what you mentioned before...")
- If memory seems outdated or contradicts current context, acknowledge the discrepancy
- Never fabricate memories that weren't retrieved
```

---

## Retrieval Strategy

### Hybrid Search Algorithm

1. **Query Preprocessing**
   - Truncate query to 8192 characters max
   - Generate embedding via text-embedding-3-small

2. **Parallel Retrieval**
   - **Keyword search**: Full-text search using PostgreSQL ts_vector with ts_rank scoring
   - **Semantic search**: Cosine similarity against pgvector embeddings

3. **Score Fusion (Reciprocal Rank Fusion)**

   ```
   RRF_score(item) = Σ 1 / (k + rank_i)

   where:
   - k = 60 (standard RRF constant)
   - rank_i = position in each result list (1-indexed)
   ```

4. **Post-Fusion Processing**
   - Filter by min_score threshold (default 0.3)
   - Apply user_id scoping (mandatory)
   - Sort by RRF_score descending
   - Truncate to token budget

5. **Token Budget Enforcement**
   - Count tokens using tiktoken (cl100k_base encoding)
   - Accumulate items until budget reached
   - Final item may be truncated if partial fit

### Retrieval Parameters

| Parameter     | Default | Configurable | Description                     |
| ------------- | ------- | ------------ | ------------------------------- |
| TOKEN_BUDGET  | 1000    | Yes (env)    | Max tokens for memory injection |
| MIN_RELEVANCE | 0.3     | Yes (env)    | Minimum score threshold         |
| MAX_RESULTS   | 10      | Yes (env)    | Maximum items to return         |
| RRF_K         | 60      | No           | RRF constant (standard value)   |

---

## Safety & Guardrails

### Memory Scoping

- **Mandatory user_id filter**: Every query MUST include user_id in WHERE clause
- **No cross-user joins**: Queries cannot reference other users' data
- **Audit logging**: All retrievals logged with user_id and correlation_id

### Content Safety

- **Input guardrails apply**: User messages are validated before storage
- **Output guardrails apply**: Retrieved memories pass through existing guardrails before Agent use
- **No raw injection**: Memories are formatted with clear delimiters, not injected as system prompts

### Failure Modes

| Failure                  | Behavior                          | User Impact                      |
| ------------------------ | --------------------------------- | -------------------------------- |
| Postgres unavailable     | Fail closed, return empty results | Response proceeds without memory |
| Redis unavailable        | Log warning, skip session cache   | Slightly slower, but functional  |
| Embedding API timeout    | Use cached embedding or skip      | Keyword-only search fallback     |
| Token budget exceeded    | Truncate results                  | Partial memory context           |
| Malformed memory content | Skip item, log error              | Reduced results                  |

### Rate Limiting

- Memory queries limited to 10/minute per user (configurable)
- Exceeding limit returns cached results or empty set
- No hard failure for rate limit (soft degradation)

---

## Evaluation Plan

### Memory Golden Dataset

Create `eval/memory_golden_dataset.json` with test cases:

```json
{
  "version": "1.0.0",
  "description": "Memory retrieval quality evaluation",
  "cases": [
    {
      "id": "recall-preference-001",
      "setup_memories": [
        { "content": "User prefers uv over pip", "type": "preference" }
      ],
      "query": "What package manager should I use?",
      "expected_retrievals": ["User prefers uv over pip"],
      "rubric": "Memory about uv preference MUST appear in top 3 results"
    }
  ]
}
```

### Metrics & Thresholds

| Metric            | Description                | Threshold | Blocking  |
| ----------------- | -------------------------- | --------- | --------- |
| Recall@5          | Correct memory in top 5    | ≥ 80%     | Yes       |
| Precision@5       | Relevant memories in top 5 | ≥ 70%     | Yes       |
| Latency (p95)     | Query-to-response time     | ≤ 200ms   | No (warn) |
| Token Compliance  | Injections within budget   | 100%      | Yes       |
| Cross-User Safety | No cross-user retrievals   | 100%      | Yes       |

### Eval Integration

- Extend `eval/runner.py` to support `--dataset memory` flag
- Log memory-specific metrics to MLflow alongside quality metrics
- Add security cases testing user_id scoping

---

## Open Questions / Follow-Ups

_Deferred to Memory v2 or later:_

1. **Automatic memory extraction**: How should the system identify facts/preferences from conversations? (v2)
2. **Memory consolidation**: How to merge overlapping or contradictory memories? (v2)
3. **Importance scoring**: How is importance calculated and updated over time? (v2)
4. **Memory expiration**: What triggers expiration and how is it enforced? (v2)
5. **User memory management UI**: How can users view/edit/delete their memories? (future)
6. **Authentication integration**: How is user_id derived from requests? (assume available for now)

---

## Assumptions

- **User ID available**: Authentication is handled upstream; user_id is available in request context.
- **Postgres with pgvector**: Docker compose includes Postgres with pgvector extension enabled.
- **Redis available**: Docker compose includes Redis for session state.
- **OpenAI API access**: Embedding API (text-embedding-3-small) is available via existing OPENAI_API_KEY.
- **Seed data for testing**: Initial memory items will be manually seeded for testing; automatic extraction is v2.
