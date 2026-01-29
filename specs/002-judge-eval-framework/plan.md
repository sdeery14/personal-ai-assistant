# Implementation Plan: Judge-Centered Evaluation Framework (MLflow)

**Branch**: `002-judge-eval-framework` | **Date**: 2026-01-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-judge-eval-framework/spec.md`

---

## Summary

Establish an LLM-as-a-judge evaluation framework using MLflow GenAI to measure Feature 001 assistant quality. A golden dataset of 10 test cases is evaluated via `mlflow.genai.evaluate()` with a custom quality judge, results logged to MLflow (Postgres + MinIO), and regression gated by pass rate and average score thresholds.

---

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: mlflow==3.8.1, openai-agents (existing), pydantic>=2.10.0
**Storage**: PostgreSQL (MLflow backend), MinIO (S3-compatible artifacts)
**Testing**: pytest for harness tests, single CLI for end-to-end eval
**Target Platform**: Docker Compose (local development)
**Project Type**: Single project (extends existing src/)
**Performance Goals**: Full eval suite (20 cases) < 5 minutes
**Constraints**: Single-turn only, local MLflow, no CI integration
**Scale/Scope**: 5–20 golden dataset cases

---

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

| Principle                             | Requirement                           | Status  | Notes                                                     |
| ------------------------------------- | ------------------------------------- | ------- | --------------------------------------------------------- |
| I. Clarity over Cleverness            | Simple, single-responsibility modules | ✅ PASS | Eval runner, judge, dataset loader as separate modules    |
| II. Evaluation-First (NON-NEGOTIABLE) | Tests before implementation           | ✅ PASS | This feature IS the evaluation framework                  |
| III. Tool Safety                      | Schema-validated tools                | ✅ PASS | No external tool execution; judge uses OpenAI API only    |
| IV. Privacy by Default                | Redact PII from logs                  | ✅ PASS | User prompts logged to MLflow; no PII in golden dataset   |
| V. Consistent UX                      | Three-part response format            | ✅ PASS | CLI output: summary → per-case details → overall decision |
| VI. Performance & Cost                | Latency/cost budgets                  | ✅ PASS | ~40 API calls per run; temperature=0 for reproducibility  |
| VII. Observability (NON-NEGOTIABLE)   | Structured logs with correlation IDs  | ✅ PASS | All results logged to MLflow with run IDs                 |

**Gate Result**: ✅ PASS — No violations. Proceed to Phase 0.

---

## Project Structure

### Documentation (this feature)

```text
specs/002-judge-eval-framework/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (JSON schema for dataset)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
eval/
├── __init__.py
├── __main__.py          # CLI entry point (python -m eval)
├── config.py            # Eval-specific settings (thresholds, judge model)
├── dataset.py           # Dataset loader and validator
├── judge.py             # LLM judge definition (mlflow.genai.judges.make_judge)
├── runner.py            # Evaluation orchestrator
├── assistant.py         # Wrapper for Feature 001 ChatService (sync adapter)
└── golden_dataset.json  # Golden test cases

docker/
├── docker-compose.yml   # MLflow stack (API + Postgres + MinIO)
└── .env.example         # Environment variables template

tests/
├── unit/
│   └── test_eval_dataset.py    # Dataset validation tests
│   └── test_eval_judge.py      # Judge output format tests
└── integration/
    └── test_eval_runner.py     # End-to-end eval harness tests
```

**Structure Decision**: Evaluation code lives in a top-level `eval/` package (not `src/`) to maintain separation from the main application. Docker stack configuration moves to `docker/` directory.

---

## Phase 0: Research

### Research Tasks

1. **MLflow GenAI evaluate API** — Confirm `mlflow.genai.evaluate()` signature, data format, and scorer integration
2. **make_judge API** — Confirm judge creation with Literal feedback types and numeric scores
3. **Docker Compose for MLflow** — Postgres backend + MinIO artifacts + MLflow server
4. **OpenAI Agents SDK sync adapter** — How to call streaming ChatService synchronously for evaluation

### Findings

#### MLflow GenAI Evaluation

- **API**: `mlflow.genai.evaluate(data, predict_fn, scorers)`
- **Data format**: DataFrame or list of dicts with `inputs`, `outputs`, `expectations` keys
- **Scorers**: Pass list of judge/scorer objects created via `make_judge`
- **Metrics**: Auto-aggregated as `{scorer_name}/mean`, `{scorer_name}/mode`

#### make_judge API

```python
from mlflow.genai.judges import make_judge
from typing import Literal

