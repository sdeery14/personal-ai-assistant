# Personal AI Assistant — Vision

This document is the single source of truth for the project's direction. It defines guiding principles, the memory architecture that underpins multiple features, and the feature roadmap.

The roadmap intentionally builds **capability + safety + confidence** in layers. Each feature delivers a clear, testable user capability and becomes the foundation for the next.

---

## Guiding Principles

### Build in Layers

Each feature ships independently with eval coverage, builds on previous guarantees, and follows the constitution. No capability is introduced without the safety and observability foundations beneath it.

### Memory Design Goals

Memory is not a single feature — it is a **foundational capability** that evolves across multiple features.

1. **Trust First** — The user must be able to understand what is remembered, why it was remembered, how it is used, and how it can be forgotten.
2. **Progressive Disclosure** — Read-only recall before automatic writes. Explicit memory before inferred memory. Deterministic retrieval before semantic expansion.
3. **Separation of Concerns** — Session state ≠ conversation history ≠ durable memory. Memory storage ≠ retrieval ≠ synthesis.
4. **Evaluation-Ready** — Memory behavior must be testable: retrieval correctness, over-recall vs under-recall, safety regressions, cost and latency impact.

### Safety & Guardrails

All systems (memory and otherwise) must:

- Fail closed
- Support forgetting / reversal
- Never cross user boundaries
- Be auditable via logs and evals
- Respect scope of consent and data minimization

---

## Memory Architecture

### What Memory Is (and Is Not)

**Memory IS:**
- A structured, inspectable system for recall, continuity, and personalization
- A mechanism for grounding assistant responses in past context
- A substrate for background jobs, preparation, and proactive assistance
- A system with clear provenance and reversibility

**Memory IS NOT:**
- A raw dump of chat transcripts
- An unbounded embedding store
- A black-box "the assistant remembers everything"
- A replacement for reasoning or tools

### Memory Layers

| Layer | Purpose | Characteristics | Examples |
|-------|---------|-----------------|----------|
| **Session** (Ephemeral) | Conversational coherence | Short-lived, fast, safe to lose | Last N messages, current goal, recent tool results |
| **Conversation** (Durable Transcript) | Source-of-truth history | Append-only, auditable, never injected wholesale | Messages, tool calls, model outputs |
| **Long-Term** (Curated) | Recall and personalization | Intentional, human-readable, typed, searchable | "User prefers Poetry over pip", "Project uses FastAPI" |

### Memory Content Types

Memory items are **atomic and typed**, not free-form blobs.

| Type | Description |
|------|-------------|
| Episode | Summary of a meaningful interaction window |
| Fact | Stable, objective information |
| Preference | User-stated or confirmed preference |
| Decision | Chosen path or resolved option |
| Note | Low-confidence or contextual information |

Each memory item has: source (messages / job / tool), importance, optional expiration, and reversible deletion.

### Retrieval Philosophy

Memory retrieval must be **selective** (few high-signal items), **explainable** (why this memory surfaced), **composable** (keyword + semantic), and **budgeted** (token-aware). Memory is injected as contextual grounding, never as authoritative truth.

The agent chooses retrieval method based on query type:

- **Graph retrieval**: Relationship queries ("What tools do I use for project X?")
- **Vector retrieval**: Narrative queries ("What did we discuss about the trip?")
- **Combined**: Complex queries requiring both context and relationships

### Summarization & Insight Extraction

The assistant may summarize conversation windows, extract durable insights, and consolidate overlapping memories — but summaries are derived artifacts, raw transcripts remain canonical, and memory writes are observable and testable. Automatic memory creation is **earned**, not assumed.

### Memory Eval Metrics

| Metric | What It Measures |
|--------|-----------------|
| Recall@K | Did the right memories surface in top K? |
| Precision | What % of retrieved memories were relevant? |
| False injection | Did irrelevant/harmful memories get used? |
| Latency | Retrieval time under budget? |
| Token budget | Memory injection ≤ target token count? |

---

## Feature Roadmap

### Feature 001 – Core Streaming Chat API

> "I can send a message and receive a streamed response from the assistant."

OpenAI Agents SDK integration, server-side SSE streaming, request lifecycle with correlation IDs, structured logging and basic error handling.

---

### Feature 002 – Evaluation Harness (MLflow)

> "I can tell if the assistant got better or worse after a change."

Golden test dataset, LLM-as-judge scoring with rubrics, MLflow-backed run tracking, pass/fail thresholds with regression gating, CI gate for prompt/routing changes.

---

### Feature 003 – Security Guardrails

> "The assistant blocks dangerous requests and never produces harmful content."

Input guardrails via OpenAI Moderation API, output guardrails with stream retraction, fail-closed behavior with exponential backoff retry, security red-team golden dataset, security-specific eval metrics (block rate, false positive rate).

---

### Feature 004 – Memory v1 (Read-Only Recall)

> "The assistant can look up relevant past information when answering."

Hybrid search (keyword + semantic), read-only memory store with typed items, explicit memory query tool for the Agent, retrieval-only grounding in responses, memory retrieval eval coverage.

---

### Feature 005 – Weather Lookup

> "The assistant can accurately tell me the weather."

Single weather provider, schema-validated tool calls, caching of safe responses, clear error states and fallbacks.

---

### Feature 006 – Memory v2 (Automatic Writes)

> "The assistant remembers what I told it without me having to repeat myself."

Automatic summarization of conversation windows, insight extraction (facts, preferences, decisions), user-observable memory writes with provenance, memory correction and deletion via conversation.

---

### Feature 007 – Knowledge Graph

> "The assistant understands how things I mention relate to each other."

Entity extraction from conversations (people, projects, tools, concepts), relationship tracking with typed edges, graph-based retrieval tool for relationship queries, provenance linking all graph elements to source messages, entity resolution with confidence scoring.

---

### Feature 008 – Web Frontend (Next.js)

> "I can chat with the assistant through a real UI in my browser."

Next.js app consuming the existing SSE chat API. Conversation view with streaming responses, memory/knowledge graph visibility. Provides the interaction layer that voice, edge clients, and background job notifications build on top of.

---

### Feature 009 – Background Jobs & Proactivity (Memory v3)

> "The assistant prepares helpful information before I ask for it."

Background job execution framework, morning briefings (news, weather, calendar), trip/event preparation summaries, opt-in proactive notifications, graph consolidation and entity merging. All proactive behavior must cite memory sources, declare assumptions, and remain opt-in.

---

### Feature 010 – Voice Interaction

> "I can talk to the assistant and hear it respond."

Phased: TTS-only output first, then two-way voice with speech-to-text input and turn-based conversations.

---

### Feature 011 – Edge Client (Raspberry Pi)

> "I can interact with the assistant from a Raspberry Pi."

Text-based interface (CLI / button / simple display), connection to existing backend, minimal local state.

---

### Feature 012 – Google Integrations (Read-Only)

> "The assistant can tell me about my emails and calendar events."

Gmail read/search, calendar read, explicit permission prompts, audit logging. No sending emails or modifying calendar events.

---

### Future Capabilities

- Memory v4: Long-horizon personalization and planning
- Tool-based reasoning (context-aware suggestions using memory + tools)
- Task automation and write-capable integrations
- Multi-modal inputs (images, documents)
- Additional tool integrations

Each new capability must follow the constitution, include evaluation coverage, and be introduced as its own scoped feature.

---

## Non-Goals

- Replicate human memory
- Achieve perfect recall
- Infer sensitive traits
- Act autonomously without oversight

---

> **Memory exists to make the assistant more helpful tomorrow — not more confident today.**
