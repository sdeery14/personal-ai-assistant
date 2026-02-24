# Feature Specification: Eval Dashboard UI

**Feature Branch**: `014-eval-dashboard-ui`
**Created**: 2026-02-24
**Status**: Draft
**Input**: User description: "Feature 014 – Eval Dashboard UI: Web frontend for the eval pipeline, giving admin users a visual dashboard in the existing Next.js app for monitoring agent quality trends, viewing regression reports, managing prompt promotions, triggering eval runs, and performing rollbacks — all from the admin panel instead of the CLI."

## Overview

Admin users currently interact with the eval pipeline exclusively through CLI commands (`uv run python -m eval.pipeline trend`, `check`, `promote`, `run-evals`, `rollback`). This feature adds a web-based dashboard to the existing Next.js admin panel, providing a visual interface for all five pipeline operations. The dashboard serves as the project's custom frontend for MLflow eval data, surfacing quality trends, regression reports, promotion gates, eval run progress, and rollback controls in one place.

## Clarifications

### Session 2026-02-24

- Q: Should the five dashboard capabilities be on a single page, separate pages, or tabbed? → A: Single page with tab navigation between sections (Trends, Regressions, Promote, Run Evals, Rollback).
- Q: What visual format should the trend detail view use? → A: Both interactive charts (line chart for pass rate over time) and detailed data tables below.
- Q: How should prompts be listed for promotion and rollback? → A: List all registered prompts from the Prompt Registry.
- Q: Should the dashboard auto-refresh data or update only on manual action? → A: Manual refresh only (page load + explicit refresh button).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Eval Quality Trends (Priority: P1)

An admin user navigates to the eval dashboard and sees a summary table of all eval types with their latest pass rate, trend direction (improving/stable/degrading), and number of historical runs. Selecting an eval type reveals a detailed view showing pass rate history annotated with prompt version changes. The admin can filter by eval type and adjust the number of historical runs displayed.

**Why this priority**: Trend visibility is the foundation of quality monitoring. Without seeing trends, the admin cannot detect problems or understand the impact of prompt changes. This is the most frequently accessed view.

**Independent Test**: Navigate to the eval dashboard page and verify it displays a summary table of eval types with pass rates and trend indicators. Verify clicking an eval type shows historical data with prompt version annotations.

**Acceptance Scenarios**:

1. **Given** the admin is authenticated and eval runs exist in MLflow, **When** they navigate to the eval dashboard, **Then** they see a summary table listing each eval type with its latest pass rate, trend direction, and run count.
2. **Given** the summary table is visible, **When** the admin selects an eval type, **Then** they see a detail view with chronological pass rate history and prompt version change annotations.
3. **Given** the detail view is visible, **When** the admin changes the history limit, **Then** the displayed data updates to show the requested number of runs.
4. **Given** no eval runs exist, **When** the admin navigates to the eval dashboard, **Then** they see an empty state message indicating no eval data is available yet.

---

### User Story 2 - View Regression Reports (Priority: P1)

An admin user views the latest regression check results, showing a comparison table of each eval type with its baseline pass rate, current pass rate, delta, threshold, and verdict (REGRESSION/WARNING/IMPROVED/PASS). Changed prompts are highlighted. The admin can see at a glance whether any regressions require attention.

**Why this priority**: Regression detection is the second core monitoring capability. Admins need to quickly identify quality drops after prompt changes to take corrective action.

**Independent Test**: Navigate to the regression report section and verify it displays a comparison table with verdicts for each eval type. Verify REGRESSION verdicts are visually distinguished and changed prompts are listed.

**Acceptance Scenarios**:

1. **Given** the admin is on the eval dashboard, **When** they view the regression report section, **Then** they see a table with columns for eval type, baseline pass rate, current pass rate, delta, threshold, and verdict.
2. **Given** a REGRESSION verdict exists, **When** the admin views the report, **Then** the regression row is visually highlighted and the changed prompts are displayed.
3. **Given** no eval types have sufficient data for comparison, **When** the admin views the regression section, **Then** they see a message indicating insufficient data.
4. **Given** all eval types show PASS or IMPROVED verdicts, **When** the admin views the report, **Then** a positive summary is displayed indicating no regressions.

---

### User Story 3 - Promote Prompt Version (Priority: P2)

An admin user initiates a prompt promotion from the dashboard. The system displays the promotion gate check results (pass/fail per eval type against thresholds) and, if all gates pass, allows the admin to execute the promotion. If any gate fails, the admin can choose to force-promote with a recorded reason. Audit details are displayed after a successful promotion.

**Why this priority**: Promotion is a controlled action that benefits from a visual gate check display, but is performed less frequently than viewing trends or regressions.

