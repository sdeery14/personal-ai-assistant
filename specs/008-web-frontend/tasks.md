# Tasks: Web Frontend

**Input**: Design documents from `/specs/008-web-frontend/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-contracts.yaml

**Tests**: Backend endpoint tests (pytest) are included for the new API surface since it forms the security boundary. Frontend test infrastructure is set up in Phase 1; component/E2E tests should be written alongside implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize frontend project and add backend dependencies

- [x] T001 Initialize Next.js 15 project with App Router, TypeScript, and Tailwind CSS in frontend/ using create-next-app
- [x] T002 Install frontend dependencies: zustand, react-markdown, remark-gfm, react-syntax-highlighter, next-auth@beta in frontend/package.json
- [x] T003 [P] Add backend Python dependencies (PyJWT, bcrypt, python-multipart) via uv add in pyproject.toml
- [x] T004 [P] Create frontend environment template with NEXT_PUBLIC_API_URL and AUTH_SECRET in frontend/.env.example
- [x] T005 [P] Configure Vitest with React Testing Library and jsdom environment in frontend/vitest.config.ts and frontend/tests/setup.ts
- [x] T006 [P] Configure Playwright for E2E tests in frontend/playwright.config.ts

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Authentication, user management, and auth-protected API surface. MUST complete before ANY user story.

**CRITICAL**: No user story work can begin until this phase is complete.

### Database Migrations

- [x] T007 Create SQL migration for users table (id, username, password_hash, display_name, is_admin, is_active, created_at, updated_at) in migrations/007_users.sql
- [x] T008 Create SQL migration for refresh_tokens table (id, user_id FK, token_hash, expires_at, revoked_at, created_at) in migrations/008_refresh_tokens.sql
- [x] T009 [P] Create SQL migration adding index on conversations(user_id, updated_at DESC) in migrations/009_conversation_user_index.sql

### Backend: Auth & User Models

- [x] T010 Create User and RefreshToken Pydantic models in src/models/user.py
- [x] T011 [P] Create auth request/response Pydantic models (LoginRequest, LoginResponse, SetupRequest, RefreshRequest, UserSummary, CreateUserRequest, UpdateUserRequest) in src/models/auth.py

### Backend: Auth & User Services

- [x] T012 Implement AuthService (password hashing with bcrypt, JWT access token creation/validation with 15min expiry, refresh token creation/rotation/revocation with 7-day expiry) in src/services/auth_service.py
- [x] T013 Implement UserService (create_user, get_by_username, get_by_id, list_users, update_user, delete_user, count_users, check admin constraints) in src/services/user_service.py

### Backend: Auth API Endpoints

- [x] T014 Create auth dependencies (get_current_user extracts user from JWT Bearer token, require_admin checks is_admin flag) in src/api/dependencies.py
- [x] T015 Implement auth endpoints (POST /auth/setup, POST /auth/login, POST /auth/refresh, GET /auth/status, GET /auth/me) in src/api/auth.py
- [x] T016 [P] Implement admin endpoints (GET /admin/users, POST /admin/users, PATCH /admin/users/{user_id}, DELETE /admin/users/{user_id}) in src/api/admin.py
- [x] T017 Register auth and admin routers in src/main.py and update CORS configuration
- [x] T018 Modify /chat endpoint to require authentication — add get_current_user dependency, derive user_id from JWT instead of request body in src/api/routes.py

### Backend: Auth Tests

- [x] T019 Write pytest tests for AuthService (password hashing, JWT creation/validation, token expiry, refresh rotation) in tests/unit/test_auth_service.py
- [x] T020 [P] Write pytest tests for UserService (create, get, list, update, delete, admin constraints) in tests/unit/test_user_service.py
- [x] T021 [P] Write pytest tests for auth endpoints (setup flow, login, refresh, invalid credentials, disabled user) in tests/unit/test_auth_endpoints.py
- [x] T022 [P] Write pytest tests for admin endpoints (CRUD, admin-only access, self-delete prevention) in tests/unit/test_admin_endpoints.py

### Frontend: Core Infrastructure

- [x] T023 [P] Define TypeScript types for auth (User, LoginRequest, LoginResponse, SetupRequest) in frontend/src/types/auth.ts
- [x] T024 [P] Define TypeScript types for chat (StreamChunk, ChatMessage, Conversation) in frontend/src/types/chat.ts
- [x] T025 [P] Define TypeScript types for memory (MemoryItem, MemoryType) in frontend/src/types/memory.ts
- [x] T026 [P] Define TypeScript types for knowledge graph (Entity, EntityType, Relationship, RelationshipType) in frontend/src/types/knowledge.ts
- [x] T027 Implement typed API client (fetch wrapper with Bearer auth header injection, error handling, JSON parsing, base URL config) in frontend/src/lib/api-client.ts
- [x] T028 Configure Auth.js v5 with Credentials provider that calls POST /auth/login, stores JWT in session, exposes accessToken to client in frontend/src/lib/auth.ts
- [x] T029 Create Auth.js API route handler in frontend/src/app/api/auth/[...nextauth]/route.ts
- [x] T030 Create Next.js middleware for route protection (redirect unauthenticated users to /login, allow /login and /setup without auth) in frontend/src/middleware.ts

### Frontend: Shared UI & Layouts

- [x] T031 [P] Create shared UI primitives (Button, Input, Card, Dialog with confirmation) in frontend/src/components/ui/
- [x] T032 Create root layout with AuthProvider, global Tailwind styles, and base metadata in frontend/src/app/layout.tsx
- [x] T033 Create auth layout (centered, no sidebar) in frontend/src/app/(auth)/layout.tsx
- [x] T034 Implement login page with username/password form, error display, and submit to Auth.js signIn in frontend/src/app/(auth)/login/page.tsx
- [x] T035 Implement first-run setup page (calls GET /auth/status to check, shows admin registration form, calls POST /auth/setup, auto-logs in on success) in frontend/src/app/(auth)/setup/page.tsx
- [x] T036 Create root page.tsx that checks auth state and setup status, redirects to /setup, /login, or /chat accordingly in frontend/src/app/page.tsx

**Checkpoint**: Auth working end-to-end. Can create admin via setup, login, access protected routes. Backend endpoints require valid JWT.

---

## Phase 3: User Story 1 — Real-Time Streaming Chat (Priority: P1) MVP

**Goal**: User can open the app, send a message, and see the assistant's response stream in real time with multi-turn conversation support.

**Independent Test**: Open browser, login, send a message, verify response streams word-by-word. Send follow-up and verify context awareness.

### Implementation for User Story 1

- [x] T037 [US1] Implement SSE streaming helper using fetch + ReadableStream async generator with auth headers and AbortController support in frontend/src/lib/chat-stream.ts
- [x] T038 [US1] Create Zustand chat store (messages array, conversationId, isStreaming, error state, addUserMessage, appendStreamChunk, finalizeStream, clearMessages) in frontend/src/stores/chat-store.ts
- [x] T039 [US1] Implement useChat hook that orchestrates: add user message to store → call chat-stream → update store per chunk → finalize on completion in frontend/src/hooks/useChat.ts
- [x] T040 [P] [US1] Create ChatInput component (textarea with Enter=submit, Shift+Enter=newline, disabled during streaming, empty prevention, 8000 char limit indicator) in frontend/src/components/chat/ChatInput.tsx
- [x] T041 [P] [US1] Create MessageBubble component with role-based styling and markdown rendering (react-markdown + remark-gfm + react-syntax-highlighter with Prism) in frontend/src/components/chat/MessageBubble.tsx
- [x] T042 [P] [US1] Create StreamingIndicator component (animated dots or pulsing cursor, shown when isStreaming=true) in frontend/src/components/chat/StreamingIndicator.tsx
- [x] T043 [US1] Create MessageList component with auto-scroll (scroll to bottom on new content unless user has scrolled up, resume auto-scroll when user scrolls to bottom) in frontend/src/components/chat/MessageList.tsx
- [x] T044 [US1] Create ChatPanel component (composes MessageList + ChatInput + StreamingIndicator, empty state for new conversations) in frontend/src/components/chat/ChatPanel.tsx
- [x] T045 [US1] Create Header component with user display name and logout button in frontend/src/components/layout/Header.tsx
- [x] T046 [US1] Create main layout with Header (Sidebar deferred to US2) in frontend/src/app/(main)/layout.tsx
- [x] T047 [US1] Create chat page that renders ChatPanel, connects to useChat hook in frontend/src/app/(main)/chat/page.tsx

**Checkpoint**: MVP complete. User can login, send messages, see streaming responses. Multi-turn conversation works within a session.

---

## Phase 4: User Story 2 — Conversation Management (Priority: P2)

**Goal**: User can start new conversations, switch between existing ones, view past conversations in a sidebar, rename and delete conversations.

**Independent Test**: Create multiple conversations, navigate between them, verify each retains its message history. Rename and delete a conversation.

### Backend for User Story 2

- [x] T048 [US2] Implement conversation REST endpoints: GET /conversations (paginated, ordered by updated_at desc), GET /conversations/{id} (with messages), PATCH /conversations/{id} (rename), DELETE /conversations/{id} in src/api/conversations.py
- [x] T049 [US2] Add auto-title generation logic — set conversation title from first user message (truncate to ~80 chars) when title is null in src/services/conversation_service.py
- [x] T050 [US2] Register conversations router in src/main.py
- [x] T051 [P] [US2] Write pytest tests for conversation endpoints (list, get, update title, delete, user isolation — cannot access another user's conversations) in tests/unit/test_conversation_endpoints.py

### Frontend for User Story 2

- [x] T052 [US2] Implement useConversations hook (fetch paginated list, create new, select/load, rename, delete) in frontend/src/hooks/useConversations.ts
- [x] T053 [P] [US2] Create ConversationItem component (title display, timestamp, inline rename on double-click, delete button with confirmation dialog) in frontend/src/components/conversation/ConversationItem.tsx
- [x] T054 [US2] Create ConversationList component (scrollable list of ConversationItem, "New conversation" button at top, pagination/load more) in frontend/src/components/conversation/ConversationList.tsx
- [x] T055 [US2] Create Sidebar component with ConversationList and navigation links (Chat, Memory, Knowledge, Admin if admin user) in frontend/src/components/layout/Sidebar.tsx
- [x] T056 [US2] Update main layout to include Sidebar (responsive: collapsible drawer on mobile, persistent on desktop) in frontend/src/app/(main)/layout.tsx
- [x] T057 [US2] Update chat store to support conversation switching — clearMessages, loadConversation (fetch messages from API), setConversationId in frontend/src/stores/chat-store.ts
- [x] T058 [US2] Integrate conversation management with chat page — select conversation loads messages, new conversation clears chat, conversation title updates after first message in frontend/src/app/(main)/chat/page.tsx

**Checkpoint**: Full conversation management. User can create, switch, rename, and delete conversations. Sidebar shows conversation history.

---

## Phase 5: User Story 4 — Error Handling & Connection Resilience (Priority: P2)

**Goal**: User sees clear, actionable error messages for all failure modes (service down, guardrail block, timeout, connection loss). Can retry without re-typing.

**Independent Test**: Simulate each error condition (stop backend, trigger guardrail, disconnect network, wait for timeout) and verify appropriate error messages appear with retry option.

### Implementation for User Story 4

- [x] T059 [US4] Create ErrorBoundary component with user-friendly fallback UI (what happened, why, what to do) in frontend/src/components/layout/ErrorBoundary.tsx
- [x] T060 [US4] Add error state handling in chat-store — store last failed message for retry, parse SSE error events (guardrail_violation, timeout, generic error) in frontend/src/stores/chat-store.ts
- [x] T061 [US4] Create ChatError component that displays contextual error messages (service unavailable → retry, guardrail → rephrase, timeout → retry, connection lost → reconnect) with retry button in frontend/src/components/chat/ChatError.tsx
- [x] T062 [US4] Add retry mechanism to useChat hook — resend last user message on retry action, preserve unsent draft message on error in frontend/src/hooks/useChat.ts
- [x] T063 [US4] Add connection loss detection in chat-stream.ts — handle fetch failures, AbortController timeout, ReadableStream errors, return structured error types in frontend/src/lib/chat-stream.ts
- [x] T064 [US4] Add automatic 401 detection and session expiry handling in API client — redirect to login, preserve current URL for post-login redirect in frontend/src/lib/api-client.ts
- [x] T065 [US4] Wrap main layout with ErrorBoundary and integrate ChatError into ChatPanel in frontend/src/app/(main)/layout.tsx

**Checkpoint**: All error paths tested. No silent failures. Every error shows user-friendly message with actionable next step.

---

## Phase 6: User Story 3 — Memory & Knowledge Visibility (Priority: P3)

**Goal**: User can browse stored memories (with search and type filter), view knowledge graph entities and their relationships, and delete memories.

**Independent Test**: Navigate to memory view, verify memories display with types and sources. Search and filter. Navigate to knowledge view, search entities, expand to see relationships. Delete a memory and verify it's removed.

### Backend for User Story 3

- [x] T066 [US3] Implement memory REST endpoints: GET /memories (paginated, with optional q search and type filter), DELETE /memories/{memory_id} (soft delete, user-scoped) in src/api/memories.py
- [x] T067 [P] [US3] Implement entity REST endpoints: GET /entities (paginated, with optional q search and type filter), GET /entities/{entity_id}/relationships (user-scoped) in src/api/entities.py
- [x] T068 [US3] Register memories and entities routers in src/main.py
- [x] T069 [P] [US3] Write pytest tests for memory endpoints (list, search, filter by type, delete, user isolation) in tests/unit/test_memory_endpoints.py
- [x] T070 [P] [US3] Write pytest tests for entity endpoints (list, search, filter by type, relationships, user isolation) in tests/unit/test_entity_endpoints.py

### Frontend for User Story 3

- [x] T071 [US3] Implement useMemories hook (fetch paginated list, search by query, filter by type, delete with optimistic update) in frontend/src/hooks/useMemories.ts
- [x] T072 [P] [US3] Implement useEntities hook (fetch paginated list, search, filter by type, fetch relationships for expanded entity) in frontend/src/hooks/useEntities.ts
- [x] T073 [P] [US3] Create MemoryCard component (type badge with color, content text, source conversation link, created_at timestamp, importance indicator, delete button with confirmation) in frontend/src/components/memory/MemoryCard.tsx
- [x] T074 [US3] Create MemoryList component (search input, type filter dropdown, paginated list of MemoryCard, empty state) in frontend/src/components/memory/MemoryList.tsx
- [x] T075 [US3] Create memory page rendering MemoryList in frontend/src/app/(main)/memory/page.tsx
- [x] T076 [P] [US3] Create EntityDetail component (expandable card: name, type badge, aliases, description, relationships rendered as typed sub-list items with target entity names) in frontend/src/components/knowledge/EntityDetail.tsx
- [x] T077 [US3] Create EntityList component (search input, type filter dropdown, list of expandable EntityDetail, empty state) in frontend/src/components/knowledge/EntityList.tsx
- [x] T078 [US3] Create knowledge page rendering EntityList in frontend/src/app/(main)/knowledge/page.tsx
- [x] T079 [US3] Add Memory and Knowledge nav links to Sidebar in frontend/src/components/layout/Sidebar.tsx

**Checkpoint**: Memory and knowledge graph fully visible. User can search, filter, inspect, and delete memories. Entities show relationships.

---

## Phase 7: Admin User Management

**Purpose**: Admin UI for managing user accounts (FR-023).

- [x] T080 Create admin page with user list table, create user form (username, password, display_name, is_admin toggle), disable/enable and delete actions with confirmations in frontend/src/app/(main)/admin/page.tsx
- [x] T081 Add admin nav link to Sidebar (visible only when current user is_admin=true) in frontend/src/components/layout/Sidebar.tsx

**Checkpoint**: Admin can create, disable, and remove user accounts from the UI.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Responsive design, production readiness, documentation

- [x] T082 [P] Apply responsive design to all layouts — Sidebar as collapsible drawer on mobile (below 768px), full-width chat on mobile, stacked layouts on small screens in frontend/src/
- [x] T083 [P] Add loading skeleton states for conversation list, memory list, entity list, and chat message loading in frontend/src/components/
- [x] T084 [P] Create Dockerfile.frontend for production Next.js build (multi-stage: install deps → build → standalone output) in docker/Dockerfile.frontend
- [x] T085 [P] Create docker-compose.frontend.yml with frontend service proxying to API backend in docker/docker-compose.frontend.yml
- [x] T086 Verify all acceptance scenarios from spec.md work end-to-end across all user stories
- [x] T087 Update CLAUDE.md with frontend development commands (npm install, npm run dev, npm test, playwright test) and updated project structure

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — delivers MVP
- **US2 (Phase 4)**: Depends on Phase 2. Integrates with US1 (ChatPanel) but is independently testable
- **US4 (Phase 5)**: Depends on Phase 2. Enhances US1 chat experience but is independently testable
- **US3 (Phase 6)**: Depends on Phase 2. Fully independent of US1/US2/US4
- **Admin (Phase 7)**: Depends on Phase 2 (admin backend already done). Independent of all user stories
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

```
Phase 1 (Setup)
    │
    ▼
