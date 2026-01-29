# Data Model: Judge-Centered Evaluation Framework

**Feature**: 002-judge-eval-framework
**Date**: 2026-01-28
**Status**: Complete

---

## Overview

This document defines the data structures used in the evaluation framework. The design prioritizes simplicity and direct mapping to MLflow's GenAI evaluation API.

---

## Entities

### TestCase

A single golden dataset case for evaluation.

| Field         | Type     | Required | Description                                  |
| ------------- | -------- | -------- | -------------------------------------------- |
| `id`          | string   | ✅       | Unique case identifier (e.g., "case-001")    |
| `user_prompt` | string   | ✅       | The question/prompt to send to the assistant |
| `rubric`      | string   | ✅       | Evaluation criteria for the judge            |
| `context`     | string   | ❌       | Optional notes about the test case           |
| `tags`        | string[] | ❌       | Optional categorization tags                 |

**Example**:

```json
{
  "id": "case-001",
  "user_prompt": "What is 2+2?",
  "rubric": "Response should correctly state that the answer is 4. Should be concise and direct.",
  "context": "Simple arithmetic test",
  "tags": ["math", "simple"]
}
```

---

### GoldenDataset

The complete golden dataset file structure.

| Field         | Type       | Required | Description                     |
| ------------- | ---------- | -------- | ------------------------------- |
| `version`     | string     | ✅       | Dataset schema version (semver) |
| `description` | string     | ❌       | Dataset purpose description     |
| `cases`       | TestCase[] | ✅       | Array of test cases (5-20)      |

**Example**:

```json
{
  "version": "1.0.0",
  "description": "Golden test cases for Personal AI Assistant evaluation",
  "cases": [
    {
      "id": "case-001",
      "user_prompt": "What is 2+2?",
      "rubric": "Response should correctly state that the answer is 4."
    }
  ]
}
```

---

### EvalResult

The result of evaluating one test case.

| Field                | Type      | Required | Description                           |
| -------------------- | --------- | -------- | ------------------------------------- |
| `case_id`            | string    | ✅       | Reference to TestCase.id              |
| `user_prompt`        | string    | ✅       | Original prompt (for logging)         |
| `assistant_response` | string    | ✅       | Complete assistant response           |
| `score`              | int (1-5) | ✅       | Judge's quality score                 |
| `passed`             | bool      | ✅       | True if score >= 4                    |
| `justification`      | string    | ✅       | Judge's reasoning (1-2 sentences)     |
| `duration_ms`        | int       | ✅       | Total time for assistant + judge (ms) |
| `error`              | string    | ❌       | Error message if evaluation failed    |

**Example**:

```json
{
  "case_id": "case-001",
  "user_prompt": "What is 2+2?",
  "assistant_response": "The answer is 4.",
  "score": 5,
  "passed": true,
  "justification": "Correctly and concisely answered the arithmetic question.",
  "duration_ms": 1250
}
```

---

### EvalRunParameters

Configuration parameters for an evaluation run.

| Field                 | Type   | Required | Description                                        |
| --------------------- | ------ | -------- | -------------------------------------------------- |
| `assistant_model`     | string | ✅       | Model used for assistant (e.g., "gpt-4.1")         |
| `judge_model`         | string | ✅       | Model used for judge (e.g., "gpt-4.1")             |
| `temperature`         | float  | ✅       | Temperature setting (always 0 for reproducibility) |
| `max_tokens`          | int    | ✅       | Max tokens for assistant response                  |
| `dataset_version`     | string | ✅       | Version from GoldenDataset.version                 |
| `pass_rate_threshold` | float  | ✅       | Minimum required pass rate (0.0-1.0)               |
| `score_threshold`     | float  | ✅       | Minimum required average score (1.0-5.0)           |

---

### EvalRunMetrics

Aggregate metrics for an evaluation run.

| Field            | Type  | Description                                               |
| ---------------- | ----- | --------------------------------------------------------- |
| `total_cases`    | int   | Total number of cases in dataset                          |
| `passed_cases`   | int   | Cases with score >= 4                                     |
| `failed_cases`   | int   | Cases with score < 4                                      |
| `error_cases`    | int   | Cases that errored during evaluation                      |
| `pass_rate`      | float | passed_cases / (total_cases - error_cases)                |
| `average_score`  | float | Mean score of non-error cases                             |
| `overall_passed` | bool  | True if pass_rate >= threshold AND avg_score >= threshold |

---

### EvalRun

Complete results for an evaluation run (logged to MLflow).

| Field        | Type              | Description                        |
| ------------ | ----------------- | ---------------------------------- |
| `run_id`     | string            | MLflow run ID (UUID)               |
| `timestamp`  | datetime          | When the run started (UTC ISO8601) |
| `parameters` | EvalRunParameters | Configuration for this run         |
| `metrics`    | EvalRunMetrics    | Aggregate results                  |
| `results`    | EvalResult[]      | Per-case results                   |

---

## Relationships

```
GoldenDataset
    └── cases: TestCase[]
              ↓ (evaluated to produce)
         EvalResult[]
              ↓ (aggregated into)
         EvalRun
              ├── parameters: EvalRunParameters
              ├── metrics: EvalRunMetrics
              └── results: EvalResult[]
```

---

## Validation Rules

### TestCase

1. `id` must be non-empty, alphanumeric with hyphens (pattern: `^[a-z0-9-]+$`)
2. `user_prompt` must be 1-8000 characters (matches Feature 001 limits)
3. `rubric` must be 10-2000 characters (enough detail for judge)

### GoldenDataset

1. `version` must be valid semver (pattern: `^\d+\.\d+\.\d+$`)
2. `cases` must contain 5-20 items
3. All `id` values must be unique within dataset

### EvalResult

1. `score` must be integer 1-5
2. `passed` must be true if and only if score >= 4
3. `duration_ms` must be positive integer

---

## MLflow Mapping

The entities map to MLflow artifacts as follows:

| Entity            | MLflow Concept | Storage                               |
| ----------------- | -------------- | ------------------------------------- |
| EvalRunParameters | Run Parameters | Logged via `mlflow.log_params()`      |
| EvalRunMetrics    | Run Metrics    | Logged via `mlflow.log_metrics()`     |
| EvalResult[]      | Artifact       | JSON file via `mlflow.log_artifact()` |
| GoldenDataset     | Artifact       | Logged for reproducibility            |

---

## Pydantic Models

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

class TestCase(BaseModel):
    id: str = Field(..., pattern=r"^[a-z0-9-]+$")
    user_prompt: str = Field(..., min_length=1, max_length=8000)
    rubric: str = Field(..., min_length=10, max_length=2000)
    context: Optional[str] = None
    tags: Optional[list[str]] = None

class GoldenDataset(BaseModel):
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    description: Optional[str] = None
    cases: list[TestCase] = Field(..., min_length=5, max_length=20)

    @field_validator("cases")
    @classmethod
    def unique_ids(cls, v):
        ids = [case.id for case in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Case IDs must be unique")
        return v

class EvalResult(BaseModel):
    case_id: str
    user_prompt: str
    assistant_response: str
    score: int = Field(..., ge=1, le=5)
    passed: bool
    justification: str
    duration_ms: int = Field(..., gt=0)
    error: Optional[str] = None

class EvalRunMetrics(BaseModel):
    total_cases: int
    passed_cases: int
    failed_cases: int
    error_cases: int
    pass_rate: float
    average_score: float
    overall_passed: bool
```
