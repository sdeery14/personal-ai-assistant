# Research: Judge-Centered Evaluation Framework

**Feature**: 002-judge-eval-framework
**Date**: 2026-01-28
**Status**: Complete

---

## Research Questions

1. How does MLflow GenAI evaluation work with custom LLM judges?
2. How to set up MLflow with Postgres + MinIO via Docker Compose?
3. How to adapt the async Feature 001 ChatService for sync evaluation?
4. What's the optimal judge prompt structure for quality scoring?

---

## 1. MLflow GenAI Evaluation API

### Decision: Use `mlflow.genai.evaluate()` with `make_judge`

### Rationale

MLflow 3.x provides a unified GenAI evaluation framework that:

- Accepts data as DataFrame or list of dicts
- Supports custom LLM judges via `make_judge`
- Auto-aggregates metrics (mean, mode)
- Logs all results to MLflow tracking

### Alternatives Considered

| Alternative                                   | Rejected Because                                 |
| --------------------------------------------- | ------------------------------------------------ |
| Custom evaluation loop                        | Reinvents wheel; no MLflow integration           |
| `mlflow.evaluate()` (legacy)                  | Deprecated in favor of `mlflow.genai.evaluate()` |
| Third-party eval frameworks (DeepEval, Ragas) | Extra dependency; MLflow native is simpler       |

### API Pattern

```python
import mlflow
from mlflow.genai.judges import make_judge
from typing import Literal

# Create judge
quality_judge = make_judge(
    name="quality",
    instructions="...",
    feedback_value_type=Literal["1", "2", "3", "4", "5"],
    model="openai:/gpt-4.1",
)

# Prepare data with inputs/outputs/expectations
data = [
    {
        "inputs": {"question": "What is 2+2?"},
        "outputs": {"response": "The answer is 4."},
        "expectations": {"rubric": "Should correctly state 4."},
    }
]

# Run evaluation
results = mlflow.genai.evaluate(
    data=data,
    scorers=[quality_judge],
)

# Access metrics
print(results.metrics)  # {"quality/mean": 4.5, "quality/mode": "5"}
```

---

## 2. MLflow Docker Compose Stack

### Decision: Postgres + MinIO + MLflow Server

### Rationale

- **Postgres**: Reliable backend store; supports concurrent access
- **MinIO**: S3-compatible; artifact proxying works seamlessly
- **MLflow Server**: Centralized tracking; UI at port 5000

### Alternatives Considered

| Alternative              | Rejected Because                          |
| ------------------------ | ----------------------------------------- |
| SQLite + file artifacts  | No artifact proxying; single-user only    |
| Postgres only (no MinIO) | Limited artifact storage; no S3 API       |
| Remote cloud services    | Out of scope; local-only for this feature |

### Docker Compose Configuration

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

---

## 3. Sync Adapter for Feature 001

### Decision: Use `Runner.run()` (non-streaming) directly

### Rationale

- Evaluation doesn't need streaming; just final response
- `Runner.run()` returns complete result synchronously
- Avoids complexity of collecting async generator chunks
- Simpler error handling

### Alternatives Considered

| Alternative                 | Rejected Because                            |
| --------------------------- | ------------------------------------------- |
| Collect stream chunks       | Unnecessary complexity for evaluation       |
| asyncio.run() wrapper       | Still collecting chunks; overhead           |
| HTTP call to running server | Requires server running; adds network layer |

### Implementation Pattern

```python
from agents import Agent, Runner
from src.config import get_settings

def get_assistant_response(prompt: str, model: str | None = None) -> str:
    """Get complete assistant response (non-streaming)."""
    settings = get_settings()
    actual_model = model or settings.openai_model

    agent = Agent(
        name="Assistant",
        instructions="You are a helpful assistant.",
        model=actual_model,
    )

    result = Runner.run_sync(agent, input=prompt)
    return result.final_output
```

Note: Using `Runner.run_sync()` for synchronous execution in eval context.

---

## 4. Judge Prompt Design

### Decision: 1-5 scale with explicit criteria, Literal feedback type

### Rationale

- 1-5 scale is intuitive and provides sufficient granularity
- Literal type ensures structured output (no parsing needed)
- Per-case rubric allows flexible evaluation criteria
- Justification aids debugging failed cases

### Alternatives Considered

| Alternative        | Rejected Because                            |
| ------------------ | ------------------------------------------- |
| Binary pass/fail   | Not enough granularity for quality tracking |
| 1-10 scale         | Harder to calibrate; diminishing returns    |
| Free-form feedback | Requires parsing; less consistent           |

### Judge Prompt Template

```python
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
- **5 (Excellent)**: Fully addresses the question, accurate, well-structured, follows rubric perfectly
- **4 (Good)**: Addresses the question correctly with minor issues or room for improvement
- **3 (Acceptable)**: Partially addresses the question; some inaccuracies or missing elements
- **2 (Poor)**: Significantly misses the point, contains notable errors, or ignores rubric
- **1 (Unacceptable)**: Completely wrong, irrelevant, or harmful

## Instructions
1. Read the user question carefully
2. Review the assistant's response
3. Evaluate against the rubric criteria
4. Assign a score from 1-5
5. Provide a brief justification (1-2 sentences)

Return ONLY the numeric score (1, 2, 3, 4, or 5).""",
    feedback_value_type=Literal["1", "2", "3", "4", "5"],
    model="openai:/gpt-4.1",
)
```

### Pass/Fail Mapping

- **Pass**: Score ≥ 4
- **Fail**: Score < 4

### Threshold Configuration

- **Pass Rate Threshold**: 80% (configurable via `EVAL_PASS_RATE_THRESHOLD`)
- **Average Score Threshold**: 3.5 (configurable via `EVAL_SCORE_THRESHOLD`)

---

## Summary

| Question          | Decision                                 | Key Reason                         |
| ----------------- | ---------------------------------------- | ---------------------------------- |
| Evaluation API    | `mlflow.genai.evaluate()` + `make_judge` | Native MLflow; auto-logging        |
| Infrastructure    | Postgres + MinIO + MLflow via Compose    | Production-like; artifact proxying |
| Assistant adapter | `Runner.run_sync()`                      | Non-streaming; simpler             |
| Judge scoring     | 1-5 Literal scale with rubric            | Structured; debuggable             |
