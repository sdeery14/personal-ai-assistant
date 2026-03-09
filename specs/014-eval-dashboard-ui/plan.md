# Implementation Plan: Eval Dashboard UI

**Branch**: `014-eval-dashboard-ui` | **Date**: 2026-02-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/014-eval-dashboard-ui/spec.md`

## Summary

Add a web-based eval dashboard to the existing Next.js admin panel, providing visual monitoring and management of the eval pipeline. The backend exposes new FastAPI endpoints under `/admin/evals/*` that proxy to existing eval pipeline functions (Feature 013). The frontend adds a tabbed dashboard page with interactive charts (Recharts), data tables, and action forms for trends, regressions, promotion, eval runs, and rollback. All endpoints require admin authentication.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5 (frontend)
**Primary Dependencies**: FastAPI (backend API), Next.js 15 App Router (frontend), Recharts (charting), Tailwind CSS (styling)
**Storage**: N/A (all data from MLflow via eval pipeline, prompt versions from MLflow Model Registry)
**Testing**: pytest (backend unit tests), Vitest + React Testing Library (frontend unit tests)
**Target Platform**: Web browser (admin panel), Linux/Docker server (backend)
**Project Type**: Web application (existing backend + frontend)
**Performance Goals**: Dashboard loads in <3s, eval progress updates within 5s of refresh
**Constraints**: Admin-only access, manual refresh (no auto-refresh/WebSocket), single concurrent eval run
**Scale/Scope**: Single admin user, up to 19 eval types, 1 tabbed dashboard page with 5 sections

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Clarity over Cleverness | PASS | Each tab component has one purpose. API endpoints are simple proxies to pipeline functions. |
| II. Evaluation-First Behavior | PASS | Backend endpoints will have pytest unit tests. Frontend components will have Vitest tests. Existing pipeline logic (already tested) is reused, not reimplemented. |
| III. Tool Safety and Correctness | N/A | No new tool schemas introduced. Dashboard calls validated API endpoints. |
| IV. Privacy by Default | PASS | Eval data contains no PII. Admin auth required for all endpoints. No sensitive data exposed to browser. |
| V. Consistent UX | PASS | Dashboard uses existing UI components (Button, Card, Input, Dialog, Skeleton). Tab pattern follows admin panel conventions. Empty states and error messages are defined. |
| VI. Performance and Cost Budgets | PASS | No LLM calls from dashboard. Backend proxies to pipeline functions. NFR-001 sets 3s load budget. |
| VII. Observability and Debuggability | PASS | Backend uses existing structlog pattern with correlation IDs. API errors return structured JSON. |
| VIII. Reproducible Environments | PASS | Python deps via uv/pyproject.toml. Frontend deps via npm/package.json. Recharts added via npm install. |

**Post-Design Re-Check**: All principles remain PASS. No violations introduced.

## Project Structure

### Documentation (this feature)

```text
specs/014-eval-dashboard-ui/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research output
├── data-model.md        # Phase 1 data model
├── quickstart.md        # Phase 1 integration scenarios
├── contracts/
│   └── eval-dashboard-api.md  # API contract
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
# Backend (Python/FastAPI)
src/
├── api/
│   └── eval_dashboard.py       # NEW: /admin/evals/* route handlers
├── models/
│   └── eval_dashboard.py       # NEW: Pydantic request/response models
└── main.py                     # MODIFY: Register eval_dashboard router

# Backend Tests
tests/
└── unit/
    └── test_eval_dashboard.py  # NEW: Unit tests for eval dashboard API

# Frontend (Next.js/TypeScript)
frontend/
├── src/
│   ├── app/
│   │   └── (main)/
│   │       └── admin/
│   │           └── evals/
│   │               └── page.tsx        # NEW: Eval dashboard page
│   ├── components/
│   │   ├── ui/
│   │   │   └── Tabs.tsx                # NEW: Reusable tab component
│   │   └── eval-dashboard/
│   │       ├── TrendsTab.tsx           # NEW: Trends summary + detail view
│   │       ├── TrendChart.tsx          # NEW: Recharts line chart
│   │       ├── RegressionsTab.tsx      # NEW: Regression report table
│   │       ├── PromoteTab.tsx          # NEW: Promotion gate + execute UI
│   │       ├── RunEvalsTab.tsx         # NEW: Eval suite trigger + progress
│   │       └── RollbackTab.tsx         # NEW: Rollback selection + execute
│   ├── hooks/
│   │   └── useEvalDashboard.ts         # NEW: Data fetching hooks for all tabs
│   └── types/
│       └── eval-dashboard.ts           # NEW: TypeScript interfaces
└── __tests__/
    └── components/
        └── eval-dashboard/
            ├── TrendsTab.test.tsx       # NEW: Trends tab tests
            ├── RegressionsTab.test.tsx  # NEW: Regressions tab tests
            ├── PromoteTab.test.tsx      # NEW: Promote tab tests
            ├── RunEvalsTab.test.tsx     # NEW: Run evals tab tests
            └── RollbackTab.test.tsx     # NEW: Rollback tab tests
```

**Structure Decision**: This feature follows the existing web application structure. Backend changes are minimal (one new router + one new models file). Frontend adds a new page under the admin route group with feature-specific components in a dedicated `eval-dashboard/` directory. This matches the existing pattern where `chat/`, `memory/`, `knowledge/` each have their own component directories.

## Key Design Decisions

### 1. Backend: Thin Proxy Layer

The API endpoints are thin proxies that:
1. Validate the request (Pydantic models)
2. Call the existing pipeline function
3. Convert the pipeline dataclass result to a Pydantic response model
4. Return JSON

No business logic is duplicated. The eval pipeline remains the single source of truth.

### 2. Backend: Eval Run Background Task

`run_eval_suite()` is long-running (minutes). The approach:
- `POST /admin/evals/run` starts a background `asyncio.Task` and returns immediately with `202 Accepted`
- A module-level dict `_eval_run_state` stores the current run's progress
- `GET /admin/evals/run/status` reads the state dict and returns current progress
- Only one run at a time (second POST returns `409 Conflict`)
- The background task updates `_eval_run_state` via `progress_callback` parameter
- After all evals complete, the task runs `check_all_regressions()` and stores results

### 3. Frontend: Tab Architecture

- Page at `/admin/evals` renders a `Tabs` component with 5 tabs
- Each tab is a separate client component with its own data-fetching hook
- Tab state managed via `useState` (no URL params needed)
- Data loads on tab activation (lazy) and via refresh button
- All components use existing UI primitives (Button, Card, Input, Dialog, Skeleton)

### 4. Frontend: Charting with Recharts

- `TrendChart` is a `"use client"` component using Recharts `LineChart`
- `ReferenceDot` marks prompt version changes on the chart
- Custom tooltip shows run details on hover
- Chart is responsive and uses Tailwind-compatible sizing

### 5. Frontend: Admin Navigation Update

- Add "Evals" link to admin section (alongside existing "Admin" link)
- Two options considered:
  - Sub-navigation within `/admin` page → chosen: add a secondary nav bar on the admin page that links to `/admin` (Users) and `/admin/evals` (Evals)
  - Separate top-level header link → rejected: clutters the main nav

### 6. Inline Imports for Pipeline Functions

The eval pipeline modules import `prompt_service` functions inline (inside function bodies) to avoid triggering `get_settings()` at module load time (which requires `OPENAI_API_KEY`). The backend API endpoints will also use inline imports for pipeline functions to avoid circular dependencies and settings initialization issues. Tests will patch at the source module path (e.g., `src.services.prompt_service.load_prompt_version`).

## Complexity Tracking

No constitution violations. No complexity justifications needed.
