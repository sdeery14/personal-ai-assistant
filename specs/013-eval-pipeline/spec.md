# Feature Specification: Eval Dashboard & Regression Pipeline

**Feature Branch**: `013-eval-pipeline`
**Created**: 2026-02-24
**Status**: Draft
**Input**: User description: "Feature 013 – Eval Dashboard & Regression Pipeline from the vision.md"

## Clarifications

### Session 2026-02-24

- Q: Should any decrease in a metric trigger a regression warning, or only drops that cross below the pass rate threshold? → A: Only flag when a metric crosses below its threshold (REGRESSION), plus warn on drops >= 10 percentage points that remain above threshold (WARNING).
- Q: Should automated eval runs execute all 19 eval types, or a configurable subset? → A: Run a configurable subset by default (core evals), with the full suite available on demand before promotion.
- Q: Where should promotion and rollback audit records be persisted? → A: As MLflow run tags on the eval runs that justified the promotion, co-locating audit data with eval results.

## User Scenarios & Testing

### User Story 1 - View Eval Trends Over Time (Priority: P1)

A developer wants to understand whether the assistant is getting better or worse across releases. They run a CLI command that shows eval pass rates over time for each eval type, annotated with prompt version changes. They can see at a glance which evals are healthy and which are degrading.

**Why this priority**: Without visibility into quality trends, developers cannot make informed decisions about prompt changes or detect slow regressions. This is the foundational "read" capability that all other stories build on.

**Independent Test**: Run 3+ eval suites, then view the trend summary. Verify each eval type shows its pass rate history and prompt version annotations appear at the correct points in the timeline.

**Acceptance Scenarios**:

1. **Given** at least 2 completed eval runs exist, **When** the developer requests the eval trend summary, **Then** the system displays pass rates over time for each eval type with run timestamps.
2. **Given** a prompt version changed between two eval runs, **When** viewing the trend summary, **Then** the prompt version transition is annotated on the timeline showing which prompts changed and from which version to which version.
3. **Given** no eval runs exist, **When** the developer requests the trend summary, **Then** the system displays a clear message indicating no data is available yet.

---

### User Story 2 - Detect and Diagnose Regressions (Priority: P1)

A developer changes a prompt and runs the eval suite. The system automatically compares the new results against the previous baseline and highlights any metrics that degraded. The developer can drill into which specific eval cases failed and which prompt version change caused the regression.

**Why this priority**: Regression detection is the core safety net — without it, prompt changes can silently degrade quality. Paired with US1, this completes the "observe and react" loop.

**Independent Test**: Change a prompt version, run evals, and verify the system flags metrics that dropped below the previous run's values. Verify the regression report links to the specific prompt version change.

**Acceptance Scenarios**:

1. **Given** a previous eval run exists as baseline, **When** a new eval run completes with a metric that crosses below its threshold, **Then** the system flags it as a REGRESSION with the delta (e.g., "pass_rate: 90% -> 70%, -20pp, REGRESSION"). Drops >= 10 percentage points that remain above threshold are flagged as WARNING.
2. **Given** a regression is detected, **When** the developer views the regression report, **Then** the report shows which prompt versions were active in both runs, highlighting any that changed.
3. **Given** a new eval run completes with equal or better metrics, **When** the developer views the comparison, **Then** no regression warnings are shown and improvements are highlighted.

---

### User Story 3 - Gate Prompt Promotion on Eval Results (Priority: P2)

Before promoting a prompt from `@experiment` to `@production`, the developer runs a promotion check. The system verifies that all eval types pass their minimum thresholds. If any eval fails, promotion is blocked with a clear explanation of which evals failed and why.

**Why this priority**: Automated gating prevents bad prompts from reaching production. This builds on US2 (regression detection) by adding an enforcement mechanism, but developers can manually manage promotions without it.

**Independent Test**: Register a new prompt version under `@experiment`, run the promotion check, and verify it blocks promotion when evals fail and allows it when all pass.

**Acceptance Scenarios**:

1. **Given** all eval types pass their minimum thresholds (>=80% pass rate), **When** the developer requests promotion of a prompt alias, **Then** the system promotes the alias and logs the promotion with the eval run IDs that justified it.
2. **Given** one or more eval types fail their minimum thresholds, **When** the developer requests promotion, **Then** the system blocks promotion and lists each failing eval with its actual vs. required pass rate.
3. **Given** a promotion is blocked, **When** the developer fixes the prompt and re-runs evals with passing results, **Then** the promotion check succeeds on the next attempt.

---

### User Story 4 - Automated Eval on Prompt Registration (Priority: P2)

When a developer registers a new prompt version, the system automatically triggers a full eval suite run. The developer is notified when the run completes and can view results immediately without manually invoking the eval command.

**Why this priority**: Automation reduces the chance of forgetting to run evals after a prompt change. However, developers can always run evals manually, making this a convenience rather than a necessity.

**Independent Test**: Register a new prompt version and verify the eval suite starts automatically. Verify results are available and linked to the prompt version that triggered the run.

**Acceptance Scenarios**:

1. **Given** a new prompt version is registered, **When** the registration completes, **Then** a configurable subset of core evals is triggered automatically within 30 seconds. The developer can also trigger the full eval suite on demand.
2. **Given** an automated eval run is in progress, **When** the developer checks status, **Then** they can see the run is in progress and which eval types have completed.
3. **Given** an automated eval run completes, **When** the developer views results, **Then** the results are linked to the prompt version that triggered the run and include regression comparison against the previous baseline.

---

### User Story 5 - Rollback Prompt on Regression (Priority: P3)

