# Tasks: Proactive Assistant ("The Alfred Engine")

**Input**: Design documents from `/specs/011-proactive-assistant/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add new dependency, create database migration, Pydantic models, and configuration for all 5 user stories

- [x] T001 Add `croniter` dependency via `uv add croniter` in pyproject.toml
- [x] T002 Create database migration `migrations/011_proactive_assistant.sql` with all 5 tables (scheduled_tasks, task_runs, observed_patterns, engagement_events, proactiveness_settings), indexes, triggers, and check constraints per data-model.md
- [x] T003 [P] Create `src/models/schedule.py` with ScheduledTask, TaskRun, TaskStatus enum, TaskType enum, and TaskSource enum per data-model.md
- [x] T004 [P] Create `src/models/pattern.py` with ObservedPattern model and PatternType enum per data-model.md
- [x] T005 [P] Create `src/models/engagement.py` with EngagementEvent, ProactivenessSettings, EngagementAction enum, and SuggestionSource enum per data-model.md
- [x] T006 Add Feature 011 configuration settings to `src/config.py`: scheduler_poll_interval_seconds (default 30), scheduler_max_concurrent_tasks (default 5), pattern_occurrence_threshold (default 3), suggestion_confidence_threshold (default 0.6), proactive_check_interval_minutes (default 15)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core services that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T007 Create `src/services/proactive_service.py` with ProactiveService class: get_or_create_settings(user_id), update_settings(user_id, updates), is_onboarded(user_id), mark_onboarded(user_id), get_user_profile(user_id) — the profile method aggregates data from memory_items, entities, observed_patterns, engagement_events, and proactiveness_settings tables
- [x] T008 Write unit tests for ProactiveService in `tests/unit/test_proactive_service.py`: test settings CRUD, is_onboarded check, mark_onboarded, user profile aggregation with mocked database queries
- [x] T009 Create `src/services/engagement_service.py` with EngagementService class: record_event(user_id, suggestion_type, action, source, context), get_engagement_stats(user_id, suggestion_type), check_suppression(user_id, suggestion_type), check_boost(user_id, suggestion_type) — suppression triggers at 3+ dismissals of same type, boosting triggers at 3+ engagements
- [x] T010 Write unit tests for EngagementService in `tests/unit/test_engagement_service.py`: test event recording, suppression threshold (3 dismissals), boosting threshold (3 engagements), stats aggregation with mocked database queries

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — First Encounter: Alfred Introduces Himself (Priority: P1) MVP

**Goal**: New users see a warm conversational onboarding prompt; returning users get a personalized greeting. Facts and preferences are saved to memory and knowledge graph during onboarding.

**Independent Test**: Create a new user account, log in, open a chat. Verify the assistant initiates a warm conversational greeting. Respond with personal info and verify memories and entities are saved. Log in again and verify no repeat onboarding.

### Implementation for User Story 1

- [x] T011 [US1] Add `ONBOARDING_SYSTEM_PROMPT` constant to `src/services/chat_service.py` — warm, conversational first-encounter instructions that direct the agent to ask about the user's context, save facts/preferences to memory, create entities/relationships in the knowledge graph, and gracefully handle users who skip onboarding
- [x] T012 [US1] Add `PROACTIVE_GREETING_PROMPT` constant to `src/services/chat_service.py` — instructions for returning users that direct the agent to reference what it knows about the user, offer relevant help based on recent activity and patterns, and cite memory/knowledge graph context
- [x] T013 [US1] Update `ChatService.create_agent()` in `src/services/chat_service.py` to query the user's onboarding status via ProactiveService.is_onboarded(user_id) — inject ONBOARDING_SYSTEM_PROMPT for new users, PROACTIVE_GREETING_PROMPT for returning users
- [x] T014 [US1] Update `ChatService.stream_completion()` in `src/services/chat_service.py` to call ProactiveService.mark_onboarded(user_id) after the first completed conversation for a new user (fire-and-forget, similar to episode summarization pattern)
- [x] T015 [US1] Write unit tests in `tests/unit/test_onboarding.py`: test that create_agent() includes onboarding prompt for new users (is_onboarded=False), proactive greeting for returning users (is_onboarded=True), graceful fallback when proactive_service is unavailable

**Checkpoint**: User Story 1 fully functional — new users see onboarding, returning users see personalized greeting

---

## Phase 4: User Story 2 — Building the Picture: Alfred Observes (Priority: P1)

**Goal**: The assistant actively detects and records behavioral patterns across conversations — recurring topics, time-based behaviors, frequently mentioned people/projects. Patterns are stored as structured data for future proactive assistance.

**Independent Test**: Have 3+ conversations mentioning the same topic. Verify observed_patterns table contains a pattern with occurrence_count >= 3.

### Implementation for User Story 2

- [x] T016 [US2] Create `src/services/pattern_service.py` with PatternService class: record_or_update_pattern(user_id, pattern_type, description, evidence, suggested_action, confidence), list_patterns(user_id, min_occurrences), get_actionable_patterns(user_id) — actionable = occurrence_count >= threshold AND acted_on = FALSE
- [x] T017 [US2] Create `src/tools/record_pattern.py` with `@function_tool` record_pattern(ctx, pattern_type, description, evidence, suggested_action, confidence) — validates inputs, calls PatternService.record_or_update_pattern(), returns JSON with pattern_id, occurrence_count, and threshold_reached flag per contracts/agent-tools.md
- [x] T018 [US2] Add `OBSERVATION_SYSTEM_PROMPT` to `src/services/chat_service.py` instructing the agent to actively look for patterns (recurring topics, time-based behaviors, frequently mentioned entities), use the record_pattern tool when patterns are detected, and focus on patterns that could inform future helpful actions
- [x] T019 [US2] Register the record_pattern tool in `ChatService._get_tools()` and add OBSERVATION_SYSTEM_PROMPT to `ChatService.create_agent()` instructions in `src/services/chat_service.py` (always active, not conditional)
- [x] T020 [US2] Write unit tests in `tests/unit/test_pattern_service.py`: test pattern creation, pattern matching/update on duplicate, occurrence_count increment, actionable pattern threshold, list filtering
- [x] T021 [P] [US2] Write unit tests in `tests/unit/test_pattern_tools.py`: test record_pattern tool validation, successful recording, duplicate pattern update, missing user_id error, following the on_invoke_tool testing pattern

**Checkpoint**: User Story 2 fully functional — patterns are detected and stored across conversations

---

## Phase 5: User Story 3 — Proactive Assistance: Alfred Has the Tea Ready (Priority: P2)

**Goal**: The assistant proactively offers relevant suggestions during conversations (based on user context, patterns, and available tools) and tracks whether suggestions are engaged with or dismissed.

**Independent Test**: Build context through several conversations, then start a new conversation. Verify the assistant offers a relevant suggestion citing its basis. Dismiss the suggestion and verify an engagement event is recorded.

**Dependencies**: Builds on US1 (onboarding provides initial context) and US2 (patterns inform suggestions). Can be implemented after Phase 2 but benefits from US2 patterns being available.

### Implementation for User Story 3

- [x] T022 [US3] Create `src/tools/record_engagement.py` with `@function_tool` record_engagement(ctx, suggestion_type, action, source) — validates action is "engaged" or "dismissed", calls EngagementService.record_event(), triggers suppression/boosting check as side effect, returns JSON confirmation per contracts/agent-tools.md
- [x] T023 [US3] Add proactive suggestion guidance to `PROACTIVE_GREETING_PROMPT` in `src/services/chat_service.py` — instruct the agent to: check user's patterns and recent context, offer relevant suggestions with citations ("Based on your mention of X..."), use record_engagement tool to track user response, respect confidence threshold from proactiveness_settings, and not block the user's primary request
- [x] T024 [US3] Register the record_engagement tool in `ChatService._get_tools()` in `src/services/chat_service.py`
- [x] T025 [US3] Add suppression/boosting side effects to `EngagementService.record_event()` in `src/services/engagement_service.py` — after recording, check if 3+ dismissals of same type → add to suppressed_types in proactiveness_settings; check if 3+ engagements → add to boosted_types
- [x] T026 [US3] Write unit tests in `tests/unit/test_engagement_tools.py`: test record_engagement tool validation, successful recording, suppression triggered after 3 dismissals, boosting triggered after 3 engagements, following the on_invoke_tool testing pattern

**Checkpoint**: User Story 3 fully functional — proactive suggestions appear in conversations with engagement tracking

---

## Phase 6: User Story 4 — Scheduled Care: Alfred Manages the Household (Priority: P2)

**Goal**: Users can create one-time and recurring scheduled tasks via conversation. Tasks execute on schedule, invoke the production agent, and deliver results as notifications. A read-only frontend page shows all schedules.

**Independent Test**: Say "Send me weather every morning at 7am" — verify task created, appears in GET /schedules, and (when due) executes and creates a notification.

**Dependencies**: Requires Feature 010 notification infrastructure for delivery. Independent of US2/US3 for core functionality.

### Implementation for User Story 4

- [x] T027 [US4] Create `src/services/schedule_service.py` with ScheduleService class: create_task(user_id, name, description, task_type, schedule_cron, scheduled_at, timezone, tool_name, tool_args, prompt_template, source), get_task(task_id, user_id), list_tasks(user_id, status_filter, limit, offset), update_status(task_id, user_id, new_status), calculate_next_run(task) using croniter — handles both cron and one-time scheduling
- [x] T028 [US4] Create `src/services/scheduler_service.py` with SchedulerService class: start() launches async loop, stop() cancels it, _poll_loop() runs every scheduler_poll_interval_seconds, _execute_task(task) acquires Redis lock, invokes production agent via Runner.run (non-streamed) with task's prompt_template, records TaskRun, creates notification via NotificationService, updates next_run_at, handles retries on failure (max_retries from task), marks one-time tasks as completed after execution
- [x] T029 [P] [US4] Create `src/tools/create_schedule.py` with `@function_tool` create_schedule(ctx, name, task_type, schedule_cron, scheduled_at, timezone, tool_name, tool_args, prompt_template, description) — validates cron expression via croniter, validates tool_name against known tools, calls ScheduleService.create_task(), returns JSON with task_id and next_run_at per contracts/agent-tools.md
- [x] T030 [P] [US4] Create `src/tools/manage_schedule.py` with `@function_tool` manage_schedule(ctx, task_id, action) — validates action is "pause", "resume", or "cancel", calls ScheduleService.update_status(), returns JSON with updated status per contracts/agent-tools.md
- [x] T031 [US4] Add `SCHEDULE_SYSTEM_PROMPT` to `src/services/chat_service.py` instructing the agent to: use create_schedule for user requests ("remind me...", "send me X every..."), use manage_schedule for pause/resume/cancel requests, parse natural language time expressions into cron or datetime, confirm schedule details before creating, and list active schedules when asked
- [x] T032 [US4] Register create_schedule and manage_schedule tools in `ChatService._get_tools()` and add SCHEDULE_SYSTEM_PROMPT to `ChatService.create_agent()` instructions in `src/services/chat_service.py`
- [x] T033 [US4] Update `src/main.py` lifespan to start SchedulerService on startup and stop it on shutdown, following the existing deferred_email_task pattern (asyncio.create_task in startup, cancel in shutdown)
- [x] T034 [US4] Create `src/api/schedules.py` with APIRouter(prefix="/schedules"): GET / (list tasks with status filter, pagination), GET /{task_id} (single task with recent runs), GET /{task_id}/runs (run history with pagination) — all endpoints require get_current_user dependency and filter by user_id per contracts/schedules-api.md
- [x] T035 [US4] Register schedules router in `src/main.py` — import and include_router(schedules_router)
- [x] T036 [P] [US4] Create `frontend/src/types/schedule.ts` with TypeScript interfaces: ScheduledTask, TaskRun, ScheduleListResponse matching contracts/schedules-api.md response shapes
- [x] T037 [P] [US4] Create `frontend/src/hooks/useSchedules.ts` with useSchedules() hook following useNotifications pattern: fetchSchedules(offset), loading state, error handling, uses api-client GET /schedules
- [x] T038 [US4] Create `frontend/src/components/schedule/ScheduleCard.tsx` displaying task name, type badge (one-time/recurring), status badge (active/paused/cancelled/completed), schedule expression or datetime, next run time, last run time, and run count
- [x] T039 [US4] Create `frontend/src/components/schedule/ScheduleList.tsx` with paginated list of ScheduleCard components, status filter tabs (All/Active/Paused/Completed), empty state message, and load-more pagination
- [x] T040 [US4] Create `frontend/src/app/(main)/schedules/page.tsx` as read-only schedule list page using ScheduleList component
- [x] T041 [US4] Add "Schedules" nav item to `frontend/src/components/layout/Sidebar.tsx` between "Notifications" and "Admin" in the navItems array
- [x] T042 [US4] Write unit tests in `tests/unit/test_schedule_service.py`: test task creation (recurring + one-time), next_run_at calculation via croniter, status transitions (active→paused→active, active→cancelled, active→completed), list filtering, user isolation
- [x] T043 [P] [US4] Write unit tests in `tests/unit/test_scheduler_service.py`: test poll loop finds due tasks, task execution calls Runner.run with correct prompt, notification created on success, task_run recorded with duration, retry on transient failure, one-time task marked completed after execution, Redis lock prevents duplicate execution
- [x] T044 [P] [US4] Write unit tests in `tests/unit/test_schedule_tools.py`: test create_schedule tool with valid cron, invalid cron validation, one-time scheduling, manage_schedule pause/resume/cancel, missing user_id error, following the on_invoke_tool testing pattern
- [x] T045 [P] [US4] Write unit tests in `tests/unit/test_schedules_api.py`: test GET /schedules returns paginated list, GET /schedules/{id} returns task with runs, GET /schedules/{id}/runs returns run history, 404 for nonexistent task, user isolation (can't see other user's tasks)

**Checkpoint**: User Story 4 fully functional — scheduled tasks created via conversation, executed on schedule, results delivered as notifications, visible in frontend

---

## Phase 7: User Story 5 — Calibration: Alfred Reads the Room (Priority: P3)

**Goal**: The assistant adjusts proactiveness based on engagement history. Users can explicitly say "be more/less proactive" and ask "what do you know about me?" to see a structured summary. Corrections take effect immediately.

**Independent Test**: Dismiss 3+ suggestions of the same type, verify the assistant stops making them. Say "be more proactive" and verify settings change. Ask "what do you know about me?" and verify a structured response.

**Dependencies**: Requires US3 engagement tracking for automatic calibration. adjust_proactiveness and get_user_profile tools are independent of US3.

### Implementation for User Story 5

- [x] T046 [US5] Create `src/tools/adjust_proactiveness.py` with `@function_tool` adjust_proactiveness(ctx, direction) — validates direction is "more" or "less", calls ProactiveService.update_settings() to adjust global_level by ±0.2 (clamped 0.0-1.0), sets user_override, clears suppressed_types on "more", returns JSON with new level and confirmation per contracts/agent-tools.md
- [x] T047 [P] [US5] Create `src/tools/get_user_profile.py` with `@function_tool` get_user_profile(ctx) — calls ProactiveService.get_user_profile(user_id) to aggregate facts, preferences, patterns, key relationships, and proactiveness settings, returns JSON matching contracts/engagement-api.md profile response shape
- [x] T048 [US5] Create `src/api/proactive.py` with APIRouter(prefix="/proactive"): GET /settings (proactiveness settings), GET /profile (aggregated user profile) — all endpoints require get_current_user dependency per contracts/engagement-api.md
- [x] T049 [US5] Register proactive router in `src/main.py` — import and include_router(proactive_router)
- [x] T050 [US5] Register adjust_proactiveness and get_user_profile tools in `ChatService._get_tools()` in `src/services/chat_service.py`
- [x] T051 [US5] Add calibration guidance to system prompt in `src/services/chat_service.py` — add `CALIBRATION_SYSTEM_PROMPT` instructing the agent to: use adjust_proactiveness when user says "be more/less proactive", use get_user_profile when user asks "what do you know about me?", use record_engagement when user engages with or dismisses a suggestion, present profile data conversationally and invite corrections
- [x] T052 [US5] Write unit tests in `tests/unit/test_calibration_tools.py`: test adjust_proactiveness with "more" (level increases, suppressed_types cleared), adjust with "less" (level decreases), clamping at 0.0 and 1.0, get_user_profile returns aggregated data, missing user_id error, following the on_invoke_tool testing pattern
- [x] T053 [P] [US5] Write unit tests in `tests/unit/test_proactive_api.py`: test GET /proactive/settings returns defaults for new user, GET /proactive/profile returns aggregated data, user isolation (can't see other user's profile)

**Checkpoint**: User Story 5 fully functional — calibration adjusts automatically and via explicit instruction, user profile is viewable and correctable

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Evaluation coverage, configuration, documentation, and final validation

- [x] T054 [P] Create `eval/onboarding_golden_dataset.json` with 5-8 test cases: new user greeting, onboarding conversation with memory saves, user who skips onboarding, returning user personalized greeting, onboarding with entity extraction
- [x] T055 [P] Create `eval/proactive_golden_dataset.json` with 5-8 test cases: proactive weather suggestion, schedule creation from natural language, pattern-based suggestion, "what do you know about me?" response, "be less proactive" compliance
- [x] T056 [P] Add Feature 011 environment variables to `.env.example`: SCHEDULER_POLL_INTERVAL_SECONDS, SCHEDULER_MAX_CONCURRENT_TASKS, PATTERN_OCCURRENCE_THRESHOLD, SUGGESTION_CONFIDENCE_THRESHOLD, PROACTIVE_CHECK_INTERVAL_MINUTES
- [x] T057 Run full backend test suite (`uv run pytest tests/unit/ -v`) and verify all new and existing tests pass
- [x] T058 Run frontend tests (`cd frontend && npm test`) and verify all tests pass
- [x] T059 Run quickstart.md smoke test checklist to verify end-to-end functionality across all 5 user stories

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — no dependencies on other stories
- **US2 (Phase 4)**: Depends on Phase 2 — no dependencies on other stories
- **US3 (Phase 5)**: Depends on Phase 2 — benefits from US2 patterns but can be implemented independently
- **US4 (Phase 6)**: Depends on Phase 2 — independent of US2/US3 for core functionality
- **US5 (Phase 7)**: Depends on Phase 2 + US3 engagement tracking (T025) for automatic calibration; tools can be built independently
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

```text
Phase 1 (Setup)
    │
    ▼
