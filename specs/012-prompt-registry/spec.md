# Feature Specification: Prompt Registry

**Feature Branch**: `012-prompt-registry`
**Created**: 2026-02-24
**Status**: Draft
**Input**: User description: "Feature 012 – Prompt Registry from the vision.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Version and Track Prompt Changes (Priority: P1)

A developer changes the wording of the orchestrator's system prompt to improve response quality. Instead of editing a hardcoded string constant and losing the previous version, they register the new prompt as a versioned artifact. Both the old and new versions are preserved with full diff history. When they later run the evaluation suite, the eval results are tagged with the exact prompt versions used, so they can trace any quality change back to the specific prompt edit that caused it.

**Why this priority**: Without versioning, prompt changes are invisible — there is no way to correlate behavior changes with prompt edits. This is the core value proposition: closing the loop between "I changed a prompt" and "the agent got better/worse."

**Independent Test**: Can be fully tested by registering a prompt, creating a new version, and verifying both versions are retrievable with their content and metadata. Delivers traceability for every prompt change.

**Acceptance Scenarios**:

1. **Given** a system prompt exists as a hardcoded constant, **When** the developer migrates it to the prompt registry, **Then** the prompt is stored as version 1 with its full text and metadata preserved.
2. **Given** a prompt is registered at version 1, **When** the developer registers a modified version, **Then** version 2 is created and version 1 remains accessible and unchanged.
3. **Given** an evaluation run executes against the agent, **When** the run completes, **Then** the eval results are tagged with the specific prompt versions that were active during the run.
4. **Given** two eval runs used different prompt versions, **When** the developer compares results, **Then** they can identify which prompt version was used in each run.

---

### User Story 2 - Load Prompts at Runtime (Priority: P1)

The assistant starts up and creates its agents (orchestrator, memory specialist, knowledge specialist, etc.). Instead of reading prompt text from Python string constants, each agent loads its system prompt from the prompt registry using an alias (e.g., `@production`). The assistant behaves identically to before — same prompts, same behavior — but the prompts are now managed artifacts rather than embedded code.

**Why this priority**: This is the mechanical prerequisite for all other prompt registry benefits. Until prompts are loaded from the registry at runtime, versioning and A/B testing have no effect on the live system.

**Independent Test**: Can be tested by starting the agent with registry-loaded prompts and verifying identical behavior to the hardcoded-prompt baseline. Delivers decoupling of prompt content from application code.

**Acceptance Scenarios**:

1. **Given** all prompts are registered in the prompt registry, **When** the agent starts up, **Then** each specialist agent loads its system prompt from the registry rather than from a Python constant.
2. **Given** a prompt is loaded from the registry, **When** the agent processes a user message, **Then** the response quality is indistinguishable from the hardcoded-prompt baseline.
3. **Given** the prompt registry is unavailable at startup, **When** the agent attempts to load prompts, **Then** the system falls back to bundled default prompts and logs a warning.

---

### User Story 3 - Swap Prompts Without Code Changes (Priority: P2)

A developer wants to test a new version of the onboarding prompt without deploying new code. They register the experimental prompt as a new version and point the `@experiment` alias to it, while `@production` continues pointing to the current proven version. They can switch the live system to use the experimental prompt by updating the alias — no code change, no redeployment needed. If the experiment degrades quality, they revert by pointing `@production` back to the previous version.

**Why this priority**: Alias-based swapping enables rapid prompt iteration and safe rollback. It builds on P1 (versioning + runtime loading) and unlocks the experimentation workflow.

**Independent Test**: Can be tested by creating two prompt versions, assigning them to different aliases, switching aliases, and verifying the agent uses the newly-pointed prompt. Delivers zero-downtime prompt updates.

**Acceptance Scenarios**:

1. **Given** a prompt has version 1 aliased as `@production`, **When** the developer creates version 2 and aliases it as `@experiment`, **Then** both aliases resolve to their respective versions simultaneously.
2. **Given** `@production` points to version 1, **When** the developer updates `@production` to point to version 2, **Then** the agent uses version 2 within the cache refresh interval without any code change or restart.
3. **Given** an experimental prompt causes quality degradation, **When** the developer reverts the alias to the previous version, **Then** the agent uses the restored prompt within the cache refresh interval.

---

### User Story 4 - Store Model Configuration Alongside Prompts (Priority: P3)

A developer registers a prompt along with its intended model parameters (e.g., temperature, max tokens). When the agent loads this prompt, it also receives the associated model configuration. This ensures that a prompt is always used with the parameters it was tuned for, preventing the common mistake of testing a prompt with one temperature and deploying it with another.

**Why this priority**: Model parameters significantly affect output quality but are often managed separately from prompts. Co-locating them prevents configuration drift. This is additive to the core versioning and loading functionality.

**Independent Test**: Can be tested by registering a prompt with model parameters and verifying the parameters are returned when the prompt is loaded. Delivers reproducible prompt+config bundles.

**Acceptance Scenarios**:

1. **Given** a developer registers a prompt with specific model parameters, **When** the prompt is loaded from the registry, **Then** the model parameters are returned alongside the prompt text.
2. **Given** a prompt has model parameters stored, **When** a new version is created with different parameters, **Then** each version retains its own parameter set independently.

---

### Edge Cases

