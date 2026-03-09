# Data Model: Eval Explorer UI

Feature 015 is a **read-only UI** — no new database tables. All data is sourced from MLflow (experiments, runs, traces, assessments) and the filesystem (golden dataset JSON files). This document defines the API response shapes that the frontend consumes.

## Entity Relationship

```
Experiment (1) ──── (N) Run (1) ──── (N) Trace (1) ──── (N) Assessment
                                        │
                                        └── (N) Session (groups traces by session ID)

Dataset (standalone, from filesystem)
```

## API Response Models

### ExperimentSummary

Represents one MLflow experiment with aggregated metadata.

| Field | Type | Description |
|-------|------|-------------|
| experiment_id | string | MLflow experiment ID |
| name | string | Experiment name (e.g., "assistant-eval-security") |
| eval_type | string | Eval type key (e.g., "security") |
| run_count | int | Total number of runs |
| last_run_timestamp | datetime | null | Timestamp of most recent run |
| latest_pass_rate | float | null | Pass rate from the most recent run |
| latest_universal_quality | float | null | Universal quality score (1-5) from most recent run |

### RunSummary

Represents one MLflow run within an experiment.

| Field | Type | Description |
|-------|------|-------------|
| run_id | string | MLflow run ID |
| timestamp | datetime | Run start time |
| params | dict[str, str] | All run parameters (model, judge_model, git_sha, prompt.*, dataset_version, etc.) |
| metrics | dict[str, float] | All run metrics (pass_rate, average_score, total_cases, error_cases, etc.) |
| universal_quality | float | null | Universal quality judge average score for this run |
| trace_count | int | Number of traces in this run |

### TraceDetail

Represents one MLflow trace with full data.

| Field | Type | Description |
|-------|------|-------------|
| trace_id | string | MLflow trace ID |
| case_id | string | Test case identifier |
| user_prompt | string | User input (extracted from trace request) |
| assistant_response | string | Assistant output (extracted from trace response) |
| duration_ms | int | null | Execution duration in milliseconds |
| error | string | null | Error message if trace failed |
| session_id | string | null | Session ID for multi-turn evals |
| assessments | list[AssessmentDetail] | All assessments on this trace |

### AssessmentDetail

Represents one scorer's assessment on a trace.

| Field | Type | Description |
|-------|------|-------------|
| name | string | Scorer name (e.g., "quality", "entity_recall_scorer") |
| raw_value | string | float | bool | Original assessment value as stored |
| normalized_score | float | null | Normalized to 1-5 scale (null if not applicable) |
| passed | bool | null | Whether score >= 4 (pass threshold), null if not a pass/fail scorer |
| rationale | string | null | Judge's reasoning text |
| source_type | string | Assessment source (e.g., "CODE", "LLM_JUDGE") |

### SessionGroup

Groups traces by session for multi-turn eval types.

| Field | Type | Description |
|-------|------|-------------|
| session_id | string | Session identifier |
| eval_type | string | Eval type (one of: onboarding, contradiction, memory-informed, multi-cap, long-conversation) |
| traces | list[TraceDetail] | Traces in chronological order |
| session_assessment | AssessmentDetail | null | Session-level assessment (from last trace in session) |

### QualityTrendPoint

One data point on the universal quality trend chart.

| Field | Type | Description |
|-------|------|-------------|
| eval_type | string | Eval type key |
| timestamp | datetime | Run timestamp |
| universal_quality | float | Average universal quality score (1-5) for this run |
| run_id | string | MLflow run ID for drill-down |

### DatasetSummary

Golden dataset file metadata.

| Field | Type | Description |
|-------|------|-------------|
| name | string | Dataset name (derived from filename) |
| file_path | string | Relative path (e.g., "eval/golden_dataset.json") |
| version | string | Dataset version from JSON |
| description | string | Dataset description from JSON |
| case_count | int | Number of test cases |

### DatasetCase

Individual test case from a golden dataset.

| Field | Type | Description |
|-------|------|-------------|
| id | string | Case identifier |
| user_prompt | string | Test prompt |
| rubric | string | null | Evaluation rubric |
| tags | list[str] | Tags for categorization |
| extra | dict[str, any] | Eval-type-specific fields (expected_behavior, severity, attack_type, expected_memories, etc.) |

## Value Normalization Rules

Assessment values are normalized server-side before returning to the frontend:

| Raw Value | Normalized Score | Passed |
|-----------|-----------------|--------|
| "excellent" or "5" | 5.0 | true |
| "good" or "4" | 4.0 | true |
| "adequate" or "3" | 3.0 | false |
| "poor" or "2" | 2.0 | false |
| "unacceptable" or "1" | 1.0 | false |
| true | 1.0 | true |
| false | 0.0 | false |
| float (0.0-1.0 range) | as-is | null (not a 1-5 scorer) |
| float (1.0-5.0 range) | as-is | value >= 4.0 |
