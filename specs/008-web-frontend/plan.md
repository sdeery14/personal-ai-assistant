# Implementation Plan: Web Frontend

**Branch**: `008-web-frontend` | **Date**: 2026-02-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-web-frontend/spec.md`

## Summary

Build a Next.js web frontend that provides a browser-based chat interface consuming the existing FastAPI SSE streaming API. Adds authentication (JWT), conversation management, memory browsing, and knowledge graph visibility. Requires new backend REST endpoints to expose existing services (ConversationService, MemoryService, GraphService) plus a new User/Auth layer.

## Technical Context

**Language/Version**: TypeScript 5.x (frontend), Python 3.11 (backend additions)
**Primary Dependencies**: Next.js 15 (App Router), React 19, Tailwind CSS, Zustand, Auth.js v5, react-markdown; FastAPI (existing), PyJWT, bcrypt (backend additions)
**Storage**: PostgreSQL (existing) — new `users` and `refresh_tokens` tables; Redis (existing) — no changes
**Testing**: Vitest + React Testing Library (frontend unit/component), Playwright (E2E), pytest (backend)
**Target Platform**: Modern browsers (Chrome, Firefox, Safari, Edge), responsive to 375px
**Project Type**: Web application (frontend + backend in same repo)
**Performance Goals**: First streamed token visible within 2s of message submission (SC-001); page navigation <500ms
**Constraints**: Must work with existing Docker infrastructure; backend Python dependencies managed with `uv`
**Scale/Scope**: Small user base (admin-provisioned accounts), hundreds of conversations per user

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Clarity over Cleverness | PASS | Single-responsibility components: each page/component has one purpose. TypeScript explicit types. No magic behavior. |
| II. Evaluation-First Behavior | PASS | Vitest for frontend unit/component tests, Playwright for E2E, pytest for new backend endpoints. Tests before implementation. |
| III. Tool Safety and Correctness | PASS | No new agent tools. Frontend only calls validated REST endpoints. Existing tool schema validation unchanged. |
| IV. Privacy by Default | PASS | Auth tokens in HttpOnly cookies (no XSS exposure). Passwords bcrypt-hashed. User data isolated by user_id with JWT-enforced scoping. No PII in logs. |
| V. Consistent UX | PASS | Error messages follow three-part format (what/why/what-to-do). Confirmations for destructive actions (delete conversation, delete memory). Streaming indicator for response generation. |
| VI. Performance and Cost Budgets | PASS | No new LLM calls (frontend is a view layer). SSE streaming keeps time-to-first-token low. Zustand prevents unnecessary re-renders during streaming. |
| VII. Observability and Debuggability | PASS | Correlation IDs flow from frontend to backend. Backend structured logging already in place. Frontend errors logged with context. |
| VIII. Reproducible Environments | PASS | Backend: `uv sync` (existing). Frontend: `package-lock.json` committed, `npm ci` in CI. Docker Compose for consistent deployment. |

**Post-Phase 1 re-check**: All gates still pass. JWT auth adds the required security boundary. Data model changes are additive (new tables, FK constraint). No new complexity violations.

## Project Structure

### Documentation (this feature)

```text
specs/008-web-frontend/
├── plan.md              # This file
├── research.md          # Phase 0 output — technology decisions
├── data-model.md        # Phase 1 output — new/modified tables
├── quickstart.md        # Phase 1 output — dev setup guide
├── contracts/
│   └── api-contracts.yaml  # Phase 1 output — OpenAPI spec for new endpoints
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
# Backend additions (Python/FastAPI)
src/
├── api/
│   ├── routes.py            # MODIFIED: add auth dependency to /chat
│   ├── auth.py              # NEW: /auth/* endpoints (login, refresh, setup, status, me)
│   ├── conversations.py     # NEW: /conversations/* endpoints (list, get, update, delete)
│   ├── memories.py          # NEW: /memories/* endpoints (list/search, delete)
│   ├── entities.py          # NEW: /entities/* endpoints (search, relationships)
│   ├── admin.py             # NEW: /admin/users/* endpoints (CRUD)
│   └── dependencies.py      # NEW: get_current_user, require_admin dependencies
├── models/
│   ├── user.py              # NEW: User, RefreshToken, auth request/response models
│   └── ...                  # EXISTING: unchanged
└── services/
    ├── auth_service.py      # NEW: JWT creation/validation, password hashing
    ├── user_service.py      # NEW: User CRUD operations
    └── ...                  # EXISTING: unchanged

# Database migrations
alembic/versions/
├── xxx_add_users_table.py           # NEW
├── xxx_add_refresh_tokens_table.py  # NEW
└── xxx_add_conversation_indexes.py  # NEW

