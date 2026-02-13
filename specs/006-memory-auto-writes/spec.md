# Feature Specification: Memory v2 – Automatic Writes

**Feature Branch**: `006-memory-auto-writes`  
**Created**: 2026-02-02  
**Status**: Draft  
**Input**: User description: "Allow the assistant to remember important information automatically without requiring users to repeat themselves."

> **Related Documents:**
>
> - [vision.md](../../vision.md) – Feature 006 in roadmap, Memory Architecture section
> - [004-memory-v1-readonly-recall/spec.md](../004-memory-v1-readonly-recall/spec.md) – Foundation this builds on

---

## Clarifications

### Session 2026-02-03

- Q: What confidence threshold triggers automatic memory creation vs. user confirmation? → A: Moderate threshold (0.7) — auto-save ≥0.7, confirm 0.5-0.7, discard <0.5.
- Q: What rate limits apply to memory creation? → A: Moderate (10 memories per conversation, 25 per hour).
- Q: What triggers episode summarization for a conversation? → A: 8+ user messages OR 15+ total exchanges.
- Q: How should conflicting information be handled (correction strategy)? → A: Supersede — create new memory, mark old as superseded with back-reference (preserves audit trail).
- Q: How should the assistant acknowledge memory writes? → A: Inline subtle acknowledgment (e.g., "I'll remember you prefer..."), at assistant's discretion based on whether it's useful to the user.
- Q: How does the agent delete memories? → A: Via a dedicated `delete_memory` tool, separate from `save_memory`.
- Q: Should the system prevent duplicate memories? → A: Yes, similarity check before write (MVP scope). Full consolidation of related memories is deferred.
- Q: When does extraction vs. persistence happen? → A: Extraction (deciding what to remember, confidence scoring, user confirmation) happens during response generation. Persistence (database write, embedding generation) happens asynchronously after the response, so it never delays the conversation.

---

## Feature Overview

### Goal

Enable the assistant to automatically extract and persist important information from conversations, creating durable memories that improve future interactions. Users no longer need to repeat information they've already shared.

### Building on Memory v1

Memory v1 established read-only retrieval from a curated memory store. Memory v2 extends this with:
- **Automatic write capability**: The system creates memory items from conversations
- **Insight extraction**: Extraction of facts, preferences, and decisions from user messages
- **Conversation summarization**: Episodic summaries of meaningful interaction windows
- **User control**: Observable writes with ability to correct or delete memories

### User Capability

> "The assistant remembers what I told it without me having to repeat myself."

### Non-Goals

This feature explicitly does **not** include:

- **Knowledge graph / entity relationships**: Entity extraction and relationship tracking is Feature 007
- **Background jobs**: No offline processing or scheduled tasks (Feature 008)
- **Proactive suggestions**: No unsolicited notifications based on memories
- **Cross-user memory**: Memory remains strictly scoped per user
- **Automatic memory consolidation**: Merging related memories or reducing redundancy across topics is deferred (basic duplicate prevention at write time is in scope)

---

## User Scenarios & Testing

### User Story 1 – Automatic Fact Extraction (Priority: P1) 🎯 MVP

As a user, when I share important information about myself during a conversation, the assistant automatically saves it as a memory so I don't have to repeat it later.

**Why this priority**: This is the core value proposition. Without automatic extraction, users must manually manage memories, defeating the purpose.

**Independent Test**: Tell the assistant "I'm a vegetarian" in one conversation, start a new conversation and ask for dinner recommendations, verify the assistant recalls the dietary preference.

**Acceptance Scenarios**:

1. **Given** the user says "I prefer TypeScript over JavaScript for all my projects", **When** the conversation completes, **Then** a memory item of type `preference` is created with this information.

2. **Given** the user shares "My cat's name is Luna", **When** the message is processed, **Then** a memory item of type `fact` is created linking to the source message.

3. **Given** the user mentions something trivial like "I'm going to grab a coffee", **When** the message is processed, **Then** no memory item is created (low importance filtering).

4. **Given** a memory is created, **When** the user queries their memories or the assistant retrieves them, **Then** the memory includes provenance (source message reference and timestamp).

---

### User Story 2 – Memory Write Observability (Priority: P1) 🎯 MVP

As a user, I can see when the assistant saves something to memory so I know what it remembers and can correct mistakes.

**Why this priority**: Trust requires transparency. Users must know what is being remembered to feel in control.

**Independent Test**: Share information that triggers a memory write, verify the assistant's response acknowledges the memory creation (e.g., "I'll remember that you prefer...").

**Acceptance Scenarios**:

1. **Given** the assistant creates a new memory, **When** the response is generated, **Then** the assistant may acknowledge what was remembered inline in a natural way when it adds value to the conversation (acknowledgment is discretionary).

