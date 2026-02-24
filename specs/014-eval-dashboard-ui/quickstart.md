# Quickstart: Eval Dashboard UI

**Feature Branch**: `014-eval-dashboard-ui`
**Date**: 2026-02-24

## Prerequisites

- Docker services running (API + MLflow): `docker compose -f docker/docker-compose.api.yml up -d` and `docker compose -f docker/docker-compose.mlflow.yml up -d`
- Frontend dev server: `cd frontend && npm run dev`
- At least one eval run completed (for trend/regression data)
- An admin user account

## Scenario 1: View Eval Trends (US1)

1. Log in as admin user
2. Navigate to Admin panel (click "Admin" in header)
3. Click "Evals" tab/link in admin navigation
4. **Verify**: Summary table shows all eval types with latest pass rate, trend direction (IMPROVING/STABLE/DEGRADING), and run count
5. Click on an eval type row (e.g., "tone")
6. **Verify**: Detail view shows:
   - Interactive line chart of pass rate over time
   - Prompt version change annotations on the chart
   - Data table with individual runs (run ID, date, pass rate, score, prompt versions)
7. Change the history limit dropdown
8. **Verify**: Chart and table update to show the selected number of runs
9. Click refresh button
10. **Verify**: Data reloads from the API

**Empty State Test**: If no eval runs exist, the dashboard shows "No eval data available yet."

## Scenario 2: View Regression Reports (US2)

1. From the eval dashboard, click the "Regressions" tab
2. **Verify**: Comparison table shows:
   - Eval type, baseline pass rate, current pass rate, delta, threshold, verdict
   - REGRESSION rows are highlighted in red/warning color
   - IMPROVED rows show positive delta
   - PASS rows show neutral styling
3. **Verify**: Changed prompts are listed below each regression entry (e.g., "orchestrator-base: v2 -> v3")
4. **Verify**: Summary at top shows verdict counts (e.g., "1 REGRESSION, 2 PASS, 1 IMPROVED")

**Empty State Test**: With insufficient data, shows "No eval types with sufficient data for comparison."

## Scenario 3: Promote Prompt Version (US3)

### 3a: Successful Promotion
1. Click the "Promote" tab
2. Select a prompt from the dropdown (e.g., "orchestrator-base")
3. **Verify**: Gate check table shows each eval type with pass rate, threshold, pass/fail
4. All gates pass — "Promote" button is enabled
5. Click "Promote"
6. **Verify**: Success message shows audit details (from v2 to v3, alias=production, timestamp)

### 3b: Blocked Promotion
1. When a gate fails, **Verify**: "Promote" button is disabled, blocking eval types listed
2. "Force Promote" option appears with a reason input
3. Enter a reason and click "Force Promote"
4. **Verify**: Warning displayed, promotion proceeds, audit shows "forced" reason

## Scenario 4: Trigger Eval Suite Run (US4)

1. Click the "Run Evals" tab
2. Select suite: "core" (5 evals) or "full" (19 evals)
3. Click "Run Suite"
4. **Verify**: Progress view shows:
   - Progress bar or counter (e.g., "2/5 complete")
   - Per-eval status as each completes (PASS/FAIL indicator)
5. Click "Refresh" to update progress
6. **Verify**: Progress updates with newly completed evals
7. After all evals complete:
   - **Verify**: Regression check results appear automatically
   - **Verify**: Summary shows pass/fail counts

**Concurrent Run Test**: While a run is active, clicking "Run Suite" again shows "An eval run is already in progress."

## Scenario 5: Rollback Prompt Version (US5)

### 5a: Successful Rollback
1. Click the "Rollback" tab
2. Select a prompt from the dropdown (e.g., "orchestrator-base")
3. **Verify**: Shows current version (v3) and target rollback version (v2)
4. Enter a reason: "Tone eval regressed after v3 promotion"
5. Click "Rollback"
6. **Verify**: Success message shows audit details (rolled back from v3 to v2)

### 5b: No Previous Version
1. Select a prompt at version 1
2. **Verify**: Message shows "No previous version available for rollback"
3. Rollback button is disabled

## Scenario 6: Access Control

1. Log in as a non-admin user
2. Navigate to `/admin/evals` directly
3. **Verify**: Redirected to `/chat` (or shown "Admin access required")
4. **Verify**: "Admin" link not visible in navigation header

## Scenario 7: Error Handling

1. Stop the API backend
2. Navigate to the eval dashboard
3. **Verify**: Connection error displayed with retry option
4. Restart the API backend
5. Click retry
6. **Verify**: Dashboard loads normally
