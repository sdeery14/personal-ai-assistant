# Feature Specification: Proactive Assistant ("The Alfred Engine")

**Feature Branch**: `011-proactive-assistant`
**Created**: 2026-02-22
**Status**: Draft
**Input**: User description: "Feature 011 – Proactive Assistant ('The Alfred Engine')"

## Clarifications

### Session 2026-02-22

- Q: Should the scheduled task system support one-time reminders in addition to recurring tasks? → A: Both one-time and recurring tasks are supported from the start
- Q: Can the assistant send proactive suggestions via notifications when the user isn't in an active conversation? → A: Both — suggestions during conversations and via notifications when the user isn't chatting
- Q: Should scheduled task management be conversational only, or also have a dedicated frontend page? → A: Conversational primary + read-only schedule list in frontend (view only, manage via chat)

## Overview

The assistant has a persistent mission: understand the user, connect what it knows to what it can do, and proactively deliver help. From the first login, it actively works to build a relationship — asking questions, observing patterns, suggesting actions, and adapting based on feedback. The personality is warm, quietly competent, and occasionally firm — like Alfred Pennyworth, who has the tea ready before you ask, pushes back when needed, and earns the right to interrupt by being consistently helpful.

This feature combines three capabilities into one cohesive experience:
1. **Onboarding** — Conversational first-encounter that learns about the user
2. **Proactive reasoning** — Connecting what the agent knows to what it can do
3. **Scheduled care** — Background jobs that deliver help on a recurring basis

## User Scenarios & Testing *(mandatory)*

### User Story 1 — First Encounter: Alfred Introduces Himself (Priority: P1)

When a new user logs in for the first time, the assistant opens with a warm, conversational prompt designed to learn about the user — not a form or questionnaire, but a genuine question that unlocks the most useful context. The assistant picks the best question to understand how it can help: "I'd like to get to know you so I can be most useful. What's on your plate right now?" If the user wants to skip the introduction and just ask something, the assistant helps immediately and learns from the interaction naturally.

**Why this priority**: This is the user's first impression and sets the tone for the entire relationship. Without onboarding, the assistant starts cold with every user and can't personalize. This is also the simplest story to implement — it's primarily a system prompt change with memory writes.

**Independent Test**: Create a new user account, log in, and verify the assistant initiates a warm conversational prompt. Respond to the assistant's questions and verify that facts, preferences, and context are saved to memory and the knowledge graph.

**Acceptance Scenarios**:

1. **Given** a user logs in for the first time, **When** they open a chat, **Then** the assistant greets them with a conversational prompt that asks about their needs and context (not a form or checklist)
2. **Given** a new user is in the onboarding conversation, **When** they share information about themselves (work, interests, routines), **Then** the assistant saves relevant facts and preferences to memory immediately
3. **Given** a new user is in the onboarding conversation, **When** they mention people, projects, or tools, **Then** the assistant creates entities and relationships in the knowledge graph
4. **Given** a new user does not want to do a Q&A, **When** they ask a direct question instead, **Then** the assistant answers helpfully and learns from the interaction without forcing the onboarding flow
5. **Given** a returning user who has already completed onboarding, **When** they start a new conversation, **Then** the assistant does not repeat the onboarding prompt and instead uses what it knows to personalize the greeting

---

### User Story 2 — Building the Picture: Alfred Observes (Priority: P1)

Across every conversation, the assistant actively builds a model of the user — their work, routines, relationships, preferences, and recurring concerns. It doesn't just store facts passively; it identifies what would be useful to know for future assistance. The assistant notices patterns: "They mentioned Sarah three times this week in the context of a deadline — this relationship matters." Memory writes and knowledge graph updates are guided by the intent to serve the user better.

**Why this priority**: This is the foundation for all proactive behavior. Without active observation, the assistant has nothing to act on. This builds on existing memory writes (Feature 006) and knowledge graph extraction (Feature 007) but adds intentional, goal-directed learning.

**Independent Test**: Have several conversations with the assistant over multiple sessions. Verify that the assistant's memory and knowledge graph reflect not just what was said, but patterns and relationships that would be useful for future assistance.

**Acceptance Scenarios**:

