# Feature Specification: Agent Notifications

**Feature Branch**: `010-agent-notifications`
**Created**: 2026-02-22
**Status**: Draft
**Input**: User description: "Feature 010 – Agent Notifications from the vision.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Agent Sends a Notification During Chat (Priority: P1)

During a conversation, the user asks the assistant to remind them about something or the assistant identifies information worth flagging later. The agent uses its notification tool to create a persistent notification that the user can see in the frontend even after the conversation ends.

**Why this priority**: This is the core capability — giving the agent a voice beyond the current chat turn. Without it, no other notification features have value.

**Independent Test**: Can be fully tested by chatting with the agent, triggering a notification, and confirming it appears in the notification panel with correct content and metadata.

**Acceptance Scenarios**:

1. **Given** a user is chatting with the assistant, **When** the agent decides to create a notification (e.g., user says "remind me about the dentist appointment"), **Then** a notification is persisted with the message content, marked as unread, and attributed to the conversation that created it.
2. **Given** the agent creates a notification, **When** the user views the notification panel, **Then** the notification displays the message, timestamp, and source context.
3. **Given** the agent creates a notification, **When** the notification tool encounters a validation error (e.g., empty message), **Then** the tool returns an error to the agent and no notification is persisted.

---

### User Story 2 - Viewing and Managing Notifications in the Frontend (Priority: P1)

The user can see a notification indicator (bell icon with unread count) in the frontend header. Clicking it opens a notification panel listing all notifications in reverse chronological order. Users can mark individual notifications as read, mark all as read, or dismiss notifications.

**Why this priority**: Notifications have no user value if there is no way to view and manage them. This is co-equal with Story 1 as the minimum viable feature.

**Independent Test**: Can be tested by seeding notifications via the API and confirming the frontend displays them correctly, updates unread counts, and supports read/dismiss actions.

**Acceptance Scenarios**:

1. **Given** a user has unread notifications, **When** they view the frontend header, **Then** a bell icon displays the count of unread notifications.
2. **Given** a user clicks the notification bell, **When** the notification panel opens, **Then** notifications are listed in reverse chronological order showing message, timestamp, and read/unread status.
3. **Given** a user has unread notifications, **When** they mark a notification as read, **Then** the unread count decreases and the notification visual state updates.
4. **Given** a user has multiple unread notifications, **When** they choose "mark all as read", **Then** all notifications are marked as read and the unread count resets to zero.
5. **Given** a user views the notification panel, **When** they dismiss a notification, **Then** the notification is removed from the panel (soft-deleted) and does not reappear.

---

### User Story 3 - Email Delivery for Out-of-App Notifications (Priority: P2)

When the agent creates a notification and the user has opted into email notifications, the system also delivers the notification via email. This ensures the user receives important messages even when they are away from the app.

**Why this priority**: Email extends the notification reach beyond the app, which is the key differentiator from simple in-app alerts. However, in-app notifications are independently useful without email.

**Independent Test**: Can be tested by creating a notification for a user with email delivery enabled and verifying that an email is sent with the notification content.

**Acceptance Scenarios**:

1. **Given** a user has email notifications enabled, **When** the agent creates a notification, **Then** an email is sent to the user's registered email address containing the notification message.
2. **Given** a user has email notifications disabled, **When** the agent creates a notification, **Then** no email is sent but the in-app notification is still created.
3. **Given** a user has email notifications enabled, **When** the email delivery fails (SMTP error, invalid address), **Then** the in-app notification is still persisted and the delivery failure is logged.
4. **Given** the email service is unavailable, **When** a notification is created, **Then** the system does not block or delay the in-app notification; email delivery failure is handled gracefully.

---

### User Story 4 - Notification Preferences (Priority: P2)

Users can configure their notification delivery preferences: which channels to receive notifications on (in-app only, email only, or both) and quiet hours during which email notifications are suppressed.

**Why this priority**: Preferences give users control over how they are contacted, which is important for trust and usability. However, sensible defaults (in-app enabled, email disabled) make the feature usable without preferences being configured.

**Independent Test**: Can be tested by setting different preference configurations and verifying that notification delivery respects each configuration.

**Acceptance Scenarios**:

1. **Given** a user has not configured preferences, **When** a notification is created, **Then** the default behavior applies (in-app enabled, email disabled).
2. **Given** a user has set delivery preference to "both", **When** a notification is created, **Then** both in-app and email notifications are delivered.
3. **Given** a user has set delivery preference to "email only", **When** a notification is created, **Then** only an email is sent and the in-app notification is still persisted (for history) but no bell indicator is shown.
4. **Given** a user has configured quiet hours (e.g., 10 PM to 7 AM), **When** a notification is created during quiet hours, **Then** the email is deferred until quiet hours end, but the in-app notification is created immediately.
5. **Given** a user updates their notification preferences, **When** they save, **Then** the new preferences take effect for all subsequent notifications.

---

### User Story 5 - Notification API Endpoints (Priority: P1)

The system exposes API endpoints for listing, reading, and managing notifications. These endpoints support the frontend and are also available for future integrations (e.g., edge clients, mobile apps).

**Why this priority**: The API is the backbone that the frontend and email delivery depend on. Without API endpoints, no notification management is possible.

**Independent Test**: Can be tested by calling the API endpoints directly and verifying correct responses for CRUD operations on notifications.

**Acceptance Scenarios**:

