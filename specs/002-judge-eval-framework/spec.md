# Feature Specification: Judge-Centered Evaluation Framework (MLflow)

**Feature Branch**: `002-judge-eval-framework`
**Created**: 2026-01-28
**Status**: Draft
**Input**: User description: "Make LLM-as-a-judge the primary evaluation mechanism for assistant behavior so we can detect regressions across changes."

---

## Overview

This feature establishes a reproducible evaluation framework using LLM-as-a-judge scoring to measure assistant quality. Developers can run a single command to evaluate the Feature 001 assistant against a golden dataset, view scores in MLflow UI, and gate releases based on regression thresholds.

---

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Run Evaluation Suite (Priority: P1) 🎯 MVP

As a developer, I want to run the evaluation suite with a single command so I can see judge-based scores for each test case and an overall pass/fail decision.

**Why this priority**: This is the core capability—without running evaluations, nothing else matters. Enables immediate feedback on assistant quality.

**Independent Test**: Run `python -m eval.run` and verify that each golden dataset case is evaluated, scores are displayed, and an overall pass/fail result is returned.

**Acceptance Scenarios**:

1. **Given** a configured environment with OPENAI_API_KEY, **When** I run `python -m eval.run`, **Then** the suite evaluates all golden dataset cases and prints per-case scores plus overall results.
2. **Given** a golden dataset with 10 cases, **When** the evaluation completes, **Then** I see a score (1-5) and pass/fail for each case, plus aggregate metrics (pass rate, average score).
3. **Given** a case where the assistant response is poor, **When** the judge evaluates it, **Then** the case is marked as "fail" with a score below the threshold.
4. **Given** all cases pass, **When** the suite completes, **Then** the overall result is "PASS" with exit code 0.
5. **Given** the pass rate falls below threshold (e.g., <80%), **When** the suite completes, **Then** the overall result is "FAIL" with exit code 1.

---

### User Story 2 - View Results in MLflow UI (Priority: P2)

As a developer, I want evaluation results logged to MLflow so I can visualize trends, compare runs, and drill into individual case results.

**Why this priority**: MLflow provides the observability layer for tracking quality over time. Without it, evaluations are ephemeral and can't inform regression decisions.

**Independent Test**: After running the evaluation suite, open MLflow UI (`mlflow ui`) and verify the run appears with all logged metrics, parameters, and artifacts.

**Acceptance Scenarios**:

1. **Given** an evaluation run completes, **When** I open MLflow UI, **Then** I see a new run with timestamp, model config, and aggregate metrics.
2. **Given** an MLflow run, **When** I view run details, **Then** I see per-case inputs, outputs, judge scores, and pass/fail status as a logged artifact (CSV or JSON).
3. **Given** multiple evaluation runs, **When** I view the experiment, **Then** I can compare aggregate metrics (pass rate, average score) across runs.
4. **Given** an evaluation run, **When** I view parameters, **Then** I see the model name, temperature, max_tokens, and judge model used.

---

### User Story 3 - Regression Gating Decision (Priority: P3)

As a developer, I want clear regression gating based on judge metrics so I know whether a change is safe to deploy.

**Why this priority**: Regression gating is the decision point—translates scores into actionable pass/fail for CI/CD integration.

**Independent Test**: Run evaluation with a known-good assistant and verify "PASS"; intentionally degrade responses and verify "FAIL".

**Acceptance Scenarios**:

1. **Given** a pass rate threshold of 80% and average score threshold of 3.5, **When** the suite achieves 90% pass rate and 4.2 average, **Then** overall result is "PASS".
2. **Given** the same thresholds, **When** the suite achieves 75% pass rate, **Then** overall result is "FAIL" with reason "pass rate below threshold".
3. **Given** the same thresholds, **When** average score is 3.2, **Then** overall result is "FAIL" with reason "average score below threshold".
4. **Given** a regression gate failure, **When** reviewing the run, **Then** I can identify which specific cases failed and why.

---

### Edge Cases

- What happens when the judge API call fails? → Retry up to 3 times, then mark case as "error" (distinct from "fail") and log the error.
- What happens when the assistant times out? → Mark case as "error" with timeout reason; do not count toward pass rate.
- What happens when a golden dataset case has invalid format? → Fail fast with a clear validation error message indicating the malformed case.
- What happens when MLflow server is unavailable? → Log results to local file as fallback; print warning but do not fail the run.

---

## Requirements _(mandatory)_

### Functional Requirements

#### Dataset & Configuration

