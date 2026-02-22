# Agent Tool Contract: send_notification

## Tool Name
`send_notification`

## Description (visible to agent)
Send a notification to the user. Use this when the user asks to be reminded about something, when you identify information worth flagging for later, or when you want to surface a warning. Notifications persist beyond the current conversation and can be delivered via email if the user has opted in.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| message | string | Yes | The notification message (1-500 characters) |
| type | string | No | Notification type: "reminder", "info", or "warning". Default: "info" |

## Context (injected via RunContextWrapper)

| Field | Source | Usage |
|-------|--------|-------|
| user_id | ctx.context["user_id"] | Owner of the notification |
| conversation_id | ctx.context["conversation_id"] | Source attribution |
| correlation_id | ctx.context["correlation_id"] | Logging |

## Response Format

### Success
```json
{
  "success": true,
  "action": "notification_created",
  "message": "Notification created: <truncated message preview>",
  "notification_id": "<uuid>",
  "type": "reminder"
}
```

### Validation Error
```json
{
  "success": false,
  "action": "validation_error",
  "message": "Message must be between 1 and 500 characters"
}
```

### Rate Limited
```json
{
  "success": false,
  "action": "rate_limited",
  "message": "Notification rate limit exceeded. Try again later."
}
```

### System Error
```json
{
  "success": false,
  "action": "error",
  "message": "Failed to create notification: <error details>"
}
```

## Validation Rules

1. `message` must be non-empty and ≤ 500 characters
2. `type` must be one of: "reminder", "info", "warning" (default: "info")
3. `user_id` must be present in context
4. Rate limit: configurable per-user hourly cap (checked via Redis)

## Side Effects

1. Creates a row in `notifications` table
2. If user has email enabled and is outside quiet hours: sends email asynchronously
3. If user has email enabled and is inside quiet hours: creates deferred email entry
4. Logs notification creation with correlation_id
