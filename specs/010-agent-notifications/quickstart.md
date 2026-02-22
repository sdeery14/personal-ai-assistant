# Quickstart: Agent Notifications

## Prerequisites

- Docker services running (API + PostgreSQL + Redis + MLflow)
- Frontend dev server running (`cd frontend && npm run dev`)
- `.env` with `OPENAI_API_KEY` configured

## New Environment Variables

Add to `.env`:

```bash
# Notification Email (Feature 010)
NOTIFICATION_EMAIL_ENABLED=false          # Set to true to enable email delivery
NOTIFICATION_EMAIL_FROM=noreply@example.com
NOTIFICATION_SMTP_HOST=localhost
NOTIFICATION_SMTP_PORT=587
NOTIFICATION_SMTP_USERNAME=              # Optional
NOTIFICATION_SMTP_PASSWORD=              # Optional
NOTIFICATION_SMTP_USE_TLS=true
NOTIFICATION_RATE_LIMIT_PER_HOUR=10      # Dev: 10, Prod: higher
```

## New Dependencies

### Backend
```bash
uv add aiosmtplib    # Async SMTP client for email delivery
```

### Frontend
```bash
# No new npm dependencies expected — uses existing UI components
```

## Database Migration

Automatically applied on API startup. Creates:
- `email` column on `users` table
- `notifications` table
- `notification_preferences` table
- `deferred_emails` table

## Verification Steps

### 1. API Health
```bash
curl http://localhost:8000/health
```

### 2. Create a Notification (via chat)
Send a message like: "Remind me to check the report tomorrow"
The agent should use the `send_notification` tool.

### 3. List Notifications
```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/notifications
```

### 4. Check Unread Count
```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/notifications/unread-count
```

### 5. Frontend
Navigate to the app — bell icon in header should show unread count.

## Running Tests

```bash
# Unit tests (mocked, no services needed)
uv run pytest tests/unit/test_notification_service.py -v
uv run pytest tests/unit/test_notification_tool.py -v

# Frontend tests
cd frontend && npm test
```
