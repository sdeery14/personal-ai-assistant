# Feature Specification: Unified Eval Navigation

**Feature Branch**: `016-unified-eval-nav`
**Created**: 2026-03-08
**Status**: Draft
**Input**: User description: "Feature 016 – Unified Eval Navigation from the vision.md"

## User Scenarios & Testing

### User Story 1 - Unified Eval Section with Sub-Page Navigation (Priority: P1)

An admin user navigates to the "Evals" section and sees a cohesive multi-page layout instead of two separate top-level pages. A persistent sub-navigation element shows all available sub-pages (Dashboard, Agents, Experiments, Datasets, Trends). The admin can move between sub-pages without losing context of where they are in the section.

**Why this priority**: The core value of this feature is replacing two disconnected pages (`/admin/evals` and `/admin/eval-explorer`) with a single unified section. Without this, the remaining stories have no foundation.

**Independent Test**: Can be tested by navigating to `/admin/evals` and verifying that sub-page links are visible, clickable, and route to distinct pages — all within a shared layout. The header shows a single "Evals" link instead of separate "Evals" and "Explorer" links.

**Acceptance Scenarios**:

1. **Given** an admin user on any page, **When** they click the "Evals" link in the header, **Then** they land on the eval dashboard page (`/admin/evals`) with a visible sub-page navigation showing Dashboard, Agents, Experiments, Datasets, and Trends.
2. **Given** an admin on the eval dashboard, **When** they click "Experiments" in the sub-navigation, **Then** they are routed to `/admin/evals/experiments` and the sub-navigation highlights "Experiments" as active.
3. **Given** a non-admin user, **When** they attempt to access any `/admin/evals/*` route, **Then** they are redirected to `/chat`.
4. **Given** an admin on any eval sub-page, **When** they look at the header navigation, **Then** there is a single "Evals" link (no separate "Explorer" link).

---

### User Story 2 - Agent Version Browsing (Priority: P2)

An admin navigates to the Agents sub-page and sees a list of all agent versions — each representing a distinct git commit that ran evaluations. They can see at a glance which commits were evaluated, the overall quality score for each version, and click into a version to see all eval runs and traces associated with that specific code state.

**Why this priority**: Agent versioning is the backbone of the Trends page and the primary way to answer "is the agent getting better or worse?" Without structured version tracking, trends are just timestamps — with it, they're tied to specific code changes.

**Independent Test**: Can be tested by navigating to `/admin/evals/agents`, verifying a list of agent versions appears with git metadata, and clicking into one to see its associated eval runs and quality metrics.

**Acceptance Scenarios**:

1. **Given** an admin on the Agents page, **When** the page loads, **Then** they see a list of agent versions sorted by creation date, each showing git branch, commit SHA, creation timestamp, and aggregate quality score.
2. **Given** an admin on the Agents page, **When** they click an agent version, **Then** they are routed to `/admin/evals/agents/[model_id]` showing that version's git metadata (branch, commit, dirty state) and a summary of eval results across all experiment types.
3. **Given** an admin on an agent version detail page, **When** they look at the eval results section, **Then** they see per-experiment-type pass rates and quality scores for runs linked to that version.
4. **Given** an admin on an agent version detail page, **When** they click an experiment name in the results, **Then** they navigate to that experiment's detail page filtered to runs for this agent version.
5. **Given** an eval run is executed from a git commit that has not been evaluated before, **When** the run completes, **Then** a new agent version is automatically created and linked to that run (no manual registration required).

---

### User Story 3 - Experiment and Run Drill-Down with Breadcrumbs (Priority: P3)

An admin browsing experiments can click into an experiment to see its runs, then click into a run to see traces and assessments. A breadcrumb trail shows the navigation path (e.g., Experiments > quality > Run abc123) and allows jumping back to any level.

**Why this priority**: Drill-down navigation is the primary interaction model for exploring eval data. Without proper routing and breadcrumbs, users lose context when navigating deep into the data.

**Independent Test**: Can be tested by clicking through Experiments → specific experiment → specific run and verifying breadcrumbs appear at each level, and clicking a breadcrumb navigates back correctly.

**Acceptance Scenarios**:

1. **Given** an admin on the experiments list, **When** they click an experiment name, **Then** they are routed to `/admin/evals/experiments/[id]` showing that experiment's runs, with a breadcrumb showing "Experiments > [experiment name]".
2. **Given** an admin viewing an experiment's runs, **When** they click a run row, **Then** they are routed to `/admin/evals/runs/[id]` showing traces and assessments, with a breadcrumb showing "Experiments > [experiment name] > Run [short id]".
3. **Given** an admin on a run detail page, **When** they click the "Experiments" breadcrumb, **Then** they navigate back to the experiments list.
4. **Given** an admin on a run detail page, **When** they click the experiment name breadcrumb, **Then** they navigate back to that experiment's runs list.

