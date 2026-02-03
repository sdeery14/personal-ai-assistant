# Personal AI Assistant — Vision/Feature Roadmap

This roadmap intentionally builds **capability + safety + confidence** in layers.
Each feature delivers a clear, testable user capability and becomes the foundation for the next.

> **Related Documents:** See [vision-memory.md](vision-memory.md) for the long-term memory architecture vision.

---

## Completed Features

### Feature 001 – Core Streaming Chat API ✅

**Goal**
Establish a reliable, observable interaction loop with the assistant.

**User Capability**

> "I can send a message and receive a streamed response from the assistant."

**Scope**

- OpenAI Agents SDK integration
- Server-side SSE streaming responses
- Request lifecycle with correlation IDs
- Structured logging and basic error handling

**Status:** Complete (spec `001-streaming-chat-api`)

---

### Feature 002 – Evaluation Harness (MLflow) ✅

**Goal**
Prevent silent regressions in assistant behavior.

**User Capability**

> "I can tell if the assistant got better or worse after a change."

**Scope**

- Golden test dataset (small, deterministic)
- LLM-as-judge scoring with rubrics
- MLflow-backed run tracking
- Pass/fail thresholds with regression gating
- CI gate for prompt / routing changes

**Status:** Complete (spec `002-judge-eval-framework`)

---

### Feature 003 – Security Guardrails ✅

**Goal**
Protect users and the system from harmful inputs and outputs.

**User Capability**

> "The assistant blocks dangerous requests and never produces harmful content."

**Scope**

- Input guardrails via OpenAI Moderation API
- Output guardrails with stream retraction
- Fail-closed behavior with exponential backoff retry
- Security red-team golden dataset
- Security-specific eval metrics (block rate, false positive rate)

**Status:** Complete (spec `003-security-guardrails`)

---

### Feature 004 – Memory v1 (Read-Only Recall) ✅

> _Implements Memory v1 from [vision-memory.md](vision-memory.md)_

**Goal**
Enable safe retrieval of relevant past information.

**User Capability**

> "The assistant can look up relevant past information when answering."

**Scope**

- Hybrid search (keyword + semantic)
- Read-only memory store with typed items (Fact, Preference, Decision, Note)
- Explicit memory query tool for the Agent
- Retrieval-only grounding in responses
- Memory retrieval eval coverage

**Explicitly Out of Scope**

- Automatic memory writes
- Summarization or insight extraction
- Long-term personalization logic

**Status:** Complete (spec `004-memory-v1-readonly-recall`)

---

### Feature 005 – External Tool v1: Weather Lookup ✅

**Goal**
Introduce a safe, real-world external tool.

**User Capability**

> "The assistant can accurately tell me the weather."

**Scope**

- Single weather provider
- Schema-validated tool calls
- Caching of safe responses
- Clear error states and fallbacks

**Explicitly Out of Scope**

- Advice or recommendations
- Multi-provider failover

**Status:** Complete (spec `005-weather-lookup`)

---

## Upcoming Features

### Feature 006 – Memory v2 (Automatic Writes)

> _Implements Memory v2 from [vision-memory.md](vision-memory.md)_

**Goal**
Allow the assistant to remember important information automatically.

**User Capability**

> "The assistant remembers what I told it without me having to repeat myself."

**Scope**

- Automatic summarization of conversation windows
- Insight extraction (facts, preferences, decisions)
- User-observable memory writes with provenance
- Memory write eval coverage (precision, relevance)

**Explicitly Out of Scope**

- Background jobs
- Proactive suggestions

---

### Feature 007 – Memory v3 (Background Jobs & Proactivity)

> _Implements Memory v3 from [vision-memory.md](vision-memory.md)_

**Goal**
Enable time-shifted intelligence and proactive preparation.

**User Capability**

> "The assistant prepares helpful information before I ask for it."

**Scope**

- Background job execution
- Morning briefings (news, weather, calendar)
- Trip/event preparation summaries
- Opt-in proactive notifications

**Explicitly Out of Scope**

- Autonomous actions
- Unsolicited interruptions

---

### Feature 008 – Voice Interaction (Phased)

#### Feature 008a – Voice Output (TTS Only)

**Goal**
Add audio output without increasing system complexity.

**User Capability**

> "I can hear the assistant's responses."

**Scope**

- Text-to-speech output
- Same backend logic as text chat
- No barge-in or interruptions

---

#### Feature 008b – Two-Way Voice Chat

**Goal**
Enable natural spoken conversations.

**User Capability**

> "I can talk to the assistant and hear it respond."

**Scope**

- Speech-to-text input
- Turn-based voice conversations
- Error handling for transcription failures

---

### Feature 009 – Edge Client v1: Raspberry Pi Interface

**Goal**
Deploy the assistant in a physical environment.

**User Capability**

> "I can interact with the assistant from a Raspberry Pi."

**Scope**

- Text-based interface (CLI / button / simple display)
- Connection to existing backend
- Minimal local state

**Explicitly Out of Scope**

- On-device model inference
- Voice (initially)

---

### Feature 010 – External Integrations v1: Google (Read-Only)

**Goal**
Allow the assistant to see personal context safely.

**User Capability**

> "The assistant can tell me about my emails and calendar events."

**Scope**

- Gmail read/search
- Calendar read
- Explicit permission prompts
- Audit logging

**Explicitly Out of Scope**

- Sending emails
- Modifying or creating calendar events

---

## Future Capability Expansion

**Goal**
Safely extend assistant usefulness over time.

**Examples**

- Memory v4: Long-horizon personalization and planning
- Tool-based reasoning (context-aware suggestions using memory + tools)
- Task automation and write-capable integrations
- Multi-modal inputs (images, documents)
- Additional tool integrations

Each new capability must:

- Follow the constitution
- Include evaluation coverage
- Be introduced as its own scoped feature
