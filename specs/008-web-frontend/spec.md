# Feature Specification: Web Frontend

**Feature Branch**: `008-web-frontend`
**Created**: 2026-02-13
**Status**: Draft
**Input**: User description: "Feature 008 – Web Frontend (Next.js) from the vision.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Real-Time Streaming Chat (Priority: P1)

As a user, I open the assistant in my browser, type a message, and see the assistant's response appear word-by-word in real time — just like a modern chat experience. I can send follow-up messages in the same conversation and see the full thread of messages above.

**Why this priority**: This is the core value proposition — replacing raw API calls with a usable chat interface. Without this, no other frontend feature matters.

**Independent Test**: Can be fully tested by opening the app in a browser, sending a message, and verifying the response streams in real time. Delivers a complete, usable chat experience as a standalone MVP.

**Acceptance Scenarios**:

1. **Given** the user opens the app for the first time, **When** the page loads, **Then** they see an empty chat area with a message input field ready for typing.
2. **Given** the user types a message and submits it, **When** the assistant begins responding, **Then** the response text appears incrementally (word-by-word) in the chat area.
3. **Given** the assistant is actively streaming a response, **When** the user looks at the interface, **Then** there is a clear visual indicator that the assistant is still generating.
4. **Given** the assistant finishes a response, **When** the streaming completes, **Then** the visual indicator disappears and the input field becomes ready for the next message.
5. **Given** the user sends a follow-up message in the same conversation, **When** the assistant responds, **Then** the response reflects awareness of the prior messages in the conversation.

---

### User Story 2 - Conversation Management (Priority: P2)

As a user, I want to start new conversations, switch between existing ones, and see my past conversations listed so I can return to any previous discussion.

**Why this priority**: Without conversation management, every page refresh starts a blank session. Persistent conversations are essential for continuity and make the assistant meaningfully more useful than a single-turn tool.

**Independent Test**: Can be tested by creating multiple conversations, navigating between them, and verifying each retains its full message history.

**Acceptance Scenarios**:

1. **Given** the user has an active conversation, **When** they choose to start a new conversation, **Then** a fresh chat area appears and a new conversation begins.
2. **Given** the user has multiple past conversations, **When** they view the conversation list, **Then** each conversation shows a title or preview and a timestamp.
3. **Given** the user selects a past conversation from the list, **When** the conversation loads, **Then** all prior messages in that conversation are displayed in order.
4. **Given** the user wants to remove a conversation, **When** they delete it, **Then** the conversation is removed from the list and its messages are no longer accessible.

---

### User Story 3 - Memory & Knowledge Visibility (Priority: P3)

As a user, I want to see what the assistant remembers about me and how it connects things I've mentioned, so I can trust and understand the assistant's recall capabilities. I can browse stored memories and see the relationships the assistant has built between entities (people, projects, tools, etc.).

**Why this priority**: Memory and knowledge graph are core differentiators of this assistant (Features 004–007). Making them visible builds trust and enables the user to verify, correct, or explore what the assistant knows — aligning with the "Trust First" memory design goal.

**Independent Test**: Can be tested by navigating to a memory/knowledge view and verifying that stored memories and entity relationships are displayed. The user can browse and inspect without needing to send a chat message.

**Acceptance Scenarios**:

1. **Given** the assistant has stored memories from past conversations, **When** the user navigates to the memory view, **Then** they see a list of remembered items with their type (fact, preference, decision, etc.) and source.
2. **Given** the assistant has built a knowledge graph with entities and relationships, **When** the user navigates to the knowledge view, **Then** they see entities and how they relate to each other.
3. **Given** the user is viewing a memory item, **When** they inspect it, **Then** they can see when it was created, what conversation it came from, and its content.
4. **Given** the user wants to remove a memory, **When** they delete it from the memory view, **Then** the memory is removed and the assistant no longer uses it in future responses.

---

### User Story 4 - Error Handling & Connection Resilience (Priority: P2)

As a user, I expect clear feedback when something goes wrong — whether the assistant service is unavailable, my message was blocked by safety guardrails, or my connection drops mid-stream.