---

### User Story 4 - Version-Based Trends Page (Priority: P4)

An admin navigates to the Trends sub-page and sees how agent quality has evolved across development. The primary view plots a universal quality score on the Y-axis against agent versions (git commits) on the X-axis, showing at a glance whether recent changes improved or degraded the agent. Below the overview chart, per-experiment-type metrics provide drill-down into specific eval dimensions.

**Why this priority**: Trends are the primary "is the agent getting better?" view. Anchoring them to agent versions (rather than just timestamps) connects quality changes to specific code changes, making regressions actionable.

**Independent Test**: Can be tested by navigating to `/admin/evals/trends` and verifying the version-based quality chart renders with agent versions on the X-axis, and the per-experiment-type detail section shows filterable metrics.

**Acceptance Scenarios**:

1. **Given** an admin on the Trends page, **When** the page loads, **Then** they see a chart with agent versions on the X-axis (labeled by short commit SHA) and universal quality score on the Y-axis, with one data point per version.
2. **Given** an admin on the Trends page, **When** they hover over a data point on the chart, **Then** they see a tooltip with the full git commit SHA, branch name, version date, and quality score.
3. **Given** an admin on the Trends page, **When** they scroll below the overview chart, **Then** they see per-eval-type metrics (pass rate, quality score) for each agent version, with the ability to expand a row to see the trend chart and run history for that eval type.
4. **Given** an admin on the Trends page, **When** they click an agent version label on the chart, **Then** they navigate to that agent version's detail page.

---

### User Story 5 - Dataset Browsing as a Sub-Page (Priority: P5)

An admin navigates to the Datasets sub-page and can browse all golden datasets, click into a dataset to see its cases, and navigate back — all within the unified eval section.

**Why this priority**: Datasets are a supporting resource. Moving them from the explorer's tab to their own sub-page with a detail route improves discoverability and supports deep-linking.

**Independent Test**: Can be tested by navigating to `/admin/evals/datasets`, clicking a dataset, verifying cases render on the detail page, and clicking back.

**Acceptance Scenarios**:

1. **Given** an admin on the Datasets page, **When** the page loads, **Then** they see a table of all golden datasets with name, description, case count, and version.
2. **Given** an admin on the Datasets page, **When** they click a dataset name, **Then** they are routed to `/admin/evals/datasets/[name]` showing the dataset's cases with expandable detail.
3. **Given** an admin on a dataset detail page, **When** they click "Back to datasets" or the breadcrumb, **Then** they return to the datasets list.

---

### User Story 6 - Operational Actions on Dashboard (Priority: P6)

The dashboard landing page (`/admin/evals`) retains all operational actions — promote, run evals, rollback — as tabs or collapsible sections, keeping the dashboard as the operational hub while the other pages handle data browsing.

**Why this priority**: Operational actions (promote, rollback, run evals) are less frequently used than browsing. They remain on the dashboard but are not the primary focus of the restructure.

**Independent Test**: Can be tested by navigating to `/admin/evals` and verifying promote, run evals, and rollback functionality is accessible and works as before.

**Acceptance Scenarios**:

1. **Given** an admin on the dashboard, **When** they look for operational actions, **Then** they can access Promote, Run Evals, and Rollback as tabs or collapsible sections on the dashboard page.
2. **Given** an admin on the dashboard, **When** they trigger a promote action, **Then** the existing promote flow works identically to before (gate check, confirmation, audit result).
3. **Given** an admin on the dashboard, **When** they trigger an eval suite run, **Then** the existing run evals flow works identically (suite selection, progress, results).

---

### Edge Cases

