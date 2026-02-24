# CLI Commands Contract: Eval Pipeline

**Feature**: 013-eval-pipeline
**Date**: 2026-02-24

All commands are accessed via `uv run python -m eval.pipeline <command>`.

---

## `trend` — View Eval Trends Over Time

**Usage**:
```
uv run python -m eval.pipeline trend [OPTIONS]
```

**Options**:
| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--eval-type` | str | (all) | Filter to specific eval type (e.g., `tone`, `routing`) |
| `--limit` | int | 10 | Max runs per eval type to display |
| `--format` | str | `table` | Output format: `table` or `json` |

**Output** (table format):
```
Eval Trend Summary (last 10 runs)
==================================

tone (latest: 95.0% pass rate, STABLE)
  Run              Date                 Pass Rate   Score   Prompts Changed
  abc123def456     2026-02-24 10:00     95.0%       4.2     -
  fed654cba321     2026-02-23 14:30     90.0%       4.0     orchestrator-base: v1→v2
  ...

routing (latest: 85.0% pass rate, IMPROVING)
  Run              Date                 Pass Rate   Score   Prompts Changed
  ...

No data: memory-write (0 runs)
```

**Exit Codes**:
- 0: Success
- 2: Error (MLflow unreachable, etc.)

---

## `check` — Detect Regressions Against Baseline

**Usage**:
```
uv run python -m eval.pipeline check [OPTIONS]
```

**Options**:
| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--eval-type` | str | (all) | Filter to specific eval type |
| `--run-id` | str | (latest) | Specific run ID to check (default: most recent complete run) |
| `--format` | str | `table` | Output format: `table` or `json` |

**Output** (table format):
```
Regression Check
=================

Eval Type           Baseline    Current     Delta    Threshold   Verdict
tone                95.0%       70.0%       -25pp    80.0%       REGRESSION
routing             85.0%       80.0%       -5pp     80.0%       PASS
quality             90.0%       78.0%       -12pp    80.0%       WARNING
memory              88.0%       92.0%       +4pp     80.0%       IMPROVED

Overall: REGRESSION DETECTED

Changed Prompts:
  orchestrator-base: v1 → v2 (between runs fed654.. and abc123..)

1 REGRESSION, 1 WARNING, 1 IMPROVED, 1 PASS
```

**Exit Codes**:
- 0: No regressions
- 1: Regressions detected
- 2: Error

---

## `promote` — Gate and Execute Prompt Promotion

**Usage**:
```
uv run python -m eval.pipeline promote [OPTIONS] PROMPT_NAME
```

**Arguments**:
| Arg | Type | Description |
|-----|------|-------------|
| `PROMPT_NAME` | str | Name of the prompt to promote (e.g., `orchestrator-base`) |

**Options**:
| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--from-alias` | str | `experiment` | Source alias |
| `--to-alias` | str | `production` | Target alias |
| `--version` | int | (latest from-alias) | Specific version to promote |
| `--force` | bool | False | Skip eval gate (with warning) |
| `--actor` | str | `cli-user` | Actor name for audit log |

**Output** (success):
```
Promotion Gate Check
=====================

Prompt: orchestrator-base (v3)
From: @experiment → To: @production

Eval Type           Pass Rate   Threshold   Status
tone                95.0%       80.0%       PASS
routing             85.0%       80.0%       PASS
quality             90.0%       80.0%       PASS
...

All 17 eval types pass. Promoting...

SUCCESS: orchestrator-base @production now points to v3
Audit logged on runs: abc123, def456, ghi789
```

**Output** (blocked):
```
Promotion Gate Check
=====================

Prompt: orchestrator-base (v3)
From: @experiment → To: @production

Eval Type           Pass Rate   Threshold   Status
tone                70.0%       80.0%       FAIL
routing             85.0%       80.0%       PASS
...

BLOCKED: 1 eval type(s) below threshold.
  tone: 70.0% < 80.0% required

Fix the prompt and re-run evals before promoting.
```

**Exit Codes**:
- 0: Promotion succeeded
- 1: Promotion blocked
- 2: Error

---

## `rollback` — Revert Prompt Alias to Previous Version

**Usage**:
```
uv run python -m eval.pipeline rollback [OPTIONS] PROMPT_NAME
```

**Arguments**:
| Arg | Type | Description |
|-----|------|-------------|
| `PROMPT_NAME` | str | Name of the prompt to roll back |

**Options**:
| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--alias` | str | `production` | Alias to roll back |
| `--reason` | str | (required) | Reason for rollback |
| `--actor` | str | `cli-user` | Actor name for audit log |

**Output**:
```
Rollback: orchestrator-base
============================

Current: @production → v3
Rolling back to: v2

SUCCESS: orchestrator-base @production now points to v2
Reason: "Regression detected in tone eval after v3 promotion"
Audit logged on run: abc123
```

**Exit Codes**:
- 0: Rollback succeeded
- 1: No previous version available
- 2: Error

---

## `run-evals` — Run Eval Suite (Full or Core Subset)

**Usage**:
```
uv run python -m eval.pipeline run-evals [OPTIONS]
```

**Options**:
| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--suite` | str | `core` | Eval suite: `core` (default subset) or `full` (all 19 types) |
| `--verbose` | bool | False | Show per-case details |
| `--check` | bool | True | Run regression check after completion |

**Output**:
```
Running core eval suite (5 types)...

[1/5] quality ............ PASS (90.0%)
[2/5] security ........... PASS (95.0%)
[3/5] tone ............... PASS (85.0%)
[4/5] routing ............ PASS (80.0%)
[5/5] greeting ........... PASS (100.0%)

All 5 eval types complete.

Regression Check (vs. previous baseline):
  No regressions detected. 2 improvements.
```

**Exit Codes**:
- 0: All evals pass, no regressions
- 1: Evals failed or regressions detected
- 2: Error