quality_judge = make_judge(
    name="quality",
    instructions="""Evaluate the assistant response quality.

User question: {{ inputs.question }}
Assistant response: {{ outputs.response }}
Evaluation criteria: {{ expectations.rubric }}

Score 1-5:
5 = Excellent: Fully addresses the question, accurate, well-structured
4 = Good: Addresses the question with minor issues
3 = Acceptable: Partially addresses the question
2 = Poor: Significantly misses the point or contains errors
1 = Unacceptable: Completely wrong or irrelevant

Return score and brief justification.""",
    feedback_value_type=Literal["1", "2", "3", "4", "5"],
    model="openai:/gpt-4.1",
)
```

#### Docker Compose Stack

MLflow official pattern uses:

- **postgres**: Backend store for experiments/runs
- **minio**: S3-compatible artifact storage
- **minio-create-bucket**: Init container to create bucket
- **mlflow**: Server connecting to both

```yaml
mlflow server \
--backend-store-uri postgresql://user:password@postgres:5432/mlflow \
--artifacts-destination s3://mlflow \
--host 0.0.0.0 --port 5000
```

#### Sync Adapter for ChatService

Feature 001 `ChatService.stream_completion()` is async generator. For evaluation:

- Collect all chunks into complete response
- Use `asyncio.run()` to call from sync context
- Or use `Runner.run()` directly (non-streaming) for simpler evaluation

**Decision**: Create `eval/assistant.py` with sync `get_response(prompt: str) -> str` that uses `Runner.run()` (non-streaming) for deterministic evaluation.

#### MLflow Tracing Integration

Enable MLflow auto-tracing for OpenAI Agents SDK to capture detailed execution traces during evaluation:

```python
import mlflow
mlflow.openai.autolog()  # Enable before evaluation
```

**Benefits**:
- Traces visible in MLflow UI for debugging failed cases
- Enables future use of trace-based scorers (`ToolCallEfficiency`, `ToolCallCorrectness`)
- Full observability into agent execution during evaluation

#### Parallelization

MLflow runs evaluations in a threadpool. Configure parallelization for faster runs:

```bash
# Speed up evaluation (default varies by system)
export MLFLOW_GENAI_EVAL_MAX_WORKERS=10

