# Memory Vision — Personal AI Assistant

> **Related Documents:** See [vision.md](vision.md) for the overall feature roadmap. Memory phases map to specific features in that document.

## Purpose

This document defines the **long-term vision and guiding principles** for memory in the Personal AI Assistant.

Memory is not treated as a single feature, but as a **foundational capability** that evolves across multiple features. This vision ensures consistency, safety, and clarity as memory is incrementally introduced, expanded, and operationalized.

---

## What Memory Is (and Is Not)

### Memory **IS**

- A structured, inspectable system for **recall, continuity, and personalization**
- A mechanism for grounding assistant responses in **past context**
- A substrate for **background jobs**, preparation, and proactive assistance
- A system with **clear provenance and reversibility**

### Memory **IS NOT**

- A raw dump of chat transcripts
- An unbounded embedding store
- A black-box “the assistant remembers everything”
- A replacement for reasoning or tools

---

## Memory Design Goals

### 1. **Trust First**

The user must be able to understand:

- what is remembered
- why it was remembered
- how it is used
- how it can be forgotten

### 2. **Progressive Disclosure**

Memory capabilities are introduced gradually:

- read-only recall before automatic writes
- explicit memory before inferred memory
- deterministic retrieval before semantic expansion

### 3. **Separation of Concerns**

Different kinds of memory serve different purposes and lifecycles:

- session state ≠ conversation history ≠ durable memory
- memory storage ≠ retrieval ≠ synthesis

### 4. **Evaluation-Ready**

Memory behavior must be testable:

- retrieval correctness
- over-recall vs under-recall
- safety regressions
- cost and latency impact

### Memory Eval Metrics

| Metric          | What It Measures                            |
| --------------- | ------------------------------------------- |
| Recall@K        | Did the right memories surface in top K?    |
| Precision       | What % of retrieved memories were relevant? |
| False injection | Did irrelevant/harmful memories get used?   |
| Latency         | Retrieval time under budget?                |
| Token budget    | Memory injection ≤ target token count?      |

Memory evaluation integrates with the existing MLflow eval framework via a dedicated `memory_golden_dataset.json`.

---

## Memory Layers (Conceptual Model)

### 1. Session Memory (Ephemeral)

**Purpose:** Maintain conversational coherence
**Characteristics:**

- Short-lived
- Fast
- Safe to lose
- Not embedded

**Examples:**

- last N messages
- current goal
- recent tool results

---

### 2. Conversation Memory (Durable Transcript)

**Purpose:** Source-of-truth history
**Characteristics:**

- Append-only
- Auditable
- Never directly injected wholesale
- Supports re-derivation

**Examples:**

- messages
- tool calls
- model outputs

---

### 3. Long-Term Memory (Curated)

**Purpose:** Recall and personalization
**Characteristics:**

- Intentional
- Human-readable
- Typed (facts, preferences, decisions)
- Searchable (keyword + semantic)

**Examples:**

- “User prefers Poetry over pip”
- “Project stack includes FastAPI, Docker, Postgres”
- “User plans winter camping in February”

---

## Memory Content Types

Memory items are **atomic and typed**, not free-form blobs.

| Type       | Description                                |
| ---------- | ------------------------------------------ |
| Episode    | Summary of a meaningful interaction window |
| Fact       | Stable, objective information              |
| Preference | User-stated or confirmed preference        |
| Decision   | Chosen path or resolved option             |
| Note       | Low-confidence or contextual information   |

Each memory item has:

- source (messages / job / tool)
- importance
- optional expiration
- reversible deletion

---

## Retrieval Philosophy

Memory retrieval must be:

- **Selective** (few high-signal items)
- **Explainable** (why this memory surfaced)
- **Composable** (keyword + semantic)
- **Budgeted** (token-aware)

Memory is injected as **contextual grounding**, never as authoritative truth.

---

## Knowledge Graph

