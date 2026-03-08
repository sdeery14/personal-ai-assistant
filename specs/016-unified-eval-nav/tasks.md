# Tasks: Unified Eval Navigation

**Input**: Design documents from `/specs/016-unified-eval-nav/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Included — backend unit tests and frontend unit tests for new components/endpoints.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Backend models, types, and eval runner integration needed before any UI work.

- [X] T001 Add AgentVersionSummary, ExperimentResult, AgentVersionDetail, and AgentVersionsResponse Pydantic models in src/models/eval_explorer.py
- [X] T002 Add AgentVersion and AgentVersionDetail TypeScript interfaces in frontend/src/types/eval-explorer.ts
- [X] T003 Add `mlflow.genai.enable_git_model_versioning()` call to the shared eval setup in eval/runner.py — insert after `mlflow.set_experiment()` and before `mlflow.start_run()` in each `run_*_evaluation()` function
- [X] T004 [P] Write unit tests for the new agent version list endpoint in tests/unit/test_eval_explorer.py (mock `mlflow.search_logged_models`, `mlflow.search_traces`)
- [X] T005 [P] Write unit tests for the new agent version detail endpoint in tests/unit/test_eval_explorer.py (mock `mlflow.get_logged_model`, `mlflow.search_traces`)

**Checkpoint**: Backend models defined, eval runner creates LoggedModels on next run, endpoint tests ready (failing).

---

## Phase 2: Foundational (Backend Endpoints + Shared Frontend Components)

**Purpose**: Backend API endpoints and shared navigation components that all user stories depend on.

- [X] T006 Implement `GET /admin/evals/explorer/agents` endpoint in src/api/eval_explorer.py — call `mlflow.search_logged_models()` via `run_in_executor`, extract git tags, compute aggregate quality, return AgentVersionsResponse
- [X] T007 Implement `GET /admin/evals/explorer/agents/{model_id}` endpoint in src/api/eval_explorer.py — call `mlflow.get_logged_model()` and `mlflow.search_traces(model_id=...)` via `run_in_executor`, aggregate per-experiment results, return AgentVersionDetail
- [X] T008 Add `useAgentVersions()` and `useAgentVersionDetail(modelId)` hooks in frontend/src/hooks/useEvalExplorer.ts
- [X] T009 Create EvalSubNav component in frontend/src/components/eval-nav/EvalSubNav.tsx — horizontal nav bar with links to Dashboard, Agents, Experiments, Datasets, Trends; highlight active page based on current route
- [X] T010 Create Breadcrumb component in frontend/src/components/eval-nav/Breadcrumb.tsx — accepts array of {label, href} items, renders clickable trail with separators
- [X] T011 [P] Write unit test for EvalSubNav in frontend/tests/components/eval-nav/EvalSubNav.test.tsx (renders all links, highlights active)
- [X] T012 [P] Write unit test for Breadcrumb in frontend/tests/components/eval-nav/Breadcrumb.test.tsx (renders trail, links are clickable)

**Checkpoint**: Backend agents endpoints return data, shared nav components ready. Run backend unit tests to verify T004/T005 pass.

---

## Phase 3: User Story 1 — Unified Eval Section with Sub-Page Navigation (Priority: P1)

**Goal**: Replace two separate pages with a unified /admin/evals/* section sharing a layout with sub-navigation.

**Independent Test**: Navigate to /admin/evals, verify sub-nav links route to distinct pages. Header shows single "Evals" link.

### Implementation

- [X] T013 [US1] Create shared layout in frontend/src/app/(main)/admin/evals/layout.tsx — wraps children with admin auth guard and EvalSubNav component; redirects non-admins to /chat
- [X] T014 [US1] Refactor frontend/src/app/(main)/admin/evals/page.tsx — remove admin auth guard (now in layout), keep dashboard content (regression banner + summary table + promote/run/rollback tabs)
- [X] T015 [P] [US1] Create placeholder page at frontend/src/app/(main)/admin/evals/agents/page.tsx — "Agents" heading with loading state (full implementation in US2)
- [X] T016 [P] [US1] Create experiments list page at frontend/src/app/(main)/admin/evals/experiments/page.tsx — import and render ExperimentBrowser with onSelect navigating to /admin/evals/experiments/[id]
- [X] T017 [P] [US1] Create datasets list page at frontend/src/app/(main)/admin/evals/datasets/page.tsx — import and render DatasetViewer in list mode with onSelect navigating to /admin/evals/datasets/[name]
- [X] T018 [P] [US1] Create placeholder page at frontend/src/app/(main)/admin/evals/trends/page.tsx — "Trends" heading (full implementation in US4)
- [X] T019 [US1] Remove "Explorer" link from frontend/src/components/layout/Header.tsx — keep only "Evals" link pointing to /admin/evals
- [X] T020 [US1] Remove "Explorer" link from frontend/src/components/layout/Sidebar.tsx — keep only "Evals" link pointing to /admin/evals
- [X] T021 [US1] Delete frontend/src/app/(main)/admin/eval-explorer/ directory (page.tsx) — functionality moved to unified section

**Checkpoint**: Admin navigates to /admin/evals, sees sub-nav with Dashboard/Agents/Experiments/Datasets/Trends. Each link routes to a page. Header has single "Evals" entry.

---

## Phase 4: User Story 2 — Agent Version Browsing (Priority: P2)

**Goal**: Agents page shows all agent versions with git metadata; detail page shows per-experiment results.

**Independent Test**: Navigate to /admin/evals/agents, verify list of versions with git info. Click one to see detail with experiment results.

### Implementation

- [X] T022 [US2] Create AgentBrowser component in frontend/src/components/eval-explorer/AgentBrowser.tsx — sortable table with columns: commit SHA (short), branch, date, aggregate quality, experiment count, traces; click row calls onSelect(modelId) [NOTE: AgentBrowser is inlined in agents/page.tsx]
- [X] T023 [US2] Create AgentDetail component in frontend/src/components/eval-explorer/AgentDetail.tsx — shows git metadata (branch, commit, dirty badge, diff viewer if dirty), experiment results table (eval type, pass rate, quality, run count, link to experiment), total traces
- [X] T024 [US2] Implement agents list page at frontend/src/app/(main)/admin/evals/agents/page.tsx — replace placeholder with AgentBrowser using useAgentVersions hook, navigate to /admin/evals/agents/[modelId] on select
- [X] T025 [US2] Create agent detail page at frontend/src/app/(main)/admin/evals/agents/[modelId]/page.tsx — render Breadcrumb (Agents > commit SHA) + AgentDetail using useAgentVersionDetail hook; experiment name click navigates to /admin/evals/experiments/[id]
- [X] T026 [P] [US2] Write unit test for AgentBrowser in frontend/tests/components/eval-explorer/AgentBrowser.test.tsx (renders rows, shows git metadata, calls onSelect) [NOTE: AgentBrowser inlined in page; tests cover AgentDetail instead]
- [X] T027 [P] [US2] Write unit test for AgentDetail in frontend/tests/components/eval-explorer/AgentDetail.test.tsx (renders git metadata, experiment results table, handles loading/empty states)

**Checkpoint**: /admin/evals/agents shows version list; clicking through shows detail with per-experiment breakdown.

---

## Phase 5: User Story 3 — Experiment and Run Drill-Down with Breadcrumbs (Priority: P3)

**Goal**: Experiment detail and run detail pages with breadcrumb navigation.

**Independent Test**: Click experiment → see runs with breadcrumb. Click run → see traces with breadcrumb. Click breadcrumb to go back.

### Implementation

- [X] T028 [US3] Create experiment detail page at frontend/src/app/(main)/admin/evals/experiments/[experimentId]/page.tsx — render Breadcrumb (Experiments > experiment name) + RunBrowser with comparison support; run click navigates to /admin/evals/runs/[runId] passing experiment context via query params
- [X] T029 [US3] Create run detail page at frontend/src/app/(main)/admin/evals/runs/[runId]/page.tsx — render Breadcrumb (Experiments > experiment name > Run short-id) + TraceViewer + SessionViewer; read experiment context from query params for breadcrumb
- [X] T030 [US3] Add RunComparison integration to experiment detail page — when 2 runs selected in RunBrowser, show RunComparison component below the table with close button

**Checkpoint**: Full drill-down works: Experiments → experiment detail with runs → run detail with traces/sessions. Breadcrumbs navigate back at every level.

---

## Phase 6: User Story 4 — Version-Based Trends Page (Priority: P4)

**Goal**: Trends page shows agent quality progression with versions on X-axis and quality on Y-axis, plus per-eval-type detail.

**Independent Test**: Navigate to /admin/evals/trends, verify version-based quality chart renders and per-eval-type detail expands.

### Implementation

- [X] T031 [US4] Create VersionTrendChart component in frontend/src/components/eval-explorer/VersionTrendChart.tsx — CSS bar chart with agent versions (short commit SHA) on X-axis, universal quality (1-5) on Y-axis; tooltip shows full commit, branch, date; clicking a bar calls onVersionClick(modelId)
- [X] T032 [US4] Implement trends page at frontend/src/app/(main)/admin/evals/trends/page.tsx — replace placeholder with: VersionTrendChart (using useAgentVersions for data), then TrendsTab from eval-dashboard (per-eval-type summary with expandable detail); version click navigates to /admin/evals/agents/[modelId]
- [X] T033 [P] [US4] Write unit test for VersionTrendChart in frontend/tests/components/eval-explorer/VersionTrendChart.test.tsx (renders chart with version labels, handles empty state, calls onVersionClick)

**Checkpoint**: /admin/evals/trends shows version-based quality progression chart above per-eval-type summary table.

---

## Phase 7: User Story 5 — Dataset Browsing as a Sub-Page (Priority: P5)

**Goal**: Dataset list and detail pages with proper routing and breadcrumbs.

**Independent Test**: Navigate to /admin/evals/datasets, click a dataset, verify detail page with cases, click back.

### Implementation

- [X] T034 [US5] Create dataset detail page at frontend/src/app/(main)/admin/evals/datasets/[datasetName]/page.tsx — render Breadcrumb (Datasets > dataset name) + DatasetViewer in detail mode using useDatasetDetail hook; back link navigates to /admin/evals/datasets
- [X] T035 [US5] Update datasets list page (T017) to pass navigation callback to DatasetViewer — onSelect navigates to /admin/evals/datasets/[name]

**Checkpoint**: /admin/evals/datasets lists datasets; clicking through shows detail page with cases and breadcrumb.

---

## Phase 8: User Story 6 — Operational Actions on Dashboard (Priority: P6)

**Goal**: Dashboard landing page retains promote, run evals, and rollback tabs.

**Independent Test**: Navigate to /admin/evals, verify promote/run/rollback tabs work identically to before.

### Implementation

- [X] T036 [US6] Verify dashboard page (T014 refactored page) retains TrendsTab summary table, PromoteTab, RunEvalsTab, and RollbackTab as tabs — test each tab renders and functions correctly
- [X] T037 [US6] Add regression banner and summary table from TrendsTab to dashboard as the default view (quick overview), keeping Promote/Run Evals/Rollback as secondary tabs

**Checkpoint**: /admin/evals shows regression status, summary table, and operational tabs — all working as before.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Error states, E2E verification, cleanup.

- [X] T038 [P] Add error state handling to all new pages — show meaningful error card when API calls fail or IDs not found (agent detail 404, run detail 404, dataset detail 404)
- [X] T039 [P] Add empty state handling to Agents page and Trends page — show "No agent versions yet" message with guidance to run evals
- [X] T040 [P] Add loading skeletons to Agents list page, Agent detail page, Trends page (match existing Skeleton patterns)
- [X] T041 Run all backend unit tests: `uv run pytest tests/unit/test_eval_explorer.py -v` — verify all pass including new agent version tests
- [X] T042 Run all frontend unit tests: `cd frontend && npm test` — verify all pass including new component tests
- [X] T043 Rebuild Docker API: `docker compose -f docker/docker-compose.api.yml up -d --build`
- [X] T044 E2E verification with Playwright: navigate to /admin/evals, verify sub-nav renders, click through each sub-page, verify drill-down from experiments → run → traces works
- [X] T045 E2E verification: navigate to /admin/evals/agents, verify page renders (may be empty if no versioned runs yet)
- [X] T046 E2E verification: verify /admin/eval-explorer returns 404 (page deleted)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (models/types must exist for endpoints and hooks)
- **US1 (Phase 3)**: Depends on Phase 2 (needs EvalSubNav, Breadcrumb)
- **US2 (Phase 4)**: Depends on Phase 2 (needs agent endpoints and hooks) + Phase 3 (needs layout)
- **US3 (Phase 5)**: Depends on Phase 3 (needs experiments page and layout)
- **US4 (Phase 6)**: Depends on Phase 2 (needs agent versions data) + Phase 3 (needs layout)
- **US5 (Phase 7)**: Depends on Phase 3 (needs datasets page from T017)
- **US6 (Phase 8)**: Depends on Phase 3 (needs refactored dashboard from T014)
- **Polish (Phase 9)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Foundational only — no other story dependencies. **MVP.**
- **US2 (P2)**: Foundational + US1 layout
- **US3 (P3)**: US1 (experiments page exists)
- **US4 (P4)**: US1 layout + US2 (agent versions data)
- **US5 (P5)**: US1 (datasets page exists)
- **US6 (P6)**: US1 (dashboard refactored)

### Within Each User Story

- Models/types before hooks/endpoints
- Hooks/endpoints before page components
- Page components before integration
- Tests can parallel with implementation (same story, different files)

### Parallel Opportunities

- T004 + T005 (backend tests, different test classes)
- T011 + T012 (frontend tests, different components)
- T015 + T016 + T017 + T018 (placeholder pages, all independent)
- T022 + T023 can parallel if hooks ready (different component files)
- T026 + T027 (frontend tests, different components)
- T038 + T039 + T040 (polish tasks, different concerns)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T005)
2. Complete Phase 2: Foundational (T006–T012)
3. Complete Phase 3: US1 — Unified Navigation (T013–T021)
4. **STOP and VALIDATE**: Sub-nav works, pages route correctly, Explorer link removed
5. This alone delivers the core restructure value

### Incremental Delivery

1. Setup + Foundational → Models, endpoints, nav components ready
2. US1 → Unified section with routing → **MVP**
3. US2 → Agent version browsing (new capability)
4. US3 → Breadcrumb drill-down (navigation polish)
5. US4 → Version-based trends (analytics view)
6. US5 → Dataset sub-page (cleanup)
7. US6 → Dashboard verification (operational parity)
8. Polish → Error states, E2E, cleanup
