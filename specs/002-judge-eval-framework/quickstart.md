# Quickstart: Judge-Centered Evaluation Framework

**Feature**: 002-judge-eval-framework
**Date**: 2026-01-28

---

## Overview

This guide walks you through running LLM-as-a-judge evaluations against the Personal AI Assistant and viewing results in MLflow.

---

## Prerequisites

- Docker and Docker Compose installed
- OpenAI API key with access to gpt-4.1 (or configured model)
- Python 3.11+ (for running evaluations)

---

## Quick Start (5 minutes)

### 1. Start the MLflow Stack

```bash
# From repository root
cd docker

# Copy environment template
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-your-key-here

# Start the stack (Postgres + MinIO + MLflow)
docker compose up -d

# Verify services are running
docker compose ps
```

**Services started:**

- **MLflow UI**: http://localhost:5000
- **MinIO Console**: http://localhost:9001 (admin/minioadmin)
- **Postgres**: localhost:5432

### 2. Run Evaluation Suite

```bash
# From repository root (not docker/)
cd ..

# Activate virtual environment
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install evaluation dependencies (if not already)
pip install -r requirements.txt

# Run evaluation with defaults
python -m eval

# Or with options
python -m eval --verbose --pass-threshold 0.75
```

### 3. View Results in MLflow

1. Open http://localhost:5000 in your browser
2. Click on the **"personal-ai-assistant-eval"** experiment
3. Click on the latest run to see:
   - **Parameters**: Model config, thresholds, dataset version
   - **Metrics**: Pass rate, average score, case counts
   - **Artifacts**: Per-case results JSON

---

## CLI Reference

```bash
python -m eval [OPTIONS]
```

| Option                    | Default                                 | Description                           |
| ------------------------- | --------------------------------------- | ------------------------------------- |
| `--dataset PATH`          | `eval/golden_dataset.json`              | Path to golden dataset                |
| `--model MODEL`           | `OPENAI_MODEL` env var                  | Assistant model to evaluate           |
| `--judge-model MODEL`     | `EVAL_JUDGE_MODEL` or same as `--model` | Model for judge                       |
| `--pass-threshold FLOAT`  | `0.80`                                  | Minimum pass rate (0.0-1.0)           |
| `--score-threshold FLOAT` | `3.5`                                   | Minimum average score (1.0-5.0)       |
| `--verbose`               | `False`                                 | Show per-case details during run      |
| `--dry-run`               | `False`                                 | Validate dataset without running eval |

### Exit Codes

| Code | Meaning                               |
| ---- | ------------------------------------- |
| 0    | PASS - All thresholds met             |
| 1    | FAIL - Thresholds not met             |
| 2    | ERROR - Evaluation could not complete |

---

## Example Output

```
╔══════════════════════════════════════════════════════════════════╗
║                    EVALUATION RESULTS                             ║
╠══════════════════════════════════════════════════════════════════╣
║ Run ID: 3f8a7b2c-1234-5678-9abc-def012345678                     ║
║ Timestamp: 2026-01-28T15:30:00Z                                   ║
╠══════════════════════════════════════════════════════════════════╣
║ Model: gpt-4.1 | Judge: gpt-4.1 | Cases: 10                      ║
╠══════════════════════════════════════════════════════════════════╣

  Case          Score  Status  Justification
  ──────────────────────────────────────────────────────────────────
  case-001      5      ✓ PASS  Correctly answered arithmetic question
  case-002      4      ✓ PASS  Good explanation with minor verbosity
  case-003      3      ✗ FAIL  Missed key detail from rubric
  case-004      5      ✓ PASS  Excellent, comprehensive response
  ...

╠══════════════════════════════════════════════════════════════════╣
║ SUMMARY                                                           ║
╠══════════════════════════════════════════════════════════════════╣
║ Total: 10 | Passed: 8 | Failed: 2 | Errors: 0                    ║
║ Pass Rate: 80.0% (threshold: 80.0%) ✓                            ║
║ Avg Score: 4.2 (threshold: 3.5) ✓                                ║
╠══════════════════════════════════════════════════════════════════╣
║                        ✓ OVERALL: PASS                           ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## Understanding Judge Scores

| Score | Rating       | Meaning                                             |
| ----- | ------------ | --------------------------------------------------- |
| 5     | Excellent    | Fully addresses question, accurate, well-structured |
| 4     | Good         | Addresses question correctly with minor issues      |
| 3     | Acceptable   | Partially addresses question; some gaps             |
| 2     | Poor         | Significantly misses the point or contains errors   |
| 1     | Unacceptable | Completely wrong or irrelevant                      |

**Pass threshold**: Score ≥ 4 (configurable)

---

## Environment Variables

| Variable                   | Required | Default                 | Description             |
| -------------------------- | -------- | ----------------------- | ----------------------- |
| `OPENAI_API_KEY`           | ✅       | -                       | OpenAI API key          |
| `OPENAI_MODEL`             | ❌       | `gpt-4.1`               | Default assistant model |
| `EVAL_JUDGE_MODEL`         | ❌       | Same as `OPENAI_MODEL`  | Judge model             |
| `EVAL_PASS_RATE_THRESHOLD` | ❌       | `0.80`                  | Pass rate threshold     |
| `EVAL_SCORE_THRESHOLD`     | ❌       | `3.5`                   | Average score threshold |
| `MLFLOW_TRACKING_URI`      | ❌       | `http://localhost:5000` | MLflow server URL       |

---

## Troubleshooting

### MLflow UI shows no experiments

1. Ensure MLflow stack is running: `docker compose ps`
2. Check MLflow logs: `docker compose logs mlflow`
3. Verify network connectivity: `curl http://localhost:5000/health`

### Evaluation errors with "Connection refused"

1. Ensure MLflow is running before evaluation
2. Check `MLFLOW_TRACKING_URI` environment variable

### Judge scores seem inconsistent

1. Verify temperature=0 (set automatically)
2. Review rubric clarity in golden dataset
3. Consider using a more capable judge model

### Rate limiting errors

1. Reduce dataset size or add delays between cases
2. Check OpenAI API usage limits

---

## Stopping the Stack

```bash
cd docker
docker compose down

# To also remove volumes (all data):
docker compose down -v
```

---

## Next Steps

- Add more cases to `eval/golden_dataset.json`
- Customize rubrics for different capability areas
- Integrate with CI/CD for automated regression detection (future feature)
