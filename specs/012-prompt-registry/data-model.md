# Data Model: Prompt Registry

**Feature**: 012-prompt-registry
**Date**: 2026-02-24

## Overview

This feature does NOT introduce new database tables. All prompt data is stored in MLflow's built-in Prompt Registry, which uses MLflow's existing tracking server storage (file store or database backend configured in Docker Compose).

The entities below describe the MLflow-managed data structures that this feature relies on.

## Entities

### Prompt

Managed by MLflow. Represents a named prompt template.

| Attribute | Type | Description |
|-----------|------|-------------|
| name | string | Unique identifier, `[a-zA-Z0-9_.-]+`. E.g., `orchestrator-base` |
| description | string | Optional human-readable description |
| tags | dict[str, str] | Prompt-level metadata (shared across versions) |
| creation_timestamp | int | Milliseconds since epoch |

**Uniqueness**: `name` is globally unique within the MLflow tracking server.

### Prompt Version

Managed by MLflow. Immutable snapshot of a prompt at a point in time.

| Attribute | Type | Description |
|-----------|------|-------------|
| name | string | Parent prompt name |
| version | int | Auto-incrementing (1, 2, 3, ...) |
| template | string | Full prompt text with `{{variable}}` placeholders |
| commit_message | string | Description of changes from previous version |
| tags | dict[str, str] | Version-level metadata |
| model_config | dict | Optional model parameters (temperature, max_tokens, etc.) |
| variables | set[str] | Auto-detected `{{variable}}` names in template |
| aliases | list[str] | Aliases currently pointing to this version |
| creation_timestamp | int | Milliseconds since epoch |

**Uniqueness**: `(name, version)` is unique.
**Immutability**: Once created, `template` cannot be changed. New content requires a new version.

### Prompt Alias

Managed by MLflow. Mutable pointer from a name to a specific version.

| Attribute | Type | Description |
|-----------|------|-------------|
| name | string | Parent prompt name |
| alias | string | Alias name, e.g., `production`, `experiment` |
| version | int | Version number this alias points to |

**Uniqueness**: `(name, alias)` is unique.
**Mutability**: Alias can be re-pointed to a different version at any time.

## Application-Level Configuration

New settings added to `src/config.py`:

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| PROMPT_CACHE_TTL_SECONDS | int | 300 | Cache TTL for prompt registry lookups |
| PROMPT_ALIAS | str | "production" | Default alias to load prompts from |

## Registered Prompts

Initial set of prompts seeded on first startup:

| Registry Name | Source Constant | Used By |
|---------------|-----------------|---------|
| `orchestrator-base` | ORCHESTRATOR_BASE_PROMPT | Orchestrator agent |
| `onboarding` | ONBOARDING_SYSTEM_PROMPT | Orchestrator (new users) |
| `proactive-greeting` | PROACTIVE_GREETING_PROMPT | Orchestrator (returning users) |
| `memory` | MEMORY_SYSTEM_PROMPT | Memory specialist |
| `memory-write` | MEMORY_WRITE_SYSTEM_PROMPT | Memory specialist |
| `weather` | WEATHER_SYSTEM_PROMPT | Weather specialist |
| `knowledge-graph` | GRAPH_SYSTEM_PROMPT | Knowledge specialist |
| `calibration` | CALIBRATION_SYSTEM_PROMPT | Proactive specialist |
| `schedule` | SCHEDULE_SYSTEM_PROMPT | Proactive specialist |
| `observation` | OBSERVATION_SYSTEM_PROMPT | Proactive specialist |
| `notification` | NOTIFICATION_SYSTEM_PROMPT | Notification specialist |

## Relationships

```
Prompt (1) ──── (N) Prompt Version
Prompt Version (N) ──── (N) Prompt Alias  (one alias per prompt, but version can have multiple aliases)
```

## State Transitions

### Prompt Version Lifecycle
```
[Created] → [Active] (immutable — no further state changes)
```
Versions are never deleted, modified, or archived. They exist permanently.

### Prompt Alias Lifecycle
```
[Created] → [Active] → [Re-pointed] → [Active] (can cycle indefinitely)
                     → [Deleted] (terminal)
```
Aliases can be re-pointed to different versions or deleted entirely.

### Auto-Seed Flow (Startup)
```
For each bundled default prompt:
  [Check registry] → exists? → skip
                   → missing? → [Register v1] → [Set @production alias]
```
