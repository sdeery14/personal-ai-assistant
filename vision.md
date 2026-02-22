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

### Cost & Resource Awareness

- **Token budgets**: Each request and feature has an explicit token budget; memory injection, system prompts, and tool outputs are metered against it
- **Caching strategy**: Redis for embeddings, weather responses, and rate-limit counters — avoid redundant API calls
- **Model tiering**: Use cheaper models (e.g., GPT-4o-mini) where quality is sufficient (guardrails, summarization); reserve expensive models for user-facing generation
- **Observable cost**: Log token usage per request, track per-feature spend in evals, surface cost regressions alongside quality regressions

---

## Multi-User Architecture

This is a **multi-tenant system** with strict per-user data isolation.

- Every data table is scoped by `user_id`; all queries enforce isolation at the application layer
- **Role model**: admin (user management, system configuration) vs. regular user (own data only)
- Admins manage accounts but **cannot access other users' data** — admin privileges grant management, not visibility
- Future consideration: database-level Row-Level Security (RLS) for defense-in-depth, ensuring isolation holds even if application-layer checks are bypassed

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

## Data Lifecycle & Portability

- **Backup**: PostgreSQL is the single point of failure; the `postgres_data` Docker volume holds all state. An automated `pg_dump` strategy (scheduled, versioned, off-host) is needed before production use.
- **Export**: Per-user data export (conversations, memories, knowledge graph) in a portable format for data portability and compliance (e.g., GDPR right to data portability).
- **Retention**: Memory `expires_at` exists but no cleanup job yet. Define retention policies per data type — ephemeral session data (days), conversation transcripts (indefinite), memories (user-controlled or expiry-based).
- **Deletion**: Soft deletes exist across the data model. A full user data purge capability is needed for account deletion — removing all conversations, memories, entities, relationships, and auth tokens for a given user.
- **Disaster recovery**: Documented restore procedures from backup, including database recreation, volume restoration, and verification steps.

---

## Integration Extensibility

### Current Pattern

Tools are `@function_tool`-decorated async functions in `src/tools/`, dynamically imported with graceful fallback in `ChatService._get_tools()`. Each tool is self-contained: validates inputs, instantiates its service on-demand, and returns JSON. Context (user_id, correlation_id, conversation_id) is injected via `RunContextWrapper`.

### Adding New Integrations

New integrations follow the same pattern: tool module (`src/tools/`) + service module (`src/services/`) + feature-specific system prompt fragment. The tool handles orchestration, the service handles external API interaction, and the system prompt teaches the agent when and how to use the tool.

### Vision: Tool Registry

Replace the manual import chain in `ChatService._get_tools()` with a lightweight tool registry — a declarative structure mapping each tool to its metadata (feature ID, required system prompt, required services, enabled-by-default flag). This enables:

- Dynamic tool discovery and feature-flag gating
- Per-user tool enablement preferences
- Cleaner startup and dependency validation

### Future Plugin Considerations

For third-party or community tools: discovery (registry listing), validation (schema conformance, sandboxed execution), and capability declarations (what data the tool reads/writes).

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

Single weather provider, schema-validated tool calls, caching of safe responses, clear error states and fallbacks. *(Placed before Memory v2 as a low-risk proof-of-concept for the tool-calling pattern, validating the `@function_tool` integration model before the more complex automatic memory writes.)*

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

### Feature 009 – Dark Mode & Theming

> "The app looks great whether I prefer light or dark mode."

System-aware theme detection (prefers-color-scheme) with manual toggle, persistent preference, and consistent dark/light palettes across all components. Tailwind CSS dark variant strategy with CSS custom properties for seamless switching.

---

### Feature 010 – Agent Notifications

> "The assistant can send me messages even when I'm not actively chatting."

Notification infrastructure that gives the agent a voice outside of reactive chat. In-app notifications for when the user is in the frontend, email delivery for when they're not.

- **Notification store**: `notifications` table in PostgreSQL (user_id, message, type, read/unread, source, created_at), scoped by user_id
- **Agent tool**: `send_notification` — the agent decides during conversation when something is worth notifying about (e.g., "I'll remind you about this later")
- **In-app delivery**: Bell icon, notification panel with unread count in the frontend
- **Email delivery**: SMTP or transactional email service (SendGrid, SES) for out-of-app reach
- **User preferences**: Per-user control over delivery channels (in-app only, email, both) and quiet hours
- **Not in scope**: No scheduling or autonomous triggers — notifications are created during active conversations. Background Jobs (Feature 011) adds the scheduler that creates notifications without user interaction.

---

### Feature 011 – Background Jobs & Scheduled Tasks

> "The assistant can run tasks on a schedule and notify me of results."

Background job execution framework, cron-style scheduling, morning briefings (weather, calendar summary), trip/event preparation from templates, opt-in notifications via the frontend. Proves the plumbing for scheduled execution — jobs are configured explicitly, not autonomously chosen.