Phase 2 (Foundational) ──── BLOCKS ALL ────┐
    │                                       │
    ▼                                       ▼
Phase 3 (US1: Chat) ◄──── MVP         Phase 6 (US3: Memory/Knowledge)
    │                                       │
    ├──► Phase 4 (US2: Conversations)  Phase 7 (Admin)
    │                                       │
    ├──► Phase 5 (US4: Error Handling)      │
    │                                       │
    ▼                                       ▼
Phase 8 (Polish) ◄─────────────────────────┘
```

### Within Each User Story

1. Backend endpoints → Backend tests → Frontend hooks → Frontend components → Frontend pages → Integration
2. Models/types before services
3. [P] tasks within a phase can run in parallel

### Parallel Opportunities

**Phase 2 parallelism**:
- T007, T008, T009 (migrations) can run in parallel
- T010, T011 (models) can run in parallel
- T019, T020, T021, T022 (backend tests) can run in parallel
- T023, T024, T025, T026 (TypeScript types) can run in parallel

**Phase 3 (US1) parallelism**:
- T040, T041, T042 (ChatInput, MessageBubble, StreamingIndicator) can run in parallel

**Phase 4 (US2) parallelism**:
- T051 (backend tests) runs in parallel with frontend work after T050

**Phase 6 (US3) parallelism**:
- T067 (entity endpoints) in parallel with T066 (memory endpoints)
- T069, T070 (backend tests) in parallel
- T071, T072 (hooks) in parallel
- T073, T076 (MemoryCard, EntityDetail) in parallel

**Cross-phase parallelism** (after Phase 2 completes):
- US1 (Phase 3) and US3 (Phase 6) can run in parallel — no dependencies between them
- US2 (Phase 4) and US3 (Phase 6) can run in parallel
- Admin (Phase 7) can run in parallel with any user story phase

---

## Parallel Example: User Story 1

```bash
# After T039 (useChat hook) completes, launch these in parallel:
Task: "T040 [P] [US1] Create ChatInput component in frontend/src/components/chat/ChatInput.tsx"
Task: "T041 [P] [US1] Create MessageBubble component in frontend/src/components/chat/MessageBubble.tsx"
Task: "T042 [P] [US1] Create StreamingIndicator component in frontend/src/components/chat/StreamingIndicator.tsx"
```

## Parallel Example: User Story 3

```bash
# After T068 (register routers) completes, launch these in parallel:
Task: "T069 [P] [US3] Write pytest tests for memory endpoints in tests/unit/test_memory_endpoints.py"
Task: "T070 [P] [US3] Write pytest tests for entity endpoints in tests/unit/test_entity_endpoints.py"

