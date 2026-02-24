# Internal Contract: Prompt Service

**Feature**: 012-prompt-registry
**Date**: 2026-02-24

## Overview

No new REST API endpoints are introduced. This feature is entirely backend — it changes how prompts are stored and loaded internally. The contract below defines the internal Python service interface.

## Module: `src/services/prompt_service.py`

### `seed_prompts() -> dict[str, int]`

Seeds missing prompts into the MLflow registry from bundled defaults. Called once during application startup.

**Returns**: Dict mapping prompt name to version number for each newly seeded prompt. Empty dict if all prompts already exist.

**Behavior**:
- For each prompt in `PROMPT_DEFAULTS`:
  - Load from registry with `allow_missing=True`
  - If missing: register with default content, set `@production` alias on v1
  - If exists: skip (no overwrite)
- On MLflow connection failure: log warning, return empty dict
- Idempotent: safe to call multiple times

---

### `load_prompt(name: str, alias: str | None = None) -> str`

Loads a prompt's text content from the registry, with fallback to bundled defaults.

**Parameters**:
- `name`: Registry prompt name (e.g., `"orchestrator-base"`)
- `alias`: Optional alias override. Defaults to the configured `PROMPT_ALIAS` setting (default: `"production"`)

**Returns**: Prompt text (string). Never returns None — always falls back to bundled default.

**Behavior**:
- Attempts `mlflow.genai.load_prompt("prompts:/{name}@{alias}", cache_ttl_seconds=settings.prompt_cache_ttl_seconds)`
- On success: returns `prompt_version.template`
- On failure (MlflowException, connection error, timeout): logs warning, returns bundled default from `PROMPT_DEFAULTS[name]`

---

### `load_prompt_version(name: str, alias: str | None = None) -> PromptVersionInfo`

Loads a prompt with full version metadata for eval lineage tracking.

**Parameters**: Same as `load_prompt()`.

**Returns**: `PromptVersionInfo` dataclass:
```python
@dataclass
class PromptVersionInfo:
    name: str           # Registry prompt name
    version: int        # Version number (0 if fallback)
    alias: str          # Alias used to load
    template: str       # Prompt text
    model_config: dict | None  # Associated model parameters
    is_fallback: bool   # True if loaded from bundled defaults
```

---

### `get_active_prompt_versions() -> dict[str, int]`

Returns a dict of all currently loaded prompt names and their version numbers. Used for eval run tagging.

**Returns**: `{"orchestrator-base": 3, "onboarding": 2, ...}`. Version is `0` for any prompt using fallback.

---

### `register_prompt(name: str, template: str, commit_message: str | None = None, model_config: dict | None = None) -> int`

Registers a new version of a prompt in the registry. Used by developers to create new prompt versions.

**Parameters**:
- `name`: Registry prompt name
- `template`: Full prompt text
- `commit_message`: Description of changes
- `model_config`: Optional model parameters

**Returns**: New version number (int).

---

### `set_alias(name: str, alias: str, version: int) -> None`

Points an alias to a specific prompt version.

**Parameters**:
- `name`: Registry prompt name
- `alias`: Alias name (e.g., `"production"`, `"experiment"`)
- `version`: Version number to point to

---

## Module: `src/prompts/defaults.py`

### `PROMPT_DEFAULTS: dict[str, str]`

Dictionary mapping registry prompt names to their bundled default text content. These are the current hardcoded constants moved to a dedicated module.

```python
PROMPT_DEFAULTS = {
    "orchestrator-base": "...",     # Current ORCHESTRATOR_BASE_PROMPT
    "onboarding": "...",            # Current ONBOARDING_SYSTEM_PROMPT
    "proactive-greeting": "...",    # Current PROACTIVE_GREETING_PROMPT
    "memory": "...",                # Current MEMORY_SYSTEM_PROMPT
    "memory-write": "...",          # Current MEMORY_WRITE_SYSTEM_PROMPT
    "weather": "...",               # Current WEATHER_SYSTEM_PROMPT
    "knowledge-graph": "...",       # Current GRAPH_SYSTEM_PROMPT
    "calibration": "...",           # Current CALIBRATION_SYSTEM_PROMPT
    "schedule": "...",              # Current SCHEDULE_SYSTEM_PROMPT
    "observation": "...",           # Current OBSERVATION_SYSTEM_PROMPT
    "notification": "...",          # Current NOTIFICATION_SYSTEM_PROMPT
}
```

### `PROMPT_NAME_MAP: dict[str, str]`

Maps old constant names to registry names for backward compatibility:

```python
PROMPT_NAME_MAP = {
    "ORCHESTRATOR_BASE_PROMPT": "orchestrator-base",
    "ONBOARDING_SYSTEM_PROMPT": "onboarding",
    # ... etc.
}
```

## Integration Points

### Modified: `src/services/agents.py`

- Remove all 11 prompt string constants
- Import `prompt_service.load_prompt()`
- Replace each constant reference with `load_prompt("registry-name")`
- `build_orchestrator_instructions()` calls `load_prompt()` for each component
- Agent factories call `load_prompt()` for specialist prompts

### Modified: `src/services/chat_service.py`

- Remove re-exports of prompt constants
- Add backward-compatible properties or functions that delegate to prompt_service
- Pass prompt version info through to eval tagging

### Modified: `src/main.py`

- Add `prompt_service.seed_prompts()` call during lifespan startup (after MLflow is reachable)

### Modified: `eval/runner.py`

- After agent creation, call `prompt_service.get_active_prompt_versions()`
- Log as `mlflow.log_params({"prompt.{name}": f"v{version}" for name, version in versions.items()})`