# Async function timeout (default: 5 minutes)
export MLFLOW_GENAI_EVAL_ASYNC_TIMEOUT=600
```

---

## Phase 1: Design

### Data Model

See [data-model.md](data-model.md) for complete entity definitions.

**Key Entities**:

| Entity       | Purpose                                                          |
| ------------ | ---------------------------------------------------------------- |
| `TestCase`   | Single golden dataset case: id, user_prompt, rubric, context     |
| `EvalResult` | Per-case result: case_id, response, score, passed, justification |
| `EvalRun`    | Aggregate run: run_id, timestamp, parameters, metrics, results[] |

### Contracts

See [contracts/golden-dataset-schema.json](contracts/golden-dataset-schema.json) for JSON Schema.

**Golden Dataset Format**:

```json
{
  "version": "1.0",
  "cases": [
    {
      "id": "case-001",
      "user_prompt": "What is 2+2?",
      "rubric": "Response should correctly state the answer is 4. Should be concise.",
      "context": "Simple arithmetic test"
    }
  ]
}
```

### API Contract

**CLI Interface**: `python -m eval [OPTIONS]`

| Option              | Default                    | Description             |
| ------------------- | -------------------------- | ----------------------- |
| `--dataset`         | `eval/golden_dataset.json` | Path to dataset         |
| `--model`           | env `OPENAI_MODEL`         | Assistant model         |
| `--judge-model`     | env `EVAL_JUDGE_MODEL`     | Judge model             |
| `--pass-threshold`  | 0.80                       | Minimum pass rate       |
| `--score-threshold` | 3.5                        | Minimum average score   |
| `--workers`         | 10                         | Parallel eval workers   |
| `--verbose`         | False                      | Show per-case details   |

**Exit Codes**: 0 = PASS, 1 = FAIL, 2 = ERROR

### Quickstart

See [quickstart.md](quickstart.md) for setup and usage guide.

---

## Implementation Phases

### Phase 1: Infrastructure Setup

| Step | Files                              | Done Criteria                                         |
| ---- | ---------------------------------- | ----------------------------------------------------- |
| 1.1  | Create `docker/docker-compose.yml` | `docker compose up -d` starts Postgres, MinIO, MLflow |
| 1.2  | Create `docker/.env.example`       | Template with all required vars documented            |
| 1.3  | Update root `requirements.txt`     | Add `mlflow==3.8.1`                                   |
| 1.4  | Create `eval/__init__.py`          | Package initialization                                |

### Phase 2: Core Evaluation Components

| Step | Files                                    | Done Criteria                                  |
| ---- | ---------------------------------------- | ---------------------------------------------- |
| 2.1  | Create `eval/config.py`                  | Pydantic settings for eval thresholds, models  |
| 2.2  | Create `eval/dataset.py`                 | Load + validate golden dataset JSON            |
| 2.3  | Create `eval/assistant.py`               | Sync wrapper with `mlflow.openai.autolog()` enabled |
| 2.4  | Create `eval/judge.py`                   | Quality judge via `make_judge`                 |
| 2.5  | Create `tests/unit/test_eval_dataset.py` | Dataset validation tests                       |

### Phase 3: Evaluation Runner

| Step | Files                                  | Done Criteria                                              |
| ---- | -------------------------------------- | ---------------------------------------------------------- |
| 3.1  | Create `eval/runner.py`                | Orchestrate: load dataset → invoke assistant → score → log |
| 3.2  | Create `eval/__main__.py`              | CLI entry point with argparse                              |
| 3.3  | Create `eval/golden_dataset.json`      | 10 golden test cases                                       |
| 3.4  | Create `tests/unit/test_eval_judge.py` | Judge output format tests                                  |

### Phase 4: MLflow Integration

| Step | Files                                          | Done Criteria                                |
| ---- | ---------------------------------------------- | -------------------------------------------- |
| 4.1  | Update `eval/runner.py`                        | Use `mlflow.genai.evaluate()` with judge     |
| 4.2  | Update `eval/runner.py`                        | Log parameters, metrics, artifacts to MLflow |
| 4.3  | Create `tests/integration/test_eval_runner.py` | End-to-end harness tests (mocked APIs)       |

### Phase 5: Regression Gating

| Step | Files                     | Done Criteria                            |
| ---- | ------------------------- | ---------------------------------------- |
| 5.1  | Update `eval/runner.py`   | Compute pass/fail based on thresholds    |
| 5.2  | Update `eval/__main__.py` | Exit code 0/1 based on gate result       |
| 5.3  | Add summary output        | Print formatted results table + decision |

### Phase 6: Documentation & Validation

| Step | Files                                                 | Done Criteria                                        |
| ---- | ----------------------------------------------------- | ---------------------------------------------------- |
| 6.1  | Create `specs/002-judge-eval-framework/quickstart.md` | Setup + usage guide                                  |
| 6.2  | Update root `README.md`                               | Add evaluation section with commands                 |
| 6.3  | End-to-end validation                                 | Full workflow: compose up → eval → view in MLflow UI |

---

## Done Criteria (Feature Complete)

1. ✅ `docker compose -f docker/docker-compose.yml up -d` starts MLflow stack
2. ✅ `python -m eval` runs full evaluation suite
3. ✅ Each case shows score (1-5), pass/fail, justification
4. ✅ Summary shows: total, passed, failed, errors, pass rate, avg score, decision
5. ✅ Exit code 0 when pass rate ≥ 80% AND avg score ≥ 3.5
6. ✅ Exit code 1 when thresholds not met
7. ✅ Results visible in MLflow UI at http://localhost:5000
8. ✅ All tests pass: `pytest tests/unit/test_eval*.py tests/integration/test_eval*.py`
9. ✅ Quickstart documentation complete

---

## Complexity Tracking

> No Constitution violations requiring justification.

| Aspect                   | Chosen Approach               | Why Not Simpler                                                           |
| ------------------------ | ----------------------------- | ------------------------------------------------------------------------- |
| Docker stack             | Compose with Postgres + MinIO | SQLite + local files don't support artifact proxying or concurrent access |
| Separate `eval/` package | Top-level package             | Evaluation is dev tooling, not part of main app runtime                   |
| MLflow tracing enabled   | `mlflow.openai.autolog()`     | Enables future agent scorers and debugging without code changes           |

---

## Future Enhancements (Post-MVP)

The following capabilities are enabled by the current architecture but deferred:

| Enhancement              | When to Add                          | How                                                    |
| ------------------------ | ------------------------------------ | ------------------------------------------------------ |
| Agent tool scorers       | When assistant uses function tools   | Add `ToolCallEfficiency()` to scorers list             |
| Multi-turn evaluation    | When conversation history matters    | Use multi-turn scorers with session IDs                |
| Evaluation datasets      | When managing 50+ cases              | Migrate from JSON to `mlflow.genai.datasets`           |
| Production trace scoring | When monitoring live assistant       | Use `mlflow.genai.evaluate()` on production traces     |
| MCP Server integration   | When AI-assisted analysis is needed  | Configure MLflow MCP Server for Cursor/VS Code         |

---

## Post-Design Constitution Re-check

| Principle                  | Status  | Notes                                                      |
| -------------------------- | ------- | ---------------------------------------------------------- |
| I. Clarity over Cleverness | ✅ PASS | 5 small modules, each single-purpose                       |
| II. Evaluation-First       | ✅ PASS | This feature enables evaluation; tests written for harness |
| III. Tool Safety           | ✅ PASS | No external tool execution                                 |
| IV. Privacy by Default     | ✅ PASS | Golden dataset contains no real user data                  |
| V. Consistent UX           | ✅ PASS | CLI output follows summary → details → decision            |
| VI. Performance & Cost     | ✅ PASS | 10-20 cases × 2 API calls = manageable cost                |
| VII. Observability         | ✅ PASS | Full MLflow logging of all inputs/outputs/scores           |

**Final Gate Result**: ✅ PASS — Ready for task generation.