# After hooks complete, launch these in parallel:
Task: "T073 [P] [US3] Create MemoryCard component in frontend/src/components/memory/MemoryCard.tsx"
Task: "T076 [P] [US3] Create EntityDetail component in frontend/src/components/knowledge/EntityDetail.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T006)
2. Complete Phase 2: Foundational (T007–T036)
3. Complete Phase 3: User Story 1 (T037–T047)
4. **STOP and VALIDATE**: Login, send message, see streaming response
5. Deploy/demo — working chat in the browser

### Incremental Delivery

1. Setup + Foundational → Auth working, backend secured
2. Add US1 → **MVP: Chat in the browser** (deploy)
3. Add US2 → Conversation history and sidebar (deploy)
4. Add US4 → Bulletproof error handling (deploy)
5. Add US3 → Memory and knowledge visibility (deploy)
6. Add Admin → User management UI (deploy)
7. Polish → Responsive, loading states, Docker (deploy)

### Estimated Scope

| Phase | Tasks | Parallel Tasks |
|-------|-------|----------------|
| Phase 1: Setup | 6 | 4 |
| Phase 2: Foundational | 30 | 14 |
| Phase 3: US1 Chat | 11 | 3 |
| Phase 4: US2 Conversations | 11 | 2 |
| Phase 5: US4 Errors | 7 | 0 |
| Phase 6: US3 Memory/Knowledge | 14 | 7 |
| Phase 7: Admin | 2 | 0 |
| Phase 8: Polish | 6 | 4 |
| **Total** | **87** | **34** |

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks in the same phase
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Backend tests use pytest with mocked DB (following existing test patterns in tests/unit/)
- Frontend component tests (Vitest + RTL) should be written alongside component implementation
