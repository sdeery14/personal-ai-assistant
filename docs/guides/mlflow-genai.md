# MLflow GenAI Guide

**Last Updated**: 2026-01-28
**MLflow Version**: 3.8.1
**Purpose**: Capture best practices and lessons learned for MLflow GenAI evaluation

---

## Overview

MLflow 3.x provides a unified GenAI evaluation framework for LLM applications. This guide documents patterns for LLM-as-a-judge evaluation, experiment tracking, and regression gating.

---

## Installation

```bash
pip install mlflow==3.8.1
```

For full stack with artifacts:

```bash
pip install mlflow[extras]==3.8.1 psycopg2-binary boto3
```

---

## Core Concepts

### Experiments

An experiment groups related runs:

```python
import mlflow

mlflow.set_experiment("personal-ai-assistant-eval")
```

### Runs

A run captures a single evaluation execution:

```python
with mlflow.start_run():
    mlflow.log_param("model", "gpt-4.1")
    mlflow.log_metric("pass_rate", 0.85)
    mlflow.log_artifact("results.json")
```

### Scorers (Judges)

LLM-based evaluators for quality assessment:

```python
from mlflow.genai.judges import make_judge
from typing import Literal

quality_judge = make_judge(
    name="quality",
    instructions="...",
    feedback_value_type=Literal["1", "2", "3", "4", "5"],
    model="openai:/gpt-4.1",
)
```

---

## Patterns We Use

### Pattern 1: Custom Quality Judge

Used in Feature 002 for LLM-as-a-judge evaluation:

```python
from mlflow.genai.judges import make_judge
from typing import Literal

quality_judge = make_judge(
    name="quality",
    instructions="""You are an evaluation judge for an AI assistant.

## Task
Evaluate the assistant's response quality based on the provided rubric.

## Input
**User Question**: {{ inputs.question }}
**Assistant Response**: {{ outputs.response }}
**Evaluation Rubric**: {{ expectations.rubric }}

## Scoring Scale
- **5 (Excellent)**: Fully addresses the question, accurate, well-structured
- **4 (Good)**: Addresses the question correctly with minor issues
- **3 (Acceptable)**: Partially addresses the question; some gaps
- **2 (Poor)**: Significantly misses the point or contains errors
- **1 (Unacceptable)**: Completely wrong or irrelevant

Return ONLY the numeric score (1, 2, 3, 4, or 5).""",
    feedback_value_type=Literal["1", "2", "3", "4", "5"],
    model="openai:/gpt-4.1",
)
```

**Key learnings:**

- Use Jinja2 templating: `{{ inputs.field }}`, `{{ outputs.field }}`, `{{ expectations.field }}`
- `feedback_value_type` must be a `Literal` type for structured output
- Model format: `openai:/model-name`

### Pattern 2: Evaluation with mlflow.genai.evaluate()

```python
import mlflow
import pandas as pd

# Prepare data
eval_data = [
    {
        "inputs": {"question": "What is 2+2?"},
        "outputs": {"response": "The answer is 4."},
        "expectations": {"rubric": "Should correctly state the answer is 4."},
    },
]

# Run evaluation
results = mlflow.genai.evaluate(
    data=eval_data,
    scorers=[quality_judge],
)

# Access metrics
print(results.metrics)
# {"quality/mean": 4.5, "quality/mode": "5"}
```

**Key learnings:**

- Data format: list of dicts with `inputs`, `outputs`, `expectations` keys
- Each key maps to a dict of fields accessible in judge template
- Metrics auto-aggregated as `{scorer_name}/mean`, `{scorer_name}/mode`

### Pattern 3: With Prediction Function

When you need to generate outputs dynamically:

```python
def predict_fn(inputs: dict) -> dict:
    """Generate assistant response."""
    response = get_assistant_response(inputs["question"])
    return {"response": response}

# Data without outputs
eval_data = [
    {
        "inputs": {"question": "What is 2+2?"},
        "expectations": {"rubric": "Should correctly state the answer is 4."},
    },
]

results = mlflow.genai.evaluate(
    data=eval_data,
    predict_fn=predict_fn,
    scorers=[quality_judge],
)
```

---

## Docker Compose Stack

### Production-like Local Setup

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: mlflow
      POSTGRES_PASSWORD: mlflow
      POSTGRES_DB: mlflow
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "mlflow"]
      interval: 5s
      retries: 5

  minio:
    image: minio/minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 5s
      retries: 5

  minio-init:
    image: minio/mc
    depends_on:
      minio:
        condition: service_healthy
    entrypoint: >
      bash -c "
      mc alias set minio http://minio:9000 minioadmin minioadmin &&
      mc mb --ignore-existing minio/mlflow
      "

  mlflow:
    image: ghcr.io/mlflow/mlflow:v2.17.0
    depends_on:
      postgres:
        condition: service_healthy
      minio-init:
        condition: service_completed_successfully
    ports:
      - "5000:5000"
    environment:
      MLFLOW_BACKEND_STORE_URI: postgresql://mlflow:mlflow@postgres:5432/mlflow
      AWS_ACCESS_KEY_ID: minioadmin
      AWS_SECRET_ACCESS_KEY: minioadmin
      MLFLOW_S3_ENDPOINT_URL: http://minio:9000
    command: >
      mlflow server
      --backend-store-uri postgresql://mlflow:mlflow@postgres:5432/mlflow
      --artifacts-destination s3://mlflow
      --host 0.0.0.0
      --port 5000

