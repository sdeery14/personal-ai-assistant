# Tasks: Agent Notifications

**Input**: Design documents from `/specs/010-agent-notifications/`
**Prerequisites**: plan.md (required), spec.md (required), data-model.md, contracts/, research.md, quickstart.md

**Tests**: Included — the project follows evaluation-first development (Constitution Principle II).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add new dependency and configuration for notification feature

- [x] T001 Add `aiosmtplib` dependency via `uv add aiosmtplib`
- [x] T002 Add notification and email settings to `src/config.py` — add fields: `notification_rate_limit_per_hour` (int, default 10), `notification_email_enabled` (bool, default False), `notification_email_from` (str), `notification_smtp_host` (str), `notification_smtp_port` (int, default 587), `notification_smtp_username` (str, optional), `notification_smtp_password` (str, optional), `notification_smtp_use_tls` (bool, default True)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database schema, Pydantic models, and core service that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Create database migration `migrations/010_notifications.sql` — add `email` column to `users` table (VARCHAR(255), NULLABLE, UNIQUE); create `notifications` table with columns per data-model.md (id, user_id, conversation_id, message, type, is_read, dismissed_at, created_at) with CHECK constraint on type, indexes `idx_notifications_user_id_created_at` and partial index `idx_notifications_user_id_unread`; create `notification_preferences` table per data-model.md (id, user_id, delivery_channel, quiet_hours_start/end/timezone, created_at, updated_at) with CHECK constraint and UNIQUE on user_id; create `deferred_emails` table per data-model.md (id, notification_id, user_id, deliver_after, delivered_at, failed_at, error_message, created_at) with partial index `idx_deferred_emails_pending`; add `update_updated_at_column` trigger to `notification_preferences`
- [x] T004 Create Pydantic models in `src/models/notification.py` — `Notification` (id, user_id, conversation_id, message, type, is_read, created_at), `NotificationPreferences` (delivery_channel, quiet_hours_start, quiet_hours_end, quiet_hours_timezone), `NotificationPreferencesUpdate` (all optional), `CreateNotificationRequest` (message: str max 500, type: enum default info). Include type enum validation (reminder, info, warning) and quiet hours validation (both set or both null)
- [x] T005 Update `src/models/user.py` — add optional `email: str | None = None` field to User model
- [x] T006 Implement `NotificationService` in `src/services/notification_service.py` — methods: `create_notification(user_id, message, type, conversation_id) -> Notification` (inserts into notifications table), `list_notifications(user_id, type_filter, is_read_filter, limit, offset) -> tuple[list[Notification], int]` (paginated, excludes dismissed, reverse chronological), `get_unread_count(user_id) -> int`, `mark_as_read(notification_id, user_id) -> Notification | None`, `mark_all_as_read(user_id) -> int` (returns updated count), `dismiss_notification(notification_id, user_id) -> bool` (sets dismissed_at, also marks read), `get_preferences(user_id) -> NotificationPreferences` (returns defaults if no row exists), `update_preferences(user_id, prefs: NotificationPreferencesUpdate) -> NotificationPreferences` (upsert), `check_rate_limit(user_id) -> bool` (Redis sliding window, uses `notification_rate_limit_per_hour` from settings). Follow existing service patterns: async methods, `get_pool()`, structured logging, user_id scoping
- [x] T007 Write unit tests in `tests/unit/test_notification_service.py` — test create_notification persists and returns correct model, test list_notifications pagination and filtering (type, is_read), test list excludes dismissed notifications, test get_unread_count only counts unread non-dismissed, test mark_as_read updates is_read, test mark_as_read returns None for wrong user_id, test mark_all_as_read updates count, test dismiss sets dismissed_at and is_read=True, test dismiss returns False for wrong user_id, test get_preferences returns defaults when no row exists, test update_preferences upsert creates then updates, test check_rate_limit returns True under limit and False over limit. Mock asyncpg pool and Redis following existing test patterns

**Checkpoint**: Foundation ready — notification service can create, list, read, dismiss, and rate-limit notifications

---

## Phase 3: User Story 5 — Notification API Endpoints (Priority: P1) + User Story 1 — Agent Tool (Priority: P1)

**Goal**: Backend is fully functional — API serves notifications, agent can create them

**Independent Test**: Call API endpoints directly to CRUD notifications; chat with agent to trigger notification creation

### US5: API Endpoints

