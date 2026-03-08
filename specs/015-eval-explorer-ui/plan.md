# Implementation Plan: Eval Explorer UI

**Branch**: `015-eval-explorer-ui` | **Date**: 2026-03-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/015-eval-explorer-ui/spec.md`

## Summary

Read-only admin UI for browsing all eval data stored in MLflow — experiments, runs, traces, assessments, sessions, and golden datasets. Includes a cross-experiment universal quality trend chart. Complements Feature 014 (pipeline operations) as a separate page at `/admin/eval-explorer`. No mutations to MLflow data. Backend serves MLflow data through new API endpoints; frontend renders it with purpose-built components.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript/Next.js 15 (frontend)
**Primary Dependencies**: FastAPI, MLflow 3.10.0, Next.js App Router, Recharts, Tailwind CSS
**Storage**: MLflow tracking server (read-only), filesystem (golden dataset JSON files)
**Testing**: pytest (backend), Vitest + React Testing Library (frontend), Playwright MCP (E2E)
**Target Platform**: Web browser (admin users)
**Project Type**: Web application (backend API + frontend SPA)
**Performance Goals**: Page load with trend chart < 3 seconds; experiment → trace drill-down in ≤ 3 clicks
**Constraints**: Read-only; admin-only; no MLflow data mutations; client-side pagination (25 items default)
**Scale/Scope**: 18 eval types, ~100 runs max per experiment, ~50 traces max per run

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Clarity over Cleverness | PASS | Each component has a single purpose; data flows from MLflow → API → hooks → components |
| II. Evaluation-First | PASS | Feature is itself eval infrastructure; unit tests for API endpoints and frontend components |
| III. Tool Safety | N/A | No tool execution; read-only data browsing |
| IV. Privacy by Default | PASS | Admin-only access; no user PII exposed (eval data contains synthetic test cases) |
| V. Consistent UX | PASS | Follows existing admin page patterns (Card, Button, Skeleton, error/loading/empty states) |
| VI. Performance Budgets | PASS | 3-second load target; client-side pagination prevents large payloads from degrading UX |
| VII. Observability | PASS | Structured logging on all API endpoints (same pattern as Feature 014) |
| VIII. Reproducible Environments | PASS | No new dependencies beyond what's already installed; `uv sync` for backend, `npm install` for frontend |

No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/015-eval-explorer-ui/
├── spec.md
├── plan.md              # This file
├── research.md          # Phase 0: technical decisions
├── data-model.md        # Phase 1: API response models
├── quickstart.md        # Phase 1: dev setup guide
├── contracts/
│   └── api.md           # Phase 1: API endpoint contracts
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```text
# Backend — new API router + models
src/
├── api/
│   └── eval_explorer.py          # New: GET-only endpoints for explorer data
└── models/
    └── eval_explorer.py          # New: Pydantic response models

# Frontend — new page, components, hooks, types
frontend/src/
├── app/(main)/admin/
│   └── eval-explorer/
│       └── page.tsx              # New: explorer page
├── components/
│   ├── eval-explorer/            # New: all explorer components
│   │   ├── ExperimentBrowser.tsx
│   │   ├── RunBrowser.tsx
│   │   ├── TraceViewer.tsx
│   │   ├── SessionViewer.tsx
│   │   ├── UniversalQualityChart.tsx
│   │   ├── DatasetViewer.tsx
│   │   └── RunComparison.tsx
│   └── layout/
│       ├── Header.tsx            # Update: add Eval Explorer nav link
│       └── Sidebar.tsx           # Update: add mobile nav link
├── hooks/
│   └── useEvalExplorer.ts        # New: data-fetching hooks
└── types/
    └── eval-explorer.ts          # New: TypeScript interfaces

# Tests
tests/unit/
└── test_eval_explorer.py         # New: backend unit tests

frontend/tests/components/
└── eval-explorer/                # New: frontend unit tests
    ├── ExperimentBrowser.test.tsx
    ├── RunBrowser.test.tsx
    └── TraceViewer.test.tsx
```

**Structure Decision**: Follows the existing web application pattern. Backend adds a new router module alongside `eval_dashboard.py`. Frontend adds a new page route and component directory alongside `eval-dashboard/`. Mirrors the Feature 014 organizational pattern exactly.

## Architecture

### Data Flow

```
MLflow Tracking Server
    ↓ (mlflow Python client)
