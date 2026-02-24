# Research: Eval Dashboard UI

**Feature Branch**: `014-eval-dashboard-ui`
**Date**: 2026-02-24

## R1: Charting Library for Interactive Line Charts

**Decision**: Recharts

**Rationale**: Recharts is the best fit for this project because:
- Component-based API native to React (works naturally with Next.js App Router)
- Excellent TypeScript support out of the box
- `ReferenceDot` and `ReferenceLine` components enable annotating prompt version changes on charts
- Lightweight (~60KB minified), appropriate for an admin dashboard
- Active maintenance with React 19 support (v2.13.0+)
- Built-in interactive tooltips, click events, and animations

**Alternatives Considered**:
- **Tremor**: Built on Recharts with pre-styled dashboard components. Adds an abstraction layer without enough benefit; less customizable for our specific annotation needs.
- **Chart.js (react-chartjs-2)**: Familiar but weaker TypeScript support, not React-native (canvas-based).
- **Nivo**: Beautiful defaults but heavier (~200KB), overkill for a lightweight admin dashboard.
- **Victory**: Flexible and composable but steeper learning curve, less dashboard-focused.

**Installation**: `cd frontend && npm install recharts`

---

## R2: Dashboard Page Architecture

**Decision**: Single tabbed page at `/admin/evals` within existing admin panel

**Rationale**: The existing admin panel has a single page at `/admin` for user management. Adding an eval dashboard as a sub-route `/admin/evals` keeps the admin area organized. Tab navigation within the page separates the five sections (Trends, Regressions, Promote, Run Evals, Rollback) without deep navigation.

**Alternatives Considered**:
- **Extend existing `/admin` page**: Would make the admin page too large and mix user management with eval concerns.
- **Top-level `/evals` route**: Would break the admin-only organizational pattern and require separate auth guarding.
- **Separate pages per section**: Over-navigated for related concerns; admins often switch between trends and regressions.

**Implementation Pattern**: Use `useState` for active tab (no URL state needed since tabs are lightweight). Custom `Tabs` component for reuse. Each tab panel is a client component with its own data fetching hook.

---

## R3: Backend API Architecture for Pipeline Proxy

**Decision**: New FastAPI router at `/admin/evals/*` using `require_admin` dependency, calling eval pipeline functions directly

**Rationale**: The existing eval pipeline functions (aggregator, regression, promotion, trigger, rollback) are designed as importable Python modules. The backend API endpoints import and call these functions directly, serializing the dataclass results to JSON via Pydantic response models. This keeps the pipeline as the single source of truth.

**Alternatives Considered**:
- **Subprocess calls to CLI**: Would be fragile, slower, and harder to get structured data from. CLI is for human consumption.
- **New microservice**: Over-engineered for a single-user admin dashboard.
- **Direct MLflow API calls from frontend**: Would expose MLflow credentials to the browser and duplicate pipeline logic.

**Key Design Decision**: The `run_eval_suite()` function is long-running (minutes). The API endpoint will run it in a background task and return a job ID. The frontend polls a status endpoint to track progress.

---

## R4: Eval Suite Progress Tracking

**Decision**: Background task with in-memory state, polled via status endpoint

**Rationale**: Eval suite runs take minutes (5-19 evals, each running subprocess calls to the eval framework). The API will:
1. Accept a POST to start the run, store state in a module-level dict, return a job ID
2. Run the suite in a background asyncio task using `run_eval_suite()` with a `progress_callback`
3. Expose a GET status endpoint that returns current progress (completed/total, per-eval results)
4. Frontend polls the status endpoint with a refresh button

**Alternatives Considered**:
- **Server-Sent Events (SSE)**: Already used for chat streaming, but declared out of scope. Polling is simpler and sufficient for admin use.
- **WebSocket**: Declared out of scope in spec.
- **Database-backed job queue (Celery, etc.)**: Over-engineered for a single concurrent run.

**Concurrency Control**: Only one eval suite run at a time. The status dict stores the current run; a second POST returns 409 Conflict.

---

## R5: Prompt Listing for Promotion/Rollback

**Decision**: Use `get_active_prompt_versions()` from prompt_service to list all registered prompts

**Rationale**: The `get_active_prompt_versions()` function returns a `dict[str, int]` of all prompt names and their current version numbers. This is populated during app startup by `seed_prompts()`. It provides exactly what the Promote and Rollback tabs need: a list of prompt names to select from.

**Alternatives Considered**:
- **Query MLflow model registry directly**: Would bypass the prompt_service abstraction and require MLflow client setup in the API.
- **Hardcode prompt names**: Fragile; wouldn't adapt to new prompts being registered.

**Note**: `get_active_prompt_versions()` requires that `seed_prompts()` has been called at startup. The chat API already does this in its lifespan handler.

---

## R6: Data Refresh Strategy

**Decision**: Manual refresh only (page load + explicit refresh button)

**Rationale**: Per clarification, no auto-refresh. The dashboard loads data on mount and provides a refresh button. This keeps the implementation simple, avoids unnecessary API calls, and is predictable for the admin user.

**Implementation**: Each data-fetching hook exposes a `refresh()` function. The tab container provides a refresh button that calls the active tab's refresh function.