1. **Given** a user has multiple conversations over several days, **When** they mention the same person or project repeatedly, **Then** the assistant's knowledge graph reflects the frequency and context of those mentions
2. **Given** a user expresses a recurring need (e.g., checking weather, preparing for meetings), **When** the pattern is detected, **Then** the assistant records the pattern as an observation that can inform future suggestions
3. **Given** a user mentions a deadline, event, or time-sensitive concern, **When** the assistant detects it, **Then** it stores a time-aware memory that can trigger future proactive assistance
4. **Given** a user corrects the assistant's understanding, **When** they say "that's not right" or similar, **Then** the assistant updates its model and does not repeat the mistake

---

### User Story 3 — Proactive Assistance: Alfred Has the Tea Ready (Priority: P2)

The assistant connects what it knows about the user to what it can do with its available tools. It surfaces relevant suggestions both during active conversations and via notifications when the user isn't chatting. In-conversation: "You mentioned wanting to prepare for your Friday presentation — I can pull together notes from your recent conversations about Project X." Via notification: "Your meeting with Sarah is in 2 hours — want me to pull together your notes?" It offers but doesn't impose. The user can dismiss suggestions, and the assistant learns from that feedback.

**Why this priority**: This is the payoff of the observation layer — turning knowledge into action. Depends on US1 and US2 having built up enough user context to make meaningful suggestions. Without proactive suggestions, the assistant is still reactive despite knowing about the user.

**Independent Test**: After building user context through several conversations, start a new conversation and verify the assistant proactively offers relevant suggestions based on what it knows. Dismiss some suggestions and verify the assistant adjusts.

**Acceptance Scenarios**:

1. **Given** the assistant knows the user has an upcoming event or deadline, **When** the user starts a conversation, **Then** the assistant proactively offers relevant preparation help
2. **Given** the assistant has context about the user's recent work, **When** the user asks a related question, **Then** the assistant references what it already knows and connects it to available tools
3. **Given** the user dismisses a proactive suggestion, **When** the assistant tracks the dismissal, **Then** it reduces the likelihood of similar suggestions in the future
4. **Given** the user engages with a proactive suggestion, **When** the assistant tracks the engagement, **Then** it increases the likelihood of similar suggestions in the future
5. **Given** the assistant has low confidence in a suggestion, **Then** it withholds the suggestion rather than making irrelevant offers

---

### User Story 4 — Scheduled Care: Alfred Manages the Household (Priority: P2)

The assistant suggests routines based on patterns it notices: "I see you ask about weather most mornings — want me to just have that ready for you?" Users can also explicitly request scheduled tasks: "Remind me to check the report every Friday." Both user-requested and agent-suggested schedules are managed through the same system. Every scheduled task delivers results via notifications (Feature 010).

**Why this priority**: Extends proactive behavior beyond active conversations into persistent, time-based assistance. Depends on the notification infrastructure (Feature 010) for delivery and the observation layer (US2) for pattern detection. This is the most infrastructure-heavy story.

**Independent Test**: Ask the assistant to set up a recurring task (e.g., "Send me weather every morning at 7am"). Verify the task runs on schedule and delivers a notification. Also verify the assistant suggests a schedule based on observed patterns.

**Acceptance Scenarios**:

1. **Given** a user requests a recurring task ("remind me every Friday"), **When** the schedule is created, **Then** the task runs at the specified time and delivers a notification with results
2. **Given** the assistant detects a repeated pattern (e.g., user asks about weather every morning), **When** enough repetitions are observed (at least 3 occurrences), **Then** the assistant suggests automating it as a scheduled task
3. **Given** a user accepts a suggested schedule, **When** the schedule is created, **Then** it behaves identically to a user-requested schedule
4. **Given** a user has active scheduled tasks, **When** they ask to see or manage their schedules, **Then** the assistant shows all active tasks with their frequency, next run time, and the ability to pause or cancel
5. **Given** a scheduled task fails (e.g., external service unavailable), **When** the failure occurs, **Then** the assistant logs the failure, retries according to policy, and notifies the user if the failure persists
6. **Given** a user wants to stop a scheduled task, **When** they ask to cancel it, **Then** the task is stopped immediately and no further notifications are sent

---

### User Story 5 — Calibration: Alfred Reads the Room (Priority: P3)

