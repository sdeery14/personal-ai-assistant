# Research: Eval Dashboard & Regression Pipeline

**Feature**: 013-eval-pipeline
**Date**: 2026-02-24

## R1: MLflow Query APIs for Trend Aggregation

**Decision**: Use `mlflow.search_runs()` with experiment name filtering to aggregate eval results across runs.

**Rationale**: `search_runs()` returns a pandas DataFrame with all metrics, params, and tags — ideal for trend computation. Filter by experiment name (one per eval type) and sort by `start_time`. The `MlflowClient` class provides lower-level access for tagging and experiment listing.

**Key APIs**:
- `mlflow.search_runs(experiment_names=[...])` → DataFrame with columns: `run_id`, `start_time`, `metrics.*`, `params.*`, `tags.*`
- `mlflow.search_experiments()` → list of all experiments
- `MlflowClient().set_tag(run_id, key, value)` → add tags post-run (for audit records)
- `MlflowClient().get_run(run_id)` → get full run details
- `mlflow.genai.set_prompt_alias(name, alias, version)` → alias management for promotion/rollback

**Alternatives Considered**:
- Direct PostgreSQL queries against MLflow backend store — rejected; tightly coupled to MLflow internals, breaks on upgrades
- MLflow REST API — viable but `search_runs()` Python API is simpler and returns DataFrames directly

## R2: Experiment Naming Convention

**Decision**: Eval experiments use the pattern `{base_name}-{eval_type_suffix}` where base name is configured via `EvalSettings.mlflow_experiment_name` (default: `personal-ai-assistant-eval`).

**Rationale**: All 19 eval types already follow this convention consistently. The pipeline can discover experiments by prefix match using `mlflow.search_experiments()`.

**Current Experiments** (17 unique suffixes):
| Suffix | Eval Type | Dataset |
|--------|-----------|---------|
| (none) | quality + security | golden_dataset.json, security_golden_dataset.json |
| -memory | memory retrieval | memory_golden_dataset.json |
| -memory-write | memory write | memory_write_golden_dataset.json |
| -weather | weather tool | weather_golden_dataset.json |
| -graph-extraction | graph extraction | graph_extraction_golden_dataset.json |
| -onboarding | onboarding flow | onboarding_golden_dataset.json |
| -tone | tone & personality | tone_golden_dataset.json |
| -greeting | returning greeting | returning_greeting_golden_dataset.json |
| -routing | orchestrator routing | routing_golden_dataset.json |
| -memory-informed | memory-informed | memory_informed_golden_dataset.json |
| -multi-cap | multi-capability | multi_cap_golden_dataset.json |
| -notification-judgment | notification judgment | notification_judgment_golden_dataset.json |
| -error-recovery | error recovery | error_recovery_golden_dataset.json |
| -schedule-cron | schedule cron | schedule_cron_golden_dataset.json |
| -knowledge-connections | knowledge connections | knowledge_connections_golden_dataset.json |
| -contradiction | contradiction handling | contradiction_handling_golden_dataset.json |
| -long-conversation | long conversation | long_conversation_golden_dataset.json |

Note: `proactive_golden_dataset.json` exists but has no dedicated experiment suffix discovered in runner.py.

## R3: Metrics Storage Patterns

**Decision**: Reuse existing metric names logged by eval runners. The primary aggregation metric is `pass_rate` (float 0.0-1.0), with `average_score` as secondary.

**Rationale**: All eval types log consistent core metrics via `mlflow.log_metrics()`: `total_cases`, `passed_cases`, `failed_cases`, `error_cases`, `pass_rate`, `average_score`, `overall_passed`. Specialized evals add domain-specific metrics (e.g., `block_rate`, `entity_precision`).

**Metric Access Pattern**:
```python
runs = mlflow.search_runs(
    experiment_names=["personal-ai-assistant-eval-tone"],
    filter_string="attributes.status = 'FINISHED'",
    order_by=["start_time DESC"],
)
# runs["metrics.pass_rate"], runs["metrics.average_score"], etc.
```

## R4: Prompt Version Tracking

**Decision**: Prompt versions are already logged as MLflow run parameters with naming convention `prompt.<name>: v<version>` (e.g., `prompt.orchestrator-base: v2`).

**Rationale**: The `_log_prompt_versions()` function in `eval/runner.py` reads from `prompt_service.get_active_prompt_versions()` and logs all active prompts as params. This enables detecting which prompts changed between runs by comparing `params.prompt.*` columns in the search_runs DataFrame.

**Implementation Note**: Prompt versions are only logged for eval types that invoke the agent (not memory-retrieval-only evals). For regression comparison, only compare prompt params that exist in both runs.

## R5: Prompt Alias Management for Promotion/Rollback

**Decision**: Use existing `prompt_service.set_alias()` for promotion and rollback. Alias swapping is already implemented in Feature 012.

**Rationale**: `set_alias(name, "production", version)` atomically re-points the alias. For rollback, we need to determine the previous version, which can be read from the previous eval run's `params.prompt.<name>` values.

**Key Functions**:
- `prompt_service.set_alias(name, alias, version)` → point alias to version
- `prompt_service.load_prompt_version(name, alias)` → get current version info
- `mlflow.genai.set_prompt_alias(name, alias, version)` → low-level MLflow call (used by set_alias)

## R6: Configurable Eval Subsets

**Decision**: Define eval subsets as lists of dataset paths in a configuration file. Default "core" subset includes P1 behavioral evals. Full suite includes all 19 datasets.

**Rationale**: Some evals are slow/expensive (onboarding, multi-cap require real agent calls). A core subset enables fast feedback on prompt changes while the full suite runs before promotion.

**Proposed Core Subset** (fast, high-signal evals):
- quality (golden_dataset.json)
- security (security_golden_dataset.json)
- tone (tone_golden_dataset.json)
- routing (routing_golden_dataset.json)
- greeting (returning_greeting_golden_dataset.json)

## R7: Audit Record Storage via MLflow Tags

**Decision**: Store promotion/rollback audit records as tags on the MLflow eval run(s) that justified the action.

**Rationale**: Tags are the only mutable metadata on completed MLflow runs. Using `MlflowClient().set_tag(run_id, key, value)` allows post-hoc annotation. Tag keys use a namespace prefix: `audit.*`.

**Tag Schema**:
- `audit.action`: `promote` or `rollback`
- `audit.prompt_name`: name of the prompt being promoted/rolled back
- `audit.from_version`: previous version number
- `audit.to_version`: new version number
- `audit.alias`: alias being changed (e.g., `production`)
- `audit.timestamp`: ISO 8601 timestamp
- `audit.actor`: identifier of who performed the action (e.g., `cli-user`)
- `audit.reason`: free-text reason (for rollbacks, includes regression details)

## R8: Partial Eval Failure Handling

**Decision**: Mark runs with `status` tag indicating completeness. Only runs with `tags.eval_status = "complete"` are used as baselines.

**Rationale**: MLflow run status (`FINISHED`, `FAILED`) covers execution-level failures but not partial eval failures (e.g., 3/10 cases errored due to API outage). Adding a custom `eval_status` tag allows finer-grained filtering.

**Tags**:
- `eval_status`: `complete` (all cases ran), `partial` (some errors), `error` (run failed)
- Baseline selection: `filter_string="tags.eval_status = 'complete'"`