- What happens when a prompt alias references a version that has been deleted or corrupted? The system should fail with a clear error rather than silently using an empty prompt.
- What happens when two developers simultaneously update the same alias? The last write wins, and both changes are recorded in the version history.
- What happens when a prompt contains template variables (e.g., placeholders for dynamic content)? Template variables must be preserved through registration and resolved at load time.
- What happens when the registry service is slow or unreachable during agent startup? The system falls back to bundled default prompts within a configurable timeout and logs the failure.
- What happens when a prompt is registered with the same content as an existing version? The system creates a new version regardless (immutable append-only history) to preserve the audit trail.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST store each prompt as an immutable, versioned artifact with a unique name, version number, full prompt text, and creation timestamp.
- **FR-002**: System MUST support at least the following named prompts: ORCHESTRATOR_BASE_PROMPT, ONBOARDING_SYSTEM_PROMPT, PROACTIVE_GREETING_PROMPT, OBSERVATION_SYSTEM_PROMPT, SCHEDULE_SYSTEM_PROMPT, CALIBRATION_SYSTEM_PROMPT, MEMORY_SYSTEM_PROMPT, MEMORY_WRITE_SYSTEM_PROMPT, WEATHER_SYSTEM_PROMPT, GRAPH_SYSTEM_PROMPT, NOTIFICATION_SYSTEM_PROMPT.
- **FR-003**: System MUST support named aliases (at minimum `@production` and `@experiment`) that point to specific prompt versions and can be updated independently.
- **FR-004**: System MUST load prompts from the registry at agent creation time, replacing all hardcoded string constants currently in the codebase.
- **FR-004a**: System MUST cache loaded prompts in-memory and refresh the cache on a configurable time-based interval. Prompts are NOT loaded from the registry on every request.
- **FR-005**: System MUST fall back to bundled default prompts when the registry is unavailable, logging a warning.
- **FR-005a**: System MUST auto-seed missing prompts into the registry from bundled defaults on startup. Seeding is idempotent — prompts that already exist in the registry are not overwritten.
- **FR-006**: System MUST allow storing model configuration parameters (e.g., temperature, max tokens) alongside each prompt version.
- **FR-007**: System MUST tag evaluation runs with the individual prompt component versions active during the run (e.g., "orchestrator-base: v3, onboarding: v2"), enabling traceability from eval results to prompt versions. Assembly logic for composite prompts is versioned via source control, not the prompt registry.
- **FR-008**: System MUST preserve all previous prompt versions — versions are immutable and append-only.
- **FR-009**: System MUST support template variables within prompts that are resolved at load time with runtime values.
- **FR-010**: System MUST log which prompt version and alias was loaded for each agent creation, including correlation ID.
- **FR-011**: System MUST allow the composite prompts (e.g., orchestrator instructions that combine base prompt + onboarding/greeting + routing hints) to be assembled from individually-versioned prompt components.

### Key Entities

- **Prompt**: A named prompt template with a unique identifier (e.g., "orchestrator-base"). Has many versions. Represents a single behavioral instruction set for an agent or specialist.
- **Prompt Version**: An immutable snapshot of a prompt's text and optional model configuration at a point in time. Identified by prompt name + version number. Contains: full prompt text, model parameters, creation timestamp.
- **Prompt Alias**: A named pointer (e.g., `@production`, `@experiment`) that resolves to a specific prompt version. Can be updated to point to a different version. Enables swapping prompts without code changes.

## Assumptions

- MLflow 3.10.0 (already installed) provides the prompt registry capabilities needed. The `mlflow.genai.register_prompt()` and `mlflow.genai.load_prompt()` APIs will be used.
- The existing MLflow tracking server (running via Docker Compose) will store prompt registry data — no additional infrastructure is required.
- The ~11 prompts identified in `src/services/agents.py` represent the complete set of prompts to migrate. If additional prompts are discovered during implementation, they follow the same migration pattern.
- Prompts are cached in-memory with a configurable time-based refresh interval, avoiding per-request registry calls. The refresh interval balances alias swap responsiveness against registry load.
- The `build_orchestrator_instructions()` function's dynamic assembly logic (combining base prompt + onboarding/greeting + routing hints) will continue to work by loading individual prompt components and composing them in code.
- Scheduled task prompt templates (stored in the database via `create_schedule`) are user-generated content and are NOT part of this migration — they remain in the database.
- On startup, the system auto-seeds any missing prompts into the registry from bundled defaults. This ensures fresh deployments, new environments, and CI pipelines work without manual migration steps.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of system prompts (all ~11 identified constants) are loaded from the prompt registry rather than hardcoded in source code.
- **SC-002**: Every prompt change creates a new traceable version — zero prompt modifications occur without a corresponding version record.
- **SC-003**: Evaluation runs are tagged with prompt versions, and a developer can determine which prompt versions were active for any given eval run.
- **SC-004**: Prompts can be swapped via alias updates with zero code changes and zero application restarts, with the new prompt taking effect within the cache refresh interval.
- **SC-005**: Agent behavior with registry-loaded prompts is indistinguishable from hardcoded-prompt behavior, as verified by the existing evaluation suite passing at the same rate (no quality regression).
- **SC-006**: When the prompt registry is unavailable, the system degrades gracefully using bundled defaults within 5 seconds, with no user-visible errors.

## Clarifications

### Session 2026-02-24

- Q: Should prompts be loaded fresh from the registry per-request, or cached in-memory with periodic refresh? → A: Cache in-memory with a configurable time-based refresh interval. Alias swaps take effect within the refresh window, not instantly.
- Q: Should eval runs tag individual prompt component versions or also record the assembled composite text? → A: Tag individual component versions only. Assembly logic is versioned via source control.
- Q: How are existing hardcoded prompts initially populated into the registry? → A: Auto-seed on startup. If a prompt is missing from the registry, register it from bundled defaults. Idempotent — existing prompts are not overwritten.