The assistant tracks which suggestions and scheduled tasks the user engages with versus dismisses, and adjusts its proactiveness accordingly. Three dismissed morning briefings in a row? It stops suggesting them. User always engages with meeting prep? It leans into that. The user can also explicitly say "be more proactive" or "be less proactive" and the assistant respects the instruction immediately. Users can see what the assistant "knows" about them and correct it.

**Why this priority**: This is the long-term refinement loop. The assistant works without it, but gets better with it. Depends on engagement data from US3 and US4. This is the most complex story from a behavioral standpoint.

**Independent Test**: Dismiss several proactive suggestions of the same type and verify the assistant stops making them. Engage with others and verify the assistant makes more of them. Explicitly tell the assistant to adjust its proactiveness and verify it complies.

**Acceptance Scenarios**:

1. **Given** a user dismisses 3 or more suggestions of the same type, **When** the assistant considers making a similar suggestion, **Then** it suppresses the suggestion
2. **Given** a user consistently engages with a certain type of suggestion, **When** a similar opportunity arises, **Then** the assistant is more likely to proactively offer it
3. **Given** a user says "be less proactive," **When** the instruction is received, **Then** the assistant immediately reduces the frequency and assertiveness of unsolicited suggestions
4. **Given** a user says "be more proactive," **When** the instruction is received, **Then** the assistant immediately increases proactive suggestions
5. **Given** a user asks "what do you know about me," **When** the assistant responds, **Then** it provides a clear summary of its understanding (preferences, patterns, key relationships) and invites corrections
6. **Given** a user corrects the assistant's understanding via the calibration flow, **When** the correction is made, **Then** the assistant updates its model and confirms the change

---

### Edge Cases

- What happens when the assistant has no context about a brand-new user who skips onboarding? The assistant operates in reactive mode (as it does today) and learns from organic conversations.
- What happens when a scheduled task references a tool that becomes unavailable? The task fails gracefully, the user is notified of the failure, and the schedule is paused (not deleted) until the issue is resolved.
- What happens when the assistant's suggestions are consistently wrong? The calibration loop (US5) suppresses low-engagement suggestion types. If all suggestion types are suppressed, the assistant reverts to reactive-only mode for that user.
- What happens when two scheduled tasks conflict (e.g., both scheduled for the same time)? Tasks are executed independently; notification delivery handles batching so the user isn't overwhelmed.
- What happens when a user has been inactive for a long time and returns? The assistant acknowledges the gap and gently re-establishes context: "Welcome back! Last time we talked about X — still relevant?"
- How does the assistant handle sensitive information shared during onboarding? The same privacy and data isolation rules apply as with all memory writes — data is scoped to the user, follows retention policies, and can be deleted.

## Requirements *(mandatory)*

### Functional Requirements

#### Onboarding

- **FR-001**: The assistant MUST detect when a user has no prior conversations and deliver a first-encounter conversational prompt
- **FR-002**: The onboarding prompt MUST be a natural conversational question, not a form or structured questionnaire
- **FR-003**: The assistant MUST save facts, preferences, and context shared during onboarding to the user's memory
- **FR-004**: The assistant MUST create entities and relationships in the knowledge graph based on onboarding conversations
- **FR-005**: The assistant MUST NOT repeat the onboarding flow for returning users who have already completed or skipped it
- **FR-006**: The assistant MUST gracefully handle users who skip onboarding and want to ask a question directly

#### Active Observation

- **FR-007**: The assistant MUST identify recurring patterns across conversations (repeated mentions of people, topics, tools, time-based behaviors)
- **FR-008**: The assistant MUST store observed patterns as a distinct type of memory item that can inform future suggestions
- **FR-009**: The assistant MUST detect time-sensitive mentions (deadlines, events, appointments) and store them with temporal context
- **FR-010**: The assistant MUST update its user model when the user provides corrections

#### Proactive Suggestions

- **FR-011**: The assistant MUST be able to surface relevant suggestions both during active conversations and via notifications when the user is not chatting, based on user context and available tools
- **FR-012**: The assistant MUST track whether suggestions are engaged with or dismissed
- **FR-013**: The assistant MUST suppress suggestions that fall below a confidence threshold
- **FR-014**: Proactive suggestions MUST cite what information they are based on (e.g., "Based on your mention of Project X last Tuesday...")
- **FR-015**: The assistant MUST NOT block or delay the user's primary request in order to deliver a suggestion

#### Scheduled Tasks

