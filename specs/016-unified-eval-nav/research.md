# Research: Unified Eval Navigation

## R1: MLflow Git Model Versioning API

**Decision**: Use `mlflow.genai.enable_git_model_versioning()` to automatically create LoggedModels per git commit during eval runs.

**Rationale**: This API is purpose-built for our use case — it detects git branch, commit SHA, dirty state, and diffs, then creates or reuses a LoggedModel for each unique git state. All traces produced while a version is active are automatically linked via `model_id`. This replaces our manual `_log_git_sha()` param with structured, queryable version tracking.

**Alternatives considered**:
- Manual `mlflow.set_active_model(name=...)` — rejected because it requires manual naming and doesn't capture git metadata automatically
- `ResponsesAgent` — rejected because it's a model packaging format for MLflow-served agents; we use OpenAI Agents SDK with our own FastAPI serving layer
- Custom version table in PostgreSQL — rejected because MLflow already provides the storage and query APIs

**Key API surface**:
- `mlflow.genai.enable_git_model_versioning()` → creates/reuses LoggedModel, returns `GitContext`
- `mlflow.search_logged_models(experiment_ids=..., filter_string=...)` → list all versions
- `mlflow.get_logged_model(model_id)` → get single version with tags/metrics
- `mlflow.search_traces(model_id=...)` → traces linked to a version
- Git tags stored as: `mlflow.source.git.branch`, `mlflow.source.git.commit`, `mlflow.source.git.dirty`, `mlflow.source.git.diff`

## R2: Next.js App Router Nested Layouts

**Decision**: Use a `layout.tsx` file at `app/(main)/admin/evals/layout.tsx` to provide shared sub-navigation across all eval sub-pages.

**Rationale**: Next.js App Router nests layouts automatically — child routes inherit parent layouts. Placing a layout at the `/admin/evals/` level gives us a persistent sub-navigation bar that renders on Dashboard, Agents, Experiments, Datasets, Trends, and all detail pages without re-mounting on navigation. This is the canonical Next.js pattern for section-level navigation.

**Alternatives considered**:
- Tab component on each page — rejected because tabs re-mount on navigation, losing scroll position and causing layout shift
- Shared component imported per page (no layout) — rejected because it duplicates admin auth checks and forces each page to manage its own shell

## R3: Agent Version Aggregate Quality Score

**Decision**: Compute aggregate quality score as the average of universal quality scores (1-5 scale) across all experiment types that ran for that version.

**Rationale**: The universal quality score already exists as a standardized 1-5 LLM judge metric across all eval types. Averaging it gives a single meaningful number without inventing a new composite metric or requiring weighted scoring logic.

**Alternatives considered**:
- Weighted average by case count — rejected because it biases toward eval types with more test cases
- Minimum score (worst-case) — rejected because a single low-scoring experiment type would dominate the trend view
- Pass rate percentage — rejected because it's binary (pass/fail per experiment) and loses the nuance of the 1-5 scale

## R4: Historical Data Migration

**Decision**: No backfill of historical eval runs. Agents and Trends pages only show data from runs with proper LoggedModel linking.

**Rationale**: Historical runs have `git_sha` as a plain param but no LoggedModel. Creating LoggedModels retroactively would be fragile (need to reconstruct git state from a short SHA, handle missing branches, etc.) for data that's already accessible through the Experiments page. The Trends page becomes useful after 3-4 eval suite runs on different commits.

**Alternatives considered**:
- Backfill migration script — rejected because git state reconstruction is unreliable and the effort doesn't justify the value for an admin tool
- Hybrid view with "pre-versioning" label — rejected because it complicates the UI for a temporary state

## R5: Backend Endpoint Pattern for LoggedModels

**Decision**: Add 2 new endpoints to the existing `eval_explorer.py` router, following the same `run_in_executor` pattern used by all other MLflow endpoints.

**Rationale**: The existing router already handles all MLflow read operations. Adding agent version endpoints there maintains consistency. The `run_in_executor` wrapper is required because MLflow's Python client makes synchronous HTTP calls that would block the async FastAPI event loop.

**Key endpoints**:
- `GET /admin/evals/explorer/agents` — calls `mlflow.search_logged_models()` across all experiment IDs, extracts git tags, computes aggregate quality score
- `GET /admin/evals/explorer/agents/{model_id}` — calls `mlflow.get_logged_model()`, `mlflow.search_traces(model_id=...)`, and aggregates per-experiment metrics

## R6: Eval Runner Integration Point

**Decision**: Add a single `mlflow.genai.enable_git_model_versioning()` call at the start of each eval run function, before `mlflow.start_run()`.

**Rationale**: This is the minimal change needed — one line added to the shared eval setup code. It must be called before `mlflow.start_run()` so traces created during the run are linked to the LoggedModel. It's safe to call multiple times (reuses existing LoggedModel for the same commit).

**Integration point**: In `eval/runner.py`, each `run_*_evaluation()` function calls `mlflow.set_tracking_uri()` and `mlflow.set_experiment()` before starting a run. The `enable_git_model_versioning()` call goes after `set_experiment()` and before `start_run()`.
