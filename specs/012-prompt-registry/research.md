# Research: Prompt Registry

**Feature**: 012-prompt-registry
**Date**: 2026-02-24

## R1: MLflow Prompt Registry API (3.10.0+)

### Decision: Use MLflow's built-in Prompt Registry

**Rationale**: MLflow 3.10.0 (already installed) provides a complete prompt registry with versioning, aliases, template variables, model config, and built-in caching. No external dependencies needed.

**Alternatives considered**:
- Custom PostgreSQL-based prompt store: More control but duplicates MLflow's functionality, requires schema migration, and loses MLflow UI integration.
- File-based prompt storage (YAML/Markdown): Simpler but no versioning, aliases, or eval lineage integration. Would require building all management tooling from scratch.

### Key API Surface

**Registration**:
```python
mlflow.genai.register_prompt(
    name: str,                    # e.g., "orchestrator-base"
    template: str | list[dict],   # Prompt text with {{variables}}
    commit_message: str | None,   # Version description
    tags: dict[str, str] | None,  # Metadata
    model_config: dict | PromptModelConfig | None,
) -> PromptVersion
```
- Auto-increments version (1, 2, 3, ...)
- Creates new prompt if name doesn't exist, new version if it does
- Versions are immutable once created

**Loading**:
```python
mlflow.genai.load_prompt(
    name_or_uri: str,             # "name" or "prompts:/name@alias"
    version: int | None,          # Specific version
    allow_missing: bool = False,  # Return None vs raise
    cache_ttl_seconds: float | None,  # Built-in caching
) -> PromptVersion | None
```
- URI format: `prompts:/name@production`, `prompts:/name/3`
- Built-in cache: alias-based defaults to 60s TTL, version-based has no TTL
- `PromptVersion` has: `.template`, `.version`, `.variables`, `.model_config`, `.format(**kwargs)`

**Aliases**:
```python
mlflow.genai.set_prompt_alias(name, alias, version)
mlflow.genai.delete_prompt_alias(name, alias)
# Load by alias: mlflow.genai.load_prompt("prompts:/name@production")
```

**Tags**:
```python
mlflow.genai.set_prompt_version_tag(name, version, key, value)
```

### Important Discovery: Built-in Caching

MLflow's `load_prompt()` has a `cache_ttl_seconds` parameter that handles caching natively:
- Alias-based loads: default 60s TTL
- Version-based loads: infinite TTL (immutable content)
- `cache_ttl_seconds=0`: bypass cache
- Custom TTL: `cache_ttl_seconds=300` (5 minutes)

**Impact on design**: We do NOT need to build a custom in-memory cache. MLflow's built-in caching satisfies FR-004a. We configure the TTL via an environment variable and pass it to `load_prompt()`.

---

## R2: Current Prompt Architecture

### Decision: Migrate 11 constants from agents.py to registry

**Current state**: All prompts are string constants in `src/services/agents.py` (lines 22–329):

| Constant | Lines | Used By |
|----------|-------|---------|
| MEMORY_SYSTEM_PROMPT | 22–35 | create_memory_agent() |
| MEMORY_WRITE_SYSTEM_PROMPT | 37–76 | create_memory_agent() |
| WEATHER_SYSTEM_PROMPT | 78–91 | create_weather_agent() |
| GRAPH_SYSTEM_PROMPT | 93–133 | create_knowledge_agent() |
| ONBOARDING_SYSTEM_PROMPT | 135–168 | build_orchestrator_instructions() |
| PROACTIVE_GREETING_PROMPT | 170–187 | build_orchestrator_instructions() |
| CALIBRATION_SYSTEM_PROMPT | 189–207 | create_proactive_agent() |
| SCHEDULE_SYSTEM_PROMPT | 209–235 | create_proactive_agent() |
| OBSERVATION_SYSTEM_PROMPT | 237–262 | create_proactive_agent() |
| NOTIFICATION_SYSTEM_PROMPT | 264–287 | create_notification_agent() |
| ORCHESTRATOR_BASE_PROMPT | 293–329 | build_orchestrator_instructions() |

**Assembly pattern**: `build_orchestrator_instructions()` (lines 630–679) composes:
1. `ORCHESTRATOR_BASE_PROMPT` (always)
2. `ONBOARDING_SYSTEM_PROMPT` or `PROACTIVE_GREETING_PROMPT` (conditional)
3. Dynamic routing hints based on specialist availability (code-generated, NOT registered)

