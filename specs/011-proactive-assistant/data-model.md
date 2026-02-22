# Data Model: Proactive Assistant ("The Alfred Engine")

**Feature**: 011-proactive-assistant
**Date**: 2026-02-22

## New Tables

### `scheduled_tasks`

Stores user-created and agent-suggested scheduled tasks.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Task identifier |
| `user_id` | UUID | NOT NULL, FK → users(id) ON DELETE CASCADE | Owner of the task |
| `name` | VARCHAR(200) | NOT NULL | Human-readable task name (e.g., "Morning weather briefing") |
| `description` | TEXT | | Detailed description of what the task does |
| `task_type` | VARCHAR(20) | NOT NULL, CHECK IN ('one_time', 'recurring') | One-time or recurring |
| `schedule_cron` | VARCHAR(100) | | Cron expression for recurring tasks (e.g., "0 7 * * *") |
| `scheduled_at` | TIMESTAMPTZ | | Specific datetime for one-time tasks |
| `timezone` | VARCHAR(50) | NOT NULL, DEFAULT 'UTC' | User's timezone for schedule interpretation |
| `tool_name` | VARCHAR(100) | NOT NULL | Which agent tool to invoke (e.g., "get_weather") |
| `tool_args` | JSONB | NOT NULL, DEFAULT '{}' | Arguments to pass to the tool |
| `prompt_template` | TEXT | NOT NULL | System prompt template for agent invocation |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'active', CHECK IN ('active', 'paused', 'cancelled', 'completed') | Current task status |
| `source` | VARCHAR(20) | NOT NULL, DEFAULT 'user', CHECK IN ('user', 'agent') | Who created the task |
| `next_run_at` | TIMESTAMPTZ | | Calculated next execution time |
| `last_run_at` | TIMESTAMPTZ | | When the task last executed |
| `run_count` | INTEGER | NOT NULL, DEFAULT 0 | Total successful executions |
| `fail_count` | INTEGER | NOT NULL, DEFAULT 0 | Total failed executions |
| `max_retries` | INTEGER | NOT NULL, DEFAULT 3 | Max retries per execution on transient failure |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | When created |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Last modified |

**Indexes**:
- `idx_scheduled_tasks_user_id` ON (user_id) — list user's tasks
- `idx_scheduled_tasks_next_run` ON (next_run_at) WHERE status = 'active' AND next_run_at IS NOT NULL — scheduler poll query
- `idx_scheduled_tasks_user_status` ON (user_id, status) — filtered list queries

**State transitions**:
- `active` → `paused` (user pauses)
- `paused` → `active` (user resumes)
- `active` → `cancelled` (user cancels)
- `active` → `completed` (one-time task finished)
- `paused` → `cancelled` (user cancels while paused)

---

### `task_runs`

