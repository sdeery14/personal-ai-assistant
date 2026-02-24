# Quickstart: Prompt Registry

**Feature**: 012-prompt-registry
**Date**: 2026-02-24

## Prerequisites

- Docker services running (API + MLflow):
  ```bash
  docker compose -f docker/docker-compose.mlflow.yml up -d
  docker compose -f docker/docker-compose.api.yml up -d --env-file .env
  ```
- `.env` file with `OPENAI_API_KEY`

## Verify Prompts Are Loaded from Registry

1. Start the API service. Check logs for seed messages:
   ```
   INFO  prompt_seeding_complete  seeded=11  skipped=0
   ```

2. On subsequent restarts, existing prompts are skipped:
   ```
   INFO  prompt_seeding_complete  seeded=0  skipped=11
   ```

3. Send a chat message and verify prompt versions are logged:
   ```
   INFO  agent_created  prompt_versions={"orchestrator-base": 1, "onboarding": 1, ...}
   ```

## Register a New Prompt Version

```python
import mlflow

# Connect to tracking server
mlflow.set_tracking_uri("http://localhost:5001")

# Register an updated prompt
version = mlflow.genai.register_prompt(
    name="orchestrator-base",
    template="You are Alfred, a thoughtful AI assistant...",  # New text
    commit_message="Refined personality instructions"
)
print(f"Created version {version.version}")

# Point experiment alias to new version
mlflow.genai.set_prompt_alias(
    name="orchestrator-base",
    alias="experiment",
    version=version.version
)
```

## Swap Production Prompt

```python
# After validating the experiment prompt via evals:
mlflow.genai.set_prompt_alias(
    name="orchestrator-base",
    alias="production",
    version=2  # Promote experiment to production
)
# Takes effect within PROMPT_CACHE_TTL_SECONDS (default: 300s)
```

## Run Evals with Prompt Lineage

```bash
uv run python -m eval --dataset eval/quality_golden_dataset.json --verbose
```

Check MLflow UI at `http://localhost:5001` — the eval run will show prompt version parameters:
- `prompt.orchestrator-base: v2`
- `prompt.onboarding: v1`
- etc.

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `PROMPT_CACHE_TTL_SECONDS` | 300 | How long loaded prompts are cached (seconds). Set to 0 during development. |
| `PROMPT_ALIAS` | production | Which alias to load prompts from. Set to `experiment` for A/B testing. |

## Rollback

If a new prompt version causes quality issues:

```python
# Revert production alias to previous version
mlflow.genai.set_prompt_alias(
    name="orchestrator-base",
    alias="production",
    version=1  # Previous known-good version
)
```

## Fallback Behavior

If MLflow tracking server is unreachable:
- Startup: Seeding is skipped with a warning log
- Runtime: Bundled default prompts are used (same content as the original hardcoded constants)
- No user-visible errors — the assistant continues to function normally
