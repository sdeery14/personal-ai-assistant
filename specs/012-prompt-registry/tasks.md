# Tasks: Prompt Registry

**Input**: Design documents from `/specs/012-prompt-registry/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/prompt-service.md

**Tests**: Included — constitution principle II (Evaluation-First Behavior) requires TDD.

**Organization**: Tasks grouped by user story. US1 and US2 are both P1 but separated because US1 (seed + register + eval lineage) creates the registry content while US2 (load + migrate + fallback) consumes it. US2 depends on US1 for seeded content but can operate via fallback independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new package structure, defaults data, and configuration settings that all user stories depend on.

- [X] T001 Create prompt package with init module in src/prompts/__init__.py
- [X] T002 Create bundled defaults module in src/prompts/defaults.py — move all 11 prompt constants from src/services/agents.py into PROMPT_DEFAULTS dict (mapping registry names to prompt text) and PROMPT_NAME_MAP dict (mapping old constant names to registry names). Registry names: orchestrator-base, onboarding, proactive-greeting, memory, memory-write, weather, knowledge-graph, calibration, schedule, observation, notification.
- [X] T003 Add prompt_cache_ttl_seconds (int, default 300) and prompt_alias (str, default "production") settings to src/config.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the prompt service skeleton and validation tests. MUST complete before user story work begins.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Create src/services/prompt_service.py with PromptVersionInfo dataclass (name, version, alias, template, model_config, is_fallback) and module-level logger. Import PROMPT_DEFAULTS from src/prompts/defaults.py and settings from src/config.py.
- [X] T005 [P] Create tests/unit/test_prompt_defaults.py — validate all 11 prompt names exist in PROMPT_DEFAULTS, all values are non-empty strings, PROMPT_NAME_MAP covers all 11 constants, and default content matches the current hardcoded constants in src/services/agents.py (import both and compare).

**Checkpoint**: Foundation ready — prompt defaults validated, service skeleton in place.

---

## Phase 3: User Story 1 — Version and Track Prompt Changes (Priority: P1) MVP

**Goal**: Prompts are stored as versioned artifacts in MLflow's registry. Eval runs are tagged with prompt versions for lineage tracking.

**Independent Test**: Register a prompt, create a new version, verify both versions are retrievable. Run an eval and verify prompt version params appear in MLflow UI.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T006 [P] [US1] Write unit tests for seed_prompts() in tests/unit/test_prompt_service.py — mock mlflow.genai.load_prompt (return None for missing, PromptVersion for existing), mock mlflow.genai.register_prompt and mlflow.genai.set_prompt_alias. Test: seeds all 11 when empty, skips existing, handles MLflow connection failure gracefully (returns empty dict), idempotent on repeated calls.
- [X] T007 [P] [US1] Write unit tests for register_prompt() and get_active_prompt_versions() in tests/unit/test_prompt_service.py — mock mlflow.genai.register_prompt. Test: returns new version number, passes commit_message and model_config through. Test get_active_prompt_versions returns dict of loaded versions.

### Implementation for User Story 1

- [X] T008 [US1] Implement seed_prompts() in src/services/prompt_service.py — iterate PROMPT_DEFAULTS, call mlflow.genai.load_prompt(name, allow_missing=True), if None call mlflow.genai.register_prompt() then mlflow.genai.set_prompt_alias(name, alias="production", version=1). Wrap in try/except for MLflow connection errors. Log seeded count and skipped count via structured logger.
- [X] T009 [US1] Implement register_prompt() in src/services/prompt_service.py — call mlflow.genai.register_prompt(name, template, commit_message, model_config), return version.version. Implement get_active_prompt_versions() — maintain module-level dict tracking loaded versions, return copy.
- [X] T010 [US1] Add seed_prompts() call to src/main.py lifespan startup — call after existing initialization steps (database, Redis, scheduler). Log results. Handle failure gracefully (log warning, continue startup).
- [X] T011 [US1] Add prompt version tagging to eval/runner.py — after agent creation in each eval runner function, call prompt_service.get_active_prompt_versions() and log as mlflow.log_params({"prompt.{name}": f"v{version}" for name, version in versions.items()}). Add --prompt-alias CLI flag to eval/__main__.py that sets the PROMPT_ALIAS config for the eval run.

**Checkpoint**: Prompts are seeded into MLflow registry on startup. Eval runs show prompt versions in MLflow UI params.

---

## Phase 4: User Story 2 — Load Prompts at Runtime (Priority: P1)

**Goal**: All agent factories load prompts from the registry instead of hardcoded constants. Fallback to bundled defaults when registry is unavailable. Behavior is identical to pre-migration.

**Independent Test**: Start the agent, send a message, verify response quality matches baseline. Stop MLflow, restart agent, verify fallback defaults are used with warning logs.

**Dependencies**: US1 (seed_prompts must run first to populate registry, but fallback allows independent operation)

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T012 [P] [US2] Write unit tests for load_prompt() in tests/unit/test_prompt_service.py — mock mlflow.genai.load_prompt. Test: returns template text on success, returns bundled default on MlflowException, returns bundled default on connection error, passes cache_ttl_seconds from settings, constructs correct URI format "prompts:/{name}@{alias}".
- [X] T013 [P] [US2] Write unit tests for load_prompt_version() in tests/unit/test_prompt_service.py — test: returns PromptVersionInfo with correct fields, is_fallback=False on success, is_fallback=True on failure with version=0.

### Implementation for User Story 2

- [X] T014 [US2] Implement load_prompt() in src/services/prompt_service.py — call mlflow.genai.load_prompt(f"prompts:/{name}@{alias}", cache_ttl_seconds=settings.prompt_cache_ttl_seconds). On success return prompt_version.template and update _active_versions dict. On failure (MlflowException, ConnectionError, Exception) log warning and return PROMPT_DEFAULTS[name].
- [X] T015 [US2] Implement load_prompt_version() in src/services/prompt_service.py — same as load_prompt but returns PromptVersionInfo dataclass with full metadata (version number, alias, model_config, is_fallback flag).
- [X] T016 [US2] Migrate build_orchestrator_instructions() in src/services/agents.py — replace ORCHESTRATOR_BASE_PROMPT with load_prompt("orchestrator-base"), replace ONBOARDING_SYSTEM_PROMPT with load_prompt("onboarding"), replace PROACTIVE_GREETING_PROMPT with load_prompt("proactive-greeting"). Keep dynamic routing hint assembly logic unchanged (code-generated, not registered).
- [X] T017 [US2] Migrate all 5 specialist agent factories in src/services/agents.py — create_memory_agent: replace MEMORY_SYSTEM_PROMPT and MEMORY_WRITE_SYSTEM_PROMPT with load_prompt("memory") and load_prompt("memory-write"). create_knowledge_agent: replace GRAPH_SYSTEM_PROMPT with load_prompt("knowledge-graph"). create_weather_agent: replace WEATHER_SYSTEM_PROMPT with load_prompt("weather"). create_proactive_agent: replace OBSERVATION_SYSTEM_PROMPT, CALIBRATION_SYSTEM_PROMPT, SCHEDULE_SYSTEM_PROMPT with load_prompt() calls. create_notification_agent: replace NOTIFICATION_SYSTEM_PROMPT with load_prompt("notification").
- [X] T018 [US2] Remove all 11 hardcoded prompt string constants from src/services/agents.py (lines ~22–329). Verify no remaining references to the old constant names within agents.py.
- [X] T019 [US2] Update src/services/chat_service.py — replace direct constant re-exports with functions or properties that delegate to prompt_service.load_prompt(). Maintain the same public names (MEMORY_SYSTEM_PROMPT, etc.) so existing test imports continue to work.
- [X] T020 [US2] Add structured logging for prompt loading in src/services/prompt_service.py — log at INFO level on each load_prompt call: prompt name, version loaded, alias used, is_fallback status, correlation_id (if available). Log at WARNING level when falling back to bundled defaults.

**Checkpoint**: All agents load prompts from registry. Fallback works when MLflow is down. Existing tests pass. Agent behavior unchanged.

---

## Phase 5: User Story 3 — Swap Prompts Without Code Changes (Priority: P2)

**Goal**: Developers can swap prompts by updating aliases. Changes take effect within the cache refresh interval without code changes or restarts.

**Independent Test**: Register two versions of a prompt, assign to different aliases, verify each alias resolves to its version. Update alias, wait for cache refresh, verify new version is loaded.

**Dependencies**: US1 (prompts registered), US2 (load_prompt uses aliases)

### Tests for User Story 3

- [X] T021 [P] [US3] Write unit tests for set_alias() in tests/unit/test_prompt_service.py — mock mlflow.genai.set_prompt_alias. Test: calls MLflow with correct name, alias, version. Test: alias-based loading returns different content after alias is re-pointed (mock two different PromptVersion returns).

### Implementation for User Story 3

- [X] T022 [US3] Implement set_alias() in src/services/prompt_service.py — call mlflow.genai.set_prompt_alias(name, alias=alias, version=version). Log alias update at INFO level.

**Checkpoint**: Alias swapping works. Combined with MLflow's built-in cache TTL (configurable via PROMPT_CACHE_TTL_SECONDS), prompts refresh within the configured interval.

---

## Phase 6: User Story 4 — Store Model Configuration Alongside Prompts (Priority: P3)

**Goal**: Prompts can be registered with model parameters (temperature, max_tokens, etc.) that are returned alongside the prompt text when loaded.

**Independent Test**: Register a prompt with model_config, load it, verify model_config is returned in PromptVersionInfo.

**Dependencies**: US1 (register_prompt), US2 (load_prompt_version)

### Tests for User Story 4

- [X] T023 [P] [US4] Write unit tests for model config support in tests/unit/test_prompt_service.py — test: register_prompt passes model_config dict through to mlflow.genai.register_prompt. Test: load_prompt_version returns model_config from PromptVersion.model_config. Test: seed_prompts works with and without model_config (currently seeds without).

### Implementation for User Story 4

- [X] T024 [US4] Verify model_config passthrough in src/services/prompt_service.py — register_prompt() already accepts model_config parameter (T009). Verify load_prompt_version() reads .model_config from the returned PromptVersion and includes it in PromptVersionInfo. No code changes expected if T009 and T015 implemented correctly — this task confirms and adds any missing wiring.

**Checkpoint**: Model config stored and retrieved alongside prompts. All four user stories independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Verify the complete migration, ensure no regressions, validate end-to-end scenarios.

- [X] T025 Run existing unit test suite (uv run pytest tests/unit/ -v) and verify all tests pass with migrated prompts
- [ ] T026 Run full eval suite (uv run python -m eval --verbose) and compare results to pre-migration baseline — verify SC-005 (no quality regression)
- [ ] T027 Verify fallback behavior — stop MLflow tracking server, start API, confirm agent responds using bundled defaults with WARNING logs (SC-006)
- [ ] T028 Verify quickstart.md scenarios end-to-end — seed on startup, prompt version logging, register new version, swap alias, eval lineage tagging

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — creates registry content
- **US2 (Phase 4)**: Depends on Phase 2. Functionally depends on US1 (seeded prompts) but fallback enables independent testing
- **US3 (Phase 5)**: Depends on US1 (registered prompts) and US2 (alias-based loading)
- **US4 (Phase 6)**: Depends on US1 (register_prompt) and US2 (load_prompt_version)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2. No dependencies on other stories.
- **US2 (P1)**: Can start after Phase 2. Benefits from US1 (seeded prompts) but works via fallback independently.
- **US3 (P2)**: Depends on US1 and US2 — aliases require prompts to be registered and loaded.
- **US4 (P3)**: Depends on US1 and US2 — model config is part of registration and loading.

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Service functions before integration points (main.py, agents.py, eval/runner.py)
- Core implementation before observability/logging
- Story complete before moving to next priority

### Parallel Opportunities

- T002 and T003 can run in parallel (different files)
- T004 and T005 can run in parallel (different files)
- T006 and T007 can run in parallel (same file but different test classes)
- T012 and T013 can run in parallel (same file but different test classes)
- T016 and T017 involve the same file (agents.py) — run sequentially
- T021 and T023 can run in parallel (different test classes)

---

## Parallel Example: User Story 2

```
# After US1 is complete, launch US2 tests in parallel:
Task T012: "Unit tests for load_prompt() in tests/unit/test_prompt_service.py"
Task T013: "Unit tests for load_prompt_version() in tests/unit/test_prompt_service.py"

