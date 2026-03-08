# Implementation Plan: Unified Eval Navigation

**Branch**: `016-unified-eval-nav` | **Date**: 2026-03-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/016-unified-eval-nav/spec.md`

## Summary

Consolidate the eval dashboard (`/admin/evals`) and eval explorer (`/admin/eval-explorer`) into a unified `/admin/evals/*` section with sub-page routing, shared layout with sub-navigation, and breadcrumb navigation on detail pages. Add agent version tracking via MLflow's `enable_git_model_versioning()` to create LoggedModels per git commit, with new Agents and Trends pages showing version-based quality progression.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5 (frontend)
**Primary Dependencies**: FastAPI, Next.js 15 (App Router), MLflow 3.10.0, Recharts, Tailwind CSS
**Storage**: MLflow tracking server (LoggedModels, traces, runs); no new database tables
**Testing**: pytest (backend unit), Vitest + React Testing Library (frontend unit), Playwright (E2E)
**Target Platform**: Web (Docker + Next.js dev server)
**Project Type**: Web application (Python API + Next.js frontend)
**Performance Goals**: Admin-only pages; standard web latency (<2s page load)
**Constraints**: MLflow API calls wrapped in `run_in_executor` to avoid blocking async FastAPI
**Scale/Scope**: Single admin user; ~50 LoggedModels, ~100 experiments, ~1000 runs at scale

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Clarity over Cleverness | PASS | Components are self-contained, single-purpose; existing patterns reused |
| II. Evaluation-First | PASS | Frontend unit tests for new components; backend unit tests for new endpoints; E2E verification via Playwright |
| III. Tool Safety | N/A | No new agent tools; this is a UI feature |
| IV. Privacy by Default | PASS | Admin-only access; no user data exposed; MLflow data is eval metadata only |
| V. Consistent UX | PASS | Sub-navigation, breadcrumbs, and empty/loading/error states follow existing patterns |
| VI. Performance/Cost | PASS | No new LLM calls; MLflow API calls are lightweight reads; `run_in_executor` for async safety |
| VII. Observability | PASS | Backend endpoints use existing structured logging with correlation IDs |
| VIII. Reproducible Environments | PASS | No new dependencies; MLflow 3.10.0 already installed; `enable_git_model_versioning()` is built-in |

**Gate result: PASS** — no violations.

## Project Structure

### Documentation (this feature)

```text
specs/016-unified-eval-nav/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api.md           # New backend endpoints
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
# Backend (new/modified files)
src/
├── api/
│   ├── eval_dashboard.py        # EXISTING — no changes
│   └── eval_explorer.py         # MODIFY — add agent version endpoints
├── models/
│   └── eval_explorer.py         # MODIFY — add AgentVersion response models
eval/
└── runner.py                    # MODIFY — add enable_git_model_versioning() call

# Frontend (new/modified files)
frontend/src/
├── app/(main)/admin/evals/
│   ├── layout.tsx               # NEW — shared layout with sub-navigation
│   ├── page.tsx                 # MODIFY — dashboard landing (keep promote/run/rollback tabs)
│   ├── agents/
│   │   ├── page.tsx             # NEW — agent versions list
│   │   └── [modelId]/
│   │       └── page.tsx         # NEW — agent version detail
│   ├── experiments/
│   │   ├── page.tsx             # NEW — experiments list (wraps ExperimentBrowser)
│   │   └── [experimentId]/
│   │       └── page.tsx         # NEW — experiment detail (wraps RunBrowser + RunComparison)
│   ├── runs/
│   │   └── [runId]/
│   │       └── page.tsx         # NEW — run detail (wraps TraceViewer + SessionViewer)
│   ├── datasets/
│   │   ├── page.tsx             # NEW — datasets list (wraps DatasetViewer list mode)
│   │   └── [datasetName]/
│   │       └── page.tsx         # NEW — dataset detail (wraps DatasetViewer detail mode)
│   └── trends/
│       └── page.tsx             # NEW — unified trends (UniversalQualityChart + TrendsTab)
├── app/(main)/admin/
│   └── eval-explorer/           # DELETE — replaced by unified section
├── components/
│   ├── eval-dashboard/          # EXISTING — no changes (reused in new routes)
│   ├── eval-explorer/           # EXISTING — no changes (reused in new routes)
│   └── eval-nav/                # NEW — shared navigation components
│       ├── EvalSubNav.tsx        # Sub-navigation bar for eval section
│       └── Breadcrumb.tsx        # Breadcrumb component for detail pages
├── hooks/
│   ├── useEvalDashboard.ts      # EXISTING — no changes
│   └── useEvalExplorer.ts       # MODIFY — add useAgentVersions, useAgentVersionDetail hooks
├── types/
│   └── eval-explorer.ts         # MODIFY — add AgentVersion, AgentVersionDetail types
└── components/layout/
    ├── Header.tsx               # MODIFY — remove "Explorer" link
    └── Sidebar.tsx              # MODIFY — remove "Explorer" link

# Tests
tests/unit/
└── test_eval_explorer.py        # MODIFY — add agent version endpoint tests
frontend/tests/components/
├── eval-nav/                    # NEW
│   ├── EvalSubNav.test.tsx
│   └── Breadcrumb.test.tsx
└── eval-explorer/               # EXISTING tests — may need path updates
```

**Structure Decision**: Web application pattern. Backend adds 2 new endpoints to the existing `eval_explorer.py` router. Frontend restructures routes under `/admin/evals/` using Next.js App Router nested layouts with a shared `layout.tsx` for sub-navigation. Existing components are reused as-is — new page files are thin wrappers that import and compose them.

## Complexity Tracking

No constitution violations to justify.