- **FR-001**: System MUST load a golden dataset from `eval/golden_dataset.json` containing 5-20 test cases.
- **FR-002**: Each test case MUST include: `id`, `user_prompt`, `rubric` (evaluation criteria), and optional `context` field.
- **FR-003**: System MUST validate dataset schema on load and fail fast with clear error if malformed.
- **FR-004**: Evaluation thresholds MUST be configurable via environment variables (`EVAL_PASS_RATE_THRESHOLD`, `EVAL_SCORE_THRESHOLD`).

#### Assistant Invocation

- **FR-005**: System MUST invoke the Feature 001 assistant (reuse `src/services/chat_service.py`) for each test case.
- **FR-006**: System MUST use deterministic configuration per run (fixed model, temperature=0, max_tokens from config).
- **FR-007**: System MUST NOT duplicate assistant implementation—import and use existing ChatService.

#### Judge Scoring

- **FR-008**: System MUST use LLM-as-a-judge to evaluate each assistant response against the case rubric.
- **FR-009**: Judge MUST return a score (1-5 scale) and a brief justification for each case.
- **FR-010**: Judge scoring MUST use a structured prompt template that includes: user prompt, assistant response, and rubric.
- **FR-011**: A case MUST be marked "pass" if score >= 4, otherwise "fail".
- **FR-012**: Judge model MUST be configurable via `EVAL_JUDGE_MODEL` environment variable (default: same as assistant model).

#### MLflow Logging

- **FR-013**: System MUST log each evaluation run to MLflow with a unique run ID.
- **FR-014**: System MUST log run parameters: assistant model, judge model, temperature, max_tokens, dataset version.
- **FR-015**: System MUST log aggregate metrics: pass_rate, average_score, total_cases, passed_cases, failed_cases, error_cases.
- **FR-016**: System MUST log per-case results as an artifact (JSON file) including: case_id, user_prompt, response, score, pass/fail, justification.
- **FR-017**: System MUST create/use an MLflow experiment named "personal-ai-assistant-eval".

#### Regression Gating

- **FR-018**: System MUST compute overall pass/fail based on: pass_rate >= threshold AND average_score >= threshold.
- **FR-019**: System MUST exit with code 0 on overall PASS, code 1 on overall FAIL.
- **FR-020**: System MUST print a summary showing: total cases, passed, failed, errors, pass rate, average score, and overall decision.

#### Error Handling

- **FR-021**: System MUST retry judge API calls up to 3 times on transient failures.
- **FR-022**: System MUST mark cases as "error" (not "fail") when assistant or judge encounters unrecoverable errors.
- **FR-023**: Error cases MUST NOT count toward pass rate calculation (excluded from denominator).

### Key Entities

- **TestCase**: A single evaluation case containing id, user_prompt, rubric, and optional context.
- **EvalResult**: The result of evaluating one test case: case_id, user_prompt, assistant_response, score, pass/fail, justification, duration_ms, error (if any).
- **EvalRun**: Aggregate results for a complete evaluation run: run_id, timestamp, parameters, metrics, list of EvalResults.

---

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Developers can run the full evaluation suite in under 5 minutes for a 20-case dataset.
- **SC-002**: 100% of evaluation runs are logged to MLflow with complete metadata and artifacts.
- **SC-003**: Regression gate correctly identifies regressions with 95%+ accuracy (fails when quality degrades, passes when quality is maintained).
- **SC-004**: Evaluation results are reproducible—same dataset + same config = same scores (within judge variance tolerance).
- **SC-005**: MLflow UI displays all required information (parameters, metrics, artifacts) without additional configuration.

---

## Assumptions

- OpenAI API is available and rate limits are sufficient for evaluation runs (approximately 40 API calls per 20-case run: 20 assistant + 20 judge).
- MLflow is installed locally and can run with default SQLite backend for local development.
- Temperature=0 provides sufficient reproducibility for assistant responses.
- A score of 4+ on a 1-5 scale is a reasonable pass threshold (can be tuned via configuration).
- The judge model is capable of consistent, fair evaluation when given a clear rubric.

---

## Out of Scope

- Automated CI/CD integration (this feature provides the building blocks; CI integration is a future feature).
- Multi-model comparison in a single run (each run evaluates one assistant configuration).
- Custom judge prompts per case (all cases use the same judge template with case-specific rubrics).
- Conversation memory or multi-turn evaluation (single-turn only, matching Feature 001 scope).
- Remote MLflow server setup (local MLflow only for this feature).

---

## Dependencies

- **Feature 001**: Core Streaming Chat API (provides ChatService for assistant invocation).
- **MLflow**: Experiment tracking and visualization.
- **OpenAI API**: For both assistant (via Agents SDK) and judge (direct API or Agents SDK).
