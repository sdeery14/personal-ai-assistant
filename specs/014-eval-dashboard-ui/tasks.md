# Tasks: Eval Dashboard UI

**Input**: Design documents from `/specs/014-eval-dashboard-ui/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Install dependencies and create shared type definitions used by all user stories

- [X] T001 Install `recharts` dependency in frontend via `cd frontend && npm install recharts`
- [X] T002 [P] Create TypeScript interfaces for all eval dashboard API responses (TrendSummary, TrendPoint, PromptChange, RegressionReport, PromotionGateResult, PromotionEvalCheck, AuditRecord, EvalRunStatus, EvalRunResult, PromptListItem, RollbackInfo) in frontend/src/types/eval-dashboard.ts. Use camelCase field names mapped from snake_case API responses.
- [X] T003 [P] Create Pydantic request/response models (TrendPointResponse, PromptChangeResponse, TrendSummaryResponse, RegressionReportResponse, PromotionEvalCheckResponse, PromotionGateResponse, AuditRecordResponse, EvalRunStatusResponse, EvalRunResultResponse, PromptListItem, RollbackInfoResponse, and request models: PromotionCheckRequest, PromotionExecuteRequest, EvalRunRequest, RollbackExecuteRequest) in src/models/eval_dashboard.py. Each response model maps from its corresponding pipeline dataclass.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: API router scaffold, page shell, shared UI components, and navigation — MUST be complete before ANY user story

- [X] T004 Create FastAPI router scaffold in src/api/eval_dashboard.py with `router = APIRouter(prefix="/admin/evals", tags=["Eval Dashboard"])`. Add placeholder endpoints for all 9 routes (trends, regressions, prompts, promote/check, promote/execute, run, run/status, rollback/info, rollback/execute). All endpoints use `admin: User = Depends(require_admin)`. Import structlog for logging.
- [X] T005 Register eval_dashboard router in src/main.py by importing `from src.api.eval_dashboard import router as eval_dashboard_router` and adding `app.include_router(eval_dashboard_router)`.
- [X] T006 [P] Create reusable Tabs UI component in frontend/src/components/ui/Tabs.tsx. Props: `tabs: {id: string, label: string}[]`, `activeTab: string`, `onTabChange: (id: string) => void`. Render tab buttons with active/inactive styling matching existing admin panel patterns (blue active, gray inactive). Export from frontend/src/components/ui/index.ts.
- [X] T007 [P] Create eval dashboard hooks scaffold in frontend/src/hooks/useEvalDashboard.ts. Export placeholder hooks: `useTrends()`, `useRegressions()`, `usePrompts()`, `usePromote()`, `useEvalRun()`, `useRollback()`. Each returns `{ data, isLoading, error, refresh }` pattern matching existing hooks (useConversations, useMemories). Use `apiClient` for API calls.
- [X] T008 Create eval dashboard page shell in frontend/src/app/(main)/admin/evals/page.tsx. Use `"use client"` directive. Check `isAdmin` from session, redirect non-admins to `/chat`. Render Tabs component with 5 tabs (Trends, Regressions, Promote, Run Evals, Rollback). Conditionally render placeholder content per active tab. Include a refresh button in the header area.
- [X] T009 Add "Evals" navigation link to admin section. In frontend/src/components/layout/Header.tsx, add a link to `/admin/evals` visible only to admins (next to existing Admin link). In frontend/src/components/layout/Sidebar.tsx, add corresponding mobile nav entry. Use same active-link styling pattern as existing admin link.

**Checkpoint**: Foundation ready — API router registered, page shell renders with tabs, admin navigation includes Evals link

---

## Phase 3: User Story 1 — View Eval Quality Trends (Priority: P1)

**Goal**: Admin users can view a summary table of eval types with pass rates and trend indicators, and drill into a detail view with an interactive chart and data table for each eval type.

**Independent Test**: Navigate to `/admin/evals`, verify the Trends tab shows a summary table. Click an eval type and verify the detail view shows a line chart and data table.

### Implementation for User Story 1

- [X] T010 [US1] Implement GET /admin/evals/trends endpoint in src/api/eval_dashboard.py. Accept query params `eval_type` (optional str) and `limit` (int, default 10). Use inline imports: `from eval.pipeline.aggregator import get_eval_experiments, get_trend_points, build_trend_summary`. For each experiment (filtered by eval_type if provided), call get_trend_points then build_trend_summary. Return `{"summaries": [TrendSummaryResponse, ...]}`. Handle empty state: return `{"summaries": []}`.
- [X] T011 [P] [US1] Write unit tests for GET /admin/evals/trends in tests/unit/test_eval_dashboard.py. Mock `eval.pipeline.aggregator.get_eval_experiments`, `eval.pipeline.aggregator.get_trend_points`, and `eval.pipeline.aggregator.build_trend_summary`. Test cases: returns summaries for multiple eval types, filters by eval_type param, respects limit param, empty state returns empty list.
- [X] T012 [US1] Implement `useTrends` hook in frontend/src/hooks/useEvalDashboard.ts. Calls `GET /admin/evals/trends` with optional `evalType` and `limit` params. Returns `{ summaries, isLoading, error, refresh }`. Fetches on mount and on `refresh()` call.
- [X] T013 [US1] Implement TrendChart component in frontend/src/components/eval-dashboard/TrendChart.tsx. Use `"use client"` directive. Accept `points: TrendPoint[]` and `promptChanges: PromptChange[]` props. Render a Recharts `ResponsiveContainer` > `LineChart` with pass_rate on Y-axis (0-100%), timestamps on X-axis. Add `ReferenceDot` markers for prompt version changes with custom tooltip showing prompt name and version change. Add hover tooltip showing run details (date, pass rate, score).
- [X] T014 [US1] Implement TrendsTab component in frontend/src/components/eval-dashboard/TrendsTab.tsx. Use `"use client"` directive. Render summary table with columns: Eval Type, Latest Pass Rate (formatted as percentage), Trend Direction (with color: green=improving, gray=stable, red=degrading), Run Count. Clicking a row expands/shows a detail view below with TrendChart and a data table of individual runs (run_id, date, pass_rate, average_score, prompt_versions, status). Include a limit dropdown (5/10/20/50). Show empty state "No eval data available yet" when summaries is empty. Use Card, Skeleton for loading state.
- [X] T015 [P] [US1] Write tests for TrendsTab in frontend/tests/components/eval-dashboard/TrendsTab.test.tsx. Mock the useTrends hook. Test cases: renders summary table with eval types, shows loading skeleton, shows empty state message, clicking a row shows detail view.

**Checkpoint**: `GET /admin/evals/trends` returns data, Trends tab displays summary table with interactive chart detail view

---

## Phase 4: User Story 2 — View Regression Reports (Priority: P1)

**Goal**: Admin users can view regression check results showing a comparison table with verdicts per eval type, with REGRESSION verdicts visually highlighted and changed prompts displayed.

**Independent Test**: Navigate to `/admin/evals`, click the Regressions tab. Verify comparison table shows verdicts with color coding and changed prompts.

### Implementation for User Story 2

- [X] T016 [US2] Implement GET /admin/evals/regressions endpoint in src/api/eval_dashboard.py. Accept query param `eval_type` (optional str). Use inline import: `from eval.pipeline.regression import check_all_regressions`. Call `check_all_regressions(eval_type_filter=eval_type)`. Return `{"reports": [RegressionReportResponse, ...], "has_regressions": bool}`. has_regressions is True if any report has verdict "REGRESSION".
- [X] T017 [P] [US2] Write unit tests for GET /admin/evals/regressions in tests/unit/test_eval_dashboard.py (append). Mock `eval.pipeline.regression.check_all_regressions`. Test cases: returns regression reports with correct has_regressions flag, filters by eval_type, empty state returns empty list with has_regressions=false.
- [X] T018 [US2] Implement `useRegressions` hook in frontend/src/hooks/useEvalDashboard.ts. Calls `GET /admin/evals/regressions` with optional `evalType`. Returns `{ reports, hasRegressions, isLoading, error, refresh }`.
- [X] T019 [US2] Implement RegressionsTab component in frontend/src/components/eval-dashboard/RegressionsTab.tsx. Use `"use client"` directive. Render a comparison table with columns: Eval Type, Baseline Pass Rate, Current Pass Rate, Delta (formatted with +/- prefix), Threshold, Verdict. Color code verdict badges: REGRESSION=red, WARNING=yellow, IMPROVED=green, PASS=gray. Below each row with changed prompts, show "Changed: prompt-name v1 → v2". Show summary at top: "N REGRESSION, N WARNING, N PASS, N IMPROVED" or "No regressions detected". Empty state: "No eval types with sufficient data for comparison." Use Card, Skeleton.
- [X] T020 [P] [US2] Write tests for RegressionsTab in frontend/tests/components/eval-dashboard/RegressionsTab.test.tsx. Mock the useRegressions hook. Test cases: renders comparison table with verdicts, REGRESSION verdict highlighted, changed prompts displayed, empty state message, summary counts.

**Checkpoint**: `GET /admin/evals/regressions` returns data, Regressions tab displays comparison table with verdict badges and changed prompts

---

## Phase 5: User Story 3 — Promote Prompt Version (Priority: P2)

**Goal**: Admin users can select a prompt, view promotion gate check results, and execute or force-promote with audit details displayed.

**Independent Test**: Navigate to Promote tab, select a prompt, verify gate check table displays. Verify promotion executes when gates pass, and force-promote works with reason when gates fail.

### Implementation for User Story 3

- [X] T021 [US3] Implement GET /admin/evals/prompts endpoint in src/api/eval_dashboard.py. Use inline import: `from src.services.prompt_service import get_active_prompt_versions`. Call `get_active_prompt_versions()`, convert to list of PromptListItem, return `{"prompts": [...]}`.
- [X] T022 [US3] Implement POST /admin/evals/promote/check endpoint in src/api/eval_dashboard.py. Accept PromotionCheckRequest body. Use inline import: `from eval.pipeline.promotion import check_promotion_gate`. Call `check_promotion_gate(prompt_name, from_alias, to_alias, version)`. Return PromotionGateResponse.
- [X] T023 [US3] Implement POST /admin/evals/promote/execute endpoint in src/api/eval_dashboard.py. Accept PromotionExecuteRequest body. If not force, run gate check first and return 403 if blocked. Use inline import: `from eval.pipeline.promotion import execute_promotion, check_promotion_gate`. Extract actor from `admin.username`. Call `execute_promotion(...)`. Return AuditRecordResponse.
- [X] T024 [P] [US3] Write unit tests for promote endpoints in tests/unit/test_eval_dashboard.py (append). Mock `src.services.prompt_service.get_active_prompt_versions`, `eval.pipeline.promotion.check_promotion_gate`, `eval.pipeline.promotion.execute_promotion`. Test cases: prompts list returns all registered prompts, gate check returns allowed/blocked, execute promotion succeeds, blocked promotion returns 403, force promotion bypasses gate.
- [X] T025 [US3] Implement `usePrompts` and `usePromote` hooks in frontend/src/hooks/useEvalDashboard.ts. `usePrompts()` calls `GET /admin/evals/prompts`. `usePromote()` provides `checkGate(promptName, ...)` calling POST promote/check and `executePromotion(...)` calling POST promote/execute.
- [X] T026 [US3] Implement PromoteTab component in frontend/src/components/eval-dashboard/PromoteTab.tsx. Use `"use client"` directive. Render prompt selector dropdown (from usePrompts). "Check Gate" button triggers gate check and displays results table (eval type, pass rate, threshold, pass/fail badge). If allowed: show "Promote" button, on click execute and display AuditRecord details (from/to version, alias, timestamp, actor). If blocked: show blocking evals, "Force Promote" button with reason Input and Dialog confirmation with warning. Use Button, Card, Input, Dialog, Skeleton.
- [X] T027 [P] [US3] Write tests for PromoteTab in frontend/tests/components/eval-dashboard/PromoteTab.test.tsx. Mock usePrompts and usePromote hooks. Test cases: renders prompt selector, gate check results displayed, promotion success shows audit, blocked shows force option, force promote requires reason.

**Checkpoint**: Promote tab fully functional — gate check, promotion, force-promote, and audit display working

---

## Phase 6: User Story 4 — Trigger Eval Suite Run (Priority: P2)

**Goal**: Admin users can trigger a core or full eval suite run, see progress as each eval completes, and view regression results after completion.

**Independent Test**: Trigger a core eval suite run, verify progress updates via refresh, verify regression results appear after completion.

### Implementation for User Story 4

- [X] T028 [US4] Implement POST /admin/evals/run endpoint in src/api/eval_dashboard.py. Accept EvalRunRequest body with `suite` field. Create a module-level `_eval_run_state: dict | None` to track the current run. If a run is already in "running" status, return 409 Conflict. Otherwise, generate a UUID job ID, initialize state dict (run_id, suite, status="running", total, completed=0, results=[], regression_reports=None, started_at, finished_at=None). Start a background asyncio.Task that: (a) calls `run_eval_suite(suite, progress_callback=_update_progress)` where `_update_progress` updates `_eval_run_state` with completed count and results, (b) after completion calls `check_all_regressions()` and stores results, (c) sets status to "completed"/"failed" and finished_at. Return 202 with initial EvalRunStatusResponse.
- [X] T029 [US4] Implement GET /admin/evals/run/status endpoint in src/api/eval_dashboard.py. Return current `_eval_run_state` as EvalRunStatusResponse. If no run has ever been started, return null (200 OK with JSON null).
- [X] T030 [P] [US4] Write unit tests for eval run endpoints in tests/unit/test_eval_dashboard.py (append). Mock `eval.pipeline.trigger.run_eval_suite` and `eval.pipeline.regression.check_all_regressions`. Test cases: POST /run starts run and returns 202, POST /run returns 409 when run in progress, GET /status returns current state, GET /status returns null when no run exists. Use `unittest.mock.AsyncMock` for background task testing.
- [X] T031 [US4] Implement `useEvalRun` hook in frontend/src/hooks/useEvalDashboard.ts. Provides `startRun(suite)` calling POST /admin/evals/run and `getStatus()` calling GET /admin/evals/run/status. Returns `{ status, isLoading, error, startRun, refreshStatus }`.
- [X] T032 [US4] Implement RunEvalsTab component in frontend/src/components/eval-dashboard/RunEvalsTab.tsx. Use `"use client"` directive. Render suite selector (core/full radio or buttons) and "Run Suite" button. When a run is active: show progress bar or "N/M complete" counter, per-eval results as they appear (dataset name, PASS/FAIL badge), "Refresh" button to poll status. When complete: show regression check results inline (reuse verdict badge styling from RegressionsTab). When run fails: show error message. If already running: disable "Run Suite" and show "Run in progress" message. Use Button, Card, Skeleton.
- [X] T033 [P] [US4] Write tests for RunEvalsTab in frontend/tests/components/eval-dashboard/RunEvalsTab.test.tsx. Mock useEvalRun hook. Test cases: renders suite selector and run button, shows progress during run, shows completion with regression results, shows "run in progress" when concurrent run attempted.

**Checkpoint**: Run Evals tab triggers eval suite, shows progress, displays regression results after completion

---

## Phase 7: User Story 5 — Rollback Prompt Version (Priority: P3)

**Goal**: Admin users can select a prompt, see current and target rollback versions, provide a reason, execute the rollback, and view audit confirmation.

**Independent Test**: Navigate to Rollback tab, select a prompt, verify current/target versions shown. Execute rollback with reason and verify audit details displayed.

### Implementation for User Story 5

- [X] T034 [US5] Implement GET /admin/evals/rollback/info endpoint in src/api/eval_dashboard.py. Accept query params `prompt_name` (required) and `alias` (default "production"). Use inline imports: `from src.services.prompt_service import load_prompt_version` and `from eval.pipeline.rollback import find_previous_version`. Call both and return RollbackInfoResponse with current_version and previous_version (null if none).
- [X] T035 [US5] Implement POST /admin/evals/rollback/execute endpoint in src/api/eval_dashboard.py. Accept RollbackExecuteRequest body. Use inline import: `from eval.pipeline.rollback import execute_rollback`. Extract actor from `admin.username`. Call `execute_rollback(prompt_name, alias, previous_version, reason, actor)`. Return AuditRecordResponse. Return 400 if previous_version is invalid.
- [X] T036 [P] [US5] Write unit tests for rollback endpoints in tests/unit/test_eval_dashboard.py (append). Mock `src.services.prompt_service.load_prompt_version`, `eval.pipeline.rollback.find_previous_version`, `eval.pipeline.rollback.execute_rollback`. Test cases: rollback info returns current and previous version, rollback info returns null previous for v1, execute rollback returns audit record, execute rollback returns 400 for invalid version.
- [X] T037 [US5] Implement `useRollback` hook in frontend/src/hooks/useEvalDashboard.ts. Provides `getRollbackInfo(promptName, alias)` calling GET /admin/evals/rollback/info and `executeRollback(...)` calling POST /admin/evals/rollback/execute. Returns `{ rollbackInfo, isLoading, error, getRollbackInfo, executeRollback }`.
- [X] T038 [US5] Implement RollbackTab component in frontend/src/components/eval-dashboard/RollbackTab.tsx. Use `"use client"` directive. Render prompt selector dropdown (reuse usePrompts from US3). On prompt selection, call getRollbackInfo and display: current version, previous (target) version. If previous_version is null: show "No previous version available" and disable rollback button. If available: show reason Input (required) and "Rollback" button with Dialog confirmation. After execution: display AuditRecord details (rolled back from vN to vM, reason, timestamp). Use Button, Card, Input, Dialog, Skeleton.
- [X] T039 [P] [US5] Write tests for RollbackTab in frontend/tests/components/eval-dashboard/RollbackTab.test.tsx. Mock usePrompts and useRollback hooks. Test cases: renders prompt selector, shows rollback info, disables button when no previous version, executes rollback and shows audit, requires reason before executing.

**Checkpoint**: Rollback tab fully functional — prompt selection, version display, rollback execution, and audit display working

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, edge cases, and integration testing

- [X] T040 Run all backend unit tests via `uv run pytest tests/unit/test_eval_dashboard.py -v` and verify all pass
- [X] T041 Run all frontend tests via `cd frontend && npm test` and verify eval dashboard tests pass
- [X] T042 Verify admin access control: non-admin users cannot access `/admin/evals` (redirect to `/chat`), admin link not visible to non-admin users
- [X] T043 Verify empty states across all tabs: Trends shows "No eval data available yet", Regressions shows "No eval types with sufficient data", Promote shows prompt list even with no evals, Run Evals works with no prior runs, Rollback shows "No previous version" for v1 prompts
- [X] T044 Run quickstart.md validation: walk through each scenario and verify expected outputs

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational (Phase 2)
- **US2 (Phase 4)**: Depends on Foundational (Phase 2) — can run in parallel with US1
- **US3 (Phase 5)**: Depends on Foundational (Phase 2) — can run in parallel with US1/US2
- **US4 (Phase 6)**: Depends on Foundational (Phase 2) — can run in parallel with US1/US2/US3
- **US5 (Phase 7)**: Depends on US3 (Phase 5) — reuses `usePrompts` hook from US3
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Foundational only — first story, establishes trend display pattern
- **US2 (P1)**: Foundational only — independent of US1, establishes verdict badge pattern
- **US3 (P2)**: Foundational only — introduces prompt selector and audit display patterns
- **US4 (P2)**: Foundational only — independent, introduces background task + progress pattern
- **US5 (P3)**: US3 — reuses `usePrompts` hook for prompt selector dropdown

### Within Each User Story

- Backend endpoint before frontend hook (hook calls the endpoint)
- Frontend hook before component (component uses the hook)
- Backend tests can run in parallel [P] with frontend implementation
- Frontend tests can run in parallel [P] with next story's backend work

### Parallel Opportunities

- T002 and T003 can run in parallel (different files: TS types vs Python models)
- T006 and T007 can run in parallel (different files: Tabs component vs page shell)
- T011 and T012-T014 can run in parallel (backend test vs frontend implementation)
- T017 and T018-T019 can run in parallel (backend test vs frontend implementation)
- T024 and T025-T026 can run in parallel (backend test vs frontend implementation)
- T030 and T031-T032 can run in parallel (backend test vs frontend implementation)
- T036 and T037-T038 can run in parallel (backend test vs frontend implementation)

---

## Parallel Example: User Story 1

```bash
# After T010 (trends endpoint) is complete:
# Launch backend tests and frontend work in parallel:
Task T011: "Unit tests for trends endpoint in tests/unit/test_eval_dashboard.py"
Task T012: "Implement useTrends hook in frontend/src/hooks/useEvalDashboard.ts"
Task T013: "Implement TrendChart component in frontend/src/components/eval-dashboard/TrendChart.tsx"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T009)
3. Complete Phase 3: US1 — View Trends (T010–T015)
4. Complete Phase 4: US2 — View Regressions (T016–T020)
5. **STOP and VALIDATE**: Trends and Regressions tabs work end-to-end
6. This provides the core "observe quality" dashboard

### Incremental Delivery

1. Setup + Foundational → Page shell exists, tabs navigate, admin-only
2. Add US1 (Trends) → Test independently → Admins can view quality trends with charts
3. Add US2 (Regressions) → Test independently → Admins can see regression verdicts
4. Add US3 (Promote) → Test independently → Admins can promote prompts via UI
5. Add US4 (Run Evals) → Test independently → Admins can trigger eval runs
6. Add US5 (Rollback) → Test independently → Admins can rollback prompts via UI
7. Polish → Edge cases, access control verification, final validation