# Then implement sequentially (same files, dependencies):
Task T014: "Implement load_prompt() in src/services/prompt_service.py"
Task T015: "Implement load_prompt_version() in src/services/prompt_service.py"
Task T016: "Migrate build_orchestrator_instructions() in src/services/agents.py"
Task T017: "Migrate specialist agent factories in src/services/agents.py"
Task T018: "Remove hardcoded constants from src/services/agents.py"
Task T019: "Update chat_service.py re-exports"
Task T020: "Add structured logging for prompt loading"
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T005)
3. Complete Phase 3: US1 — Version and Track (T006–T011)
4. Complete Phase 4: US2 — Load at Runtime (T012–T020)
5. **STOP and VALIDATE**: Run existing tests, verify agent works identically to pre-migration
6. This delivers SC-001 through SC-003 and SC-005 through SC-006

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 → Prompts seeded, eval lineage working → Validate
3. US2 → Agents load from registry, fallback works → Validate (MVP!)
4. US3 → Alias swapping without restarts → Validate
5. US4 → Model config alongside prompts → Validate
6. Polish → Full regression test, end-to-end verification

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- All MLflow calls in unit tests MUST be mocked (no real MLflow server in unit tests)
- Existing eval tests are the regression suite for SC-005 — run them post-migration
- The prompt constants remain in src/prompts/defaults.py as fallback — they are NOT deleted from the codebase, just moved from agents.py
- chat_service.py re-exports must maintain backward compatibility for test imports