2. **Given** the assistant attempts to create a memory, **When** extraction confidence is between 0.5–0.7, **Then** the assistant asks for confirmation ("Should I remember that you prefer X?").

3. **Given** a memory was recently created, **When** the user asks "What do you remember about me?", **Then** the assistant can list recently created memories with their sources.

4. **Given** a memory write fails (database error), **When** the failure occurs, **Then** the assistant continues the conversation gracefully and logs the failure for retry.

---

### User Story 3 – Memory Correction (Priority: P2)

As a user, I can correct or delete memories the assistant has saved so outdated or incorrect information doesn't affect future conversations.

**Why this priority**: Users need agency over their data. Without correction capability, wrong memories persist indefinitely.

**Independent Test**: Create a memory via conversation, then say "Actually, I changed my mind - I now prefer Python over TypeScript", verify the old memory is updated or superseded.

**Acceptance Scenarios**:

1. **Given** a memory exists that "User prefers TypeScript", **When** the user says "I've switched to Python now", **Then** a new superseding preference is created and the old memory is marked as superseded with a reference to the new one.

2. **Given** any memory exists, **When** the user says "Forget that I told you about [topic]", **Then** the relevant memory is soft-deleted and no longer retrieved.

3. **Given** a memory was corrected or deleted, **When** the user asks about the topic, **Then** only the current, correct information is retrieved.

4. **Given** the user requests deletion, **When** the assistant identifies the memory, **Then** the assistant confirms what will be forgotten before executing the deletion.

---

### User Story 4 – Conversation Episode Summarization (Priority: P2)

As a user, the assistant summarizes meaningful conversations into episode memories so the context of past discussions is preserved without storing every message.

**Why this priority**: Raw message storage is insufficient for long-term context. Summaries enable efficient retrieval of conversation gist.

**Independent Test**: Have a multi-turn conversation about planning a trip, verify an episode summary is created capturing the key decisions and context.

**Acceptance Scenarios**:

1. **Given** a conversation with 10+ meaningful exchanges, **When** the conversation ends or a natural break occurs, **Then** an episode summary is generated capturing: topic, key points, decisions made, and outstanding questions.

2. **Given** an episode summary is created, **When** stored as a memory item, **Then** it has type `episode` and links to the source conversation/messages.

3. **Given** the user asks "What did we discuss about my trip last week?", **When** memory retrieval runs, **Then** the episode summary is returned with relevant context.

4. **Given** a short, trivial conversation (e.g., single weather query), **When** the conversation ends, **Then** no episode summary is created (conversation too shallow).

---

### User Story 5 – Decision Extraction (Priority: P3)

As a user, when I make explicit decisions during a conversation, the assistant remembers those decisions so it can reference them in future discussions.

**Why this priority**: Decisions are high-value memories that prevent re-litigating resolved questions.

**Independent Test**: Tell the assistant "I've decided to use PostgreSQL for this project", later ask "What database am I using?", verify the decision is recalled.

**Acceptance Scenarios**:

1. **Given** the user says "I'm going to use FastAPI for the backend", **When** this is detected as a decision, **Then** a memory item of type `decision` is created.

2. **Given** decision language is ambiguous ("I'm thinking about using X"), **When** processing the message, **Then** the assistant asks for confirmation before saving as a definite decision.

3. **Given** a decision contradicts a previous decision, **When** creating the new memory, **Then** the old decision is marked as superseded with a reference to the new one.

---

### User Story 6 – Memory Write Evaluation (Priority: P3)

As a developer, I can evaluate the quality of memory extraction to ensure the system captures relevant information accurately.

**Why this priority**: Evaluation prevents quality degradation and enables tuning extraction logic.

**Independent Test**: Run `python -m eval --dataset memory-writes` and verify precision, recall, and relevance metrics are logged to MLflow.

**Acceptance Scenarios**:

1. **Given** a memory write golden dataset with conversations and expected extractions, **When** the eval suite runs, **Then** each case is evaluated for extraction correctness.

2. **Given** the eval completes, **When** viewing MLflow results, **Then** metrics include: Extraction Precision (% of writes that should have been made), Extraction Recall (% of expected writes that were made), Relevance score (judge-rated quality).

3. **Given** extraction quality falls below threshold, **When** the eval suite completes, **Then** the overall result is FAIL with clear metric breakdown.

---

### Edge Cases