**Why this priority**: Tied with conversation management as P2 because poor error handling makes the entire interface feel unreliable. Users must understand what happened and what they can do about it.

**Independent Test**: Can be tested by simulating error conditions (service down, guardrail trigger, network disconnect) and verifying the user receives appropriate, actionable messages.

**Acceptance Scenarios**:

1. **Given** the backend service is unavailable, **When** the user sends a message, **Then** they see a friendly error message explaining the service is temporarily unavailable, with an option to retry.
2. **Given** the user's message is blocked by a safety guardrail, **When** the guardrail triggers, **Then** the user sees a clear message that their request could not be processed due to safety concerns, and they are invited to rephrase.
3. **Given** the network connection drops while the assistant is streaming a response, **When** the connection is lost, **Then** the user sees an indication that the connection was interrupted and can retry.
4. **Given** the assistant response times out, **When** the timeout occurs, **Then** the user sees a timeout message and can resend their message.

---

### Edge Cases

- What happens when the user submits an empty or whitespace-only message? The submit action should be disabled or the message should be rejected with inline feedback.
- What happens when the user sends a very long message (approaching the character limit)? A character counter or limit indicator should appear before submission.
- What happens when the user rapidly sends multiple messages? Messages should be queued and sent in order; the interface should not allow sending while a response is actively streaming.
- What happens when the user navigates away mid-stream? The current stream should be gracefully terminated without leaving orphaned connections.
- What happens when the user's session expires or their identity cannot be verified? The user should be prompted to re-authenticate without losing their current draft message.
- What happens when the conversation list grows very large (hundreds of conversations)? The list should remain performant with pagination or virtual scrolling.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display a chat interface where users can type and send messages to the assistant.
- **FR-002**: System MUST display the assistant's response in real time as it is generated, showing text incrementally rather than waiting for the full response.
- **FR-003**: System MUST show a visual indicator while the assistant is actively generating a response (e.g., typing indicator, pulsing cursor, or progress animation).
- **FR-004**: System MUST support multi-turn conversations where the assistant maintains context across messages within the same conversation.
- **FR-005**: System MUST allow users to start a new conversation at any time.
- **FR-006**: System MUST persist conversations so users can return to them after closing the browser or navigating away.
- **FR-007**: System MUST display a list of past conversations with a title (auto-generated from the first user message) and a timestamp.
- **FR-025**: System MUST allow users to rename a conversation title at any time.
- **FR-008**: System MUST allow users to select and resume any past conversation.
- **FR-009**: System MUST allow users to delete conversations they no longer want.
- **FR-010**: System MUST display error messages in a user-friendly format when the backend service is unavailable, a guardrail blocks a request, a timeout occurs, or the connection drops.
- **FR-011**: System MUST provide a way for users to retry after an error without re-typing their message.
- **FR-012**: System MUST prevent submission of empty or whitespace-only messages.
- **FR-013**: System MUST provide a view where users can browse their stored memories (facts, preferences, decisions, etc.).
- **FR-014**: System MUST provide a searchable entity list where users can browse knowledge graph entities and expand each entity to see its relationships displayed as a list. No visual graph diagram is required.
- **FR-015**: System MUST allow users to delete individual memories from the memory view.
- **FR-016**: System MUST be usable on both desktop and mobile screen sizes.
- **FR-017**: System MUST render the assistant's responses with proper formatting (paragraphs, lists, code blocks, emphasis).
- **FR-018**: System MUST auto-scroll to show the latest message or streaming content, unless the user has manually scrolled up to review earlier messages.
- **FR-019**: System MUST support keyboard shortcuts for common actions (submit message on Enter, new line on Shift+Enter).
- **FR-020**: System MUST support multiple named users, each with their own separate account. Each user's conversations, memories, and knowledge graph data are fully isolated from other users.
- **FR-021**: System MUST provide a login flow using username and password credentials where users identify themselves before accessing the assistant.
- **FR-022**: System MUST prevent users from accessing another user's conversations, memories, or knowledge graph data.
- **FR-023**: System MUST allow an administrator to create, disable, and remove user accounts. There is no self-registration; all accounts are provisioned by an admin.
- **FR-024**: System MUST include a first-run setup flow that creates the initial administrator account when no users exist.