src/api/eval_explorer.py (FastAPI, GET-only, admin-gated)
    ↓ (JSON over HTTP)
frontend/src/hooks/useEvalExplorer.ts (apiClient.get)
    ↓ (React state)
frontend/src/components/eval-explorer/*.tsx (render)
```

### Backend Design

**Router**: `src/api/eval_explorer.py` — mounted at `/admin/evals/explorer`

Six GET endpoints (see [contracts/api.md](contracts/api.md)):
1. `GET /experiments` — list experiments with metadata
2. `GET /experiments/{id}/runs` — runs for an experiment
3. `GET /runs/{id}/traces` — traces with full assessments + session grouping
4. `GET /trends/quality` — universal quality trend data
5. `GET /datasets` — list golden datasets
6. `GET /datasets/{name}` — single dataset with cases

**Key patterns**:
- All MLflow calls wrapped in `run_in_executor()` (non-blocking async)
- Assessment normalization reuses logic from `eval/pipeline/aggregator.py`
- Session grouping done server-side for multi-turn eval types
- Dataset files read from filesystem with JSON parsing + error handling

### Frontend Design

**Page**: `/admin/eval-explorer` — single page with sub-views managed by component state (not URL routing). The page renders the experiment browser by default. Clicking an experiment shows runs, clicking a run shows traces.

**Navigation flow**:
```
ExperimentBrowser (default view)
    → click experiment → RunBrowser (shows runs for that experiment)
        → click run → TraceViewer (shows traces + assessments)
            → session grouping for multi-turn eval types
    → select 2 runs → RunComparison (side-by-side diff)

UniversalQualityChart (always visible at top)
DatasetViewer (separate tab or section)
```

**Component responsibilities**:
- `ExperimentBrowser` — table of experiments, click to drill down
- `RunBrowser` — table of runs with sortable columns, checkboxes for comparison
- `TraceViewer` — expandable trace rows with all assessments
- `SessionViewer` — groups traces by session, renders conversation timeline
- `UniversalQualityChart` — multi-line Recharts chart (one line per eval type)
- `DatasetViewer` — expandable dataset list with case details
- `RunComparison` — side-by-side param/metric/case diff

**State management**: Local React state (useState/useCallback). No Zustand store needed — the explorer is stateless between page loads.

### Relationship to Feature 014

Feature 014 (Eval Dashboard) and Feature 015 (Eval Explorer) are **separate pages**:
- `/admin/evals` — pipeline operations (trends, regressions, promote, rollback, run evals)
- `/admin/eval-explorer` — data browsing (experiments, runs, traces, assessments, datasets)

They share:
- Admin auth pattern (`require_admin`)
- UI component library (`Card`, `Button`, `Skeleton`, `Tabs`)
- MLflow as data source
- Assessment normalization logic

They do NOT share:
- API endpoints (separate routers)
- Frontend components (separate directories)
- Navigation state

## Implementation Phases

### Phase 1: Backend API + Types (P1 foundation)

1. Create `src/models/eval_explorer.py` — Pydantic response models
2. Create `src/api/eval_explorer.py` — all 6 GET endpoints
3. Mount router in `src/main.py`
4. Backend unit tests

### Phase 2: Frontend Foundation + Experiment Browser (P1)

1. Create TypeScript types (`eval-explorer.ts`)
2. Create data-fetching hooks (`useEvalExplorer.ts`)
3. Create page route (`/admin/eval-explorer/page.tsx`)
4. Build `ExperimentBrowser` component
5. Update navigation (Header + Sidebar)
6. Frontend unit tests

### Phase 3: Universal Quality Trend Chart (P1)

1. Build `UniversalQualityChart` component with Recharts
2. Integrate into page (always visible at top)
3. Frontend tests

### Phase 4: Run Browser + Trace Viewer (P2)

1. Build `RunBrowser` component (sortable table, pagination)
2. Build `TraceViewer` component (expandable rows, all assessments)
3. Wire drill-down navigation (experiment → runs → traces)
4. Frontend tests

### Phase 5: Session Viewer + Dataset Viewer (P3)

1. Build `SessionViewer` component (conversation timeline)
2. Build `DatasetViewer` component (expandable dataset list)
3. Frontend tests

### Phase 6: Run Comparison (P3)

1. Build `RunComparison` component (side-by-side diff)
2. Add checkbox selection to `RunBrowser`
3. Frontend tests