When a regression is detected after a prompt change, the developer can revert to the previous prompt version with a single command. The rollback re-points the alias to the previous version and logs the rollback action with the reason.

**Why this priority**: Rollback is a safety net for when regressions slip through. The alias-swapping infrastructure from Feature 012 already supports this mechanically; this story adds the workflow convenience and audit trail.

**Independent Test**: Promote a prompt, detect a regression, then roll back. Verify the alias points to the previous version and the rollback is logged.

**Acceptance Scenarios**:

1. **Given** a regression was detected after promoting prompt version N, **When** the developer requests a rollback, **Then** the alias is re-pointed to version N-1 and a log entry records the rollback with the regression details.
2. **Given** no previous version exists for a prompt, **When** the developer requests a rollback, **Then** the system reports that no previous version is available to roll back to.
3. **Given** a rollback was performed, **When** the developer views the trend summary, **Then** the rollback event is annotated on the timeline.

---

### Edge Cases

- What happens when an eval run fails mid-way (e.g., OpenAI API outage)? Partial results are saved with an error status; the run is not counted as a valid baseline for regression comparison.
- What happens when multiple prompt versions change simultaneously? The regression report lists all changed prompts, but cannot attribute the regression to a single prompt without additional A/B testing.
- What happens when eval thresholds are updated between runs? Comparisons use the thresholds that were active at the time of each run, stored as run parameters.
- What happens when a new eval type is added that has no historical data? The trend summary shows it starting from its first run; promotion gates include it only once it has at least one completed run.

## Requirements

### Functional Requirements

- **FR-001**: System MUST aggregate eval results across runs and display pass rate trends over time for each eval type.
- **FR-002**: System MUST annotate eval trend timelines with prompt version changes, showing which prompts changed between runs.
- **FR-003**: System MUST compare new eval run results against the most recent baseline. Metrics that cross below their pass rate threshold are flagged as REGRESSION. Metrics that drop >= 10 percentage points but remain above threshold are flagged as WARNING. Smaller intra-threshold fluctuations are not flagged.
- **FR-004**: Regression reports MUST identify which prompt versions were active in both runs and highlight changes.
- **FR-005**: System MUST provide a promotion gate that checks all eval types against minimum pass rate thresholds before allowing alias promotion.
- **FR-006**: System MUST block alias promotion and provide a clear failure report when any eval type fails its threshold.
- **FR-007**: System MUST trigger an eval suite run automatically when a new prompt version is registered. By default, a configurable subset of core evals is run. The full suite of all eval types is available on demand (e.g., before promotion).
- **FR-008**: System MUST support single-command rollback of a prompt alias to its previous version with audit logging.
- **FR-009**: System MUST log all promotion and rollback actions with timestamps, prompt versions, eval run IDs, and the actor who performed the action. Audit records are stored as tags on the MLflow eval runs that justified the action.
- **FR-010**: System MUST handle partial eval failures gracefully, saving partial results without counting them as valid baselines.
- **FR-011**: System MUST provide a command-line interface for all operations (trend view, regression check, promotion gate, rollback).

### Key Entities

- **Eval Run Summary**: Aggregated results from a single eval suite execution — timestamp, eval type, pass rate, score, prompt versions active, run status (complete/partial/error).
- **Regression Report**: Comparison between two eval runs — baseline run, current run, per-metric deltas, changed prompt versions, overall verdict (pass/regressed).
- **Promotion Record**: Audit entry for alias promotions and rollbacks — prompt name, from-version, to-version, alias, action type (promote/rollback), eval run IDs justifying the action, timestamp. Stored as MLflow run tags on the justifying eval runs.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Developers can view eval quality trends across all eval types within 5 seconds of requesting the summary.
- **SC-002**: Regressions are detected and reported within 10 seconds of an eval run completing.
- **SC-003**: Prompt promotion is blocked 100% of the time when any eval type falls below its pass rate threshold.
- **SC-004**: Single-command rollback restores the previous prompt version in under 5 seconds.
- **SC-005**: Automated eval runs trigger within 30 seconds of a new prompt version being registered.
- **SC-006**: All promotion and rollback actions have complete audit trails with zero gaps in logging.
- **SC-007**: The system handles all existing eval types without requiring code changes to add trend tracking for new eval types.

## Assumptions

- The existing MLflow tracking server stores all eval run data (metrics, parameters, artifacts) and is the source of truth for historical results.
- Prompt versions and aliases are managed via the Feature 012 prompt registry infrastructure.
- The CLI is the primary interface; no custom web dashboard is built in this feature (MLflow UI serves that role for detailed drill-down).
- All existing eval types use consistent parameter naming (`pass_rate`, `dataset_version`, `prompt.*`) enabling automated aggregation.
- The eval suite can be run as a single command (`uv run python -m eval`) that executes all eval types sequentially.

## Scope

### In Scope

- CLI tools for trend summary, regression detection, promotion gating, and rollback
- Automated eval triggering on prompt registration
- Aggregation of existing MLflow eval run data
- Audit logging for promotion and rollback actions

### Out of Scope

- Custom web dashboard (use MLflow UI for detailed views)
- A/B testing infrastructure (attributing regressions to individual prompts when multiple change)
- Per-user or per-conversation eval segmentation
- Real-time alerting or notification integration (developers check results via CLI)
- Modifying existing eval scorers or thresholds (consumed as-is)

## Dependencies

- **Feature 012 (Prompt Registry)**: Provides prompt versioning, alias management, and `prompt.*` params in eval runs.
- **MLflow 3.10.0**: Stores eval runs, metrics, and parameters. Provides the data layer for trend aggregation.
- **Existing eval framework**: 19 eval types with golden datasets, two-phase evaluation pattern, and consistent metric naming.
