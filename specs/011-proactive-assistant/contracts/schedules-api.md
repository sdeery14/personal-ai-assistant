# API Contract: Scheduled Tasks

**Prefix**: `/schedules`
**Auth**: All endpoints require `Authorization: Bearer <token>` (JWT)
**Scoping**: All queries filtered by authenticated user's `user_id`

---

## GET /schedules

List the authenticated user's scheduled tasks.

**Query Parameters**:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `status` | string | (none) | Filter by status: `active`, `paused`, `cancelled`, `completed` |
| `limit` | integer | 20 | Results per page (1-100) |
| `offset` | integer | 0 | Pagination offset |

**Response 200**:

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Morning weather briefing",
      "description": "Get current weather for Seattle every morning",
      "task_type": "recurring",
      "schedule_cron": "0 7 * * *",
      "scheduled_at": null,
      "timezone": "America/Los_Angeles",
      "status": "active",
      "source": "user",
      "next_run_at": "2026-02-23T15:00:00Z",
      "last_run_at": "2026-02-22T15:00:00Z",
      "run_count": 5,
      "fail_count": 0,
      "created_at": "2026-02-18T10:00:00Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

---

## GET /schedules/{task_id}

Get a single scheduled task with its recent run history.

**Response 200**:

```json
{
  "id": "uuid",
  "name": "Morning weather briefing",
  "description": "Get current weather for Seattle every morning",
  "task_type": "recurring",
  "schedule_cron": "0 7 * * *",
  "scheduled_at": null,
  "timezone": "America/Los_Angeles",
  "status": "active",
  "source": "user",
  "next_run_at": "2026-02-23T15:00:00Z",
  "last_run_at": "2026-02-22T15:00:00Z",
  "run_count": 5,
  "fail_count": 0,
  "created_at": "2026-02-18T10:00:00Z",
  "recent_runs": [
    {
      "id": "uuid",
      "started_at": "2026-02-22T15:00:00Z",
      "completed_at": "2026-02-22T15:00:05Z",
      "status": "success",
      "duration_ms": 5000,
      "notification_id": "uuid"
    }
  ]
}
```

**Response 404**: `{"detail": "Schedule not found"}`

---

## GET /schedules/{task_id}/runs

List execution history for a scheduled task.

**Query Parameters**:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | integer | 10 | Results per page (1-50) |
| `offset` | integer | 0 | Pagination offset |

**Response 200**:

```json
{
  "items": [
    {
      "id": "uuid",
      "started_at": "2026-02-22T15:00:00Z",
      "completed_at": "2026-02-22T15:00:05Z",
      "status": "success",
      "result": "Current weather in Seattle: 45°F, cloudy...",
      "error": null,
      "notification_id": "uuid",
      "retry_count": 0,
      "duration_ms": 5000
    }
  ],
  "total": 5,
  "limit": 10,
  "offset": 0
}
```

---

## Notes

- **No POST/PUT/DELETE endpoints**: Task creation, pausing, resuming, and cancellation are handled through conversation with the agent (via tools). The API is read-only per spec clarification.
- The agent uses `manage_schedule` and `create_schedule` tools to modify tasks. These tools write directly to the database, not through the REST API.
- Frontend consumes these read-only endpoints for the schedule list page.
