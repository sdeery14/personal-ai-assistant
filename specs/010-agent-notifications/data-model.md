# Data Model: Agent Notifications

**Feature**: 010-agent-notifications
**Date**: 2026-02-22

## Entity Relationship Diagram

```
users (existing)
  ├── 1:N → notifications
  └── 1:1 → notification_preferences

conversations (existing)
  └── 1:N → notifications (source)
```

## Tables

### users (MODIFIED — add email column)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| email | VARCHAR(255) | NULLABLE, UNIQUE | New column. Nullable because existing users don't have one yet. |

Migration adds `email` column to existing `users` table. No default value — existing rows get NULL.

### notifications (NEW)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| user_id | UUID | NOT NULL, FK → users(id) ON DELETE CASCADE | Owner of the notification |
| conversation_id | UUID | NULLABLE, FK → conversations(id) ON DELETE SET NULL | Source conversation (nullable for system notifications in future) |
| message | VARCHAR(500) | NOT NULL | Notification content, max 500 chars |
| type | VARCHAR(20) | NOT NULL, DEFAULT 'info' | Enum: 'reminder', 'info', 'warning' |
| is_read | BOOLEAN | NOT NULL, DEFAULT FALSE | Read/unread status |
| dismissed_at | TIMESTAMPTZ | NULLABLE | Soft-delete timestamp; NULL = active |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes**:
- `idx_notifications_user_id_created_at` on `(user_id, created_at DESC)` — primary list query
- `idx_notifications_user_id_unread` on `(user_id) WHERE is_read = FALSE AND dismissed_at IS NULL` — unread count query (partial index)

**CHECK constraint**: `type IN ('reminder', 'info', 'warning')`

### notification_preferences (NEW)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| user_id | UUID | NOT NULL, UNIQUE, FK → users(id) ON DELETE CASCADE | One row per user |
| delivery_channel | VARCHAR(20) | NOT NULL, DEFAULT 'in_app' | Enum: 'in_app', 'email', 'both' |
| quiet_hours_start | TIME | NULLABLE | Start of quiet hours (local time) |
| quiet_hours_end | TIME | NULLABLE | End of quiet hours (local time) |
| quiet_hours_timezone | VARCHAR(50) | NULLABLE, DEFAULT 'UTC' | IANA timezone name |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**CHECK constraint**: `delivery_channel IN ('in_app', 'email', 'both')`

**Note**: Both `quiet_hours_start` and `quiet_hours_end` must be set together (both NULL or both non-NULL). Enforced at application layer.

### deferred_emails (NEW)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| notification_id | UUID | NOT NULL, FK → notifications(id) ON DELETE CASCADE | The notification to email |
| user_id | UUID | NOT NULL, FK → users(id) ON DELETE CASCADE | Recipient |
| deliver_after | TIMESTAMPTZ | NOT NULL | When to send (quiet hours end time in UTC) |
| delivered_at | TIMESTAMPTZ | NULLABLE | NULL = pending, set when sent |
| failed_at | TIMESTAMPTZ | NULLABLE | Set on permanent failure |
| error_message | TEXT | NULLABLE | Last error if failed |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes**:
- `idx_deferred_emails_pending` on `(deliver_after) WHERE delivered_at IS NULL AND failed_at IS NULL` — pending delivery query (partial index)

## State Transitions

### Notification Lifecycle

```
Created (is_read=FALSE, dismissed_at=NULL)
  │
  ├── Mark as read → (is_read=TRUE, dismissed_at=NULL)
  │     │
  │     └── Dismiss → (is_read=TRUE, dismissed_at=NOW())
  │
  └── Dismiss (unread) → (is_read=TRUE, dismissed_at=NOW())
```

- Dismissing an unread notification also marks it as read.
- Dismissed notifications are excluded from all list queries.
- "Mark all as read" only affects non-dismissed notifications.

### Deferred Email Lifecycle

```
Created (delivered_at=NULL, failed_at=NULL)
  │
  ├── Delivered → (delivered_at=NOW())
  │
  └── Failed → (failed_at=NOW(), error_message=...)
```

- No retry for deferred emails in this feature. Feature 011 can add retry logic.

## Validation Rules

| Entity | Field | Rule |
|--------|-------|------|
| Notification | message | Non-empty, max 500 characters |
| Notification | type | Must be one of: reminder, info, warning |
| Notification | user_id | Must reference an existing, active user |
| Notification Preferences | delivery_channel | Must be one of: in_app, email, both |
| Notification Preferences | quiet_hours_start/end | Both must be set or both must be NULL |
| Notification Preferences | quiet_hours_timezone | Must be a valid IANA timezone |
| Users | email | Valid email format when provided; unique across users |
