# Quickstart: Unified Eval Navigation

## Prerequisites

- Docker API service running (`docker compose -f docker/docker-compose.api.yml up -d`)
- MLflow tracking server running (`docker compose -f docker/docker-compose.mlflow.yml up -d`)
- Frontend dev server running (`cd frontend && npm run dev`)
- At least one eval suite run completed after agent versioning is enabled

## Scenario 1: Navigate the Unified Eval Section

1. Log in as admin (`sdeery` / `password123`)
2. Click "Evals" in the header
3. Verify landing on dashboard page (`/admin/evals`) with regression banner and summary table
4. Verify sub-navigation shows: Dashboard, Agents, Experiments, Datasets, Trends
5. Click each sub-nav link and verify routing to correct page
6. Verify "Explorer" link no longer appears in header

**Expected**: Single "Evals" entry in header, persistent sub-navigation on all pages.

## Scenario 2: Browse Agent Versions

1. Navigate to `/admin/evals/agents`
2. Verify list of agent versions with git branch, commit SHA, date, quality score
3. Click an agent version
4. Verify detail page shows git metadata and per-experiment results
5. Click an experiment name in the results
6. Verify navigation to that experiment's detail page

**Expected**: Agent versions are sorted by creation date, newest first.

## Scenario 3: Experiment → Run → Trace Drill-Down

1. Navigate to `/admin/evals/experiments`
2. Click an experiment name (e.g., "personal-ai-assistant-eval")
3. Verify breadcrumb shows "Experiments > personal-ai-assistant-eval"
4. Click a run row
5. Verify breadcrumb shows "Experiments > personal-ai-assistant-eval > Run abc123"
6. Expand a trace to see assessment details
7. Click "Experiments" in breadcrumb to return to list

**Expected**: Breadcrumbs update at each level, back navigation works.

## Scenario 4: View Version-Based Trends

1. Navigate to `/admin/evals/trends`
2. Verify universal quality chart with agent versions on X-axis
3. Hover over a data point to see commit SHA, branch, date, quality score
4. Scroll down to per-eval-type summary table
5. Expand an eval type row to see its trend chart

**Expected**: Chart shows quality progression across git commits.

## Scenario 5: Browse Datasets

1. Navigate to `/admin/evals/datasets`
2. Verify list of golden datasets with name, description, case count
3. Click a dataset name
4. Verify detail page shows cases with expandable rows
5. Click "Back to datasets" to return to list

**Expected**: URL changes to `/admin/evals/datasets/[name]` on detail.

## Scenario 6: Run Evals with Agent Versioning

1. Make a code change and commit it
2. Run eval suite: `uv run python -m eval --dataset eval/quality_golden_dataset.json`
3. Navigate to `/admin/evals/agents`
4. Verify new agent version appears with the commit SHA from step 1
5. Click into it and verify the eval run is linked

**Expected**: Agent version auto-created from git state, run auto-linked.

## Scenario 7: Dashboard Operations Still Work

1. Navigate to `/admin/evals` (dashboard landing)
2. Verify Promote, Run Evals, Rollback tabs/sections are present
3. Test promote gate check flow
4. Test run evals flow (start core suite)

**Expected**: All operational actions work identically to before restructure.
