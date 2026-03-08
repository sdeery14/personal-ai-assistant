# Tasks: Eval Explorer UI

**Input**: Design documents from `/specs/015-eval-explorer-ui/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/api.md

**Tests**: Included — backend unit tests and frontend component tests.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Backend API foundation and frontend scaffolding shared by all user stories

- [X] T001 [P] Create Pydantic response models (ExperimentSummary, RunSummary, TraceDetail, AssessmentDetail, SessionGroup, QualityTrendPoint, DatasetSummary, DatasetCase) in `src/models/eval_explorer.py`
- [X] T002 [P] Create TypeScript interfaces matching API response shapes in `frontend/src/types/eval-explorer.ts`
- [X] T003 [P] Create FastAPI router skeleton with `require_admin` dependency on all endpoints, mount in `src/main.py` at `/admin/evals/explorer` in `src/api/eval_explorer.py`
- [X] T004 [P] Create data-fetching hooks skeleton (useExperiments, useExperimentRuns, useRunTraces, useUniversalQualityTrend, useDatasets) in `frontend/src/hooks/useEvalExplorer.ts`
- [X] T005 Create eval explorer page with admin access guard and basic layout in `frontend/src/app/(main)/admin/eval-explorer/page.tsx`
- [X] T006 [P] Add "Eval Explorer" navigation link to admin section in `frontend/src/components/layout/Header.tsx` and `frontend/src/components/layout/Sidebar.tsx`

**Checkpoint**: Router mounted, page accessible at `/admin/eval-explorer`, navigation links visible for admin users

---

## Phase 2: User Story 1 — Universal Quality Trend (Priority: P1) MVP

**Goal**: Cross-experiment chart showing agent quality over time using the universal 1-5 judge score across all eval types

**Independent Test**: Navigate to `/admin/eval-explorer`, verify multi-line chart renders with one line per eval type on a 1-5 scale

### Tests for User Story 1

- [X] T007 [P] [US1] Backend unit test for `GET /admin/evals/explorer/trends/quality` endpoint — mock `mlflow.search_experiments` and `mlflow.search_runs`, verify response shape and score extraction in `tests/unit/test_eval_explorer.py`
- [X] T008 [P] [US1] Frontend unit test for UniversalQualityChart component — mock hook data, verify chart renders with multiple eval type lines and tooltip content in `frontend/tests/components/eval-explorer/UniversalQualityChart.test.tsx`

### Implementation for User Story 1

- [X] T009 [US1] Implement `GET /admin/evals/explorer/trends/quality` endpoint — iterate all experiments, extract universal quality metric per run, return `QualityTrendResponse` in `src/api/eval_explorer.py`
- [X] T010 [US1] Implement `useUniversalQualityTrend` hook with session-aware API call in `frontend/src/hooks/useEvalExplorer.ts`
- [X] T011 [US1] Build `UniversalQualityChart` component — multi-line Recharts LineChart with one line per eval type, Y-axis 1-5 scale, hover tooltip showing eval type + date + score + run ID in `frontend/src/components/eval-explorer/UniversalQualityChart.tsx`
- [X] T012 [US1] Integrate chart into explorer page as always-visible top section in `frontend/src/app/(main)/admin/eval-explorer/page.tsx`

**Checkpoint**: Universal quality trend chart visible with real data from MLflow. Developer can see agent health across all eval types at a glance.

---

## Phase 3: User Story 2 — Experiment Browser (Priority: P1)

**Goal**: List all eval experiments with metadata (eval type, run count, last run date, latest pass rate, latest quality score). Clicking navigates to runs.

**Independent Test**: Load explorer page, verify all 18 experiments appear with correct metadata, click one to drill down

### Tests for User Story 2

- [X] T013 [P] [US2] Backend unit test for `GET /admin/evals/explorer/experiments` endpoint — mock MLflow client, verify all experiments returned with aggregated metadata in `tests/unit/test_eval_explorer.py`
- [X] T014 [P] [US2] Frontend unit test for ExperimentBrowser component — mock hook data, verify table renders experiments with metrics and click handler fires in `frontend/tests/components/eval-explorer/ExperimentBrowser.test.tsx`

### Implementation for User Story 2

- [X] T015 [US2] Implement `GET /admin/evals/explorer/experiments` endpoint — query `mlflow.search_experiments`, aggregate run counts and latest metrics per experiment in `src/api/eval_explorer.py`
- [X] T016 [US2] Implement `useExperiments` hook with session-aware API call in `frontend/src/hooks/useEvalExplorer.ts`
- [X] T017 [US2] Build `ExperimentBrowser` component — sortable table with eval type, run count, last run date, pass rate, quality score columns; click handler for drill-down; loading skeleton and empty state in `frontend/src/components/eval-explorer/ExperimentBrowser.tsx`
- [X] T018 [US2] Integrate ExperimentBrowser as default view in explorer page, wire click handler to set selected experiment state in `frontend/src/app/(main)/admin/eval-explorer/page.tsx`

**Checkpoint**: Experiment list visible with real data. Clicking an experiment sets state for drill-down (run browser not yet built).

---

## Phase 4: User Story 3 — Run Browser (Priority: P2)

**Goal**: Within a selected experiment, display all runs with sortable params/metrics. Clicking a run drills down to traces.

**Independent Test**: Select an experiment, verify runs appear with all params/metrics, sort by pass rate, click a run

### Tests for User Story 3

- [X] T019 [P] [US3] Backend unit test for `GET /admin/evals/explorer/experiments/{id}/runs` endpoint — mock MLflow search_runs, verify params/metrics extraction and run ordering in `tests/unit/test_eval_explorer.py`
- [X] T020 [P] [US3] Frontend unit test for RunBrowser component — mock hook data, verify sortable table renders with run metadata and click handler in `frontend/tests/components/eval-explorer/RunBrowser.test.tsx`

### Implementation for User Story 3

- [X] T021 [US3] Implement `GET /admin/evals/explorer/experiments/{id}/runs` endpoint — query `mlflow.search_runs`, extract params/metrics/trace counts in `src/api/eval_explorer.py`
- [X] T022 [US3] Implement `useExperimentRuns` hook accepting experiment ID and eval type in `frontend/src/hooks/useEvalExplorer.ts`
- [X] T023 [US3] Build `RunBrowser` component — sortable table with timestamp, model, pass rate, avg score, total cases, errors, git SHA, prompt versions columns; client-side pagination (25 per page); click handler for drill-down in `frontend/src/components/eval-explorer/RunBrowser.tsx`
- [X] T024 [US3] Wire RunBrowser into explorer page — show when experiment selected, breadcrumb navigation back to experiment list in `frontend/src/app/(main)/admin/eval-explorer/page.tsx`

**Checkpoint**: Full experiment → run drill-down works. Runs display with all params and metrics, sortable and paginated.

---

## Phase 5: User Story 4 — Trace & Assessment Viewer (Priority: P2)

**Goal**: Within a selected run, display all traces with complete assessment data from all scorers (not just primary).

**Independent Test**: Click a run, verify all traces appear with all assessments showing name, score, pass/fail, and full rationale

### Tests for User Story 4

- [X] T025 [P] [US4] Backend unit test for `GET /admin/evals/explorer/runs/{id}/traces` endpoint — mock `mlflow.search_traces`, verify assessment normalization (word labels, numerics, booleans) and all scorers included in `tests/unit/test_eval_explorer.py`
- [X] T026 [P] [US4] Frontend unit test for TraceViewer component — mock hook data with multi-scorer assessments, verify all assessments render with rationale in `frontend/tests/components/eval-explorer/TraceViewer.test.tsx`

### Implementation for User Story 4

- [X] T027 [US4] Implement `GET /admin/evals/explorer/runs/{id}/traces` endpoint — query `mlflow.search_traces`, normalize all assessments (reuse aggregator logic), return TraceDetail list in `src/api/eval_explorer.py`
- [X] T028 [US4] Implement `useRunTraces` hook accepting run ID and eval type in `frontend/src/hooks/useEvalExplorer.ts`
- [X] T029 [US4] Build `TraceViewer` component — expandable trace rows showing case ID, prompt preview, score badge; expanded view shows user prompt, assistant response, all assessments with name/value/pass-fail/rationale; client-side pagination in `frontend/src/components/eval-explorer/TraceViewer.tsx`
- [X] T030 [US4] Wire TraceViewer into explorer page — show when run selected, breadcrumb navigation back to runs in `frontend/src/app/(main)/admin/eval-explorer/page.tsx`

**Checkpoint**: Full experiment → run → trace drill-down works. All assessments visible with rationales. SC-002 met (3 clicks from experiment to trace assessments).

---

## Phase 6: User Story 5 — Run Comparison (Priority: P3)

**Goal**: Select two runs and see side-by-side param/metric deltas and per-case result diffs.

**Independent Test**: Select two runs via checkboxes, click Compare, verify deltas are highlighted and per-case diffs show improved/regressed/unchanged

### Tests for User Story 5

- [X] T031 [P] [US5] Frontend unit test for RunComparison component — mock two run details with overlapping and unique cases, verify delta highlighting and missing case indicators in `frontend/tests/components/eval-explorer/RunComparison.test.tsx`

### Implementation for User Story 5

- [X] T032 [US5] Add checkbox selection to RunBrowser for multi-select (max 2) and "Compare" button in `frontend/src/components/eval-explorer/RunBrowser.tsx`
- [X] T033 [US5] Build `RunComparison` component — side-by-side layout with param diff (changed values highlighted), metric diff (green for improvement, red for regression), per-case score diff matched by case_id in `frontend/src/components/eval-explorer/RunComparison.tsx`
- [X] T034 [US5] Wire RunComparison into explorer page — show comparison view when two runs selected and Compare clicked in `frontend/src/app/(main)/admin/eval-explorer/page.tsx`

**Checkpoint**: Run comparison fully functional. Param/metric deltas and per-case diffs visible.

---

## Phase 7: User Story 6 — Session Viewer (Priority: P3)

**Goal**: For multi-turn eval types, group traces by session and display conversation timelines with session-level assessments.

**Independent Test**: View a multi-turn eval type run, verify traces grouped by session with chronological conversation thread

### Tests for User Story 6

- [X] T035 [P] [US6] Backend unit test for session grouping in traces endpoint — mock traces with session IDs, verify `sessions` array returned with correct grouping and chronological ordering in `tests/unit/test_eval_explorer.py`
- [X] T036 [P] [US6] Frontend unit test for SessionViewer component — mock session data with multi-turn conversation, verify conversation timeline and session-level assessment rendering in `frontend/tests/components/eval-explorer/SessionViewer.test.tsx`

### Implementation for User Story 6

- [X] T037 [US6] Add session grouping logic to `GET /admin/evals/explorer/runs/{id}/traces` — group traces by `mlflow.trace.session` metadata for session eval types, return in `sessions` array in `src/api/eval_explorer.py`
- [X] T038 [US6] Build `SessionViewer` component — session header with session ID, conversation timeline showing user/assistant turns in order, session-level assessment display in `frontend/src/components/eval-explorer/SessionViewer.tsx`
- [X] T039 [US6] Integrate SessionViewer into TraceViewer — detect session eval types and render SessionViewer for grouped traces instead of flat trace list in `frontend/src/components/eval-explorer/TraceViewer.tsx`

**Checkpoint**: Multi-turn evals display as conversation timelines grouped by session.

---

## Phase 8: User Story 7 — Dataset Viewer (Priority: P3)

**Goal**: Browse golden dataset files with metadata and individual test cases.

**Independent Test**: Navigate to dataset viewer, verify all 18 datasets appear with case counts, expand one to see cases with prompts/rubrics/tags

### Tests for User Story 7

- [X] T040 [P] [US7] Backend unit test for `GET /admin/evals/explorer/datasets` and `GET /admin/evals/explorer/datasets/{name}` — mock filesystem reads, verify dataset parsing and error handling for malformed JSON in `tests/unit/test_eval_explorer.py`
- [X] T041 [P] [US7] Frontend unit test for DatasetViewer component — mock hook data with datasets and cases, verify expandable list renders with special fields (expected_behavior, tags) in `frontend/tests/components/eval-explorer/DatasetViewer.test.tsx`

### Implementation for User Story 7

- [X] T042 [US7] Implement `GET /admin/evals/explorer/datasets` endpoint — scan `eval/*_golden_dataset.json` files, parse JSON, return metadata with optional cases in `src/api/eval_explorer.py`
- [X] T043 [US7] Implement `GET /admin/evals/explorer/datasets/{name}` endpoint — load single dataset with all cases in `src/api/eval_explorer.py`
- [X] T044 [US7] Implement `useDatasets` and `useDatasetDetail` hooks in `frontend/src/hooks/useEvalExplorer.ts`
- [X] T045 [US7] Build `DatasetViewer` component — dataset list with name, version, description, case count; expandable case detail showing prompt, rubric, tags, and eval-type-specific fields (expected_behavior, severity, attack_type) in `frontend/src/components/eval-explorer/DatasetViewer.tsx`
- [X] T046 [US7] Add DatasetViewer as a section/tab in the explorer page in `frontend/src/app/(main)/admin/eval-explorer/page.tsx`

**Checkpoint**: All datasets browsable with full case details. Dataset viewer accessible from explorer page.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, error handling, and validation

- [X] T047 Verify all API endpoints return proper error responses (404 for missing experiments/runs/datasets, 403 for non-admin) in `src/api/eval_explorer.py`
- [X] T048 Add structured logging to all explorer API endpoints (consistent with Feature 014 pattern) in `src/api/eval_explorer.py`
- [X] T049 Rebuild Docker API service and verify all endpoints work end-to-end via `docker compose -f docker/docker-compose.api.yml up -d --build`
- [X] T050 Verify full drill-down flow with Playwright MCP: experiment list → click experiment → run list → click run → trace assessments (SC-002: ≤ 3 clicks)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **US1 Universal Quality Trend (Phase 2)**: Depends on T001, T002, T003, T004, T005
- **US2 Experiment Browser (Phase 3)**: Depends on T001, T002, T003, T004, T005
- **US3 Run Browser (Phase 4)**: Depends on Phase 3 (needs experiment selection state)
- **US4 Trace Viewer (Phase 5)**: Depends on Phase 4 (needs run selection state)
- **US5 Run Comparison (Phase 6)**: Depends on Phase 4 (extends RunBrowser)
- **US6 Session Viewer (Phase 7)**: Depends on Phase 5 (extends TraceViewer)
- **US7 Dataset Viewer (Phase 8)**: Depends on Phase 1 only (independent of other stories)
- **Polish (Phase 9)**: Depends on all desired stories being complete

### User Story Dependencies

- **US1 (P1)**: Independent after Setup — chart only needs trends/quality endpoint
- **US2 (P1)**: Independent after Setup — experiment list only needs experiments endpoint
- **US3 (P2)**: Depends on US2 (experiment selection state on page)
- **US4 (P2)**: Depends on US3 (run selection state on page)
- **US5 (P3)**: Depends on US3 (extends RunBrowser with checkboxes)
- **US6 (P3)**: Depends on US4 (extends TraceViewer with session grouping)
- **US7 (P3)**: Independent after Setup — dataset viewer is standalone

### Parallel Opportunities

Within each phase, tasks marked [P] can run in parallel:
- Phase 1: T001, T002, T003, T004, T006 all parallel
- Phase 2: T007, T008 parallel; T009, T010 sequential
- Phase 3: T013, T014 parallel
- Phase 4: T019, T020 parallel
- Phase 5: T025, T026 parallel
- Phase 6: T031 standalone
- Phase 7: T035, T036 parallel; T040, T041 parallel

US1 and US2 can proceed in parallel after Setup.
US7 (Dataset Viewer) can proceed in parallel with US3-US6.

---

## Parallel Example: Setup Phase

```bash
# All of these can run simultaneously:
Task T001: "Create Pydantic response models in src/models/eval_explorer.py"
Task T002: "Create TypeScript interfaces in frontend/src/types/eval-explorer.ts"
Task T003: "Create FastAPI router skeleton in src/api/eval_explorer.py"
Task T004: "Create data-fetching hooks skeleton in frontend/src/hooks/useEvalExplorer.ts"
Task T006: "Add navigation links in Header.tsx and Sidebar.tsx"
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Complete Phase 1: Setup (T001-T006)
2. Complete Phase 2: US1 Universal Quality Trend (T007-T012)
3. Complete Phase 3: US2 Experiment Browser (T013-T018)
4. **STOP and VALIDATE**: Chart + experiment list working, admin can see agent health
5. Deploy/demo — this alone replaces the need for MLflow UI for quality monitoring

### Incremental Delivery

1. Setup → Foundation ready
2. US1 + US2 → Quality chart + experiment list (MVP!)
3. US3 + US4 → Run + trace drill-down (full browsing)
4. US5 + US6 + US7 → Comparison + sessions + datasets (complete explorer)
5. Polish → Error handling, logging, E2E validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- All backend endpoints are GET-only (read-only, no mutations)
- Assessment normalization reuses existing logic from `eval/pipeline/aggregator.py`
- Client-side pagination default: 25 items per page
- Session eval types defined in `eval/pipeline_config.py::EVAL_SESSION_TYPES`
- Commit after each task or logical group
