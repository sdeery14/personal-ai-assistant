# Quickstart: Eval Explorer UI

## Prerequisites

- Docker services running (API + MLflow + PostgreSQL + Redis)
- At least one eval suite run completed (data in MLflow)
- Frontend dev server running (`cd frontend && npm run dev`)
- Admin user account (e.g., `sdeery` / `password123`)

## Development Setup

```bash
# 1. Start backend services
docker compose -f docker/docker-compose.mlflow.yml up -d
docker compose -f docker/docker-compose.api.yml up -d --build

# 2. Start frontend dev server
cd frontend && npm run dev

# 3. Navigate to explorer
# http://localhost:3000/admin/eval-explorer
# Login as admin user first
```

## Project Structure (Feature 015)

```
# Backend — new API router
src/api/eval_explorer.py              # FastAPI endpoints (GET-only)
src/models/eval_explorer.py           # Pydantic response models

# Frontend — new page and components
frontend/src/app/(main)/admin/eval-explorer/page.tsx
frontend/src/components/eval-explorer/
├── ExperimentBrowser.tsx              # Experiment list with metadata
├── RunBrowser.tsx                     # Run list within an experiment
├── TraceViewer.tsx                    # Trace list with assessment details
├── SessionViewer.tsx                  # Multi-turn session grouping
├── UniversalQualityChart.tsx          # Cross-experiment trend chart
├── DatasetViewer.tsx                  # Golden dataset browser
└── RunComparison.tsx                  # Side-by-side run diff
frontend/src/hooks/useEvalExplorer.ts  # Data-fetching hooks
frontend/src/types/eval-explorer.ts    # TypeScript interfaces

# Navigation updates
frontend/src/components/layout/Header.tsx   # Add "Eval Explorer" link
frontend/src/components/layout/Sidebar.tsx  # Add mobile nav link

# Tests
frontend/tests/components/eval-explorer/    # Frontend unit tests
tests/unit/test_eval_explorer.py            # Backend unit tests
```

## Key Patterns to Follow

### Backend API
- Mount router in `src/main.py` (same as `eval_dashboard.router`)
- Use `require_admin` dependency on all endpoints
- Call MLflow Python client in `run_in_executor()` to avoid blocking async
- Reuse normalization logic from `eval/pipeline/aggregator.py`

### Frontend Components
- Use `"use client"` directive on all components
- Follow `useEvalDashboard.ts` hook pattern (session check → apiClient.get → state)
- Use existing UI components: `Card`, `Button`, `Skeleton`, `Tabs`
- Admin access check: redirect to `/chat` if not admin
- Client-side pagination with default page size of 25

### Testing
- Backend: mock MLflow client calls, test response shapes
- Frontend: mock hooks, test component rendering with Vitest + RTL
- E2E: Playwright MCP for manual verification

## Verification

```bash
# Run backend tests
uv run pytest tests/unit/test_eval_explorer.py -v

# Run frontend tests
cd frontend && npx vitest run tests/components/eval-explorer/

# Rebuild API and verify
docker compose -f docker/docker-compose.api.yml up -d --build
# Navigate to http://localhost:3000/admin/eval-explorer
```