# Frontend (Next.js)
frontend/
├── next.config.ts
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── .env.example
├── src/
│   ├── app/
│   │   ├── layout.tsx                # Root layout (providers, global styles)
│   │   ├── page.tsx                  # Redirect to /chat or /login
│   │   ├── (auth)/
│   │   │   ├── layout.tsx            # Auth layout (no sidebar)
│   │   │   ├── login/page.tsx        # Login form
│   │   │   └── setup/page.tsx        # First-run admin setup
│   │   ├── (main)/
│   │   │   ├── layout.tsx            # Main layout (sidebar + nav)
│   │   │   ├── chat/
│   │   │   │   └── page.tsx          # Chat view
│   │   │   ├── memory/
│   │   │   │   └── page.tsx          # Memory browser
│   │   │   ├── knowledge/
│   │   │   │   └── page.tsx          # Entity list with relationships
│   │   │   └── admin/
│   │   │       └── page.tsx          # User management (admin only)
│   │   └── api/
│   │       └── auth/[...nextauth]/
│   │           └── route.ts          # Auth.js API routes
│   ├── components/
│   │   ├── ui/                       # Generic primitives (Button, Input, Card, Dialog)
│   │   ├── chat/
│   │   │   ├── ChatPanel.tsx         # Main chat container
│   │   │   ├── MessageList.tsx       # Scrollable message list with auto-scroll
│   │   │   ├── MessageBubble.tsx     # Single message with markdown rendering
│   │   │   ├── ChatInput.tsx         # Input bar (Enter submit, Shift+Enter newline)
│   │   │   └── StreamingIndicator.tsx
│   │   ├── memory/
│   │   │   ├── MemoryList.tsx        # Memory item list with type filters
│   │   │   └── MemoryCard.tsx        # Single memory with details + delete
│   │   ├── knowledge/
│   │   │   ├── EntityList.tsx        # Searchable entity list
│   │   │   └── EntityDetail.tsx      # Expandable entity with relationships
│   │   ├── conversation/
│   │   │   ├── ConversationList.tsx  # Sidebar conversation list
│   │   │   └── ConversationItem.tsx  # Single conversation (title, timestamp, delete)
│   │   └── layout/
│   │       ├── Sidebar.tsx           # Navigation sidebar
│   │       ├── Header.tsx            # Top bar with user info
│   │       └── ErrorBoundary.tsx     # Global error boundary
│   ├── lib/
│   │   ├── api-client.ts            # Typed fetch wrapper for all backend endpoints
│   │   ├── chat-stream.ts           # SSE streaming via fetch + ReadableStream
│   │   ├── auth.ts                  # Auth.js v5 configuration
│   │   └── utils.ts                 # Shared utilities (formatDate, truncate, etc.)
│   ├── hooks/
│   │   ├── useChat.ts               # Chat state + streaming orchestration
│   │   ├── useConversations.ts      # Conversation list management
│   │   ├── useMemories.ts           # Memory browsing
│   │   └── useEntities.ts           # Entity search + relationship expansion
│   ├── stores/
│   │   └── chat-store.ts            # Zustand store for chat messages + streaming state
│   └── types/
│       ├── chat.ts                  # StreamChunk, ChatMessage, Conversation
│       ├── memory.ts                # MemoryItem, MemoryType
│       ├── knowledge.ts             # Entity, Relationship, EntityType
│       └── auth.ts                  # User, LoginRequest, etc.
├── tests/
│   ├── e2e/                         # Playwright tests
│   │   ├── chat.spec.ts
│   │   ├── auth.spec.ts
│   │   └── navigation.spec.ts
│   ├── components/                  # Vitest + React Testing Library
│   │   ├── ChatInput.test.tsx
│   │   ├── MessageBubble.test.tsx
│   │   └── ConversationList.test.tsx
│   └── lib/                         # Unit tests
│       ├── chat-stream.test.ts
│       └── api-client.test.ts
└── playwright.config.ts

# Docker
docker/
├── Dockerfile.frontend              # NEW: Next.js production build
└── docker-compose.frontend.yml      # NEW: Frontend service
```

**Structure Decision**: Web application layout with `frontend/` at repo root alongside existing Python `src/`. Backend additions follow existing patterns (new route files registered in `main.py`, new services following existing conventions). Frontend uses Next.js App Router with route groups for layout separation.

## Complexity Tracking

No constitution violations to justify. All patterns are standard:
- JWT auth is the standard approach for API authentication
- New REST endpoints are thin wrappers around existing services
- Next.js App Router is the standard React framework
- No new abstractions beyond what's required