Phase 2 (Foundational)
    │
    ├──► Phase 3: US1 (Onboarding) ────────────┐
    │                                            │
    ├──► Phase 4: US2 (Observation) ─────┐       │
    │                                    │       │
    ├──► Phase 5: US3 (Suggestions) ◄────┘       │
    │         │                                  │
    ├──► Phase 6: US4 (Scheduling) ──────────────┤
    │                                            │
    └──► Phase 7: US5 (Calibration) ◄── US3 ────┘
                                                 │
                                            Phase 8 (Polish)
```

### Within Each User Story

- Models before services
- Services before tools
- Tools before system prompt integration
- System prompt integration before registering tools in ChatService
- Core implementation before API endpoints and frontend
- Unit tests accompany each service/tool

### Parallel Opportunities

- T003, T004, T005 (all model files — different files)
- T029, T030 (create_schedule + manage_schedule tools — different files)
- T036, T037 (frontend types + hook — different files)
- T043, T044, T045 (scheduler/tool/API tests — different files)
- T046, T047 (adjust_proactiveness + get_user_profile tools — different files)
- T054, T055, T056 (eval datasets + env vars — different files)
- US1 and US2 can be worked on in parallel (both P1, no cross-dependency)
- US3 and US4 can be worked on in parallel (both P2, minimal cross-dependency)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T006)
2. Complete Phase 2: Foundational (T007–T010)
3. Complete Phase 3: US1 — Onboarding (T011–T015)
4. **STOP and VALIDATE**: New user sees onboarding, returning user sees personalized greeting
5. This is a meaningful, user-visible increment on its own

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (Onboarding) → Test independently → **MVP!** Users get a warm first encounter
3. Add US2 (Observation) → Test independently → Assistant detects patterns
4. Add US3 (Suggestions) → Test independently → Proactive suggestions appear in conversation
5. Add US4 (Scheduling) → Test independently → Scheduled tasks + frontend page
6. Add US5 (Calibration) → Test independently → Full calibration loop
7. Polish → Eval coverage + validation

### Suggested MVP Scope

**Phase 1 + Phase 2 + Phase 3 (US1 — Onboarding)**: 15 tasks. This delivers the most impactful user-visible change (warm first encounter, personalized greetings) with the least implementation complexity (primarily system prompt changes + one database query).

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] labels map tasks to specific user stories for traceability
- Each user story is independently completable and testable
- All new tools follow the existing `@function_tool` pattern with `on_invoke_tool` testing
- All new services follow the existing asyncpg pool pattern with structlog logging
- The scheduler follows the existing `asyncio.create_task` background loop pattern from main.py
- Frontend components follow existing patterns from notifications page (ScheduleCard ≈ NotificationItem)
- Constitution compliance: all tools schema-validated, all data user-scoped, structured logging on all operations
