# Agent Tool Contracts: Proactive Assistant

These tools are available to the production agent via `@function_tool` decorator.

---

## create_schedule

Creates a new scheduled task for the user.

**Parameters**:

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Human-readable task name |
| `description` | string | no | What the task does |
| `task_type` | string | yes | "one_time" or "recurring" |
| `schedule_cron` | string | conditional | Cron expression (required for recurring) |
| `scheduled_at` | string | conditional | ISO datetime (required for one_time) |
| `timezone` | string | no | User's timezone (default: UTC) |
| `tool_name` | string | yes | Tool to invoke (e.g., "get_weather") |
| `tool_args` | object | no | Arguments for the tool |
| `prompt_template` | string | yes | Prompt for agent when executing |

**Returns**: JSON with success status, task ID, next run time

**Example invocation**:
```
Agent decides: User said "remind me to check the weather every morning at 7am"
→ create_schedule(
    name="Morning weather check",
    task_type="recurring",
    schedule_cron="0 7 * * *",
    timezone="America/Los_Angeles",
    tool_name="get_weather",
    tool_args={"location": "Seattle"},
    prompt_template="Provide a brief weather update for Seattle."
  )
```

---

## manage_schedule

Modifies an existing scheduled task (pause, resume, cancel).

**Parameters**:

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `task_id` | string | yes | UUID of the task to modify |
| `action` | string | yes | "pause", "resume", or "cancel" |

**Returns**: JSON with success status and updated task state

---

## record_pattern

Records or updates an observed behavioral pattern.

**Parameters**:

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `pattern_type` | string | yes | Category: "recurring_query", "time_based", "topic_interest" |
| `description` | string | yes | Human-readable pattern description |
| `evidence` | string | yes | Context of the current observation |
| `suggested_action` | string | no | What the agent could do about this pattern |
| `confidence` | float | no | Confidence in the pattern (0.0-1.0, default 0.5) |

**Returns**: JSON with pattern ID, occurrence count, whether threshold reached for suggestion

**Behavior**: If a similar pattern already exists for the user (matched by `pattern_type` + fuzzy description), increments `occurrence_count` and appends evidence. Otherwise creates a new pattern.

---

## record_engagement

Records the user's response to a proactive suggestion.

**Parameters**:

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `suggestion_type` | string | yes | Category of the suggestion |
| `action` | string | yes | "engaged" or "dismissed" |
| `source` | string | yes | "conversation", "notification", or "schedule" |

**Returns**: JSON with success status

**Side effects**: After recording, checks if suppression or boosting thresholds are reached and updates `proactiveness_settings` accordingly.

---

## adjust_proactiveness

Adjusts the user's proactiveness level based on explicit instruction.

**Parameters**:

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `direction` | string | yes | "more" or "less" |

**Returns**: JSON with new global_level and confirmation message

**Behavior**:
- "more": Sets `global_level` to min(1.0, current + 0.2), sets `user_override` to "more", clears `suppressed_types`
- "less": Sets `global_level` to max(0.0, current - 0.2), sets `user_override` to "less"

---

## get_user_profile

Retrieves a summary of what the assistant knows about the user.

**Parameters**: None (uses user_id from context)

**Returns**: JSON with facts, preferences, patterns, key relationships, and proactiveness settings (same structure as `GET /proactive/profile`)

**Usage**: Called when user asks "what do you know about me?" or similar. The agent formats the response conversationally.
