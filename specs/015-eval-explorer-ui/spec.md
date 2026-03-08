# Feature Specification: Eval Explorer UI

**Feature Branch**: `015-eval-explorer-ui`
**Created**: 2026-03-08
**Status**: Draft
**Input**: User description: "A read-only admin UI for browsing all eval data stored in MLflow. Replaces the need to use MLflow's generic UI by providing navigation and visualization tailored to this project's eval structure. Experiment browser, run browser with comparison, trace viewer with span trees, assessment viewer, session viewer, dataset viewer, and universal quality trend across all experiments."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Universal Quality Trend (Priority: P1)

The developer opens the eval explorer and sees a single chart showing agent quality over time across all 18 eval types. Each eval type contributes a 1-5 LLM quality judge score (the "universal judge"), plotted as a separate line on the same chart. This gives an immediate "is the agent getting better or worse?" answer without clicking into individual experiments.

**Why this priority**: This is the core differentiator from MLflow's UI and the primary reason for building the explorer. No other tool provides this cross-experiment quality view. It also drives a framework change (adding a universal quality judge to every eval type) that other stories benefit from.

**Independent Test**: Can be tested by navigating to the explorer page and verifying the chart renders with data from multiple eval types on a shared 1-5 scale.

**Acceptance Scenarios**:

1. **Given** eval runs exist for multiple eval types, **When** the developer opens the explorer, **Then** a trend chart displays one line per eval type showing the universal quality score over time on a 1-5 scale.
2. **Given** an eval type has no universal quality score yet (pre-migration runs), **When** the chart renders, **Then** that eval type is omitted from the chart with a note indicating missing data.
3. **Given** the developer hovers over a data point, **When** the tooltip appears, **Then** it shows the eval type, run date, quality score, and run ID.

---

### User Story 2 - Experiment Browser (Priority: P1)

The developer sees a list of all eval experiments with key metadata: eval type, total run count, date of last run, latest pass rate, and latest universal quality score. Clicking an experiment navigates to its run list.

**Why this priority**: This is the entry point for all drill-down exploration. Without it, no other browsing story works.

**Independent Test**: Can be tested by loading the page and verifying all 18 eval experiments appear with correct metadata, and clicking one navigates to its runs.

**Acceptance Scenarios**:

1. **Given** MLflow has experiments for 18 eval types, **When** the developer opens the experiment browser, **Then** all 18 appear as rows with eval type, run count, last run date, latest pass rate, and latest quality score.
2. **Given** an experiment has zero runs, **When** the list renders, **Then** that experiment shows "No runs" with dashes for metrics.
3. **Given** the developer clicks an experiment row, **When** navigation occurs, **Then** the run browser opens filtered to that experiment's runs.

---

### User Story 3 - Run Browser (Priority: P2)

Within an experiment, the developer sees all runs with sortable/filterable columns for params (model, judge model, git SHA, prompt versions, dataset version) and metrics (pass rate, average score, total cases, errors). Clicking a run expands to show its traces.

**Why this priority**: Runs are the primary unit of eval work. Browsing them is essential for understanding what changed between runs, but the experiment browser (P1) must exist first.

**Independent Test**: Can be tested by selecting an experiment, verifying runs appear with correct params/metrics, and expanding a run to see its traces.

**Acceptance Scenarios**:

1. **Given** an experiment has 10 runs, **When** the developer views the run browser, **Then** all 10 runs appear with timestamp, model, pass rate, average score, total cases, errors, git SHA, and prompt versions.
2. **Given** the developer sorts by pass rate descending, **When** the table re-renders, **Then** runs are ordered highest to lowest pass rate.
3. **Given** the developer clicks a run row, **When** the detail expands, **Then** the trace list for that run appears below.

---

### User Story 4 - Trace & Assessment Viewer (Priority: P2)

Within a run, the developer sees all traces with their assessments. Each trace shows the user prompt, assistant response, and all scorer results (not just the primary scorer). Each assessment shows its name, score, pass/fail status, and rationale.

**Why this priority**: Traces and assessments are where the actual eval data lives. This replaces the most common MLflow UI workflow (clicking through runs to find individual trace results).

**Independent Test**: Can be tested by expanding a run and verifying all traces appear with complete assessment data for all scorers.

**Acceptance Scenarios**:

1. **Given** a run has 8 traces, **When** the developer expands the run, **Then** all 8 traces appear showing case ID, user prompt preview, score, and rating badge.
2. **Given** a trace has assessments from 3 scorers (e.g., entity_recall, entity_precision, relationship_recall), **When** the developer expands the trace, **Then** all 3 assessments appear with name, value, pass/fail, and rationale.
3. **Given** an assessment has a rationale, **When** the developer views it, **Then** the full rationale text is visible (not truncated).
4. **Given** a trace has an error, **When** it renders, **Then** the error is prominently displayed with the error message.

---

### User Story 5 - Run Comparison (Priority: P3)

The developer selects two runs and sees a side-by-side comparison of their params and metrics with deltas highlighted, plus per-case result differences showing which cases improved, regressed, or stayed the same.

**Why this priority**: Valuable for deep analysis but requires run browser (P2) to be functional first. The basic run list covers the most common need; comparison adds analytical depth.

**Independent Test**: Can be tested by selecting two runs and verifying param/metric deltas and per-case diffs render correctly.

**Acceptance Scenarios**:

1. **Given** the developer selects two runs via checkboxes, **When** they click "Compare", **Then** a side-by-side view shows both runs' params and metrics with differences highlighted (green for improvement, red for regression).
2. **Given** case "Q1" scored 4 in run A and 2 in run B, **When** the comparison renders, **Then** case Q1 shows a red regression indicator with the delta.
3. **Given** run A has a case that run B does not, **When** the comparison renders, **Then** the missing case is shown with a "not in run B" indicator.

---

### User Story 6 - Session Viewer (Priority: P3)

For multi-turn eval types (onboarding, contradiction, memory-informed, multi-cap, long-conversation), the developer sees traces grouped by session. Each session shows the full conversation timeline (all turns in order) with the session-level assessment.

**Why this priority**: Session-based evals are a subset of eval types (5 of 18). Important for understanding multi-turn quality, but single-turn trace viewing (P2) covers the majority of use cases.

**Independent Test**: Can be tested by viewing a multi-turn eval type's run and verifying traces are grouped by session with conversation timelines.

**Acceptance Scenarios**:

1. **Given** a run from the onboarding eval, **When** the developer views its traces, **Then** traces are grouped by session ID with a session header showing the session name.
2. **Given** a session has 4 turns, **When** the developer expands the session, **Then** all 4 turns appear in chronological order showing user/assistant messages as a conversation thread.
3. **Given** a session has a session-level assessment, **When** it renders, **Then** the assessment appears at the session level (not duplicated per trace).

---

### User Story 7 - Dataset Viewer (Priority: P3)

The developer can browse the golden datasets used for evaluation. Each dataset shows its version, description, case count, and individual test cases with their prompts, rubrics, tags, and special fields.

**Why this priority**: Useful for understanding what is being tested, but the data is also available in the JSON files directly. Lower priority than viewing results.

**Independent Test**: Can be tested by navigating to the dataset viewer and verifying all golden datasets appear with their cases.

**Acceptance Scenarios**:

1. **Given** 18 golden dataset files exist, **When** the developer opens the dataset viewer, **Then** all datasets appear with name, version, description, and case count.
2. **Given** the developer clicks a dataset, **When** the cases expand, **Then** each case shows its ID, prompt, rubric, tags, and any special fields.
3. **Given** a security dataset case has an `expected_behavior` field, **When** it renders, **Then** "block" or "allow" is displayed alongside the case.

---

### Edge Cases

- What happens when the MLflow tracking server is unreachable? The explorer shows a clear error message with a retry button, consistent with Feature 014's error handling pattern.
- What happens when an experiment exists but has zero runs? The experiment appears in the list with "No runs" and dashes for all metrics.
- What happens when a trace has no assessments? The trace is displayed with its prompt/response but the assessment section shows "No assessments recorded."
- What happens when assessment values are in legacy word format (e.g., "excellent") vs. numeric? Both are normalized to the 1-5 numeric scale for display, with the original value shown on hover.
- What happens when the dataset JSON file has a parse error? That dataset shows an error badge in the list; other datasets still load normally.
- What happens when an experiment has 100+ runs or a run has 50+ traces? Lists use client-side pagination with a default page size of 25 items and page navigation controls.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display all MLflow eval experiments with metadata (eval type, run count, last run date, latest pass rate, latest universal quality score).
- **FR-002**: System MUST display all runs within an experiment with sortable columns for params and metrics.
- **FR-003**: System MUST display all traces within a run with their complete assessment data from all scorers.
- **FR-004**: System MUST render a cross-experiment quality trend chart using the universal 1-5 quality judge score.
- **FR-005**: System MUST group traces by session for the 5 multi-turn eval types and render conversation timelines.
- **FR-006**: System MUST support side-by-side run comparison with param/metric deltas and per-case result diffs.
- **FR-007**: System MUST display golden dataset cases with all fields (prompt, rubric, tags, special fields per eval type).
- **FR-008**: System MUST normalize legacy word-label assessment values ("excellent", "good", etc.) to the 1-5 numeric scale.
- **FR-009**: System MUST be entirely read-only — no mutations to MLflow data, experiments, runs, or traces.
- **FR-010**: System MUST restrict access to admin users only.
- **FR-011**: System MUST display assessment rationales in full (not truncated) when a trace is expanded.
- **FR-012**: System MUST show all assessment scorers per trace, not just the primary scorer.
- **FR-013**: Every eval type MUST include a universal 1-5 quality judge scorer so that cross-experiment trends are comparable. The universal judge is a prerequisite framework change completed before this feature's UI work begins. Feature 015 assumes the data already exists in MLflow.

