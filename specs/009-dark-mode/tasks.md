# Tasks: Dark Mode & Theming

**Input**: Design documents from `/specs/009-dark-mode/`
**Prerequisites**: plan.md, spec.md, research.md, quickstart.md

**Tests**: No automated tests requested. Validation is visual inspection per quickstart.md scenarios.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Install dependency and configure Tailwind dark mode infrastructure

- [x] T001 Install next-themes dependency in frontend/package.json via `npm install next-themes`
- [x] T002 Add `@custom-variant dark (&:where(.dark, .dark *));` and dark-mode CSS custom properties to frontend/src/app/globals.css (replace the existing light-mode-only placeholder comment)
- [x] T003 Wrap app with ThemeProvider (attribute="class", defaultTheme="system", enableSystem) and add suppressHydrationWarning to `<html>` in frontend/src/app/layout.tsx

**Checkpoint**: Dark mode infrastructure ready — `dark:` Tailwind variants now work throughout the app

---

## Phase 2: User Story 1 + 2 — Auto Detection & Manual Toggle (Priority: P1)

**Goal**: App detects OS theme preference automatically and provides a 3-way toggle (Light/Dark/System) in the header

**Independent Test**: Toggle OS dark mode → app follows. Click toggle → app switches. Select System → app follows OS.

- [x] T004 [US2] Create ThemeToggle component with 3-way cycle (Light → Dark → System) using useTheme() hook, mounted state pattern, and sun/moon/monitor icons in frontend/src/components/layout/ThemeToggle.tsx
- [x] T005 [US1] [US2] Add ThemeToggle to Header component next to the user name / sign out area in frontend/src/components/layout/Header.tsx

**Checkpoint**: Theme auto-detection (US1), manual toggle (US2), and persistence (US3 — handled by next-themes automatically) all work

---

## Phase 3: User Story 4 — Consistent Dark Palette: UI Primitives (Priority: P2)

**Goal**: All shared UI components render correctly in both light and dark mode

**Independent Test**: Navigate to any page using these components in dark mode — all elements readable

- [x] T006 [P] [US4] Add dark variants to Button component (all variants: primary, secondary, danger, ghost; hover, focus, disabled states) in frontend/src/components/ui/Button.tsx
- [x] T007 [P] [US4] Add dark variants to Input component (background, border, label, error text, focus ring) in frontend/src/components/ui/Input.tsx
- [x] T008 [P] [US4] Add dark variants to Card component (background, border, shadow) in frontend/src/components/ui/Card.tsx
- [x] T009 [P] [US4] Add dark variants to Dialog component (overlay, panel background, border, button styling) in frontend/src/components/ui/Dialog.tsx
- [x] T010 [P] [US4] Add dark variants to Skeleton component (pulse animation color) in frontend/src/components/ui/Skeleton.tsx

**Checkpoint**: All 5 UI primitives themed — any component using them inherits dark mode support

---

## Phase 4: User Story 4 — Consistent Dark Palette: Layout Components (Priority: P2)

**Goal**: Header, sidebar, error boundary render correctly in dark mode

- [x] T011 [P] [US4] Add dark variants to Header component (background, border, text, sign-out button) in frontend/src/components/layout/Header.tsx
- [x] T012 [P] [US4] Add dark variants to Sidebar component (background, nav links, active state, mobile drawer overlay, hamburger icon) in frontend/src/components/layout/Sidebar.tsx
- [x] T013 [P] [US4] Add dark variants to ErrorBoundary fallback UI (background, text, retry button) in frontend/src/components/layout/ErrorBoundary.tsx

**Checkpoint**: Layout shell fully themed

---

## Phase 5: User Story 4 — Consistent Dark Palette: Chat Components (Priority: P2)

**Goal**: Chat page renders correctly in dark mode including streaming and code blocks

- [x] T014 [P] [US4] Add dark variants to ChatInput component (textarea background, border, placeholder text, send button) in frontend/src/components/chat/ChatInput.tsx
- [x] T015 [P] [US4] Add dark variants to ChatError component (error backgrounds per type, text, retry button) in frontend/src/components/chat/ChatError.tsx
- [x] T016 [P] [US4] Add dark variants to MessageBubble component (user/assistant bubble backgrounds, text) and switch syntax highlighter to vscDarkPlus in dark mode using useTheme() + resolvedTheme in frontend/src/components/chat/MessageBubble.tsx
- [x] T017 [P] [US4] Add dark variants to MessageList component (empty state text, scroll-to-bottom button) in frontend/src/components/chat/MessageList.tsx
- [x] T018 [P] [US4] Add dark variants to StreamingIndicator component (dot colors, label text) in frontend/src/components/chat/StreamingIndicator.tsx