The knowledge graph captures **structured relationships** between entities mentioned in conversations. It complements the memory store by enabling relationship-based queries that vector search cannot answer well.

### Purpose

- Track connections between people, projects, tools, and concepts
- Answer "how does X relate to Y?" queries
- Provide context for decisions and preferences
- Enable reasoning about user's world model

### Design Principles

1. **Derived, not primary**: The graph is built from conversation transcripts and memory items. Raw transcripts remain canonical.

2. **Provenance required**: Every edge must link back to source material (message, episode, or memory item).

3. **Confidence-aware**: Entity resolution and relationship extraction include confidence scores. Low-confidence items are flagged for review.

4. **Conservative merging**: Ambiguous entity matches are kept separate rather than incorrectly merged. Complex consolidation is deferred to background jobs.

5. **User-scoped**: Graph data is strictly per-user. No cross-user relationships.

### Entity Types

| Type       | Description                              |
| ---------- | ---------------------------------------- |
| person     | People mentioned (friends, colleagues)   |
| project    | Projects, repos, initiatives             |
| tool       | Tools, libraries, services               |
| concept    | Abstract ideas, topics                   |
| decision   | Choices made                             |
| preference | Stated preferences                       |
| goal       | User goals and intentions                |

### Relationship Types

| Relationship  | Description                        |
| ------------- | ---------------------------------- |
| USES          | User/project uses a tool           |
| PREFERS       | User prefers X over Y              |
| DECIDED       | User decided on X                  |
| WORKS_ON      | User works on project              |
| KNOWS         | User knows person                  |
| DEPENDS_ON    | Project depends on tool/service    |
| MENTIONED_IN  | Entity mentioned in episode        |

### Retrieval Routing

The agent chooses retrieval method based on query type:

- **Graph retrieval**: Relationship queries ("What tools do I use for project X?")
- **Vector retrieval**: Narrative queries ("What did we discuss about the trip?")
- **Combined**: Complex queries requiring both context and relationships

---

## Summarization & Insight Extraction

The assistant may:

- summarize conversation windows
- extract durable insights
- consolidate overlapping memories

But:

- summaries are _derived artifacts_
- raw transcripts remain canonical
- memory writes are observable and testable

Automatic memory creation is **earned**, not assumed.

---

## Background Jobs & Proactivity

Memory enables **time-shifted intelligence**, not constant interruption.

Examples:

- morning briefings (news + weather)
- hobby preparation
- trend detection across weeks
- readiness summaries (“You have a trip coming up…”)

All proactive behavior must:

- cite memory sources
- declare assumptions
- remain opt-in

---

## Safety & Guardrails

Memory must respect:

- user boundaries
- scope of consent
- data minimization

Memory systems must:

- fail closed
- support forgetting
- never cross user boundaries
- be auditable via logs and evals

---

## Relationship to Feature Roadmap

Memory is intentionally **multi-feature**, with each phase shipping as a distinct feature in [vision.md](vision.md):

| Phase           | Capability                                   | Feature     |
| --------------- | -------------------------------------------- | ----------- |
| Memory v1       | Read-only recall (keyword + semantic)        | Feature 004 ✅ |
| Memory v2       | Automatic summarization + insight extraction | Feature 006 ✅ |
| Knowledge Graph | Entity relationships + graph retrieval       | Feature 007 |
| Memory v3       | Background jobs + proactive synthesis        | Feature 008 |
| Memory v4       | Personalization + long-horizon planning      | Future      |

Each phase:

- ships independently
- has eval coverage
- builds on previous guarantees

---

## Success Criteria

The memory system is successful when:

- the assistant feels _continuous but not invasive_
- memory improves usefulness without surprising behavior
- failures are diagnosable
- additions do not require redesign

---

## Non-Goals

This vision explicitly does **not** attempt to:

- replicate human memory
- achieve perfect recall
- infer sensitive traits
- act autonomously without oversight

---

## Guiding Principle

> **Memory exists to make the assistant more helpful tomorrow — not more confident today.**