1. **Given** an authenticated user, **When** they request their notifications list, **Then** the API returns only their notifications (not other users'), paginated, in reverse chronological order.
2. **Given** an authenticated user, **When** they mark a notification as read via the API, **Then** the notification's status is updated and subsequent list requests reflect the change.
3. **Given** an authenticated user, **When** they dismiss a notification via the API, **Then** the notification is soft-deleted and no longer returned in list requests.
4. **Given** an authenticated user, **When** they request an unread count, **Then** the API returns the count of unread notifications for that user only.
5. **Given** an unauthenticated request, **When** any notification endpoint is called, **Then** the API returns a 401 error.

---

### Edge Cases

- What happens when a notification message exceeds 500 characters? The tool rejects the notification with an error returned to the agent (no truncation).
- What happens when the agent tries to send a notification for a user that doesn't exist? The tool returns an error and no notification is persisted.
- What happens when a user has hundreds of notifications? The notification list is paginated with a reasonable default page size.
- What happens when email delivery is configured but no email address is on file for the user? Email delivery is skipped and logged; in-app notification is still created.
- What happens when the same notification is created twice (idempotency)? Each notification is treated as distinct; deduplication is not required at this stage.
- What happens when quiet hours span midnight (e.g., 10 PM to 7 AM)? The system correctly handles cross-midnight quiet hour windows.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The agent MUST have a tool that creates notifications for the current user during a conversation.
- **FR-002**: Each notification MUST contain a message, type (one of: reminder, info, warning), source reference (conversation ID), and creation timestamp. The type enum is expandable in future features.
- **FR-003**: Notifications MUST be scoped to the owning user; users MUST NOT see other users' notifications.
- **FR-004**: The system MUST provide API endpoints for: listing notifications (paginated), getting unread count, marking as read, marking all as read, and dismissing (soft-deleting) notifications.
- **FR-005**: The frontend MUST display a notification bell icon in the header with a badge showing the unread count.
- **FR-006**: The frontend MUST provide a notification panel that lists notifications in reverse chronological order with message, timestamp, and read/unread status.
- **FR-007**: The system MUST support email delivery of notifications via a configurable email service.
- **FR-008**: Email delivery MUST NOT block or delay in-app notification creation; email failures MUST be handled gracefully with logging.
- **FR-009**: Users MUST be able to configure notification preferences: delivery channel (in-app only, email only, both) and quiet hours for email suppression.
- **FR-010**: The system MUST apply sensible defaults when no preferences are configured: in-app notifications enabled, email notifications disabled.
- **FR-011**: Notification dismissal MUST be a soft delete; dismissed notifications are not returned in list queries but remain in the database for audit purposes.
- **FR-012**: All notification API endpoints MUST require authentication and enforce per-user data isolation.
- **FR-013**: The notification tool MUST validate inputs (non-empty message, valid type, message length ≤ 500 characters) and return clear errors to the agent on failure.
- **FR-014**: Email notifications created during quiet hours MUST be deferred until quiet hours end.
- **FR-015**: The system MUST enforce a configurable per-user rate limit on notification creation (per hour). A conservative limit applies during development; a higher limit applies in production to support high-frequency use cases (e.g., live event tracking).
- **FR-016**: The system MUST log notification creation rates and provide monitoring to detect unusual patterns, favoring observability over hard capability limits.

### Key Entities

- **Notification**: A message from the agent to a user. Attributes: owner (user), message content, type (enum: reminder, info, warning), read/unread status, source conversation, creation timestamp, dismissed status.
- **Notification Preferences**: Per-user delivery settings. Attributes: owner (user), delivery channel selection, quiet hours start/end times.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The agent can create a notification during a conversation and the user can view it in the notification panel within 5 seconds of creation.
- **SC-002**: Notification list loads within 1 second for users with up to 1,000 notifications.
- **SC-003**: Email delivery completes within 30 seconds of notification creation (when email is enabled and outside quiet hours).
- **SC-004**: 100% of notifications are correctly scoped to their owning user — no cross-user data leakage.
- **SC-005**: Email delivery failures do not impact in-app notification availability — in-app notifications succeed independently of email.
- **SC-006**: Quiet hours suppress email delivery with 100% accuracy, including cross-midnight windows.
- **SC-007**: All notification API endpoints return appropriate error responses for unauthenticated and unauthorized requests.

## Clarifications

### Session 2026-02-22

- Q: What notification types should the system support? → A: Small fixed enum: reminder, info, warning (expandable later)
- Q: Should the agent be rate-limited on notifications? → A: Per-user time window cap. Conservative limit during development (10/hour), higher production limit for versatile usage (e.g., live event tracking). Invest in monitoring over hard caps.
- Q: What is the maximum notification message length? → A: 500 characters

## Assumptions

- Users already have registered email addresses stored in the user profile (from the existing auth system).
- The existing authentication and authorization infrastructure (JWT, middleware) is used for notification endpoints.
- Notification creation is triggered by the agent during active conversations only; autonomous/scheduled triggers are deferred to Feature 011 (Background Jobs).
- The frontend header component exists and can accommodate a notification bell icon alongside existing elements.
- Email delivery uses a configurable email service connection; the specific provider is an implementation decision.
- Notification volume per user is expected to be low (tens per day) in the initial release, scaling with Feature 011.

## Scope Boundaries

**In Scope**:
- Agent notification tool for creating notifications during conversations
- Notification persistence and API endpoints
- Frontend notification bell and panel
- Email delivery channel
- User notification preferences (channel selection, quiet hours)

**Out of Scope**:
- Push notifications (browser push, mobile push)
- Real-time WebSocket delivery (deferred to Feature 011)
- Scheduled or autonomous notifications (Feature 011)
- Rich notification content (images, action buttons, deep links)
- Notification categories/filtering in the UI (future enhancement)
- SMS or other delivery channels beyond email

## Dependencies

- Feature 008 (Web Frontend) — frontend notification UI builds on existing layout
- Feature 009 (Dark Mode & Theming) — notification components must support both themes
- Existing auth system — user identity, email addresses, JWT middleware
