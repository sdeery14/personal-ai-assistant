# Tasks: Eval Dashboard & Regression Pipeline

**Input**: Design documents from `/specs/013-eval-pipeline/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the eval pipeline package structure and add dependencies

- [X] T001 Add `click` dependency to pyproject.toml via `uv add click`
- [X] T002 Create eval/pipeline/ package with __init__.py in eval/pipeline/__init__.py
- [X] T003 [P] Create pipeline configuration with eval subsets (core vs full) and per-eval-type thresholds in eval/pipeline_config.py
- [X] T004 [P] Create tests/unit/test_pipeline/ package with __init__.py in tests/unit/test_pipeline/__init__.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data models and CLI framework that ALL user stories depend on

- [X] T005 Implement pipeline data models (TrendPoint, TrendSummary, PromptChange, RegressionReport, PromotionResult, PromotionEvalCheck, AuditRecord) as dataclasses in eval/pipeline/models.py
- [X] T006 Implement Click CLI group with `__main__.py` entry point in eval/pipeline/__main__.py and command group scaffold in eval/pipeline/cli.py. The CLI group should define the `pipeline` group with placeholder commands (trend, check, promote, rollback, run-evals) that will be filled in by each user story phase.
- [X] T007 [P] Write unit tests for all pipeline data models (construction, field validation, verdict logic for RegressionReport) in tests/unit/test_pipeline/test_models.py

**Checkpoint**: Foundation ready — pipeline package exists, models defined, CLI scaffold in place

---

## Phase 3: User Story 1 — View Eval Trends Over Time (Priority: P1)

**Goal**: Developers can view pass rate trends over time for each eval type, annotated with prompt version changes

**Independent Test**: Run `uv run python -m eval.pipeline trend` and verify it displays pass rate history per eval type with prompt version annotations. Verify empty state shows a clear "no data" message.

### Implementation for User Story 1

- [X] T008 [US1] Implement `get_eval_experiments()` function in eval/pipeline/aggregator.py that discovers all eval experiments by prefix-matching `mlflow.search_experiments()` against the configured base experiment name. Return a list of (experiment_name, eval_type) tuples.
- [X] T009 [US1] Implement `get_trend_points()` function in eval/pipeline/aggregator.py that queries `mlflow.search_runs()` for a given experiment, extracts metrics (pass_rate, average_score, total_cases, error_cases) and params (prompt.*), and returns a list of TrendPoint objects sorted chronologically. Compute eval_status from existing metrics: error_cases==0 → complete, error_cases>0 → partial, MLflow status FAILED → error.
- [X] T010 [US1] Implement `build_trend_summary()` function in eval/pipeline/aggregator.py that takes a list of TrendPoints, computes trend_direction (improving/stable/degrading based on last 3 runs), and detects prompt version changes between consecutive runs. Return a TrendSummary.
- [X] T011 [US1] Implement `trend` Click command in eval/pipeline/cli.py with --eval-type, --limit (default 10), and --format (table/json) options. Table format: header per eval type showing latest pass rate and trend direction, rows with run_id, date, pass rate, score, and prompts changed. JSON format: serialize TrendSummary list. Handle empty state with "No eval runs found" message.
- [X] T012 [P] [US1] Write unit tests for aggregator functions (get_eval_experiments, get_trend_points, build_trend_summary) with mocked MLflow search_runs/search_experiments responses in tests/unit/test_pipeline/test_aggregator.py. Test cases: multiple runs with changing pass rates, prompt version changes detected, empty experiment, partial runs filtered from baselines.
- [X] T013 [P] [US1] Write unit tests for trend CLI command using Click's CliRunner in tests/unit/test_pipeline/test_cli.py. Test cases: table output format, json output format, --eval-type filter, empty state message.

**Checkpoint**: `uv run python -m eval.pipeline trend` displays eval trends with prompt version annotations

---

## Phase 4: User Story 2 — Detect and Diagnose Regressions (Priority: P1)

**Goal**: After an eval run, the system compares against the previous baseline and flags REGRESSION/WARNING/IMPROVED/PASS verdicts per eval type

**Independent Test**: Run `uv run python -m eval.pipeline check` and verify it compares the latest complete run against the previous baseline for each eval type. Verify REGRESSION when pass_rate crosses below threshold, WARNING when delta >= -10pp but above threshold, IMPROVED when delta > 0, PASS otherwise.

### Implementation for User Story 2

- [X] T014 [US2] Implement `get_baseline_run()` function in eval/pipeline/regression.py that finds the most recent complete run (error_cases == 0, MLflow status FINISHED) before a given run for an experiment. Uses aggregator.get_trend_points() with completeness filtering.
- [X] T015 [US2] Implement `compare_runs()` function in eval/pipeline/regression.py that takes a baseline TrendPoint and current TrendPoint, computes delta_pp, applies verdict logic (REGRESSION if current < threshold, WARNING if delta <= -10 and current >= threshold, IMPROVED if delta > 0, PASS otherwise), detects changed prompts, and returns a RegressionReport.
- [X] T016 [US2] Implement `check_all_regressions()` function in eval/pipeline/regression.py that iterates over all eval experiments, finds the latest run and its baseline for each, and returns a list of RegressionReport objects. Skip eval types with fewer than 2 complete runs.
- [X] T017 [US2] Implement `check` Click command in eval/pipeline/cli.py with --eval-type, --run-id, and --format (table/json) options. Table format: columns for eval type, baseline, current, delta, threshold, verdict. Show changed prompts section. Summary line with counts per verdict. Exit code 0 if no regressions, 1 if any REGRESSION found.
- [X] T018 [P] [US2] Write unit tests for regression functions (get_baseline_run, compare_runs, check_all_regressions) in tests/unit/test_pipeline/test_regression.py. Test cases: REGRESSION verdict, WARNING verdict, IMPROVED verdict, PASS verdict, no baseline available, partial runs excluded from baseline.
- [X] T019 [P] [US2] Write unit tests for check CLI command using Click's CliRunner in tests/unit/test_pipeline/test_cli.py (append to existing file). Test cases: regression detected exit code 1, no regression exit code 0, changed prompts displayed.

**Checkpoint**: `uv run python -m eval.pipeline check` detects regressions and generates reports

---

## Phase 5: User Story 3 — Gate Prompt Promotion on Eval Results (Priority: P2)

**Goal**: Promotion of a prompt alias is blocked unless all eval types pass their minimum thresholds. Audit records are logged as MLflow tags.

**Independent Test**: Run `uv run python -m eval.pipeline promote orchestrator-base` and verify it checks all eval types, blocks if any fail, promotes and logs audit tags if all pass.

### Implementation for User Story 3

- [X] T020 [US3] Implement `check_promotion_gate()` function in eval/pipeline/promotion.py that loads the latest complete run for each eval type, checks pass_rate against per-eval-type thresholds from pipeline_config, and returns a PromotionResult with per-eval PromotionEvalCheck entries. Collects justifying run IDs.
- [X] T021 [US3] Implement `execute_promotion()` function in eval/pipeline/promotion.py that calls prompt_service.set_alias() to promote the alias, then logs audit tags (audit.action, audit.prompt_name, audit.from_version, audit.to_version, audit.alias, audit.timestamp, audit.actor) on each justifying MLflow run using MlflowClient().set_tag().
- [X] T022 [US3] Implement `promote` Click command in eval/pipeline/cli.py with PROMPT_NAME argument and --from-alias, --to-alias, --version, --force, --actor options. Display gate check table, execute promotion if allowed (or --force), show success/blocked message with audit details. Exit code 0 if promoted, 1 if blocked.
- [X] T023 [P] [US3] Write unit tests for promotion functions (check_promotion_gate, execute_promotion) with mocked MLflow and prompt_service in tests/unit/test_pipeline/test_promotion.py. Test cases: all pass → allowed, one fail → blocked, force flag bypasses gate, audit tags written correctly.
- [X] T024 [P] [US3] Write unit tests for promote CLI command using Click's CliRunner in tests/unit/test_pipeline/test_cli.py (append to existing file). Test cases: successful promotion output, blocked promotion output, force flag warning.

**Checkpoint**: `uv run python -m eval.pipeline promote` gates promotion on eval thresholds and logs audit tags

---

## Phase 6: User Story 4 — Automated Eval on Prompt Registration (Priority: P2)

**Goal**: When running evals, support configurable subsets (core vs full) with progress tracking and automatic regression check

**Independent Test**: Run `uv run python -m eval.pipeline run-evals --suite core` and verify only core eval types run. Run with `--suite full` and verify all 19 types run. Verify regression check runs after completion.

### Implementation for User Story 4

- [X] T025 [US4] Implement `run_eval_suite()` function in eval/pipeline/trigger.py that takes a suite name (core/full), resolves dataset paths from pipeline_config, runs each eval sequentially via subprocess (`uv run python -m eval --dataset <path>`), captures exit codes, and returns per-eval results with progress tracking.
- [X] T026 [US4] Implement `run-evals` Click command in eval/pipeline/cli.py with --suite (core/full, default core), --verbose, and --check (default True) options. Display progress as each eval completes ([N/M] eval_type ... PASS/FAIL). If --check is enabled, run regression check after all evals complete. Exit code 0 if all pass and no regressions, 1 otherwise.
- [X] T027 [P] [US4] Write unit tests for trigger functions (run_eval_suite) with mocked subprocess calls in tests/unit/test_pipeline/test_trigger.py. Test cases: core subset runs 5 evals, full subset runs 19, failed eval captured in results, progress tracking works.
- [X] T028 [P] [US4] Write unit tests for run-evals CLI command using Click's CliRunner in tests/unit/test_pipeline/test_cli.py (append to existing file). Test cases: core suite output, full suite output, regression check after run.

**Checkpoint**: `uv run python -m eval.pipeline run-evals` runs configurable eval subsets with progress and regression check

---

## Phase 7: User Story 5 — Rollback Prompt on Regression (Priority: P3)

**Goal**: Single-command rollback of a prompt alias to its previous version with audit logging

**Independent Test**: Run `uv run python -m eval.pipeline rollback orchestrator-base --reason "test"` and verify the alias is reverted, audit tags are logged, and the rollback is reported.

### Implementation for User Story 5

- [X] T029 [US5] Implement `find_previous_version()` function in eval/pipeline/rollback.py that queries MLflow eval runs for the most recent baseline run before the current alias version, extracts the prompt version from params.prompt.<name>, and returns the previous version number. Return None if no previous version exists.
- [X] T030 [US5] Implement `execute_rollback()` function in eval/pipeline/rollback.py that calls prompt_service.set_alias() to revert the alias, logs audit tags (audit.action=rollback, audit.reason, etc.) on the most recent eval run using MlflowClient().set_tag(), and returns the AuditRecord.
- [X] T031 [US5] Implement `rollback` Click command in eval/pipeline/cli.py with PROMPT_NAME argument and --alias, --reason (required), --actor options. Display current version and rollback target, execute rollback, show success message with audit details. Exit code 0 if rolled back, 1 if no previous version.
- [X] T032 [P] [US5] Write unit tests for rollback functions (find_previous_version, execute_rollback) with mocked MLflow and prompt_service in tests/unit/test_pipeline/test_rollback.py. Test cases: successful rollback, no previous version returns None, audit tags written correctly.
- [X] T033 [P] [US5] Write unit tests for rollback CLI command using Click's CliRunner in tests/unit/test_pipeline/test_cli.py (append to existing file). Test cases: successful rollback output, no previous version error.

**Checkpoint**: `uv run python -m eval.pipeline rollback` reverts alias and logs audit

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Integration, edge cases, and final validation

- [X] T034 Wire pipeline CLI into eval/__main__.py by adding a `--pipeline` flag or detecting `pipeline` subcommand to dispatch to eval.pipeline.cli when invoked as `uv run python -m eval.pipeline`
- [X] T035 Handle edge case: new eval type with no historical data — ensure trend shows "starting from first run" and promotion gate skips eval types with zero runs (log a warning)
- [X] T036 Handle edge case: multiple prompt versions changed simultaneously — ensure regression report lists all changed prompts in the changed_prompts field
- [X] T037 Run all unit tests via `uv run pytest tests/unit/test_pipeline/ -v` and verify all pass
- [X] T038 Run quickstart.md validation: execute each scenario end-to-end against Docker MLflow stack and verify expected outputs

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational (Phase 2)
- **US2 (Phase 4)**: Depends on US1 (Phase 3) — reuses aggregator.get_trend_points() for baseline finding
- **US3 (Phase 5)**: Depends on Foundational (Phase 2) — can run in parallel with US1/US2 but benefits from aggregator functions
- **US4 (Phase 6)**: Depends on US2 (Phase 4) — uses regression check after eval completion
- **US5 (Phase 7)**: Depends on US3 (Phase 5) — reuses audit tag logging pattern from promotion
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Foundational only — first story, establishes aggregator module
- **US2 (P1)**: US1 — reuses aggregator for trend points and baseline finding
- **US3 (P2)**: Foundational — can proceed independently, but benefits from aggregator (for latest run lookup)
- **US4 (P2)**: US2 — uses regression check module after eval runs complete
- **US5 (P3)**: US3 — reuses audit tag logging pattern; also uses aggregator for version history

### Within Each User Story

- Service/logic modules before CLI commands
- CLI commands before tests (tests mock the service layer)
- Tests marked [P] can run in parallel within a story

### Parallel Opportunities

- T003 and T004 can run in parallel (different files, no dependencies)
- T012 and T013 can run in parallel (different test files)
- T018 and T019 can run in parallel (different test files)
- T023 and T024 can run in parallel (different test files)
- T027 and T028 can run in parallel (different test files)
- T032 and T033 can run in parallel (different test files)

---

## Parallel Example: User Story 1

```bash
# After T010 (build_trend_summary) is complete:
# Launch tests in parallel:
Task T012: "Unit tests for aggregator in tests/unit/test_pipeline/test_aggregator.py"
Task T013: "Unit tests for trend CLI in tests/unit/test_pipeline/test_cli.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup (T001–T004)
2. Complete Phase 2: Foundational (T005–T007)
3. Complete Phase 3: US1 — View Trends (T008–T013)
4. Complete Phase 4: US2 — Detect Regressions (T014–T019)
5. **STOP and VALIDATE**: `trend` and `check` commands work end-to-end
6. This provides the core "observe and react" loop

### Incremental Delivery

1. Setup + Foundational → Package exists, models and CLI scaffold ready
2. Add US1 (Trends) → Test independently → Developers can view quality trends
3. Add US2 (Regressions) → Test independently → Regressions auto-detected
4. Add US3 (Promotion) → Test independently → Promotion gated on eval results
5. Add US4 (Run Evals) → Test independently → Configurable eval subsets
6. Add US5 (Rollback) → Test independently → Single-command rollback
7. Polish → Edge cases, integration, final validation