### Key Entities

- **Experiment**: An MLflow experiment corresponding to one eval type. Has a name, eval type suffix, and contains runs.
- **Run**: A single eval execution within an experiment. Has params (model, prompt versions, git SHA), metrics (pass rate, average score, case counts), and contains traces.
- **Trace**: A single evaluation case execution. Has request/response data, execution duration, and assessments.
- **Assessment**: A scorer's evaluation of a trace. Has a name (scorer name), value (numeric or label), rationale, and source type.
- **Session**: A group of traces sharing a session ID, representing a multi-turn conversation evaluation.
- **Dataset**: A golden test dataset file with versioned test cases containing prompts, rubrics, and eval-type-specific fields.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The developer can view the quality trend for all eval types in a single chart within 3 seconds of page load.
- **SC-002**: The developer can navigate from experiment list to a specific trace's assessments in 3 clicks or fewer.
- **SC-003**: All 18 eval types display a comparable universal quality score on the trend chart.
- **SC-004**: Run comparison highlights all param and metric differences and per-case score changes between two runs.
- **SC-005**: The developer no longer needs to open the MLflow UI for routine eval data browsing (all information accessible from the explorer).
- **SC-006**: Multi-turn eval sessions display complete conversation timelines with session-level assessments.

## Clarifications

### Session 2026-03-08

- Q: Explorer placement — new page or new tabs within existing eval dashboard? → A: Separate page/route (e.g., `/admin/eval-explorer`) with its own navigation, linked from admin sidebar.
- Q: Feature 014 overlap — what happens to the existing Trends tab? → A: Keep both. Feature 014 Trends stays as-is (operational health check); Feature 015 is additive with its own deeper data views.
- Q: Pagination for large lists — how should runs and traces handle volume? → A: Client-side pagination with a default page size (e.g., 25 items) and page controls.
- Q: In Scope contradiction — universal judge ownership? → A: Remove from In Scope. Feature 015 is UI-only; universal judge is a prerequisite done separately.

## Assumptions

- The MLflow tracking server is the same instance used by the existing eval pipeline (Feature 013) and dashboard (Feature 014).
- The existing admin authentication and authorization infrastructure (Feature 008) is reused.
- The explorer is a separate page/route (e.g., `/admin/eval-explorer`) with its own navigation, linked from the admin sidebar. It is distinct from Feature 014's eval dashboard page.
- Assessment value normalization follows the same mapping already implemented in the eval pipeline aggregator.
- Golden dataset files are read from the filesystem at the API layer (they are committed to the repository).
- The universal quality judge does not replace existing per-eval-type scorers — it runs alongside them as an additional assessment.
- The universal judge addition to all eval runners is a separate prerequisite change completed before this feature's UI work begins.

## Scope Boundaries

### In Scope

- Read-only browsing of experiments, runs, traces, assessments, sessions, datasets
- Cross-experiment quality trend visualization
- Run-to-run comparison (params, metrics, per-case diffs)
- Admin-only access control

### Out of Scope

- Editing or deleting MLflow experiments, runs, or traces
- Artifact browsing (model artifacts, logged models)
- Real-time streaming of in-progress eval runs (covered by Feature 014's run status)
- Span-level tree visualization (traces are treated as atomic units; span hierarchy is not exposed in this version)
- User-facing (non-admin) eval data access
- Prompt promotion, rollback, or regression detection (covered by Feature 014)
- User feedback collection or display (covered by Feature 016)
