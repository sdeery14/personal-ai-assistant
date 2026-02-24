# Implementation Plan: Eval Dashboard & Regression Pipeline

**Branch**: `013-eval-pipeline` | **Date**: 2026-02-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/013-eval-pipeline/spec.md`

## Summary

Build a CLI-driven eval pipeline that aggregates MLflow eval results into trend summaries, detects regressions when metrics cross below thresholds, gates prompt promotions on eval pass rates, triggers automated eval subsets on prompt registration, and supports single-command rollback with audit logging. All data lives in MLflow (existing infrastructure); new code is pure Python CLI tooling.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: MLflow 3.10.0 (existing), pandas (from MLflow), click (CLI framework), structlog (existing logging)
**Storage**: MLflow tracking server (PostgreSQL backend + MinIO artifacts) — no new storage
**Testing**: pytest (unit tests with mocked MLflow client), existing eval framework for integration
**Target Platform**: CLI on developer workstations + Docker containers
**Project Type**: Single project — extends existing `eval/` and `src/` directories
**Performance Goals**: Trend summary < 5s, regression detection < 10s post-run, rollback < 5s
**Constraints**: Must not modify existing eval runners or scorers. Read-only access to existing MLflow data. All new CLI commands under `eval/` package.
**Scale/Scope**: 19 eval types, ~50-200 runs per experiment, 11 registered prompts

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Clarity over Cleverness | PASS | Each CLI command is a single-purpose module. Explicit inputs/outputs via Click parameters. |
| II. Evaluation-First Behavior | PASS | This feature IS the eval pipeline. Unit tests for all pipeline logic. |
| III. Tool Safety and Correctness | N/A | No new agent tools. CLI commands are developer-facing only. |
| IV. Privacy by Default | PASS | No user data involved. Eval datasets are synthetic golden cases. Audit logs contain only prompt names/versions. |
| V. Consistent UX | PASS | CLI output follows structured format: summary → details → next steps. |
| VI. Performance and Cost Budgets | PASS | All operations query existing MLflow data (no LLM calls). Performance targets defined in spec. |
| VII. Observability and Debuggability | PASS | Structured logging for all pipeline operations. Audit trail for promotions/rollbacks via MLflow tags. |
| VIII. Reproducible Environments | PASS | Dependencies managed via pyproject.toml/uv. Click added as dependency. |

## Project Structure

### Documentation (this feature)

```text
specs/013-eval-pipeline/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research findings
├── data-model.md        # Entity definitions
├── quickstart.md        # Integration scenarios
├── contracts/           # CLI command contracts
│   └── cli-commands.md  # CLI interface specifications
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Task breakdown (from /speckit.tasks)
```

### Source Code (repository root)

```text
eval/
├── __main__.py          # Extended: add pipeline subcommands
├── config.py            # Extended: add pipeline config (core eval subset, thresholds)
├── runner.py            # Existing: no changes (read-only dependency)
├── models.py            # Existing: no changes (read-only dependency)
├── pipeline/
│   ├── __init__.py      # Package init
│   ├── cli.py           # Click CLI group: trend, regression, promote, rollback, run-evals
│   ├── aggregator.py    # Query MLflow runs, compute pass rate trends per experiment
│   ├── regression.py    # Compare runs, detect REGRESSION/WARNING, generate reports
│   ├── promotion.py     # Gate promotion on eval thresholds, audit logging via tags
│   ├── rollback.py      # Single-command alias rollback with audit logging
│   ├── trigger.py       # Auto-trigger eval subset on prompt registration
│   └── models.py        # Pipeline-specific data models (TrendPoint, RegressionReport, etc.)
└── pipeline_config.py   # Pipeline configuration (eval subsets, thresholds per eval type)

tests/unit/
└── test_pipeline/
    ├── __init__.py
    ├── test_aggregator.py   # Trend aggregation with mocked MLflow data
    ├── test_regression.py   # Regression detection logic
    ├── test_promotion.py    # Promotion gate logic
    ├── test_rollback.py     # Rollback logic
    ├── test_trigger.py      # Auto-trigger logic
    └── test_cli.py          # CLI command parsing and output formatting
```

**Structure Decision**: New pipeline code lives in `eval/pipeline/` as a subpackage of the existing eval framework. This keeps pipeline logic co-located with eval infrastructure while cleanly separated from existing runners/scorers. No changes to `src/` beyond importing `prompt_service` for promotion/rollback.

## Complexity Tracking

No constitution violations. No complexity justifications needed.
