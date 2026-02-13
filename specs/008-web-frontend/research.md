# Research: Web Frontend (008)

**Date**: 2026-02-13
**Branch**: `008-web-frontend`

## Decision 1: Next.js Router

**Decision**: App Router (not Pages Router)

**Rationale**: App Router is the production standard since 2024. Provides React Server Components for heavy pages (memory, knowledge graph), built-in streaming/Suspense for SSE chat, nested layouts for shared navigation shell, and route groups for organizing views without affecting URLs.

**Alternatives considered**:
- Pages Router — legacy, missing server components and streaming primitives
- SPA (Vite + React Router) — no SSR, no middleware auth, worse SEO (not critical here but no upside vs Next.js)

## Decision 2: SSE Consumption

**Decision**: `fetch()` + `ReadableStream` with manual SSE parsing

**Rationale**: The existing `/chat` endpoint is POST with a JSON body. The browser's native `EventSource` API only supports GET requests and cannot send custom auth headers. The `fetch` + `ReadableStream` approach supports POST, auth headers, and has zero dependencies. An async generator pattern composes cleanly with React state updates.

**Alternatives considered**:
- `EventSource` — GET-only, no auth headers, no POST body
- Vercel AI SDK `useChat` — requires specific wire protocol (Data Stream Protocol), adds vendor coupling, reported compatibility issues with non-Node backends
- Third-party SSE libraries (`eventsource-parser`, `@microsoft/fetch-event-source`) — unnecessary complexity for a straightforward SSE format

## Decision 3: Authentication Architecture

**Decision**: FastAPI owns authentication (issues JWTs); Next.js stores tokens in HttpOnly cookies via Auth.js v5 (Credentials provider)

**Rationale**: FastAPI is the security boundary — all clients (web, future mobile, future voice) must authenticate against the same system. Auth.js handles cookie management, CSRF protection, and session rotation automatically. HttpOnly cookies prevent XSS token theft.

**Key design**:
- FastAPI: `/auth/login` validates credentials, returns JWT (access + refresh)
- FastAPI: All endpoints get `Depends(get_current_user)` to validate JWT
- Next.js: Auth.js Credentials provider calls FastAPI login, stores JWT in secure cookie
- Next.js: Middleware redirects unauthenticated users to `/login`
- Access tokens: 15-minute expiry; Refresh tokens: 7-day expiry

**Alternatives considered**:
- Auth only in Next.js middleware — not a security boundary, FastAPI endpoints would be unprotected
- Session-based auth (server-side sessions) — requires session store sharing between Next.js and FastAPI, more complex
- OAuth/social login — out of scope per spec (admin-created accounts only)

## Decision 4: State Management

**Decision**: Zustand for chat state; React built-in state for component-local concerns

**Rationale**: During SSE streaming, state updates dozens of times per second (per token). React Context re-renders all consumers on any change. Zustand's selector-based subscriptions let `MessageBubble` subscribe to only its own message without re-rendering when other messages update. Minimal boilerplate (~1KB).

**Alternatives considered**:
- React Context — re-renders all consumers per token during streaming, unacceptable performance
- Jotai — atomic model better for independent state pieces, chat messages are fundamentally a single ordered list
- Redux Toolkit — excessive boilerplate for this use case

## Decision 5: Markdown Rendering

**Decision**: `react-markdown` + `remark-gfm` + `react-syntax-highlighter` (Prism)

**Rationale**: `react-markdown` is the de facto standard (10M+ weekly downloads), renders as React components (safe, no `dangerouslySetInnerHTML`). `remark-gfm` adds GitHub Flavored Markdown. `react-syntax-highlighter` with Prism supports JSX/TSX and many languages the assistant will produce (Python, TypeScript, SQL, YAML, Docker). Handles partial markdown gracefully during streaming.

**Alternatives considered**:
- `rehype-highlight` (highlight.js) — fewer languages, no JSX support
- `marked` + `DOMPurify` — string-based rendering, requires sanitization, not React-native

## Decision 6: Testing Stack

**Decision**: Vitest + React Testing Library for unit/component tests; Playwright for E2E

**Rationale**: Vitest has native ESM support (no transform issues with Next.js), faster than Jest, officially recommended by Next.js docs. Playwright provides multi-browser support and better async handling than Cypress. Aligns with the project's existing pytest-based test philosophy.

**Test layers**:
- Unit: SSE parser, Zustand store state transitions, utility functions
- Component: Message rendering, input handling, streaming indicators
- E2E: Full chat flow, login flow, navigation between views, against running Docker stack

**Alternatives considered**:
- Jest — ESM transform issues with Next.js, slower
- Cypress — single-browser focus, weaker async handling

## Decision 7: Project Structure

**Decision**: `frontend/` directory at repository root, alongside existing Python `src/`

**Rationale**: Keeps the Next.js app separate from the Python backend while staying in the same git repo. The existing `docker-compose` already manages multiple services. Route groups `(auth)` and `(main)` provide different layouts without affecting URLs.

**Alternatives considered**:
- Monorepo with Turborepo — overkill for a single frontend + single backend
- Separate repository — unnecessary complexity for a personal project, harder to keep in sync

## Decision 8: Backend API Gaps

**Decision**: Add new REST endpoints to the FastAPI backend to expose existing services to the frontend

**Rationale**: The backend has comprehensive services (ConversationService, MemoryService, GraphService) but only two HTTP endpoints (`/health`, `/chat`). The frontend needs REST endpoints for conversation listing, memory browsing, knowledge graph browsing, user management, and authentication. These are thin REST wrappers around existing service methods — no new business logic required.

**New endpoints needed**:
- Auth: login, refresh token, first-run setup
- Admin: user CRUD (create, list, disable, delete)
- Conversations: list, get by ID, update title, delete
- Memories: list/search, delete
- Knowledge: search entities, get entity relationships

**Alternatives considered**:
- Frontend-only with localStorage — violates spec (backend is source of truth), no multi-device support
- GraphQL — unnecessary for this use case, adds complexity without clear benefit

## Decision 9: CSS/Styling Approach

**Decision**: Tailwind CSS

**Rationale**: Standard choice for Next.js projects, included in `create-next-app` scaffolding, utility-first approach enables rapid UI development without separate CSS files. Works well with responsive design (FR-016) via built-in breakpoint utilities.

**Alternatives considered**:
- CSS Modules — more boilerplate, harder to maintain responsive design
- styled-components — SSR complications with App Router
- shadcn/ui — can be used on top of Tailwind for pre-built accessible components (Button, Input, Dialog)