- **Job runner**: Python async task queue (e.g., APScheduler or Celery with Redis broker, leveraging existing Redis infrastructure)
- **Notification transport**: Leverages Feature 010 notification infrastructure; adds WebSocket push for real-time delivery
- **Job types**: cron-scheduled (morning briefing), event-triggered (new entity detected), user-initiated (run now)
- **Persistence**: Job definitions and run history stored in PostgreSQL, scoped by user_id
- **Observability**: Structured logging per job execution, success/failure metrics, duration tracking
- **Scope**: Jobs are explicitly configured by user or admin, not autonomously chosen by the assistant
- **Open questions**: Max concurrent jobs per user, retry policy, job timeout limits

---

### Feature 012 – Proactive Relevance Engine (Memory v3)

> "The assistant connects what it can do to what might be helpful, and gets better at it over time."

Reasoning layer that connects user context (memory, knowledge graph, schedule) with available capabilities (tools, integrations) to surface timely, relevant suggestions. Relevance scoring based on user patterns and entity relationships. Feedback loop: tracks which suggestions the user engaged with vs. dismissed, adjusts future behavior accordingly. All proactive suggestions cite sources, declare confidence, and respect opt-in preferences. Builds on Feature 011 scheduling infrastructure and Feature 007 knowledge graph.

- **Relevance scoring**: Entity recency, mention frequency, relationship strength, user engagement history
- **Feedback loop**: Track suggestion engagement vs. dismissal, adjust scoring weights over time
- **Confidence thresholds**: Suggestions below threshold are suppressed; thresholds adapt per user based on feedback
- **Privacy**: All suggestions cite sources, declare confidence, respect opt-in preferences
- **Dependencies**: Feature 007 (knowledge graph), Feature 011 (scheduling infrastructure)
- **Eval coverage**: Suggestion precision, engagement rate, false-positive suppression rate

---

### Feature 013 – Voice Interaction

> "I can talk to the assistant and hear it respond."

Phased: TTS-only output first, then two-way voice with speech-to-text input and turn-based conversations.

- **Phase 1 (TTS output)**: Browser-based Web Speech API or OpenAI TTS, streamed alongside text SSE
- **Phase 2 (STT input)**: Browser MediaRecorder → Whisper API or Web Speech Recognition
- **Latency target**: First audio chunk within 500ms of response start
- **Architecture**: Voice is a frontend transport layer; backend remains text-based SSE — no audio processing server-side
- **Fallback**: Text always available; voice is additive, never required
- **Open questions**: Wake word detection, continuous listening vs. push-to-talk, audio storage policy

---

### Feature 014 – Edge Client (Raspberry Pi)

> "I can interact with the assistant from a Raspberry Pi."

Text-based interface (CLI / button / simple display), connection to existing backend, minimal local state.

- **Interface**: CLI-based TUI (e.g., Textual) or minimal web kiosk (lightweight browser)
- **Connectivity**: Always-online assumed for v1; offline graceful degradation (queued messages, cached last response) as stretch goal
- **Authentication**: Device-level API token (long-lived), not interactive login
- **Local state**: Minimal — last N messages cached for display continuity, no local database
- **Hardware targets**: Raspberry Pi 4/5 with network access
- **Deployment**: Docker container or systemd service
- **Open questions**: Display hardware (e-ink, HDMI, none), audio integration with Feature 013

---

### Feature 015 – Google Integrations (Read-Only)

> "The assistant can tell me about my emails and calendar events."

Gmail read/search, calendar read, explicit permission prompts, audit logging. No sending emails or modifying calendar events.

- **Auth**: OAuth 2.0 with offline refresh tokens, scoped to read-only (`gmail.readonly`, `calendar.readonly`); no write scopes requested
- **Gmail**: Search/read messages, thread summarization, label filtering
- **Calendar**: Read events, free/busy lookup, upcoming event summaries
- **Token storage**: Encrypted in PostgreSQL, per-user, revocable
- **Audit**: All Google API calls logged with correlation IDs
- **Rate limiting**: Respect Google API quotas, back off on 429s
- **Scope enforcement**: Read-only scopes only; write-capable integrations are a separate future feature
- **Privacy**: Email content processed in-memory for tool responses, not persisted to memory unless user explicitly saves
- **Open questions**: Attachment handling, shared calendar support, re-consent flow

---

### Future Capabilities

#### Memory & Intelligence

- Memory v4: Long-horizon personalization and planning
- Cross-user insights (opt-in): Aggregate patterns across consenting users

#### Interaction & Modality

- Multi-modal inputs (images, documents, file uploads in chat)
- Interactive knowledge graph visualization (zoomable node-and-edge diagram)

#### Integrations & Automation

- Write-capable integrations (send email, create calendar events)
- Additional tool integrations (Notion, Slack, GitHub, etc.)
- Task automation pipelines (multi-step workflows)

#### Frontend & UX

- User settings & preferences page
- Memory editing (content modification, not just deletion)
- Conversation search and filtering

Each new capability must follow the constitution, include evaluation coverage, and be introduced as its own scoped feature.

---

## Non-Goals

- Replicate human memory
- Achieve perfect recall
- Infer sensitive traits
- Act autonomously without oversight

---

> **Memory exists to make the assistant more helpful tomorrow — not more confident today.**