- [x] T008 [US5] Create notification API routes in `src/api/notifications.py` — `APIRouter(prefix="/notifications", tags=["Notifications"])` with endpoints per contract: `GET /notifications` (list, paginated, optional type/is_read filters), `GET /notifications/unread-count`, `PATCH /notifications/{id}/read`, `PATCH /notifications/read-all`, `DELETE /notifications/{id}` (dismiss). All endpoints use `Depends(get_current_user)` and delegate to `NotificationService`. Follow existing patterns from `src/api/memories.py`
- [x] T009 [US5] Register notification router in `src/main.py` — import and include the notifications router alongside existing routers
- [x] T010 [US5] Write unit tests for API endpoints in `tests/unit/test_notification_api.py` — test list returns paginated response with correct structure, test type filter, test is_read filter, test unread-count returns `{"count": N}`, test mark-as-read returns updated notification, test mark-as-read returns 404 for nonexistent/wrong-user, test read-all returns `{"updated_count": N}`, test dismiss returns 204, test dismiss returns 404 for nonexistent/wrong-user, test all endpoints return 401 without auth token. Mock NotificationService

### US1: Agent Tool

- [x] T011 [P] [US1] Create `send_notification` agent tool in `src/tools/send_notification.py` — `@function_tool` decorated async function per tool contract: extract user_id, conversation_id, correlation_id from `ctx.context`; validate message (non-empty, ≤500 chars) and type (reminder/info/warning, default info); check rate limit via `NotificationService.check_rate_limit()`; call `NotificationService.create_notification()`; return JSON response per contract (success/validation_error/rate_limited/error). Export as `send_notification_tool`. Follow patterns from `src/tools/save_memory.py`
- [x] T012 [US1] Register `send_notification_tool` in `ChatService._get_tools()` in `src/services/chat_service.py` — add dynamic import with graceful fallback, following the existing pattern for `save_memory_tool` and `save_entity_tool`
- [x] T013 [US1] Add notification system prompt to `src/services/chat_service.py` — add `NOTIFICATION_SYSTEM_PROMPT` constant with usage guidelines (when to create notifications: reminders, important info, warnings; respect user intent; keep messages concise). Append to agent instructions alongside existing MEMORY_SYSTEM_PROMPT and GRAPH_SYSTEM_PROMPT
- [x] T014 [P] [US1] Write unit tests for send_notification tool in `tests/unit/test_notification_tool.py` — test successful notification creation returns success JSON, test empty message returns validation error, test message over 500 chars returns validation error, test invalid type returns validation error, test missing user_id returns error, test rate limit exceeded returns rate_limited response, test service exception returns error response. Mock NotificationService following existing tool test patterns (patch at source module, use `tool.on_invoke_tool`)

**Checkpoint**: Backend complete for MVP — agent can create notifications, API can list/read/dismiss them

---

## Phase 4: User Story 2 — Viewing and Managing Notifications in the Frontend (Priority: P1) MVP

**Goal**: Users can see and manage notifications through the web UI

**Independent Test**: Seed notifications via API, verify bell icon shows count, panel lists notifications, mark-as-read and dismiss work

- [x] T015 [P] [US2] Create TypeScript interfaces in `frontend/src/types/notification.ts` — `Notification` (id, message, type, is_read, conversation_id, created_at), `NotificationPreferences` (delivery_channel, quiet_hours_start, quiet_hours_end, quiet_hours_timezone), `NotificationPreferencesUpdate`, `PaginatedNotifications` (items, total, limit, offset), `UnreadCountResponse` (count)
- [x] T016 [P] [US2] Add notification API methods to `frontend/src/lib/api-client.ts` — add methods to `apiClient`: `getNotifications(params?)`, `getUnreadCount()`, `markAsRead(id)`, `markAllAsRead()`, `dismissNotification(id)`, `getNotificationPreferences()`, `updateNotificationPreferences(prefs)`. Follow existing patterns (typed responses, auth headers)
- [x] T017 [US2] Create `useNotifications` hook in `frontend/src/hooks/useNotifications.ts` — state: notifications[], unreadCount, isLoading. Methods: fetchNotifications (paginated), fetchUnreadCount, markAsRead(id), markAllAsRead, dismiss(id). Auto-fetch on mount. Follow pattern from `frontend/src/hooks/useMemories.ts`. Poll unread count on page load
- [x] T018 [P] [US2] Create `NotificationItem` component in `frontend/src/components/notification/NotificationItem.tsx` — displays single notification: type icon (bell for reminder, info circle for info, warning triangle for warning), message text, relative timestamp, read/unread visual state (bold for unread). Actions: mark as read button, dismiss (X) button. Support dark mode via existing Tailwind dark variants
- [x] T019 [US2] Create `NotificationPanel` component in `frontend/src/components/notification/NotificationPanel.tsx` — dropdown panel (absolute positioned below bell): header with "Notifications" title and "Mark all as read" button, scrollable list of `NotificationItem` components, empty state message when no notifications, loading skeleton while fetching. Close on click outside. Support dark mode
- [x] T020 [US2] Create `NotificationBell` component in `frontend/src/components/notification/NotificationBell.tsx` — bell icon button in header, badge with unread count (hidden when 0), click toggles `NotificationPanel` dropdown. Use `useNotifications` hook for data. Close panel on outside click
- [x] T021 [US2] Add `NotificationBell` to `Header` component in `frontend/src/components/layout/Header.tsx` — insert `<NotificationBell />` before `<ThemeToggle />` in the header actions div
- [x] T022 [US2] Create barrel export in `frontend/src/components/notification/index.ts` — export NotificationBell, NotificationPanel, NotificationItem
- [x] T023 [P] [US2] Write frontend component tests in `frontend/src/components/notification/__tests__/NotificationBell.test.tsx` — test bell renders with unread count badge, test badge hidden when count is 0, test click toggles panel visibility, test panel shows notification list, test mark-as-read updates state, test dismiss removes notification from list, test empty state displayed when no notifications. Mock useNotifications hook

