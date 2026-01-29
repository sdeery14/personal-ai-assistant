# Tasks: Judge-Centered Evaluation Framework (Feature 002)

**Input**: Design documents from `/specs/002-judge-eval-framework/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: REQUIRED per user request for dataset loading, judge structure, and gating logic.

**Organization**: Tasks grouped by user story (US1, US2, US3) to enable independent implementation.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1=Run Eval, US2=MLflow UI, US3=Regression Gate)

---

## Phase 1: Setup (Infrastructure & Docker Compose)

**Purpose**: Establish MLflow stack (Postgres + MinIO + MLflow) and project structure

- [x] T001 Create `docker/` directory and move docker-compose.yml from root
- [x] T002 Create `docker/docker-compose.yml` with Postgres, MinIO, minio-init, and MLflow services
- [x] T003 Create `docker/.env.example` with MLflow credentials and S3 config template
- [x] T004 [P] Update root `requirements.txt` to add `mlflow==3.8.1`
- [x] T005 [P] Create `eval/__init__.py` with package docstring
- [x] T006 [P] Create `eval/config.py` with Pydantic settings (thresholds, models, env vars)

**Gate**: `docker compose -f docker/docker-compose.yml up -d` starts all services, MLflow UI at http://localhost:5000

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core components that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T007 Create `eval/models.py` with Pydantic models: TestCase, GoldenDataset, EvalResult, EvalRunMetrics
- [x] T008 Create `eval/dataset.py` with `load_dataset(path) -> GoldenDataset` and JSON Schema validation
- [x] T009 Create `eval/assistant.py` with `get_response(prompt) -> str` using `Runner.run_sync()` and `mlflow.openai.autolog()`
- [x] T010 Create `eval/judge.py` with `create_quality_judge()` using `mlflow.genai.judges.make_judge`

**Gate**: Foundation ready — `eval/` package imports without errors

---

## Phase 3: User Story 1 — Run Evaluation Suite (Priority: P1) 🎯 MVP

**Goal**: Developer runs `python -m eval` and sees per-case scores plus overall pass/fail.

**Independent Test**: Run `python -m eval --dry-run` to validate dataset; run full eval with golden cases.

### Tests for User Story 1

- [x] T011 [P] [US1] Create `tests/unit/test_eval_dataset.py` — dataset loading, validation, error cases
- [x] T012 [P] [US1] Create `tests/unit/test_eval_judge.py` — judge output structure (Literal 1-5), not score values

### Implementation for User Story 1

- [x] T013 [US1] Create `eval/golden_dataset.json` with 10 golden test cases (diverse prompts/rubrics)
- [x] T014 [US1] Create `eval/runner.py` with `run_evaluation()` — load dataset, invoke assistant, score with judge
- [x] T015 [US1] Create `eval/__main__.py` with CLI entry point using argparse (--dataset, --model, --verbose, --dry-run, --workers)
- [x] T016 [US1] Add console output: per-case score/pass/fail, summary table with totals

**Checkpoint**: `python -m eval` runs all 10 cases, prints scores, shows summary. Tests pass.

---

## Phase 4: User Story 2 — View Results in MLflow UI (Priority: P2)

**Goal**: Evaluation results logged to MLflow with parameters, metrics, and artifacts.

**Independent Test**: After eval run, verify run appears in MLflow UI with all logged data.

### Implementation for User Story 2

- [x] T017 [US2] Update `eval/runner.py` to use `mlflow.genai.evaluate()` with scorers=[quality_judge]
- [x] T018 [US2] Update `eval/runner.py` to log parameters: assistant_model, judge_model, temperature, dataset_version, thresholds
- [x] T019 [US2] Update `eval/runner.py` to log metrics: pass_rate, average_score, total_cases, passed_cases, failed_cases
- [x] T020 [US2] Update `eval/runner.py` to log artifacts: per-case results JSON, golden dataset snapshot
- [x] T021 [US2] Configure MLflow experiment name: `personal-ai-assistant-eval`

**Checkpoint**: Run eval, open MLflow UI at http://localhost:5000, verify run with params/metrics/artifacts.

---

## Phase 5: User Story 3 — Regression Gating Decision (Priority: P3)

**Goal**: Clear pass/fail based on thresholds with proper exit codes for CI integration.

**Independent Test**: Run with known-good data → exit 0; run with degraded data → exit 1.

### Tests for User Story 3

- [x] T022 [US3] Create `tests/unit/test_eval_gating.py` — threshold logic (pass_rate >= X AND avg_score >= Y)

### Implementation for User Story 3

- [x] T023 [US3] Update `eval/runner.py` to compute overall_passed based on configurable thresholds
- [x] T024 [US3] Update `eval/__main__.py` to exit with code 0 (PASS), 1 (FAIL), or 2 (ERROR)
- [x] T025 [US3] Add final summary output: decision banner (PASS/FAIL), threshold comparison, failure reasons

**Checkpoint**: Passing run → exit 0; failing run → exit 1 with clear reason.

---

## Phase 6: Integration Tests & Validation

**Purpose**: End-to-end harness tests with mocked APIs

- [x] T026 Create `tests/integration/test_eval_runner.py` — full eval flow with mocked OpenAI responses
- [x] T027 Validate error handling: API failures (retry 3x), timeout cases (mark as error), invalid dataset (fail fast)
- [x] T028 Run quickstart.md validation: compose up → eval → view in MLflow UI

**Checkpoint**: All tests pass: `pytest tests/unit/test_eval*.py tests/integration/test_eval*.py`

---

## Phase 7: Polish & Documentation

**Purpose**: Final cleanup and documentation updates

- [x] T029 [P] Verify `specs/002-judge-eval-framework/quickstart.md` is complete and accurate
- [x] T030 [P] Update root `README.md` with Evaluation section (commands, links to quickstart)
- [x] T031 Final validation: full workflow from `docker compose up` through eval to MLflow UI

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) → Phase 2 (Foundational) → Phases 3-5 (User Stories) → Phases 6-7 (Tests/Polish)
                                          ↓
                                [US1, US2, US3 can be sequential or parallel]
```

