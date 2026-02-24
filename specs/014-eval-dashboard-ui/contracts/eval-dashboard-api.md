# API Contract: Eval Dashboard

**Base Path**: `/admin/evals`
**Auth**: All endpoints require `require_admin` dependency (admin JWT)
**Router File**: `src/api/eval_dashboard.py`

---

## GET /admin/evals/trends

**Description**: Get trend summaries for all eval types (or filtered by eval type).

**Query Parameters**:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| eval_type | str (optional) | null | Filter to a single eval type |
| limit | int | 10 | Max historical runs per eval type |

**Response**: `200 OK`
```json
{
  "summaries": [
    {
      "eval_type": "tone",
      "latest_pass_rate": 0.95,
      "trend_direction": "improving",
      "run_count": 5,
      "points": [
        {
          "run_id": "abc123",
          "timestamp": "2026-02-24T10:00:00Z",
          "eval_type": "tone",
          "pass_rate": 0.90,
          "average_score": 4.2,
          "total_cases": 10,
          "error_cases": 0,
          "prompt_versions": {"orchestrator-base": "v3"},
          "eval_status": "complete"
        }
      ],
      "prompt_changes": [
        {
          "timestamp": "2026-02-24T11:00:00Z",
          "run_id": "def456",
          "prompt_name": "orchestrator-base",
          "from_version": "v2",
          "to_version": "v3"
        }
      ]
    }
  ]
}
```

**Empty State**: `200 OK` with `{"summaries": []}`

**Pipeline Functions Called**:
- `get_eval_experiments()`
- `get_trend_points(experiment_name, eval_type, limit)`
- `build_trend_summary(eval_type, points)`

---

## GET /admin/evals/regressions

**Description**: Get regression check results for all eval types.

**Query Parameters**:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| eval_type | str (optional) | null | Filter to a single eval type |

**Response**: `200 OK`
```json
{
  "reports": [
    {
      "eval_type": "tone",
      "baseline_run_id": "abc123",
      "current_run_id": "def456",
      "baseline_pass_rate": 0.90,
      "current_pass_rate": 0.70,
      "delta_pp": -20.0,
      "threshold": 0.80,
      "verdict": "REGRESSION",
      "changed_prompts": [
        {
          "timestamp": "2026-02-24T12:00:00Z",
          "run_id": "def456",
          "prompt_name": "orchestrator-base",
          "from_version": "v2",
          "to_version": "v3"
        }
      ],
      "baseline_timestamp": "2026-02-24T10:00:00Z",
      "current_timestamp": "2026-02-24T12:00:00Z"
    }
  ],
  "has_regressions": true
}
```

**Empty State**: `200 OK` with `{"reports": [], "has_regressions": false}`

**Pipeline Functions Called**:
- `check_all_regressions(eval_type_filter=eval_type)`

---

## GET /admin/evals/prompts

**Description**: List all registered prompts for promotion/rollback selection.

**Response**: `200 OK`
```json
{
  "prompts": [
    {"name": "orchestrator-base", "current_version": 3},
    {"name": "onboarding", "current_version": 2},
    {"name": "guardrails-input", "current_version": 1}
  ]
}
```

**Pipeline Functions Called**:
- `get_active_prompt_versions()` from prompt_service

---

## POST /admin/evals/promote/check

**Description**: Run the promotion gate check for a prompt (does NOT execute the promotion).

