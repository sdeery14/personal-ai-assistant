# Research: Eval Explorer UI

## R1: Explorer Page Routing & Navigation

**Decision**: Separate route at `/admin/eval-explorer` with a new App Router page.

**Rationale**: The eval explorer is a distinct browsing experience from Feature 014's operational dashboard. Separate routing keeps concerns clean and avoids overloading the existing eval dashboard with 7+ additional tab-like views.

**Alternatives considered**:
- Additional tabs on `/admin/evals` — rejected because the explorer's 7 stories would create too many tabs alongside the existing 5.
- Replace Feature 014 entirely — rejected because pipeline ops (promote, rollback, run evals) are a distinct workflow from data browsing.

**Integration points**:
- Add link in `Header.tsx` (line ~42-65, admin links section) and `Sidebar.tsx` (line ~53-77, mobile admin links section).
- Use same `pathname.startsWith("/admin/eval-explorer")` pattern for active state.

## R2: Backend API Design — MLflow Data Access

**Decision**: New FastAPI router at `/admin/evals/explorer/` with endpoints that call MLflow Python client directly (same pattern as `eval/pipeline/aggregator.py`).

**Rationale**: The existing aggregator already knows how to query MLflow experiments, runs, and traces. The new endpoints extend this pattern with more granular data access (full trace lists, all assessments, session grouping).

**Alternatives considered**:
- Proxy MLflow's REST API directly from the frontend — rejected because MLflow's API is not auth-gated and exposes internal structure.
- Reuse existing `/admin/evals/trends` endpoint — rejected because it aggregates too aggressively; the explorer needs raw data.

**Key MLflow API calls needed**:
- `mlflow.search_experiments()` — list all experiments
- `mlflow.search_runs()` — list runs with params/metrics for an experiment
- `mlflow.search_traces()` — list traces for a run with assessments
- Golden dataset files read from filesystem (`eval/*.json`)

## R3: Assessment Normalization

**Decision**: Reuse the existing normalization logic from `eval/pipeline/aggregator.py` (lines ~270-596). The API layer normalizes assessment values before sending to the frontend.

**Rationale**: The aggregator already handles word labels → numeric, string numbers → float, booleans → 0/1, and complex dict values. No need to duplicate this logic.

**Key mapping**:
- "excellent" → 5.0, "good" → 4.0, "adequate" → 3.0, "poor" → 2.0, "unacceptable" → 1.0
- "5"→5.0, "4"→4.0, etc.
- True→1.0, False→0.0

## R4: Session Grouping for Multi-Turn Evals

**Decision**: Server-side grouping by `mlflow.trace.session` metadata key, returned as nested structure in the API response.

**Rationale**: The aggregator already implements session grouping (line ~395-497). The 5 session-based eval types are defined in `EVAL_SESSION_TYPES` in `pipeline_config.py`. Grouping on the server avoids sending raw session metadata to the frontend.

**Session eval types**: onboarding, contradiction, memory-informed, multi-cap, long-conversation.

## R5: Universal Quality Trend Data Source

**Decision**: New API endpoint that queries each experiment's runs for the universal quality judge assessment score, returning time-series data across all eval types.

**Rationale**: The universal judge is a prerequisite framework change (separate from Feature 015). Once it exists, every run will have a `universal_quality` assessment. The trend endpoint aggregates the average universal quality score per run across all experiments.

**Data flow**: For each experiment → get runs sorted by time → extract universal quality metric → return as `{eval_type, timestamp, score, run_id}[]`.

## R6: Dataset Viewer Data Source

**Decision**: Read golden dataset JSON files from the filesystem via a new API endpoint. Files are committed to the repo under `eval/`.

**Rationale**: Datasets are static JSON files, not stored in MLflow. The API reads them, parses the JSON, and returns structured data. This is simpler than registering them as MLflow datasets (which the project does separately for eval tracking).

**Dataset files pattern**: `eval/*_golden_dataset.json` — 18 files total.

## R7: Run Comparison Implementation

**Decision**: Client-side comparison using data already fetched by the run browser. The frontend diffs params, metrics, and per-case results between two selected runs.

**Rationale**: Both runs' data is already loaded in the browser (from the run detail endpoint). Computing diffs client-side avoids a dedicated comparison API endpoint and keeps the backend simple.

**Per-case diff**: Match cases by `case_id`, compute score delta, classify as improved/regressed/unchanged.

## R8: Client-Side Pagination

**Decision**: Default page size of 25 items with page controls (prev/next + page size selector). Data fetched in full from the API, paginated on the client.

**Rationale**: Expected data volumes are manageable (max ~100 runs per experiment, max ~50 traces per run). Client-side pagination is simpler and avoids API complexity. The existing eval dashboard uses a similar pattern with `DETAIL_LIMIT_OPTIONS`.

**If volumes grow**: Can add server-side pagination later by adding `limit` and `offset` query params to the API endpoints.