**Checkpoint**: MVP complete — agent creates notifications, API serves them, frontend displays and manages them

---

## Phase 5: User Story 4 — Notification Preferences (Priority: P2)

**Goal**: Users can configure delivery channel and quiet hours

**Independent Test**: Set preferences via API, verify they persist and return correctly; verify frontend preferences UI saves and loads

- [x] T024 [US4] Add preferences API endpoints to `src/api/notifications.py` — `GET /notifications/preferences` (returns current or defaults), `PUT /notifications/preferences` (upsert). Validate quiet_hours_start/end are both set or both null. Use `NotificationService.get_preferences()` and `.update_preferences()`
- [x] T025 [P] [US4] Write unit tests for preferences endpoints in `tests/unit/test_notification_preferences_api.py` — test GET returns defaults when no preferences set, test GET returns saved preferences, test PUT creates preferences, test PUT updates existing preferences, test PUT validates quiet hours (both or neither), test PUT validates delivery_channel enum, test 401 without auth
- [x] T026 [US4] Create notification preferences UI in `frontend/src/components/notification/NotificationPreferences.tsx` — form with: delivery channel radio/select (in_app, email, both), quiet hours start/end time inputs (shown when email or both selected), timezone selector, save button. Load current preferences on mount, save via API. Show success/error feedback. Support dark mode
- [x] T027 [US4] Add preferences section to notification panel or as a settings link — add a gear icon or "Settings" link in the `NotificationPanel` header that opens `NotificationPreferences` in a dialog/modal

**Checkpoint**: Users can configure how they receive notifications

---

## Phase 6: User Story 3 — Email Delivery (Priority: P2)

**Goal**: Notifications are delivered via email when user has opted in

**Independent Test**: Enable email in preferences, create notification, verify email sent; test quiet hours deferral

- [x] T028 [US3] Implement `EmailService` in `src/services/email_service.py` — methods: `send_notification_email(to_email, notification: Notification) -> bool` (sends via aiosmtplib using settings for host/port/credentials/TLS, returns True on success, False on failure with logging), `is_in_quiet_hours(preferences: NotificationPreferences) -> bool` (checks current time against quiet hours window including cross-midnight handling, uses timezone from preferences), `defer_email(notification_id, user_id, deliver_after) -> None` (inserts into deferred_emails table), `process_deferred_emails() -> int` (finds pending emails past deliver_after, sends them, marks delivered_at or failed_at, returns count processed). Use structured logging with correlation_id for all operations
- [x] T029 [US3] Integrate email delivery into `NotificationService.create_notification()` in `src/services/notification_service.py` — after creating notification: check if email enabled in settings, look up user preferences via `get_preferences()`, if delivery_channel is 'email' or 'both': get user email from database, if no email address skip with warning log, if in quiet hours call `EmailService.defer_email()`, otherwise call `EmailService.send_notification_email()` asynchronously (fire-and-forget via `asyncio.create_task`, catch and log exceptions). Email failure must NOT affect in-app notification success
- [x] T030 [US3] Add deferred email processing to app lifespan in `src/main.py` — start a background asyncio task during app startup that periodically (every 60 seconds) calls `EmailService.process_deferred_emails()`. Cancel the task during shutdown. Log each cycle with count of emails processed
- [x] T031 [US3] Update `UserService` in `src/services/user_service.py` — add `get_email(user_id) -> str | None` method that fetches the email column for a user. Update `update_user()` to accept optional email parameter
- [x] T032 [US3] Add email field to admin user management — update `src/api/admin.py` to accept email in user create/update endpoints. Update relevant request models in `src/models/auth.py` or `src/models/user.py` to include optional email field
- [x] T033 [P] [US3] Write unit tests for EmailService in `tests/unit/test_email_service.py` — test send_notification_email success (mock aiosmtplib.SMTP), test send_notification_email failure returns False and logs, test is_in_quiet_hours returns True during quiet hours, test is_in_quiet_hours handles cross-midnight window (e.g., 22:00-07:00), test is_in_quiet_hours returns False outside quiet hours, test is_in_quiet_hours returns False when no quiet hours configured, test defer_email creates row in deferred_emails, test process_deferred_emails sends pending emails and marks delivered, test process_deferred_emails marks failed emails with error message
- [x] T034 [P] [US3] Write unit tests for email integration in `tests/unit/test_notification_email_integration.py` — test create_notification sends email when preference is 'email' or 'both', test create_notification does not send email when preference is 'in_app', test create_notification defers email during quiet hours, test create_notification skips email when no email address on file (with warning log), test email failure does not block notification creation, test email not sent when notification_email_enabled is False in settings

