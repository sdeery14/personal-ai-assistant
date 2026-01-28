# Personal AI Assistant — Vision/Feature Roadmap

This roadmap intentionally builds **capability + safety + confidence** in layers.
Each feature delivers a clear, testable user capability and becomes the foundation for the next.

---

## Feature 001 – Core Streaming Chat API

**Goal**
Establish a reliable, observable interaction loop with the assistant.

**User Capability**

> “I can send a message and receive a streamed response from the assistant.”

**Scope**

- OpenAI chat model integration
- Server-side streaming responses
- Request lifecycle with correlation IDs
- Structured logging and basic error handling

**Explicitly Out of Scope**

- Memory
- External tools
- Evaluations
- Voice

---

## Feature 002 – Evaluation Harness (MLflow)

**Goal**
Prevent silent regressions in assistant behavior.

**User Capability**

> “I can tell if the assistant got better or worse after a change.”

**Scope**

- Golden test dataset (small, deterministic)
- Prompt and schema versioning
- MLflow-backed run tracking
- Pass/fail thresholds
- CI gate for prompt / routing changes

**Explicitly Out of Scope**

- Complex scoring models
- Large-scale benchmarking

---

## Feature 003 – Memory v1 (Hybrid Retrieval, Read-Only)

**Goal**
Enable safe retrieval of relevant past information.

**User Capability**

> “The assistant can look up relevant past information when answering.”

**Scope**

- Hybrid search (keyword + vector)
- Read-only memory store
- Explicit memory query tool
- Retrieval-only grounding in responses

**Explicitly Out of Scope**

- Automatic memory writes
- Long-term personalization logic

---

## Feature 004 – External Tool v1: Weather Lookup

**Goal**
Introduce a safe, real-world external tool.

**User Capability**

> “The assistant can accurately tell me the weather.”

**Scope**

- Single weather provider
- Schema-validated tool calls
- Caching of safe responses
- Clear error states and fallbacks

**Explicitly Out of Scope**

- Advice or recommendations
- Multi-provider failover

---

## Feature 005 – Tool-Based Reasoning (Weather-Aware Suggestions)

**Goal**
Combine factual tools with assistant reasoning.

**User Capability**

> “The assistant can suggest plans, clothing, or gear based on weather.”

**Scope**

- Reasoned suggestions using weather data
- Explicit assumptions and confidence language
- Structured response format (facts → suggestions)

**Explicitly Out of Scope**

- Proactive notifications
- Memory updates

---

## Feature 006 – Voice Interaction (Phased)

### Feature 006a – Voice Output (TTS Only)

**Goal**
Add audio output without increasing system complexity.

**User Capability**

> “I can hear the assistant’s responses.”

**Scope**

- Text-to-speech output
- Same backend logic as text chat
- No barge-in or interruptions

---

### Feature 006b – Two-Way Voice Chat

**Goal**
Enable natural spoken conversations.

**User Capability**

> “I can talk to the assistant and hear it respond.”

**Scope**

- Speech-to-text input
- Turn-based voice conversations
- Error handling for transcription failures

---

## Feature 007 – Edge Client v1: Raspberry Pi Interface

**Goal**
Deploy the assistant in a physical environment.

**User Capability**

> “I can interact with the assistant from a Raspberry Pi.”

**Scope**

- Text-based interface (CLI / button / simple display)
- Connection to existing backend
- Minimal local state

**Explicitly Out of Scope**

- On-device model inference
- Voice (initially)

---

## Feature 008 – External Integrations v1: Google (Read-Only)

**Goal**
Allow the assistant to see personal context safely.

**User Capability**

> “The assistant can tell me about my emails and calendar events.”

**Scope**

- Gmail read/search
- Calendar read
- Explicit permission prompts
- Audit logging

**Explicitly Out of Scope**

- Sending emails
- Modifying or creating calendar events

---

## Feature 009+ – Capability Expansion

**Goal**
Safely extend assistant usefulness over time.

**Examples**

- Memory writes and personalization
- Task automation
- Proactive suggestions
- Additional tools and integrations

Each new capability must:

- Follow the constitution
- Include evaluation coverage
- Be introduced as its own scoped feature