### User Story Dependencies

| Story | Depends On   | Can Parallelize With |
| ----- | ------------ | -------------------- |
| US1   | Phase 2      | None (do first)      |
| US2   | US1 (runner) | US3                  |
| US3   | US1 (runner) | US2                  |

### Within Each Phase

- Tasks marked [P] can run in parallel
- Models/config before services
- Services before CLI
- Tests can run after implementation

---

## Parallel Opportunities

### Phase 1 Parallel Set

```
T004: Update requirements.txt (mlflow==3.8.1)
T005: Create eval/__init__.py
T006: Create eval/config.py
```

### Phase 3 (US1) Parallel Set

```
T011: tests/unit/test_eval_dataset.py
T012: tests/unit/test_eval_judge.py
```

### Phase 7 Parallel Set

```
T029: Verify quickstart.md
T030: Update README.md
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Docker stack running
2. Complete Phase 2: Core modules ready
3. Complete Phase 3: `python -m eval` works end-to-end
4. **STOP and VALIDATE**: Run eval, verify scores appear
5. This is a functional MVP — judge evaluation works

### Incremental Delivery

1. **MVP (US1)**: Eval runs, scores printed → Core value delivered
2. **Add US2**: Results in MLflow UI → Observability enabled
3. **Add US3**: Exit codes for CI → Automation ready
4. **Polish**: Documentation complete → Feature shippable

---

## Feature Complete Checklist

When all items below are checked, Feature 002 is DONE:

- [ ] `docker compose -f docker/docker-compose.yml up -d` starts MLflow stack
- [ ] `python -m eval` runs full evaluation suite
- [ ] Each case shows: score (1-5), pass/fail, justification
- [ ] Summary shows: total, passed, failed, errors, pass rate, avg score, decision
- [ ] Exit code 0 when pass_rate ≥ 80% AND avg_score ≥ 3.5
- [ ] Exit code 1 when thresholds not met
- [ ] Results visible in MLflow UI at http://localhost:5000
- [ ] All tests pass: `pytest tests/unit/test_eval*.py tests/integration/test_eval*.py`
- [ ] quickstart.md validated end-to-end

---

## Stop Condition

**Feature 002 is COMPLETE when:**

1. All 31 tasks are checked off
2. Feature Complete Checklist passes
3. Branch `002-judge-eval-framework` merged to main
4. LLM-as-a-judge is the operational evaluation mechanism for Feature 001 assistant

**Out of Scope (confirmed not done):**

- ❌ UI dashboards beyond default MLflow UI
- ❌ Human review workflows
- ❌ Production/cloud deployment
- ❌ Memory, tools, voice, or agent extensions
- ❌ Alternative evaluation paths (judge-first only)