**Independent Test**: Trigger a promotion for a prompt and verify the gate check results are displayed. Verify promotion succeeds when all gates pass and is blocked (with force option) when any gate fails.

**Acceptance Scenarios**:

1. **Given** the admin selects a prompt to promote, **When** the gate check runs, **Then** a table shows each eval type with its pass rate, threshold, and pass/fail status.
2. **Given** all eval gates pass, **When** the admin confirms the promotion, **Then** the alias is updated and audit details (from/to version, timestamp, actor) are displayed.
3. **Given** one or more eval gates fail, **When** the admin views the gate results, **Then** the promotion is blocked with a clear message and a force-promote option is available.
4. **Given** the admin force-promotes, **When** they provide a reason, **Then** the promotion proceeds with a warning and the reason is recorded in the audit log.

---

### User Story 4 - Trigger Eval Suite Run (Priority: P2)

An admin user triggers an eval suite run (core or full) from the dashboard. The system shows progress as each eval type completes, with pass/fail status per eval. After completion, the regression check results are displayed automatically.

**Why this priority**: Triggering evals from the UI is convenient but less critical than viewing results. Admins can still use the CLI for this, so it's a quality-of-life improvement.

**Independent Test**: Trigger a core eval suite run and verify progress is displayed as each eval completes. Verify the regression check results appear after all evals finish.

**Acceptance Scenarios**:

1. **Given** the admin is on the eval dashboard, **When** they select a suite (core/full) and trigger a run, **Then** a progress view shows each eval type completing with pass/fail indicators.
2. **Given** an eval suite run is in progress, **When** an individual eval completes, **Then** the progress updates in near-real-time.
3. **Given** all evals in the suite complete, **When** the run finishes, **Then** the regression check results are displayed automatically.
4. **Given** an eval fails during the suite run, **When** the admin views progress, **Then** the failed eval is clearly marked and the suite continues with remaining evals.

---

### User Story 5 - Rollback Prompt Version (Priority: P3)

An admin user performs a prompt rollback from the dashboard. The system shows the current version and the target rollback version, requires a reason, and executes the rollback with audit logging. The result is displayed with confirmation details.

**Why this priority**: Rollback is a corrective action triggered by regression detection. It's the least frequent operation but still valuable in the UI for quick response to quality issues.

**Independent Test**: Initiate a rollback for a prompt and verify the current and target versions are displayed. Verify the rollback executes and shows audit confirmation.

**Acceptance Scenarios**:

1. **Given** the admin selects a prompt to roll back, **When** the rollback view loads, **Then** the current version and previous (target) version are displayed.
2. **Given** the admin provides a reason and confirms, **When** the rollback executes, **Then** the alias is reverted and audit details (from/to version, reason, timestamp) are displayed.
3. **Given** no previous version exists for the prompt, **When** the admin attempts a rollback, **Then** an error message indicates that rollback is not possible.

---

### Edge Cases

- What happens when the backend API is unreachable while the dashboard is loading? The dashboard displays a connection error with a retry option.
- What happens when an eval suite run is already in progress and the admin triggers another? The system prevents concurrent runs and displays a message indicating a run is already active.
- What happens when prompt data in MLflow is stale or inconsistent? The dashboard displays the data as-is from the API and does not attempt to reconcile inconsistencies.
- What happens when the admin's session expires during a long-running eval suite? The eval continues server-side; the admin can refresh and see the current state.
- What happens when there are many eval types (19 in full suite)? The summary table is scrollable and all eval types are displayed without pagination.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a dedicated eval dashboard page accessible only to authenticated admin users from the admin panel navigation. The dashboard MUST use tab navigation to organize five sections: Trends, Regressions, Promote, Run Evals, and Rollback.
- **FR-002**: System MUST display a summary table of all eval types with latest pass rate, trend direction, and run count.
- **FR-003**: System MUST display a detail view for each eval type showing an interactive line chart of pass rate over time, annotated with prompt version changes, followed by a detailed data table of individual runs.
- **FR-004**: System MUST allow filtering the trend view by eval type and configuring the number of historical runs displayed. Data updates on page load and via an explicit refresh button (no auto-refresh).
- **FR-005**: System MUST display regression check results as a comparison table with baseline pass rate, current pass rate, delta, threshold, and verdict per eval type.
- **FR-006**: System MUST visually distinguish REGRESSION verdicts from WARNING, IMPROVED, and PASS verdicts using color coding or badges.
- **FR-007**: System MUST display changed prompts associated with each regression report entry.
- **FR-008**: System MUST allow an admin to initiate a prompt promotion by selecting from a list of all registered prompts (sourced from the Prompt Registry), then displaying the gate check results before execution.
- **FR-009**: System MUST block promotion when any eval gate fails, with a force-promote option that requires a reason.
- **FR-010**: System MUST display audit details (action, prompt name, from/to version, alias, timestamp, actor) after promotion or rollback.
- **FR-011**: System MUST allow an admin to trigger an eval suite run (core or full) and display progress as each eval type completes.
- **FR-012**: System MUST automatically display regression check results after an eval suite run completes.
- **FR-013**: System MUST allow an admin to perform a prompt rollback by selecting from a list of all registered prompts (sourced from the Prompt Registry), showing current and target versions, requiring a reason before execution.
- **FR-014**: System MUST prevent concurrent eval suite runs and inform the admin when a run is already in progress.
- **FR-015**: System MUST display appropriate empty states when no eval data exists for any view.
- **FR-016**: System MUST expose backend API endpoints that proxy to the existing eval pipeline logic, keeping the pipeline as the source of truth.