- What happens when a user navigates directly to a deep URL like `/admin/evals/runs/nonexistent-id`? The page should show a meaningful error state rather than crashing.
- What happens when the user's browser back button is used after drill-down? Standard browser history should work correctly with the route-based navigation.
- What happens when an admin is on a sub-page and their session expires? The existing auth redirect behavior should apply uniformly across all sub-pages.
- What happens on mobile viewports? The sub-page navigation should be accessible (e.g., collapsible or horizontal scroll) without breaking the layout.
- What happens when evals run from a dirty git state (uncommitted changes)? The agent version should still be created, marked as dirty, and the uncommitted diffs stored for reproducibility.
- What happens when no agent versions exist yet (fresh install)? The Agents page and Trends page should show meaningful empty states rather than blank or broken views.
- What happens when the same git commit runs evals multiple times? The existing agent version should be reused (not duplicated), and the new runs should be linked to it.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST provide a unified eval section at `/admin/evals/*` with sub-page routing for Dashboard, Agents, Experiments, Datasets, and Trends.
- **FR-002**: The system MUST display a persistent sub-page navigation element visible on all eval sub-pages.
- **FR-003**: The system MUST route an agents list page at `/admin/evals/agents` showing all agent versions.
- **FR-004**: The system MUST route agent detail pages at `/admin/evals/agents/[model_id]` showing git metadata, linked eval runs, and per-experiment quality metrics.
- **FR-005**: The system MUST route experiment detail pages at `/admin/evals/experiments/[id]` showing that experiment's runs.
- **FR-006**: The system MUST route run detail pages at `/admin/evals/runs/[id]` showing traces, sessions, and assessments.
- **FR-007**: The system MUST route dataset detail pages at `/admin/evals/datasets/[name]` showing individual cases.
- **FR-008**: The system MUST display breadcrumb navigation on detail pages showing the full navigation path.
- **FR-009**: The system MUST remove the separate `/admin/eval-explorer` page and its header/sidebar navigation link.
- **FR-010**: The system MUST retain all existing operational functionality (promote, run evals, rollback) on the dashboard landing page.
- **FR-011**: The system MUST enforce admin-only access on all `/admin/evals/*` routes, redirecting non-admins to `/chat`.
- **FR-012**: The system MUST support run-to-run comparison from the experiment detail page (select two runs, view side-by-side diff).
- **FR-013**: The Trends page MUST display agent versions on the X-axis and universal quality score on the Y-axis as the primary trend view, with per-eval-type metrics available as a secondary view.
- **FR-014**: The system MUST support browser back/forward navigation correctly across all sub-pages and detail views.
- **FR-015**: The eval framework MUST automatically create and link agent versions to eval runs based on the current git state (branch, commit, dirty state) — no manual version registration required.
- **FR-016**: Each agent version MUST store git metadata: branch name, commit SHA, whether the working directory had uncommitted changes, and uncommitted diffs (if dirty).

### Key Entities

- **Agent Version**: A snapshot of the agent's code at a specific git commit. Created automatically when evals run. Stores git branch, commit SHA, dirty state, and diffs. All eval runs and traces produced from that commit are linked to this version. The aggregate quality score is the average of universal quality scores (1-5 scale) across all experiment types that ran for that version.
- **Eval Sub-Page**: A distinct routed page within the unified eval section (Dashboard, Agents, Experiments, Datasets, Trends).
- **Breadcrumb Trail**: A navigation element showing the user's current position in the eval section hierarchy (e.g., Experiments > quality > Run abc123).
- **Detail Page**: A sub-page showing detailed information for a specific agent version, experiment, run, or dataset, accessed via URL parameters.

## Success Criteria

### Measurable Outcomes

- **SC-001**: An admin can navigate from the header "Evals" link to any eval sub-page (agents, experiments, datasets, trends) within 1 click of the landing page.
- **SC-002**: An admin can drill down from experiments list to a specific trace's assessment detail in 3 clicks or fewer (experiment → run → expand trace).
- **SC-003**: All existing eval dashboard functionality (promote, rollback, run evals, trend viewing) remains accessible and functional after the restructure.
- **SC-004**: The header navigation shows exactly one "Evals" entry instead of two separate entries ("Evals" and "Explorer").
- **SC-005**: Every eval sub-page and detail page is directly linkable via URL — sharing a URL like `/admin/evals/runs/abc123` loads the correct content.
- **SC-006**: Browser back/forward buttons navigate correctly through the eval section drill-down history.
- **SC-007**: After running an eval suite, the resulting runs are automatically linked to the current agent version and visible on that version's detail page.
- **SC-008**: The Trends page shows agent quality progression across at least 3 versions when sufficient eval history exists.

## Assumptions

- All existing eval dashboard and explorer components are reusable with minimal modification — the bulk of work is routing, layout, and the new agents/trends views.
- The backend needs a small addition to the eval framework to enable automatic agent version creation, plus new API endpoints for listing agent versions and their details. Existing eval endpoints do not change.
- Mobile responsiveness follows the same patterns as the existing admin pages.
- The `/admin/eval-explorer` route is fully removed (not redirected) since this is an internal admin tool with no external links to preserve.
- Agent versions are created automatically from git state — there is no manual version creation or naming workflow.
- Historical eval runs (created before agent versioning is enabled) are not backfilled. The Agents and Trends pages only show data from runs with proper version linking. Historical runs remain accessible through the Experiments page.

## Clarifications

### Session 2026-03-08

- Q: Should the Agents and Trends pages show historical eval runs (pre-versioning), or only runs created after agent versioning is enabled? → A: Fresh start — Agents/Trends pages only show data from runs with proper version linking; historical runs remain visible in Experiments.
- Q: How should the single aggregate quality score per agent version be computed? → A: Average of universal quality scores (1-5) across all experiment types that ran for that version.

## Dependencies

- Feature 014 (Eval Dashboard UI) — provides dashboard components, API endpoints, and operational actions.
- Feature 015 (Eval Explorer UI) — provides explorer components, drill-down patterns, and additional API endpoints.
