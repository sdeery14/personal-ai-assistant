# Research: Agent Notifications

**Feature**: 010-agent-notifications
**Date**: 2026-02-22

## Email Delivery Approach

**Decision**: SMTP with `aiosmtplib` for async email delivery

**Rationale**: The project already uses asyncio throughout (FastAPI, asyncpg, agents SDK). `aiosmtplib` is a lightweight async SMTP client that integrates cleanly. SMTP is provider-agnostic — works with Gmail, SendGrid, Mailgun, Amazon SES, or any SMTP relay. This avoids vendor lock-in and keeps the dependency surface small.

**Alternatives considered**:
- **SendGrid SDK**: Vendor-specific, adds a proprietary dependency. SMTP relay works with SendGrid anyway.
- **Amazon SES SDK (boto3)**: Heavy dependency, AWS-specific. Overkill for notification emails.
- **Synchronous `smtplib`**: Would block the event loop. Must use async.

## Email Deferral for Quiet Hours

**Decision**: Store deferred emails in a `deferred_emails` table and process them with a lightweight startup/periodic check

**Rationale**: Full job queue (Celery, APScheduler) is out of scope — that's Feature 011. A simple database-backed deferral queue with a periodic check (e.g., every minute via `asyncio.create_task` in the app lifespan) is sufficient for the expected low volume. When Feature 011 adds a real job runner, deferred email processing can migrate to it.

**Alternatives considered**:
- **In-memory queue**: Lost on restart. Unacceptable for notifications.
- **Redis sorted set by delivery time**: Viable but adds complexity. Database is simpler and already the source of truth.
- **APScheduler**: Would pull in Feature 011 scope prematurely.

## Rate Limiting Strategy

**Decision**: Use Redis-based sliding window counter (same pattern as entity extraction rate limiting)

**Rationale**: The codebase already uses Redis for rate limiting in `src/tools/save_entity.py`. Reusing the same pattern keeps consistency. Redis atomic operations (INCR + EXPIRE) provide accurate per-user hourly counts without database overhead.

**Alternatives considered**:
- **Database-based counting**: Slower, adds load to PostgreSQL for a hot-path check.
- **In-memory counter**: Not shared across workers, lost on restart.
- **Token bucket**: More complex than needed for hourly caps.

## Notification Panel UX

**Decision**: Dropdown panel from header bell icon (not a separate page)

**Rationale**: Notifications are secondary to the primary chat experience. A dropdown panel (similar to GitHub/Slack notification trays) provides quick access without navigating away from the current page. The panel shows recent notifications with a "view all" link if a full page is needed later.

**Alternatives considered**:
- **Dedicated page**: Too heavy for MVP. Could be added later.
- **Sidebar section**: Sidebar is already used for navigation. Adding notifications there would clutter it.
- **Toast/snackbar**: Ephemeral — doesn't satisfy the "persistent, reviewable" requirement.

## Unread Count Polling

**Decision**: Poll unread count on page load and after notification-creating actions; no real-time push

**Rationale**: WebSocket delivery is explicitly out of scope (deferred to Feature 011). Polling on page load and after chat interactions is sufficient for the expected usage pattern — users will see new notifications when they navigate or refresh. A dedicated polling interval (e.g., every 60 seconds) can be added if needed but is not required for MVP.

**Alternatives considered**:
- **WebSocket**: Out of scope per spec.
- **SSE for notifications**: Adds complexity; existing SSE is for chat streaming only.
- **Aggressive polling (every 5s)**: Wasteful for low notification volume.

## User Email Storage

**Decision**: Add `email` column to existing `users` table via new migration

**Rationale**: The users table currently has no email field. Email is required for notification delivery. Adding it to the existing table is cleaner than a separate preferences table for a single field. The email is nullable (not all users may have/want email notifications).

**Alternatives considered**:
- **Separate user_emails table**: Over-normalized for a single field.
- **Store email only in notification_preferences**: Couples email address to notification feature. Email is a general user attribute.