**Checkpoint**: Full email delivery pipeline working — immediate send, quiet hours deferral, failure resilience

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, documentation, and hardening

- [x] T035 Update `frontend/src/components/layout/Sidebar.tsx` — add "Notifications" nav item linking to notification preferences or a dedicated notifications page if warranted
- [x] T036 Add notification type icons and colors — ensure `NotificationItem` uses distinct visual treatment per type: reminder (clock icon, blue), info (info icon, gray), warning (warning icon, amber). Verify dark mode variants
- [x] T037 Add `.env.example` entries for all new notification/email environment variables with comments
- [x] T038 Run quickstart.md validation — follow all steps in `specs/010-agent-notifications/quickstart.md` and verify each passes against running Docker services

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US5 + US1 (Phase 3)**: Depends on Phase 2 — API and tool can be built in parallel
- **US2 (Phase 4)**: Depends on Phase 3 (US5 API endpoints must exist for frontend to consume)
- **US4 (Phase 5)**: Depends on Phase 2 (preferences service is in foundational), can run parallel with Phase 4
- **US3 (Phase 6)**: Depends on Phase 5 (needs preferences to determine email delivery)
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

- **US5 (API)**: Depends on foundational only — no other story dependencies
- **US1 (Agent Tool)**: Depends on foundational only — parallel with US5
- **US2 (Frontend)**: Depends on US5 (consumes API endpoints)
- **US4 (Preferences)**: Depends on foundational only — can parallel with US2
- **US3 (Email)**: Depends on US4 (preferences determine email behavior)

### Within Each User Story

- Models before services
- Services before endpoints/tool
- Core implementation before integration
- Tests alongside implementation

### Parallel Opportunities

- T001 and T002 can run in parallel (Setup phase)
- T004 and T005 can run in parallel (Pydantic models)
- T008-T010 (US5) and T011-T014 (US1) can run in parallel (different files, both depend on T006)
- T015, T016, T018 can run in parallel (frontend types, API client, component — different files)
- T023 and T025 can run in parallel (frontend tests and backend preference tests)
- T033 and T034 can run in parallel (email service tests)

---

## Parallel Example: Phase 3 (US5 + US1)

```bash
# After Phase 2 foundational is complete, launch both in parallel:

# US5 track:
Task: "T008 [US5] Create notification API routes in src/api/notifications.py"
Task: "T009 [US5] Register notification router in src/main.py"
Task: "T010 [US5] Write unit tests for API endpoints"

# US1 track (parallel with US5):
Task: "T011 [US1] Create send_notification agent tool in src/tools/send_notification.py"
Task: "T012 [US1] Register send_notification_tool in ChatService._get_tools()"
Task: "T013 [US1] Add notification system prompt"
Task: "T014 [US1] Write unit tests for send_notification tool"
```

---

## Implementation Strategy

### MVP First (Phase 1-4: US5 + US1 + US2)

1. Complete Phase 1: Setup (dependency + config)
2. Complete Phase 2: Foundational (migration, models, service)
3. Complete Phase 3: US5 API + US1 Agent Tool (backend complete)
4. Complete Phase 4: US2 Frontend (bell + panel)
5. **STOP and VALIDATE**: Agent can create notifications, user can see and manage them in the UI
6. Deploy/demo if ready — email can be added incrementally

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US5 + US1 → Backend works → API + tool testable
3. Add US2 → Frontend works → Full MVP demo
4. Add US4 → Preferences configurable
5. Add US3 → Email delivery active
6. Polish → Production ready

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Migration file number 009 — verify no conflict with existing migrations before creating