### Non-Functional Requirements

- **NFR-001**: Dashboard page MUST load and display the summary table within 3 seconds under normal conditions.
- **NFR-002**: All dashboard actions MUST require admin authentication; non-admin users MUST NOT see or access eval dashboard features.
- **NFR-003**: Eval suite progress MUST update within 5 seconds of each individual eval completing.

### Key Entities

- **Eval Trend Summary**: Represents an eval type's quality trend — includes eval type name, latest pass rate, trend direction, run count, and historical data points.
- **Trend Point**: A single eval run's results — includes run ID, timestamp, pass rate, average score, total/error cases, prompt versions, and eval status.
- **Regression Report**: Comparison between baseline and current eval runs — includes eval type, baseline/current pass rates, delta, threshold, verdict, and changed prompts.
- **Promotion Result**: Outcome of a promotion gate check — includes allowed/blocked status, per-eval gate results, blocking eval types, and justifying run IDs.
- **Eval Run Progress**: Status of an in-progress eval suite run — includes suite name, total/completed eval count, per-eval pass/fail status, and overall completion state.
- **Audit Record**: Record of a promotion or rollback action — includes action type, prompt name, from/to version, alias, timestamp, actor, and reason.

## Assumptions

- The existing eval pipeline CLI logic (Feature 013) is the source of truth. The dashboard calls backend API endpoints that delegate to the same pipeline functions.
- The existing Next.js admin panel (Feature 008) provides the shell (navigation, layout, auth) into which the eval dashboard is added.
- Admin authentication is already implemented via Auth.js with `isAdmin` session checks.
- The eval pipeline depends on MLflow being running and accessible from the backend.
- Eval suite runs are long-running operations (minutes) and require progress tracking via polling (manual refresh button).

## Scope Boundaries

### In Scope

- Admin-only eval dashboard page in the existing Next.js app
- Backend API endpoints that proxy to eval pipeline functions
- Summary table, trend detail view, regression reports, promotion gate UI, eval run trigger with progress, rollback UI
- Audit detail display for promotions and rollbacks

### Out of Scope

- Direct MLflow UI integration or embedding (this replaces the need to use MLflow's UI)
- Modifying the eval pipeline CLI behavior (the CLI continues to work independently)
- Real-time WebSocket connections (polling is acceptable for progress updates)
- Eval dataset management or editing from the UI
- Non-admin user access to eval features
- Historical audit log browsing (only shows audit details for the current action)

## Dependencies

- **Feature 008 (Web Frontend)**: Provides the Next.js app shell, admin panel, authentication, and UI component library.
- **Feature 012 (Prompt Registry)**: Provides prompt versioning and alias management used by promotion and rollback.
- **Feature 013 (Eval Pipeline)**: Provides all pipeline logic (trend aggregation, regression detection, promotion gating, eval suite running, rollback execution) that the dashboard calls via backend API endpoints.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Admin users can view eval quality trends for all eval types within 3 clicks from the admin panel.
- **SC-002**: Admin users can identify regressions (REGRESSION verdict) from the dashboard without using the CLI.
- **SC-003**: Admin users can promote a prompt version through the full gate-check workflow from the dashboard.
- **SC-004**: Admin users can trigger a core eval suite run and see progress updates as each eval completes.
- **SC-005**: Admin users can roll back a prompt version with a recorded reason from the dashboard.
- **SC-006**: All eval dashboard features are restricted to admin users; non-admin users cannot access the dashboard.
- **SC-007**: The eval dashboard displays the same data as the CLI commands (`trend`, `check`, `promote`, `run-evals`, `rollback`).
- **SC-008**: 90% of admin eval monitoring tasks (viewing trends, checking regressions) can be completed from the dashboard without CLI access.
