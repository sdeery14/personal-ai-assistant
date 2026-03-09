# API Contracts: Unified Eval Navigation

## New Endpoints

All endpoints added to the existing `eval_explorer` router under `/admin/evals/explorer/`.

### GET /admin/evals/explorer/agents

List all agent versions (LoggedModels) with git metadata and aggregate quality scores.

**Query Parameters**: None

**Response** `200 OK`:
```json
{
  "agents": [
    {
      "model_id": "m-074689226d3b40bf",
      "name": "personal-ai-assistant-agent",
      "git_branch": "main",
      "git_commit": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
      "git_commit_short": "a1b2c3d",
      "git_dirty": false,
      "creation_timestamp": "2026-03-08T12:00:00Z",
      "aggregate_quality": 4.2,
      "experiment_count": 15,
      "total_traces": 342
    }
  ]
}
```

**Error Response** `500 Internal Server Error`:
```json
{
  "detail": "Failed to fetch agent versions: <error message>"
}
```

### GET /admin/evals/explorer/agents/{model_id}

Get detailed information for a single agent version including per-experiment results.

**Path Parameters**:
- `model_id` (string, required): The MLflow LoggedModel ID

**Response** `200 OK`:
```json
{
  "model_id": "m-074689226d3b40bf",
  "name": "personal-ai-assistant-agent",
  "git_branch": "main",
  "git_commit": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
  "git_commit_short": "a1b2c3d",
  "git_dirty": false,
  "git_diff": "",
  "git_repo_url": "https://github.com/user/repo.git",
  "creation_timestamp": "2026-03-08T12:00:00Z",
  "aggregate_quality": 4.2,
  "experiment_results": [
    {
      "experiment_name": "personal-ai-assistant-eval",
      "experiment_id": "1",
      "eval_type": "quality",
      "run_count": 3,
      "pass_rate": 0.85,
      "average_quality": 4.3,
      "latest_run_id": "abc123def456"
    }
  ],
  "total_traces": 342
}
```

**Error Response** `404 Not Found`:
```json
{
  "detail": "Agent version not found: <model_id>"
}
```

## Existing Endpoints (Unchanged)

All existing endpoints from `eval_dashboard.py` and `eval_explorer.py` remain unchanged:

### eval_dashboard.py
- `GET /admin/evals/trends`
- `GET /admin/evals/runs/{run_id}/detail`
- `GET /admin/evals/regressions`
- `GET /admin/evals/prompts`
- `POST /admin/evals/promote/check`
- `POST /admin/evals/promote/execute`
- `POST /admin/evals/run`
- `GET /admin/evals/run/status`
- `GET /admin/evals/rollback/info`
- `POST /admin/evals/rollback/execute`

### eval_explorer.py
- `GET /admin/evals/explorer/experiments`
- `GET /admin/evals/explorer/experiments/{experiment_id}/runs`
- `GET /admin/evals/explorer/runs/{run_id}/traces`
- `GET /admin/evals/explorer/trends/quality`
- `GET /admin/evals/explorer/datasets`
- `GET /admin/evals/explorer/datasets/{dataset_name}`

## Pydantic Response Models (New)

### AgentVersionSummary
```python
class AgentVersionSummary(BaseModel):
    model_id: str
    name: str
    git_branch: str
    git_commit: str
    git_commit_short: str
    git_dirty: bool
    creation_timestamp: str  # ISO 8601
    aggregate_quality: float | None  # None if no quality data
    experiment_count: int
    total_traces: int
```

### ExperimentResult
```python
class ExperimentResult(BaseModel):
    experiment_name: str
    experiment_id: str
    eval_type: str
    run_count: int
    pass_rate: float | None
    average_quality: float | None
    latest_run_id: str | None
```

### AgentVersionDetail
```python
class AgentVersionDetail(BaseModel):
    model_id: str
    name: str
    git_branch: str
    git_commit: str
    git_commit_short: str
    git_dirty: bool
    git_diff: str
    git_repo_url: str
    creation_timestamp: str  # ISO 8601
    aggregate_quality: float | None
    experiment_results: list[ExperimentResult]
    total_traces: int
```

### AgentVersionsResponse
```python
class AgentVersionsResponse(BaseModel):
    agents: list[AgentVersionSummary]
```
