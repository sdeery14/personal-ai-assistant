# Data Model: Eval Dashboard UI

**Feature Branch**: `014-eval-dashboard-ui`
**Date**: 2026-02-24

## Overview

This feature introduces no new database tables. All data comes from two sources:
1. **Eval pipeline modules** — dataclasses already defined in `eval/pipeline/models.py`
2. **Prompt service** — `get_active_prompt_versions()` returns registered prompt names

The data model for this feature consists of:
- **API response models** (Pydantic) in the backend that serialize pipeline dataclasses to JSON
- **TypeScript interfaces** in the frontend that mirror the API response shapes

## Backend Response Models (Pydantic)

These are new Pydantic models in `src/models/eval_dashboard.py` that wrap existing pipeline dataclasses for JSON serialization.

### TrendPointResponse

Maps from: `eval.pipeline.models.TrendPoint`

| Field | Type | Description |
|-------|------|-------------|
| run_id | str | MLflow run ID |
| timestamp | datetime | Run start time (UTC) |
| eval_type | str | Short eval type name (e.g., "tone") |
| pass_rate | float | Pass rate (0.0–1.0) |
| average_score | float | Average judge score |
| total_cases | int | Total eval cases run |
| error_cases | int | Cases that errored |
| prompt_versions | dict[str, str] | Map of prompt name → version string |
| eval_status | str | "complete", "partial", or "error" |

### PromptChangeResponse

Maps from: `eval.pipeline.models.PromptChange`

| Field | Type | Description |
|-------|------|-------------|
| timestamp | datetime | When the change was detected |
| run_id | str | Run where change occurred |
| prompt_name | str | Name of changed prompt |
| from_version | str | Previous version string |
| to_version | str | New version string |

### TrendSummaryResponse

Maps from: `eval.pipeline.models.TrendSummary`

| Field | Type | Description |
|-------|------|-------------|
| eval_type | str | Short eval type name |
| latest_pass_rate | float | Most recent pass rate |
| trend_direction | str | "improving", "stable", or "degrading" |
| run_count | int | Number of historical runs (len of points) |
| points | list[TrendPointResponse] | Historical data points |
| prompt_changes | list[PromptChangeResponse] | Detected prompt version changes |

### RegressionReportResponse

Maps from: `eval.pipeline.models.RegressionReport`

| Field | Type | Description |
|-------|------|-------------|
| eval_type | str | Short eval type name |
| baseline_run_id | str | Baseline MLflow run ID |
| current_run_id | str | Current MLflow run ID |
| baseline_pass_rate | float | Baseline pass rate |
| current_pass_rate | float | Current pass rate |
| delta_pp | float | Delta in percentage points |
| threshold | float | Pass rate threshold for this eval type |
| verdict | str | "REGRESSION", "WARNING", "PASS", or "IMPROVED" |
| changed_prompts | list[PromptChangeResponse] | Prompts changed between baseline and current |
| baseline_timestamp | datetime | Baseline run timestamp |
| current_timestamp | datetime | Current run timestamp |

### PromotionEvalCheckResponse

Maps from: `eval.pipeline.models.PromotionEvalCheck`

| Field | Type | Description |
|-------|------|-------------|
| eval_type | str | Short eval type name |
| pass_rate | float | Latest pass rate for this eval type |
| threshold | float | Required threshold |
| passed | bool | Whether this eval type passes the gate |
| run_id | str | Justifying run ID |

### PromotionGateResponse

Maps from: `eval.pipeline.models.PromotionResult`

| Field | Type | Description |
|-------|------|-------------|
| allowed | bool | Whether promotion is allowed |
| prompt_name | str | Prompt being promoted |
| from_alias | str | Source alias |
| to_alias | str | Target alias |
| version | int | Version being promoted |
| eval_results | list[PromotionEvalCheckResponse] | Per-eval-type gate results |
| blocking_evals | list[str] | Eval types that failed the gate |
| justifying_run_ids | list[str] | Run IDs that justify the promotion |

### AuditRecordResponse

Maps from: `eval.pipeline.models.AuditRecord`

| Field | Type | Description |
|-------|------|-------------|
| action | str | "promote" or "rollback" |
| prompt_name | str | Prompt name |
| from_version | int | Previous version |
| to_version | int | New version |
| alias | str | Alias affected |
| timestamp | datetime | Action timestamp |
| actor | str | Who performed the action |
| reason | str | Reason for the action |

### EvalRunStatusResponse

New model (no direct pipeline equivalent — wraps in-memory job state)

| Field | Type | Description |
|-------|------|-------------|
| run_id | str | Unique job ID for this eval suite run |
| suite | str | "core" or "full" |
| status | str | "running", "completed", or "failed" |
| total | int | Total number of eval types in suite |
| completed | int | Number of evals completed so far |
| results | list[EvalRunResultResponse] | Per-eval results (grows as evals complete) |
| regression_reports | list[RegressionReportResponse] | null | Regression results (populated after completion) |
| started_at | datetime | When the run started |
| finished_at | datetime | null | When the run finished |

### EvalRunResultResponse

Maps from: `eval.pipeline.trigger.EvalRunResult`

| Field | Type | Description |
|-------|------|-------------|
| dataset_path | str | Path to the eval dataset |
| exit_code | int | Process exit code |
| passed | bool | Whether the eval passed |

### PromptListItem

New model for prompt listing

| Field | Type | Description |
|-------|------|-------------|
| name | str | Prompt registry name |
| current_version | int | Current active version number |

### RollbackInfoResponse

New model for rollback preview

| Field | Type | Description |
|-------|------|-------------|
| prompt_name | str | Prompt name |
| current_version | int | Current version of the alias |
| previous_version | int | null | Target rollback version (null if none) |
| alias | str | Alias being rolled back |

## Frontend TypeScript Interfaces

These mirror the backend response models in `frontend/src/types/eval-dashboard.ts`.

All field names use camelCase (standard JS convention), mapped from snake_case API responses by the API client or response transformation.

## Entity Relationships

```
TrendSummaryResponse
  └── has many TrendPointResponse (points)
  └── has many PromptChangeResponse (prompt_changes)

RegressionReportResponse
  └── has many PromptChangeResponse (changed_prompts)

PromotionGateResponse
  └── has many PromotionEvalCheckResponse (eval_results)

EvalRunStatusResponse
  └── has many EvalRunResultResponse (results)
  └── has many RegressionReportResponse (regression_reports, after completion)
```

## State Transitions

### Eval Run Status
```
(none) → running → completed
                 → failed
```

Only one run can be in "running" state at a time. The transition from running to completed/failed is managed by the background task.