Records each execution of a scheduled task.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Run identifier |
| `task_id` | UUID | NOT NULL, FK → scheduled_tasks(id) ON DELETE CASCADE | Parent task |
| `started_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | When execution began |
| `completed_at` | TIMESTAMPTZ | | When execution finished |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'running', CHECK IN ('running', 'success', 'failed', 'retrying') | Run outcome |
| `result` | TEXT | | Agent's response text (on success) |
| `error` | TEXT | | Error message (on failure) |
| `notification_id` | UUID | FK → notifications(id) ON DELETE SET NULL | Notification created for this run |
| `retry_count` | INTEGER | NOT NULL, DEFAULT 0 | How many retries attempted |
| `duration_ms` | INTEGER | | Execution duration in milliseconds |

**Indexes**:
- `idx_task_runs_task_id` ON (task_id, started_at DESC) — run history for a task

---

### `observed_patterns`

Behavioral patterns detected across conversations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Pattern identifier |
| `user_id` | UUID | NOT NULL, FK → users(id) ON DELETE CASCADE | User the pattern belongs to |
| `pattern_type` | VARCHAR(50) | NOT NULL | Category (e.g., "recurring_query", "time_based", "topic_interest") |
| `description` | TEXT | NOT NULL | Human-readable description (e.g., "Asks about weather most mornings") |
| `evidence` | JSONB | NOT NULL, DEFAULT '[]' | Array of evidence entries: [{date, context, conversation_id}] |
| `occurrence_count` | INTEGER | NOT NULL, DEFAULT 1 | How many times observed |
| `first_seen_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | First occurrence |
| `last_seen_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Most recent occurrence |
| `acted_on` | BOOLEAN | NOT NULL, DEFAULT FALSE | Whether a suggestion or schedule was created from this |
| `suggested_action` | TEXT | | What the agent could do (e.g., "Schedule daily weather at 7am") |
| `confidence` | FLOAT | NOT NULL, DEFAULT 0.5 | Agent's confidence in the pattern (0.0-1.0) |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | When first detected |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Last updated |

**Indexes**:
- `idx_observed_patterns_user_id` ON (user_id) — list user's patterns
- `idx_observed_patterns_user_type` ON (user_id, pattern_type) — filter by type
- `idx_observed_patterns_actionable` ON (user_id) WHERE acted_on = FALSE AND occurrence_count >= 3 — find patterns ready to suggest

---

### `engagement_events`

Tracks user response to proactive suggestions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Event identifier |
| `user_id` | UUID | NOT NULL, FK → users(id) ON DELETE CASCADE | User who received the suggestion |
| `suggestion_type` | VARCHAR(50) | NOT NULL | Category of suggestion (e.g., "weather_briefing", "meeting_prep", "deadline_reminder") |
| `action` | VARCHAR(20) | NOT NULL, CHECK IN ('engaged', 'dismissed') | What the user did |
| `source` | VARCHAR(20) | NOT NULL, CHECK IN ('conversation', 'notification', 'schedule') | Where the suggestion was delivered |
| `context` | JSONB | DEFAULT '{}' | Additional context (suggestion text, pattern_id, task_id) |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | When the event occurred |

**Indexes**:
- `idx_engagement_events_user_type` ON (user_id, suggestion_type, created_at DESC) — calibration queries
- `idx_engagement_events_user_action` ON (user_id, action, created_at DESC) — aggregate engagement rate

---

### `proactiveness_settings`

Per-user calibration state for proactive behavior.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Settings identifier |
| `user_id` | UUID | NOT NULL, UNIQUE, FK → users(id) ON DELETE CASCADE | User these settings belong to |
| `global_level` | FLOAT | NOT NULL, DEFAULT 0.7, CHECK (global_level >= 0.0 AND global_level <= 1.0) | Overall proactiveness (0.0 = reactive only, 1.0 = maximum proactive) |
| `suppressed_types` | JSONB | NOT NULL, DEFAULT '[]' | Array of suggestion types suppressed due to repeated dismissals |
| `boosted_types` | JSONB | NOT NULL, DEFAULT '[]' | Array of suggestion types boosted due to repeated engagement |
| `user_override` | VARCHAR(20) | CHECK IN ('more', 'less', NULL) | Explicit user instruction, NULL if no override |
| `is_onboarded` | BOOLEAN | NOT NULL, DEFAULT FALSE | Whether user has completed or skipped onboarding |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | When created |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Last modified |

**Indexes**:
- (UNIQUE on `user_id` — already enforced by UNIQUE constraint)

---

## Existing Table Modifications

### `users`

No schema changes needed. The `is_onboarded` flag is stored in `proactiveness_settings` rather than the users table, keeping Feature 011 concerns isolated.

### `notifications`

No schema changes needed. Scheduled task runs create notifications using the existing `notifications` table via Feature 010's `NotificationService`.

---

## Relationships

```text
users (1) ──── (*) scheduled_tasks
users (1) ──── (*) observed_patterns
users (1) ──── (*) engagement_events
users (1) ──── (1) proactiveness_settings

scheduled_tasks (1) ──── (*) task_runs
task_runs (*) ──── (1) notifications
```

---

## Migration File

File: `migrations/011_proactive_assistant.sql`

Creates all 5 tables, indexes, triggers (for `updated_at` auto-update on `scheduled_tasks`, `observed_patterns`, `proactiveness_settings`), and check constraints in a single idempotent migration.
