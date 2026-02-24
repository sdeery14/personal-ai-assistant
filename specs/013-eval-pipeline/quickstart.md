# Quickstart: Eval Dashboard & Regression Pipeline

**Feature**: 013-eval-pipeline
**Date**: 2026-02-24

## Prerequisites

1. MLflow stack running: `docker compose -f docker/docker-compose.mlflow.yml up -d`
2. At least one eval run completed (provides baseline data)
3. Prompt registry seeded (Feature 012)

## Scenario 1: View Eval Quality Trends

After running evals a few times, check how quality is trending:

```bash
# View trends for all eval types (last 10 runs each)
uv run python -m eval.pipeline trend

# View trends for a specific eval type
uv run python -m eval.pipeline trend --eval-type tone

# Get JSON output for scripting
uv run python -m eval.pipeline trend --format json
```

**Expected**: Table showing pass rates over time with prompt version change annotations.

## Scenario 2: Check for Regressions After a Prompt Change

After modifying a prompt and running evals, check for regressions:

```bash
# Register a new prompt version under @experiment
uv run python -m eval.pipeline promote orchestrator-base --from-alias experiment --to-alias experiment --version 3

# Run core eval suite
uv run python -m eval.pipeline run-evals

# Check regressions explicitly
uv run python -m eval.pipeline check
```

**Expected**: Regression report comparing latest run against baseline, flagging any REGRESSION or WARNING verdicts.

## Scenario 3: Promote a Prompt with Eval Gating

When satisfied with eval results under `@experiment`, promote to `@production`:

```bash
# Run full eval suite first
uv run python -m eval.pipeline run-evals --suite full

# Attempt promotion (checks all eval types automatically)
uv run python -m eval.pipeline promote orchestrator-base

# If blocked, view which evals failed
# Fix the prompt, re-run evals, try again
```

**Expected**: Promotion succeeds only if all eval types pass their thresholds. Audit record logged.

## Scenario 4: Rollback After Detecting a Regression

If a regression is detected post-promotion:

```bash
# Roll back to previous version
uv run python -m eval.pipeline rollback orchestrator-base --reason "Tone eval regressed from 95% to 70% after v3"

# Verify rollback
uv run python -m eval.pipeline trend --eval-type tone
```

**Expected**: Alias reverted to previous version, audit record logged, rollback visible in trend timeline.

## Scenario 5: Automated Eval on Prompt Registration

When registering a new prompt version, evals trigger automatically:

```bash
# Register a new prompt version (triggers core eval subset automatically)
# This happens via the trigger module when integrated with prompt_service

# Check status of running evals
uv run python -m eval.pipeline run-evals --suite core

# For promotion, run the full suite
uv run python -m eval.pipeline run-evals --suite full
```

**Expected**: Core evals run automatically after prompt registration. Full suite available on demand.

## Verification Checklist

- [ ] `trend` command displays pass rate history with prompt version annotations
- [ ] `check` command detects REGRESSION when pass rate crosses below threshold
- [ ] `check` command detects WARNING when pass rate drops >= 10pp but stays above threshold
- [ ] `promote` command blocks when any eval type fails its threshold
- [ ] `promote` command succeeds and logs audit tags when all evals pass
- [ ] `rollback` command reverts alias and logs audit tags
- [ ] `run-evals --suite core` runs only the configured subset
- [ ] `run-evals --suite full` runs all 19 eval types
- [ ] Empty state (no runs) handled gracefully with informative messages