### Key Entities

- **Conversation**: A thread of messages between the user and the assistant. Has a creation timestamp, a title (auto-generated from the first user message, editable by the user), and an ordered list of messages.
- **Message**: A single utterance from either the user or the assistant within a conversation. Has content, a sender role (user or assistant), a timestamp, and optionally error information.
- **Memory Item**: A stored piece of information the assistant remembers. Has a type (fact, preference, decision, episode, note), content, source conversation, creation timestamp, and importance.
- **Entity**: A person, project, tool, concept, or other noun extracted from conversations. Has a name, type, and relationships to other entities.
- **Relationship**: A typed connection between two entities (e.g., "uses", "works on", "prefers"). Has a source entity, target entity, relationship type, and provenance.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can send a message and see the first word of the assistant's response within 2 seconds of submission.
- **SC-002**: Users can complete a full conversational exchange (send message, read response, send follow-up) in under 30 seconds.
- **SC-003**: Users can find and resume a past conversation from the conversation list in under 5 seconds.
- **SC-004**: Users can browse their stored memories and identify a specific memory item in under 10 seconds.
- **SC-005**: 100% of backend error states (service down, guardrail block, timeout, connection loss) result in a user-visible, actionable error message — never a silent failure or blank screen.
- **SC-006**: The interface is fully usable on screens as small as 375px wide (standard mobile) without horizontal scrolling or overlapping elements.
- **SC-007**: Users can access all primary features (chat, conversation list, memory view, knowledge view) within 2 clicks from any screen.

## Clarifications

### Session 2026-02-13

- Q: What authentication method should the login flow use? → A: Username + password (standard credential-based login)
- Q: How are new user accounts created? → A: Admin-created (an existing user or initial setup creates accounts for others)
- Q: What is explicitly out of scope for this feature? → A: Dark mode/themes, push notifications, user settings page, memory editing (deletion only), file uploads
- Q: How should the knowledge graph be displayed? → A: Searchable entity list with expandable relationship details (no visual graph)
- Q: How should conversation titles work? → A: Auto-generated from first user message, user-editable

## Assumptions

- This is a personal assistant supporting multiple named users with separate accounts. It does not need enterprise-grade multi-tenancy or role-based access control beyond basic per-user data isolation.
- The existing backend services (ConversationService, MemoryService, GraphService) contain all the business logic the frontend needs. New REST endpoints are required to expose these services over HTTP, plus a new authentication layer (User model, JWT auth). See `contracts/api-contracts.yaml` for the full API surface.
- Conversation persistence will be handled by the existing backend — the frontend will retrieve and display conversations from the API, not store them locally as the primary source of truth.
- Memory and knowledge graph data is read from existing backend services. The frontend displays what the backend provides and sends deletion requests back to the backend.
- The frontend will be deployed alongside (or proxying to) the existing backend services. Cross-origin concerns are handled at the deployment/infrastructure level.
- Standard web accessibility practices (keyboard navigation, screen reader compatibility, sufficient color contrast) will be followed.

## Out of Scope

The following capabilities are explicitly excluded from this feature and deferred to future work:

- **Dark mode / theme customization**: The frontend ships with a single visual theme. Theming support is a future enhancement.
- **Push notifications**: No real-time notifications for background events. Users must open the app to see updates. (Deferred to Feature 009 – Background Jobs & Proactivity.)
- **User settings / preferences page**: No UI for configuring assistant behavior, notification preferences, or display settings.
- **Memory editing**: Users can delete memories from the memory view but cannot edit their content. Corrections are made through conversation (as established in Feature 006).
- **File uploads**: Users cannot attach files, images, or documents to messages. (Deferred to Future Capabilities – Multi-modal inputs.)

## Dependencies

- **Feature 001** (Core Streaming Chat API): The SSE streaming endpoint the frontend consumes.
- **Feature 004** (Memory v1): Memory retrieval service the frontend queries for the memory view.
- **Feature 006** (Memory v2): Memory write/delete capabilities for memory management in the UI.
- **Feature 007** (Knowledge Graph): Entity and relationship data the frontend displays in the knowledge view.