**Checkpoint**: Chat page fully themed with dark-appropriate syntax highlighting

---

## Phase 6: User Story 4 — Consistent Dark Palette: Conversation, Memory, Knowledge (Priority: P2)

**Goal**: Sidebar conversations, memory page, and knowledge page render correctly in dark mode

- [x] T019 [P] [US4] Add dark variants to ConversationItem component (item background, hover, active highlight, title text, timestamp, delete/rename controls) in frontend/src/components/conversation/ConversationItem.tsx
- [x] T020 [P] [US4] Add dark variants to ConversationList component (list background, new conversation button, load more button) in frontend/src/components/conversation/ConversationList.tsx
- [x] T021 [P] [US4] Add dark variants to MemoryCard component (card background, type badge colors for all types, content text, date text, delete button, confirmation dialog) in frontend/src/components/memory/MemoryCard.tsx
- [x] T022 [P] [US4] Add dark variants to MemoryList component (search input, type filter buttons active/inactive states, empty state text) in frontend/src/components/memory/MemoryList.tsx
- [x] T023 [P] [US4] Add dark variants to EntityDetail component (detail panel background, type badge, description, aliases, relationship list, relationship type labels) in frontend/src/components/knowledge/EntityDetail.tsx
- [x] T024 [P] [US4] Add dark variants to EntityList component (search input, type filter buttons, empty state, entity count text) in frontend/src/components/knowledge/EntityList.tsx

**Checkpoint**: Conversation sidebar, memory page, and knowledge page fully themed

---

## Phase 7: User Story 4 — Consistent Dark Palette: Pages & Layouts (Priority: P2)

**Goal**: All page-level and layout-level backgrounds and text properly themed

- [x] T025 [P] [US4] Add dark variants to auth layout (centered background) in frontend/src/app/(auth)/layout.tsx
- [x] T026 [P] [US4] Add dark variants to login page (heading text, form styling, error text) in frontend/src/app/(auth)/login/page.tsx
- [x] T027 [P] [US4] Add dark variants to setup page (heading, form, status messages, loading state) in frontend/src/app/(auth)/setup/page.tsx
- [x] T028 [P] [US4] Add dark variants to main layout (background) in frontend/src/app/(main)/layout.tsx
- [x] T029 [US4] Add dark variants to admin page (user table, table headers, row borders, create form, status badges, action buttons) in frontend/src/app/(main)/admin/page.tsx

**Checkpoint**: All pages and layouts fully themed

---

## Phase 8: Polish & Validation

**Purpose**: Final verification across all user stories and edge cases

- [x] T030 Build the frontend (`npx next build`) and verify no TypeScript or build errors
- [x] T031 Run quickstart.md validation scenarios: verify all 7 scenarios pass (system detection, toggle, persistence, all-pages audit, code block theming, FOUC check, edge cases)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (US1+US2 Toggle)**: Depends on Phase 1 (ThemeProvider must be configured)
- **Phases 3–7 (US4 Dark Palette)**: Depend on Phase 1 (dark variant CSS must be configured). Can run in parallel with Phase 2.
- **Phase 8 (Polish)**: Depends on all previous phases

### User Story Dependencies

- **US1 (Auto Detection)**: Phase 1 setup only — next-themes handles detection automatically
- **US2 (Manual Toggle)**: Phase 1 setup + ThemeToggle component
- **US3 (Persistence)**: Fully handled by next-themes — no dedicated tasks needed
- **US4 (Consistent Palette)**: Phase 1 setup, then all component/page updates (Phases 3–7)

### Parallel Opportunities

Within Phases 3–7, **all tasks marked [P] can run in parallel** since each modifies a different file with no interdependencies. This means up to 19 component updates can run concurrently.

---

## Implementation Strategy

### MVP First (Phase 1 + Phase 2)

1. Complete Phase 1: Install next-themes, configure Tailwind dark variant, wrap app with ThemeProvider
2. Complete Phase 2: Create ThemeToggle, add to Header
3. **STOP and VALIDATE**: Dark mode auto-detection works, toggle works, persistence works
4. At this point the app is functional in dark mode — just with unstyled components

### Full Theme Rollout (Phases 3–7)

5. Theme UI primitives first (Phase 3) — cascading benefit to all components using them
6. Theme layout components (Phase 4) — app shell looks correct
7. Theme chat components (Phase 5) — core feature looks correct
8. Theme remaining components (Phase 6) — secondary pages look correct
9. Theme page-level styles (Phase 7) — auth pages, admin page

### Validation (Phase 8)

10. Build check + quickstart.md scenario verification