- **FR-016**: Users MUST be able to request both one-time and recurring tasks via natural language ("remind me tomorrow at 3pm to call Sarah," "remind me every Friday," "send me weather every morning")
- **FR-017**: The assistant MUST be able to suggest scheduled tasks based on observed patterns (minimum 3 occurrences of a pattern before suggesting)
- **FR-018**: Scheduled tasks MUST deliver results via the existing notification system (Feature 010)
- **FR-019**: Users MUST be able to pause, resume, and cancel their scheduled tasks via conversation with the assistant
- **FR-019a**: The frontend MUST provide a read-only schedule list page where users can see their active, paused, and completed tasks at a glance (management actions route through conversation)
- **FR-020**: Scheduled tasks MUST retry on transient failures and notify the user if failures persist
- **FR-021**: Scheduled tasks MUST be scoped per user — no user can see or modify another user's schedules

#### Calibration & Feedback

- **FR-022**: The assistant MUST adjust suggestion frequency and type based on engagement history (engagement increases similar suggestions; dismissal decreases them)
- **FR-023**: Users MUST be able to explicitly instruct the assistant to be more or less proactive, with immediate effect
- **FR-024**: Users MUST be able to ask "what do you know about me" and receive a clear, structured summary
- **FR-025**: Users MUST be able to correct the assistant's understanding, with the correction taking effect immediately
- **FR-026**: All proactive behavior MUST respect the user's notification preferences (delivery channel, quiet hours) from Feature 010

### Key Entities

- **User Profile Model**: An aggregate view of the user built from memory, knowledge graph, and engagement data. Includes preferences, patterns, key relationships, and proactiveness settings. Not a single database record, but a computed model the assistant uses.
- **Observed Pattern**: A recurring behavior detected across conversations — what the pattern is, how many times it was observed, when it was last seen, and whether it has been acted on (suggested or scheduled).
- **Scheduled Task**: A one-time or recurring job associated with a user — what it does, when it runs (specific datetime for one-time, cron expression or interval for recurring), what tool it invokes, its current status (active, paused, cancelled, completed), and its run history. One-time tasks transition to "completed" after execution.
- **Task Run**: A single execution of a scheduled task — when it ran, whether it succeeded or failed, the result or error, and the notification that was sent.
- **Engagement Event**: A record of the user's response to a proactive suggestion — what was suggested, whether it was engaged with or dismissed, and when.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 80% of new users who engage with the onboarding prompt provide at least 3 facts or preferences that are saved to memory within their first conversation
- **SC-002**: After 5 conversations, the assistant's user model contains at least 10 distinct facts, preferences, or patterns for the average user
- **SC-003**: Proactive suggestions have a 40% or higher engagement rate (user acts on the suggestion rather than dismissing it)
- **SC-004**: Users who dismiss a suggestion type 3 times see zero further suggestions of that type unless they explicitly request more proactiveness
- **SC-005**: Scheduled tasks execute within 60 seconds of their scheduled time
- **SC-006**: Users can create and cancel scheduled tasks through natural language conversation, and view all active schedules on a dedicated frontend page
- **SC-007**: 90% of users who ask "what do you know about me" receive a response they rate as accurate and complete

## Assumptions

- Feature 006 (Memory v2 — automatic writes) is complete and the assistant can already save memories during conversations
- Feature 007 (Knowledge Graph) is complete and the assistant can already extract entities and relationships
- Feature 010 (Agent Notifications) is complete and provides the delivery infrastructure for scheduled task results
- The existing system prompt architecture supports adding onboarding-specific and proactive-behavior instructions
- Users are authenticated and have unique identities (Feature 008)
- The assistant's existing tools (weather, memory, knowledge graph) are available for scheduled task execution

## Dependencies

- **Feature 006** — Memory v2 (automatic writes): Provides the memory write capability that onboarding and observation build on
- **Feature 007** — Knowledge Graph: Provides entity/relationship storage for building the user model
- **Feature 010** — Agent Notifications: Provides the delivery channel for scheduled task results and proactive notifications

## Out of Scope

- Voice-based onboarding or interaction (Feature 012)
- Google Calendar or Gmail integration for scheduling context (Feature 014)
- Multi-user shared schedules or collaborative features
- Custom tool creation by users — the assistant uses its existing tools
- Real-time push notifications via WebSocket (polling or notification panel refresh is sufficient for v1)
