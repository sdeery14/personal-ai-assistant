# Research: Proactive Assistant ("The Alfred Engine")

**Feature**: 011-proactive-assistant
**Date**: 2026-02-22

## R1: Scheduling Library

**Decision**: Custom asyncio + PostgreSQL scheduler with `croniter` for cron parsing

**Rationale**: The scheduling needs are well-scoped (per-user one-time and recurring tasks, ~100s of tasks not millions). A custom scheduler avoids introducing heavy dependencies (Celery, SQLAlchemy) and fits naturally into the existing architecture:
- Existing background task pattern in `main.py` lifespan (`asyncio.create_task` with `while True` / `asyncio.sleep`)
- Existing asyncpg connection pool for persistence
- Existing Redis for distributed locking (prevent duplicate execution in multi-worker scenarios)

`croniter` (~200KB, pure Python, well-maintained) handles cron expression parsing and next-run calculation. The scheduler loop is ~200 lines of custom code that:
1. Polls PostgreSQL for due tasks every 30 seconds
2. Acquires a Redis lock per task to prevent duplicate execution
3. Executes the task (agent tool invocation)
4. Records the result in `task_runs`
5. Calculates and updates `next_run_at` via croniter

**Alternatives considered**:
- **APScheduler 4.x**: Async-native, PostgreSQL persistence via SQLAlchemy — but introduces SQLAlchemy dependency alongside existing asyncpg, still alpha (v4.0.0a6), and the persistence layer is more complex than needed
- **Celery + Redis**: Industry standard but overkill for single-process, adds 5+ dependencies, not async-native, requires separate worker process
- **arq**: Redis-based, async, but no built-in cron/recurring support — would need custom scheduling on top
- **Taskiq**: Similar to Celery but async — still overkill, adds broker dependency
- **PGQueuer**: PostgreSQL-native queuing via LISTEN/NOTIFY — interesting but asyncpg doesn't support LISTEN well, immature ecosystem

## R2: System Prompt Architecture for Onboarding

**Decision**: Contextual system prompt injection based on user state (new vs returning)

**Rationale**: The existing pattern in `chat_service.py` builds system instructions by concatenating feature-specific prompt constants. For onboarding, we add a conditional block:
- Query user's conversation count at agent creation time
- If zero conversations: inject `ONBOARDING_SYSTEM_PROMPT` (warm first-encounter)
- If returning user: inject `PROACTIVE_SYSTEM_PROMPT` (personalized greeting using recent context)

This follows the existing pattern exactly — no new architecture needed. The onboarding prompt teaches the agent to ask conversational questions and save discoveries to memory/knowledge graph using existing tools.

**Alternatives considered**:
- Separate "onboarding agent" with handoff: Adds complexity (agent routing) for minimal benefit — the same agent with different instructions is simpler
- Frontend-driven onboarding wizard: Spec explicitly says "conversational, not a form"

## R3: Observed Pattern Storage

**Decision**: New `observed_patterns` table in PostgreSQL with a dedicated service

**Rationale**: Patterns (e.g., "user asks about weather every morning") are a new entity type that doesn't fit cleanly into existing memory items or knowledge graph entities. They have unique attributes: occurrence count, temporal data, acted-upon status. A dedicated table keeps the data model clean and queryable.

Pattern detection runs as a post-conversation analysis step (similar to episode summarization), not in real-time. The agent's LLM identifies patterns by reviewing recent conversation history and memory, then stores them via a new tool.

**Alternatives considered**:
- Store patterns as memory items with special type: Pollutes the memory table, hard to query occurrence counts and temporal data
- Store in knowledge graph as entities: Graph entities are about relationships, not behavioral patterns — semantic mismatch

## R4: Engagement Tracking

**Decision**: New `engagement_events` table + `proactiveness_settings` table in PostgreSQL

**Rationale**: Engagement events (suggestion engaged vs dismissed) need to be queryable for calibration (US5). A simple table with event type, suggestion category, and timestamp enables aggregation queries like "how many times has the user dismissed weather suggestions in the last 30 days?"

Proactiveness settings store per-user calibration state: overall proactiveness level (0.0-1.0), per-category suppression thresholds, and explicit user overrides ("be more/less proactive").

**Alternatives considered**:
- Redis counters: Fast but ephemeral — engagement history needs to persist across restarts
- Memory items: Not structured enough for aggregate queries

## R5: Scheduled Task Execution via Agent

**Decision**: Scheduled tasks invoke the production agent with a system-generated prompt

**Rationale**: When a scheduled task fires (e.g., "morning weather briefing"), the scheduler:
1. Creates a synthetic prompt based on the task definition (e.g., "Provide a weather briefing for {location}")
2. Runs the production agent with that prompt (using `Runner.run` non-streamed)
3. Captures the agent's response
4. Delivers the response as a notification via Feature 010

This reuses the existing agent infrastructure (tools, guardrails, memory) rather than building parallel execution paths. The agent has full context of the user and can provide personalized responses.

**Alternatives considered**:
- Direct tool invocation (bypass agent): Loses personalization, memory context, and natural language response formatting
- Streaming execution: Unnecessary for background tasks — non-streamed is simpler and sufficient

## R6: Frontend Schedule List Page

**Decision**: Read-only page at `/schedules` using existing frontend patterns

**Rationale**: Per spec clarification, the frontend provides a read-only view of scheduled tasks. Management (create, pause, cancel) happens through conversation. The page follows the existing pattern of other list pages (notifications, memory, knowledge) with:
- New API endpoint `GET /schedules` returning paginated task list
- New Next.js page at `app/(main)/schedules/page.tsx`
- New `useSchedules` hook following `useNotifications` pattern
- Sidebar nav item added

## R7: Proactive Suggestion Delivery

**Decision**: Two delivery paths — in-conversation suggestions via system prompt, out-of-conversation via notifications

**Rationale**:
- **In-conversation**: The proactive system prompt instructs the agent to check the user's context (patterns, upcoming events, recent activity) at the start of each conversation and offer relevant suggestions. The agent uses memory query and knowledge graph tools to gather context, then naturally weaves suggestions into the greeting.
- **Out-of-conversation**: A periodic background job (every 15 minutes) checks for proactive opportunities (upcoming deadlines, pattern-based suggestions) and delivers them as notifications via Feature 010. This uses the same agent invocation pattern as scheduled tasks.

Confidence thresholds prevent low-quality suggestions. Engagement tracking (US5) feeds back to adjust thresholds.