**Request Body**:
```json
{
  "prompt_name": "orchestrator-base",
  "from_alias": "experiment",
  "to_alias": "production",
  "version": null
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| prompt_name | str (required) | — | Prompt registry name |
| from_alias | str | "experiment" | Source alias |
| to_alias | str | "production" | Target alias |
| version | int (optional) | null | Specific version (null = current) |

**Response**: `200 OK`
```json
{
  "allowed": true,
  "prompt_name": "orchestrator-base",
  "from_alias": "experiment",
  "to_alias": "production",
  "version": 3,
  "eval_results": [
    {"eval_type": "tone", "pass_rate": 0.95, "threshold": 0.80, "passed": true, "run_id": "run1"},
    {"eval_type": "routing", "pass_rate": 0.85, "threshold": 0.80, "passed": true, "run_id": "run2"}
  ],
  "blocking_evals": [],
  "justifying_run_ids": ["run1", "run2"]
}
```

**Pipeline Functions Called**:
- `check_promotion_gate(prompt_name, from_alias, to_alias, version)`

---

## POST /admin/evals/promote/execute

**Description**: Execute a prompt promotion (optionally forced).

**Request Body**:
```json
{
  "prompt_name": "orchestrator-base",
  "to_alias": "production",
  "version": 3,
  "force": false,
  "reason": "All evals pass"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| prompt_name | str (required) | — | Prompt registry name |
| to_alias | str | "production" | Target alias |
| version | int (required) | — | Version to promote |
| force | bool | false | Bypass gate check |
| reason | str | "" | Reason for promotion (required if force=true) |

**Response**: `200 OK`
```json
{
  "action": "promote",
  "prompt_name": "orchestrator-base",
  "from_version": 2,
  "to_version": 3,
  "alias": "production",
  "timestamp": "2026-02-24T14:00:00Z",
  "actor": "admin-user",
  "reason": "All evals pass"
}
```

**Error Responses**:
- `403 Forbidden`: Gate check failed and force=false
- `400 Bad Request`: Missing required fields

**Pipeline Functions Called**:
- `check_promotion_gate(prompt_name, ...)` (unless force=true)
- `execute_promotion(prompt_name, to_alias, version, actor, justifying_run_ids)`

---

## POST /admin/evals/run

**Description**: Start an eval suite run. Returns immediately with a job ID.

**Request Body**:
```json
{
  "suite": "core"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| suite | str | "core" | "core" or "full" |

**Response**: `202 Accepted`
```json
{
  "run_id": "job-uuid-123",
  "suite": "core",
  "status": "running",
  "total": 5,
  "completed": 0,
  "results": [],
  "regression_reports": null,
  "started_at": "2026-02-24T14:30:00Z",
  "finished_at": null
}
```

**Error Responses**:
- `409 Conflict`: An eval suite run is already in progress

**Pipeline Functions Called**:
- `run_eval_suite(suite, progress_callback=...)` (in background task)
- `check_all_regressions()` (after suite completes)

---

## GET /admin/evals/run/status

**Description**: Get the status of the current or most recent eval suite run.

**Response**: `200 OK`
```json
{
  "run_id": "job-uuid-123",
  "suite": "core",
  "status": "completed",
  "total": 5,
  "completed": 5,
  "results": [
    {"dataset_path": "eval/golden_dataset.json", "exit_code": 0, "passed": true},
    {"dataset_path": "eval/security_golden_dataset.json", "exit_code": 0, "passed": true}
  ],
  "regression_reports": [],
  "started_at": "2026-02-24T14:30:00Z",
  "finished_at": "2026-02-24T14:35:00Z"
}
```

**Empty State**: `200 OK` with `null` (no run has been started yet)

---

## GET /admin/evals/rollback/info

**Description**: Get rollback information for a prompt (current and previous version).

**Query Parameters**:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| prompt_name | str (required) | — | Prompt registry name |
| alias | str | "production" | Alias to roll back |

**Response**: `200 OK`
```json
{
  "prompt_name": "orchestrator-base",
  "current_version": 3,
  "previous_version": 2,
  "alias": "production"
}
```

**When no previous version**:
```json
{
  "prompt_name": "orchestrator-base",
  "current_version": 1,
  "previous_version": null,
  "alias": "production"
}
```

**Pipeline Functions Called**:
- `load_prompt_version(prompt_name, alias)` from prompt_service
- `find_previous_version(prompt_name, alias)`

---

## POST /admin/evals/rollback/execute

**Description**: Execute a prompt rollback.

**Request Body**:
```json
{
  "prompt_name": "orchestrator-base",
  "alias": "production",
  "previous_version": 2,
  "reason": "Tone eval regressed after v3"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| prompt_name | str (required) | — | Prompt registry name |
| alias | str | "production" | Alias to roll back |
| previous_version | int (required) | — | Version to revert to |
| reason | str (required) | — | Reason for rollback |

**Response**: `200 OK`
```json
{
  "action": "rollback",
  "prompt_name": "orchestrator-base",
  "from_version": 3,
  "to_version": 2,
  "alias": "production",
  "timestamp": "2026-02-24T15:00:00Z",
  "actor": "admin-user",
  "reason": "Tone eval regressed after v3"
}
```

**Error Responses**:
- `400 Bad Request`: No previous version available or invalid parameters

**Pipeline Functions Called**:
- `execute_rollback(prompt_name, alias, previous_version, reason, actor)`