**Re-exports**: `chat_service.py` re-exports all 10 prompt constants (excluding ORCHESTRATOR_BASE_PROMPT) for backward compatibility with tests and eval framework.

### Decision: Routing hints remain code-generated

**Rationale**: Routing hints are dynamic fragments based on which specialist agents loaded successfully at runtime. They are not static prompt content and change based on environment (e.g., missing Redis disables weather agent). Registering them would require re-registration on every startup with different tool availability.

---

## R3: Prompt Naming Convention

### Decision: Use lowercase-hyphenated names

MLflow prompt names allow `[a-zA-Z0-9_.-]+`. We'll use lowercase-hyphenated names for consistency:

| Constant | Registry Name |
|----------|---------------|
| ORCHESTRATOR_BASE_PROMPT | `orchestrator-base` |
| ONBOARDING_SYSTEM_PROMPT | `onboarding` |
| PROACTIVE_GREETING_PROMPT | `proactive-greeting` |
| MEMORY_SYSTEM_PROMPT | `memory` |
| MEMORY_WRITE_SYSTEM_PROMPT | `memory-write` |
| WEATHER_SYSTEM_PROMPT | `weather` |
| GRAPH_SYSTEM_PROMPT | `knowledge-graph` |
| CALIBRATION_SYSTEM_PROMPT | `calibration` |
| SCHEDULE_SYSTEM_PROMPT | `schedule` |
| OBSERVATION_SYSTEM_PROMPT | `observation` |
| NOTIFICATION_SYSTEM_PROMPT | `notification` |

**Rationale**: Matches existing branch naming convention. Readable in MLflow UI. Avoids underscores which could confuse with Python naming.

---

## R4: Caching Strategy

### Decision: Use MLflow's built-in cache with configurable TTL

**Approach**: Pass `cache_ttl_seconds` to every `load_prompt()` call. Default 300s (5 minutes) via environment variable `PROMPT_CACHE_TTL_SECONDS`.

**Why 300s default**: Balances responsiveness (alias swaps visible within 5 minutes) with reduced registry load. The system creates agents per-request, so even a 60s TTL could mean hundreds of registry calls per minute under load. 300s is conservative.

**Override for development**: Set `PROMPT_CACHE_TTL_SECONDS=0` to disable caching during prompt iteration.

**Alternatives considered**:
- Custom in-memory dict with threading.Timer: Unnecessary — MLflow already solves this.
- Redis-based prompt cache: Over-engineered for ~11 prompts.

---

## R5: Fallback Strategy

### Decision: Bundled defaults in code, loaded only when registry is unreachable

**Approach**: Move current prompt constants to a `src/prompts/defaults.py` module. The prompt service tries registry first; on failure, returns the bundled default and logs a warning.

**Why keep defaults in code**:
- Ensures the system starts even if MLflow is down
- Serves as the seed content for auto-seeding (FR-005a)
- Provides a code-reviewable reference for prompt content
- Tests can import defaults directly without MLflow

---

## R6: Eval Lineage Integration

### Decision: Log prompt versions as MLflow run parameters

**Approach**: When creating an agent for eval, collect all loaded prompt versions and log them via `mlflow.log_params()`:
```python
mlflow.log_params({
    "prompt.orchestrator-base": "v3",
    "prompt.onboarding": "v2",
    "prompt.memory": "v1",
    ...
})
```

**Why params not tags**: Params are displayed in the MLflow UI's run comparison table, making version differences immediately visible when comparing eval runs.

**Alternatives considered**:
- MLflow tags: Less visible in comparison UI.
- Custom artifact (JSON file): Not queryable/filterable.

---

## R7: Auto-Seeding Strategy

### Decision: Seed during application lifespan startup

**Approach**: During `main.py` lifespan startup (after MLflow connection is confirmed), iterate over all bundled defaults. For each prompt, attempt `load_prompt(name, allow_missing=True)`. If `None`, call `register_prompt()` with the default content and set the `@production` alias on version 1.

**Idempotency**: `allow_missing=True` makes the check safe. Existing prompts are never overwritten.

**Failure handling**: If MLflow is unreachable during seeding, log warning and continue — the fallback mechanism (R5) handles runtime loading.
