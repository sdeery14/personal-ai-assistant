# Quickstart: Proactive Assistant ("The Alfred Engine")

**Feature**: 011-proactive-assistant
**Date**: 2026-02-22

## Prerequisites

- Docker services running (API, PostgreSQL, Redis, MLflow)
- Frontend dev server running (`cd frontend && npm run dev`)
- Valid OpenAI API key in `.env`
- At least one user account created

## Verification Scenarios

### 1. Onboarding (US1)

**Setup**: Create a fresh user account (or clear all conversations for an existing user)

**Steps**:
1. Log in with the new account
2. Open a new chat conversation
3. Send any message (e.g., "Hello")

**Expected**: The assistant responds with a warm, conversational greeting that includes a question to learn about the user — not a form or checklist. Something like: "I'd like to get to know you so I can be most useful. What's on your plate right now?"

**Verify memory**: After the user responds with personal information, check `GET /memories?limit=5` — new facts/preferences should be saved.

**Verify skip**: Create another new user, immediately ask a direct question (e.g., "What's the weather in Seattle?"). The assistant should answer helpfully without forcing onboarding.

---

### 2. Active Observation (US2)

**Setup**: Have 3-5 conversations where you mention the same topic repeatedly (e.g., ask about weather in different ways across sessions)

**Steps**:
1. Conversation 1: "What's the weather in Seattle?"
2. Conversation 2: "How's the weather looking today in Seattle?"
3. Conversation 3: "Is it going to rain in Seattle this week?"

**Expected**: After 3+ occurrences, the `observed_patterns` table should contain a pattern like "Asks about weather in Seattle regularly" with `occurrence_count >= 3`.

**Verify**: `SELECT * FROM observed_patterns WHERE user_id = '<user_id>'` should show the detected pattern.

---

### 3. Scheduled Task Creation (US4)

**Steps**:
1. In a conversation, say: "Can you send me the weather for Seattle every morning at 7am?"
2. The assistant should confirm and create a scheduled task

**Expected**:
- `GET /schedules` returns the new task with `status: active`, `schedule_cron: "0 7 * * *"`
- The task's `next_run_at` should be the next 7:00 AM in the user's timezone

**One-time task**: Say "Remind me to call Sarah tomorrow at 3pm"
- `GET /schedules` should show a one-time task with `scheduled_at` set to tomorrow 3pm
- After execution, status should transition to `completed`

---

### 4. Schedule Management (US4)

**Steps**:
1. "Show me my scheduled tasks" → assistant lists active tasks
2. "Pause the morning weather briefing" → task status changes to `paused`
3. "Resume the morning weather briefing" → task status changes back to `active`
4. "Cancel the morning weather briefing" → task status changes to `cancelled`

**Verify**: `GET /schedules` reflects each status change

---

### 5. Frontend Schedule Page (US4)

**Steps**:
1. Navigate to `/schedules` in the frontend
2. Verify the page shows a list of scheduled tasks with name, type, status, next run time
3. Verify paused and cancelled tasks are visible but visually distinguished

**Expected**: Read-only list page, no management controls (those go through conversation)

---

### 6. Proactive Suggestions (US3)

**Setup**: Build context through several conversations (mention an upcoming deadline, a regular pattern)

**Steps**:
1. Start a new conversation after building context
2. The assistant should reference what it knows: "I noticed you have that presentation on Friday — would you like me to pull together your recent notes on Project X?"

**Expected**: Suggestion is relevant, cites its basis, and doesn't block the user's request

---

### 7. Calibration (US5)

**Steps**:
1. Dismiss several weather-related suggestions (say "no thanks" or ignore them)
2. After 3 dismissals of the same type, verify the assistant stops suggesting it
3. Say "be more proactive" — verify the assistant acknowledges and adjusts
4. Ask "what do you know about me?" — verify a structured summary of facts, preferences, patterns, and relationships

**Verify**: `GET /proactive/settings` shows updated `suppressed_types` after dismissals and updated `global_level` after explicit instruction

---

## Smoke Test Checklist

- [ ] New user sees onboarding greeting
- [ ] Returning user does NOT see onboarding greeting
- [ ] Memory writes occur during onboarding conversation
- [ ] Knowledge graph entities created from onboarding
- [ ] Scheduled recurring task created via conversation
- [ ] Scheduled one-time task created via conversation
- [ ] `GET /schedules` returns user's tasks
- [ ] Task execution creates a notification
- [ ] Task pause/resume/cancel works via conversation
- [ ] Frontend `/schedules` page renders task list
- [ ] Pattern detection stores patterns after 3+ occurrences
- [ ] Proactive suggestion appears in conversation
- [ ] Dismissed suggestions are tracked
- [ ] "Be more/less proactive" adjusts settings
- [ ] "What do you know about me?" returns profile summary
- [ ] Sidebar shows "Schedules" nav item
