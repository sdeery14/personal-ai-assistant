# Data Model: Eval Dashboard & Regression Pipeline

**Feature**: 013-eval-pipeline
**Date**: 2026-02-24

## Entities

All entities are Python dataclasses used in-memory. No new database tables — all persistent data lives in MLflow runs/tags.

### TrendPoint

A single data point in an eval trend timeline.

| Field | Type | Description |
|-------|------|-------------|
| run_id | str | MLflow run ID (UUID) |
| timestamp | datetime | Run start time |
| experiment_name | str | Full MLflow experiment name (e.g., `personal-ai-assistant-eval-tone`) |
| eval_type | str | Short eval type name (e.g., `tone`, `routing`, `quality`) |
| pass_rate | float | Pass rate (0.0–1.0) |
| average_score | float | Average judge score (1.0–5.0) |
| total_cases | int | Total eval cases in run |
| error_cases | int | Cases that errored |
| prompt_versions | dict[str, str] | Map of prompt name → version string (e.g., `{"orchestrator-base": "v2"}`) |
| eval_status | str | `complete`, `partial`, or `error` |

**Source**: Constructed from `mlflow.search_runs()` DataFrame rows.

---

### TrendSummary

Aggregated trend data for a single eval type.

| Field | Type | Description |
|-------|------|-------------|
| eval_type | str | Short eval type name |
| points | list[TrendPoint] | Chronologically ordered trend points |
| latest_pass_rate | float | Most recent run's pass rate |
| trend_direction | str | `improving`, `stable`, or `degrading` (based on last 3 runs) |
| prompt_changes | list[PromptChange] | Points where prompt versions changed |

---

### PromptChange

Annotation for a prompt version transition between two consecutive runs.

| Field | Type | Description |
|-------|------|-------------|
| timestamp | datetime | Timestamp of the run where the change was first observed |
| run_id | str | Run ID where new version was first used |
| prompt_name | str | Name of the changed prompt |
| from_version | str | Previous version (e.g., `v1`) |
| to_version | str | New version (e.g., `v2`) |

---

### RegressionReport

Comparison between a baseline run and the current run for one eval type.

| Field | Type | Description |
|-------|------|-------------|
| eval_type | str | Short eval type name |
| baseline_run_id | str | MLflow run ID of the baseline (previous complete run) |
| current_run_id | str | MLflow run ID of the current run |
| baseline_pass_rate | float | Baseline pass rate |
| current_pass_rate | float | Current pass rate |
| delta_pp | float | Change in percentage points (current - baseline) |
| threshold | float | Pass rate threshold for this eval type |
| verdict | str | `REGRESSION`, `WARNING`, `PASS`, or `IMPROVED` |
| changed_prompts | list[PromptChange] | Prompts that changed between baseline and current |
| baseline_timestamp | datetime | When baseline ran |
| current_timestamp | datetime | When current ran |

**Verdict Logic**:
- `REGRESSION`: `current_pass_rate < threshold`
- `WARNING`: `current_pass_rate >= threshold` AND `delta_pp <= -10`
- `IMPROVED`: `delta_pp > 0`
- `PASS`: all other cases (stable or minor fluctuation)

---

### PromotionResult

Outcome of a promotion gate check.

| Field | Type | Description |
|-------|------|-------------|
| allowed | bool | Whether promotion is permitted |
| prompt_name | str | Prompt being promoted |
| from_alias | str | Source alias (e.g., `experiment`) |
| to_alias | str | Target alias (e.g., `production`) |
| version | int | Version number being promoted |
| eval_results | list[PromotionEvalCheck] | Per-eval-type gate results |
| blocking_evals | list[str] | Eval types that failed (empty if allowed) |
| justifying_run_ids | list[str] | MLflow run IDs used as evidence |

---

### PromotionEvalCheck

Per-eval-type result within a promotion gate check.

| Field | Type | Description |
|-------|------|-------------|
| eval_type | str | Short eval type name |
| pass_rate | float | Current pass rate |
| threshold | float | Required minimum pass rate |
| passed | bool | Whether this eval type meets its threshold |
| run_id | str | MLflow run ID used for this check |

---

### AuditRecord

Represents a promotion or rollback action stored as MLflow tags.

| Field | Type | Description |
|-------|------|-------------|
| action | str | `promote` or `rollback` |
| prompt_name | str | Prompt affected |
| from_version | int | Previous version |
| to_version | int | New version |
| alias | str | Alias changed (e.g., `production`) |
| timestamp | datetime | When the action occurred |
| actor | str | Who performed the action |
| reason | str | Free-text reason (especially for rollbacks) |
| justifying_run_ids | list[str] | Eval runs that justified this action |

**Storage**: Serialized as `audit.*` prefixed tags on the justifying MLflow eval runs.

---

### EvalSubsetConfig

Configuration for which eval types to run automatically vs. on demand.

| Field | Type | Description |
|-------|------|-------------|
| core_evals | list[str] | Dataset paths for the default automated subset |
| full_evals | list[str] | Dataset paths for all eval types |
| thresholds | dict[str, float] | Per-eval-type pass rate thresholds (defaults to 0.80) |

**Source**: Loaded from `eval/pipeline_config.py` constants.

## Relationships

```
TrendSummary 1──* TrendPoint
TrendSummary 1──* PromptChange
RegressionReport 1──* PromptChange
PromotionResult 1──* PromotionEvalCheck
AuditRecord *──* MLflow Run (via tags)
```

## State Transitions

### Eval Run Lifecycle (existing, no changes)
```
RUNNING → FINISHED (success)
RUNNING → FAILED (execution error)
```

### Eval Status Tag (new)
```
complete → (immutable once set)
partial → (immutable once set)
error → (immutable once set)
```

### Promotion Flow
```
Check Gate → ALLOWED → Promote Alias → Log Audit Tags
Check Gate → BLOCKED → Report Failures
```

### Rollback Flow
```
Request Rollback → Find Previous Version → Swap Alias → Log Audit Tags
Request Rollback → No Previous Version → Report Error
```