volumes:
  postgres_data:
  minio_data:
```

**Key learnings:**

- Use health checks for proper startup ordering
- MinIO init container creates bucket before MLflow starts
- Artifacts stored in S3-compatible MinIO, not local filesystem

### Client Configuration

```python
import os

os.environ["MLFLOW_TRACKING_URI"] = "http://localhost:5000"
os.environ["AWS_ACCESS_KEY_ID"] = "minioadmin"
os.environ["AWS_SECRET_ACCESS_KEY"] = "minioadmin"
os.environ["MLFLOW_S3_ENDPOINT_URL"] = "http://localhost:9000"
```

---

## Logging Best Practices

### Parameters (Configuration)

```python
mlflow.log_params({
    "assistant_model": "gpt-4.1",
    "judge_model": "gpt-4.1",
    "temperature": 0,
    "max_tokens": 2000,
    "dataset_version": "1.0.0",
    "pass_rate_threshold": 0.80,
    "score_threshold": 3.5,
})
```

### Metrics (Results)

```python
mlflow.log_metrics({
    "total_cases": 10,
    "passed_cases": 8,
    "failed_cases": 2,
    "error_cases": 0,
    "pass_rate": 0.80,
    "average_score": 4.2,
})
```

### Artifacts (Files)

```python
import json
import tempfile

# Log JSON artifact
results_data = [{"case_id": "case-001", "score": 5, ...}]
with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
    json.dump(results_data, f, indent=2)
    mlflow.log_artifact(f.name, "results")
```

---

## Regression Gating

### Computing Pass/Fail

```python
def compute_gate_result(
    pass_rate: float,
    average_score: float,
    pass_rate_threshold: float = 0.80,
    score_threshold: float = 3.5,
) -> tuple[bool, str]:
    """Compute overall pass/fail for regression gate."""
    reasons = []

    if pass_rate < pass_rate_threshold:
        reasons.append(f"pass rate {pass_rate:.1%} < {pass_rate_threshold:.1%}")

    if average_score < score_threshold:
        reasons.append(f"avg score {average_score:.2f} < {score_threshold:.2f}")

    passed = len(reasons) == 0
    reason = "; ".join(reasons) if reasons else "all thresholds met"

    return passed, reason
```

### Exit Codes

```python
import sys

passed, reason = compute_gate_result(pass_rate, avg_score)

mlflow.log_metric("overall_passed", 1 if passed else 0)
mlflow.set_tag("gate_reason", reason)

if passed:
    print("✓ OVERALL: PASS")
    sys.exit(0)
else:
    print(f"✗ OVERALL: FAIL - {reason}")
    sys.exit(1)
```

---

## Testing

### Mocking MLflow

```python
from unittest.mock import patch, MagicMock

@patch("mlflow.start_run")
@patch("mlflow.log_params")
@patch("mlflow.log_metrics")
def test_evaluation_logging(mock_metrics, mock_params, mock_run):
    mock_run.return_value.__enter__ = MagicMock()
    mock_run.return_value.__exit__ = MagicMock()

    # Run evaluation
    run_evaluation(...)

    # Assert logging calls
    mock_params.assert_called_once()
    mock_metrics.assert_called_once()
```

### Testing Without Server

Use file-based tracking for tests:

```python
import tempfile
import os

with tempfile.TemporaryDirectory() as tmpdir:
    os.environ["MLFLOW_TRACKING_URI"] = f"file://{tmpdir}"

    # Tests run with local file storage
    run_evaluation(...)
```

---

## Gotchas & Lessons Learned

### 1. Judge Template Variables

❌ **Wrong:**

```python
instructions="Question: {question}"  # Python f-string won't work
```

✅ **Correct:**

```python
instructions="Question: {{ inputs.question }}"  # Jinja2 template
```

### 2. Literal Type for Feedback

❌ **Wrong:**

```python
feedback_value_type=str  # Unstructured output
```

✅ **Correct:**

```python
feedback_value_type=Literal["1", "2", "3", "4", "5"]  # Constrained
```

### 3. Data Format Keys

The data format uses specific keys that map to template variables:

- `inputs` → `{{ inputs.* }}`
- `outputs` → `{{ outputs.* }}`
- `expectations` → `{{ expectations.* }}`

### 4. S3 Endpoint for MinIO

When using MinIO locally, set the endpoint:

```python
os.environ["MLFLOW_S3_ENDPOINT_URL"] = "http://localhost:9000"
```

Without this, boto3 will try to reach AWS S3.

---

## Resources

- [MLflow Documentation](https://mlflow.org/docs/latest/)
- [MLflow GenAI Evaluation](https://mlflow.org/docs/latest/genai/eval-monitor/)
- [MLflow Tracking Server Setup](https://mlflow.org/docs/latest/tracking.html)

---

## Changelog

| Date       | Change                                         |
| ---------- | ---------------------------------------------- |
| 2026-01-28 | Initial guide created for Feature 002 planning |