- **Conflicting information**: User says contradictory things in same conversation – capture most recent, flag for low confidence.
- **Sensitive information**: User shares potentially sensitive data (health, finances) – standard extraction applies; no special redaction in this phase.
- **Very long conversations**: Conversation with 100+ messages – use windowed summarization, don't attempt full context.
- **Rapid corrections**: User corrects themselves immediately ("I mean Y, not X") – only extract the corrected information.
- **Multi-topic conversations**: Single conversation covers many topics – generate multiple memories/summaries as appropriate.
- **Implicit information**: User implies but doesn't state ("I'll pick up my kids from school") – extract with lower confidence, note inference.
- **Rate limiting**: Prevent memory spam from adversarial users – max N memories per conversation/hour.

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST automatically extract memory items from user messages when confidence score ≥ 0.7.
- **FR-002**: System MUST support memory types: `fact`, `preference`, `decision`, `note`, `episode`.
- **FR-003**: System MUST provide a `save_memory` tool callable by the Agent for explicit memory writes.
- **FR-003a**: System MUST provide a `delete_memory` tool callable by the Agent for memory deletion and correction.
- **FR-004**: System MUST include provenance with every memory write (source_message_id, source_conversation_id).
- **FR-005**: System MUST allow the assistant to acknowledge memory writes inline (e.g., "I'll remember that...") when useful to the user; acknowledgment is discretionary, not mandatory.
- **FR-006**: System MUST request user confirmation for extractions with confidence 0.5–0.7 before writing.
- **FR-006a**: System MUST discard potential extractions with confidence < 0.5 (too uncertain to surface).
- **FR-007**: System MUST support memory correction via natural conversation ("Actually, I prefer X now").
- **FR-008**: System MUST support memory deletion via natural conversation ("Forget that I told you X").
- **FR-009**: System MUST implement soft-delete for all memory deletions (preserve audit trail).
- **FR-010**: System MUST generate episode summaries for conversations with 8+ user messages OR 15+ total exchanges.
- **FR-011**: System MUST log all memory writes with correlation ID, extraction type, confidence, and processing time.
- **FR-012**: System MUST enforce rate limits on memory creation (max 10 per conversation, 25 per hour per user).
- **FR-013**: System MUST mark superseded memories when conflicting information is extracted.
- **FR-014**: System MUST check for duplicate memories before writing (semantic similarity check) and skip creation if a substantially similar memory already exists.
- **FR-015**: System MUST respect per-user memory scoping – users can only write/modify their own memories.
- **FR-016**: System MUST fail closed on write errors – log failure, continue conversation, queue for retry.
- **FR-017**: Extraction decisions (what to remember, confidence scoring, user confirmation) MUST occur during response generation. Persistence (database write, embedding generation) MUST occur asynchronously after the response is sent, never blocking the conversation.

### Key Entities

- **MemoryItem** (extended): Adds `source_conversation_id`, `confidence` score, `superseded_by` reference, and `status` (active, superseded, deleted).
- **MemoryWriteEvent**: Audit log of all memory operations. Has operation type (create, update, delete), before/after state, actor (user/system), and timestamp.
- **Episode**: A summary of a conversation window. Has conversation_id, summary content, key_points, decisions, and time_range.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: Extraction Precision ≥ 85% – at least 85% of created memories should be worth remembering (judge-rated).
- **SC-002**: Extraction Recall ≥ 70% – system captures at least 70% of information a human would flag as memorable.
- **SC-003**: Users can correct or delete memories within a single conversational turn (no multi-step flows).
- **SC-004**: Memory writes complete within 500ms (p95) of message processing, not blocking response.
- **SC-005**: 100% of memory writes include valid provenance (source message/conversation linkage).
- **SC-006**: User satisfaction: 80%+ of users report the assistant "remembers appropriately" (future survey metric).
- **SC-007**: False positive rate < 5% – less than 5% of memories created should be trivial/irrelevant.
- **SC-008**: Zero unauthorized cross-user memory writes in security test suite.

---

## Assumptions

- Memory v1 infrastructure (conversations, messages, memory_items tables, hybrid retrieval) is operational and stable.
- OpenAI API (for extraction via GPT-4 or similar) is available with acceptable latency and cost.
- Episode summarization uses the same model as chat responses (no separate summarization model).
- User authentication provides a stable user_id for memory scoping (deferred to auth feature).
- Extraction decisions happen during response generation (the agent decides whether to save, confirm, or ignore). Persistence (embedding + DB write) is asynchronous and never blocks the user.

---

## Dependencies

- **Feature 004 (Memory v1)**: Database schema, retrieval infrastructure, memory query tool
- **Feature 002 (Eval Framework)**: MLflow integration for memory write evaluation
- **Feature 003 (Security Guardrails)**: Input/output guardrails apply to memory content

---

## Out of Scope (Explicitly Deferred)

- **Automatic consolidation**: Merging related or overlapping memories across conversations (basic duplicate prevention at write time is in scope)
- **Memory importance decay**: Reducing importance of old/unused memories over time
- **Proactive memory suggestions**: "You mentioned X last month, is that still true?"
- **Bulk memory export/import**: User data portability
- **Memory encryption at rest**: Beyond standard database encryption
