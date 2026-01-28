<!--
SYNC IMPACT REPORT
==================
Version Change: [NEW] → 1.0.0
Type: MINOR (Initial constitution creation)
Modified Principles: N/A (initial creation)
Added Sections:
  - Core Principles (7 principles)
  - Decision Framework
  - Privacy & Security Standards
  - Governance
Templates Updated:
  ✅ .specify/templates/plan-template.md (already contains Constitution Check section)
  ✅ .specify/templates/spec-template.md (already contains acceptance scenarios structure)
  ✅ .specify/templates/tasks-template.md (already contains test-first workflow)
Follow-up TODOs: None
-->

# Personal AI Assistant Constitution

## Core Principles

### I. Clarity over Cleverness

**NON-NEGOTIABLE**: Every capability must be implemented as a simple, readable module with explicit inputs and outputs. Favor composition of small, single-responsibility components over complex monolithic solutions.

**Requirements**:

- Each agent/tool has one clear purpose documented in its header
- Function signatures use explicit type hints (Python) or interfaces (TypeScript)
- No "magic" behavior—side effects must be documented
- Configuration is explicit, never implicit

**Rationale**: Personal assistants handle sensitive life data. Debugging must be trivial, and maintainability is paramount for a project meant to evolve over time.

---

### II. Evaluation-First Behavior (NON-NEGOTIABLE)

**NON-NEGOTIABLE**: Every user-visible behavior MUST have at least one deterministic test (unit test) or a golden-case test (for LLM-based features). Changes to prompts, tool schemas, or routing logic require running the golden suite before merge.

**Requirements**:

- New feature branches include tests before implementation (TDD)
- Prompts and tool schemas are versioned artifacts in version control
- Golden test suite runs on CI for prompt/schema changes
- Test coverage tracked; regressions block deployment

**Rationale**: AI assistants are non-deterministic by nature. Without rigorous testing, silent regressions in behavior are inevitable and erode user trust.

---

### III. Tool Safety and Correctness

**NON-NEGOTIABLE**: All tools must be explicitly allowlisted and schema-validated before execution. No freeform command execution is permitted.

**Requirements**:

- Tool registry maintains allowlist with explicit schemas (JSON Schema or equivalent)
- Every tool call validated against schema before execution
- Timeouts configured per tool (default: 30s, adjustable per tool)
- Retries with exponential backoff for transient failures (max 3 attempts)
- Graceful failure mode: safe defaults + clear, actionable error messages to user

**Rationale**: Personal assistants have access to calendars, filesystems, and external APIs. A single malformed tool call can corrupt data or leak information. Defense-in-depth is required.

---

### IV. Privacy by Default

**NON-NEGOTIABLE**: Minimize sensitive data sent to any model or external tool. Secrets and PII must be redacted from all logs and traces.

**Requirements**:

- Local execution preferred for sensitive operations (e.g., local embeddings, local file search)
- Remote API calls redact PII (emails, names, addresses) before sending
- Secrets stored in encrypted stores (OS keychain, environment variables, never in code)
- User data storage minimized to what's necessary; encrypted at rest
- Least-privilege credentials for all external integrations

**Rationale**: Users entrust personal data to this assistant. Privacy violations destroy trust and may violate regulations (GDPR, CCPA). Data must be treated as toxic by default.

---

### V. Consistent UX

**NON-NEGOTIABLE**: Assistant responses follow a consistent three-part format: (1) brief answer, (2) next steps or options, (3) optional details.

**Requirements**:

- Responses structured: answer → actionable next steps → (if requested) deeper explanation
- Assistant can and should say "I don't know" or "I need more information" rather than guessing
- Error messages explain what happened, why, and what the user can do
- Confirmations required for destructive actions (delete, overwrite, external charges)

**Rationale**: Consistency reduces cognitive load. Users should never wonder if the assistant understood them or if it's acting on bad assumptions.

---

### VI. Performance and Cost Budgets

**NON-NEGOTIABLE**: Set budgets for latency (seconds) and cost (tokens). Degrade gracefully when approaching limits.

**Requirements**:

- Latency budget: <3s for simple queries, <10s for complex workflows
- Token budget per request tracked; summarize context when exceeding threshold
- Graceful degradation strategy: smaller model → fewer tools → summarized context → apologize
- Cache safe, repeatable results (e.g., embeddings, knowledge base lookups) per cache policy
- Monitor usage; alert on anomalies (runaway loops, cost spikes)

**Rationale**: Personal projects have tight budgets. Runaway API costs or hanging requests kill adoption. Performance discipline ensures sustainability.

---

### VII. Observability and Debuggability (NON-NEGOTIABLE)

**NON-NEGOTIABLE**: Every request must produce structured logs/traces with inputs (redacted), tool calls, outputs, and decision points. Failures must be diagnosable from logs alone without local reproduction.

**Requirements**:

- Structured logging (JSON) with correlation IDs for multi-step workflows
- Log levels: DEBUG (decisions), INFO (milestones), WARN (degraded), ERROR (failures)
- Redact sensitive data automatically in logs (PII, secrets, tokens)
- Trace tool call sequence: tool name, input schema, output, duration, errors
- Error logs include context: user intent, attempted action, failure reason, recovery taken

**Rationale**: When something breaks at 2 AM, logs are the only diagnostic tool. Without structured observability, debugging is guesswork.

---

## Decision Framework

When principles conflict, apply this priority order:

1. **Privacy** > Correctness > UX consistency > Performance > Developer convenience
2. **Correctness** > UX consistency > Performance > Developer convenience
3. **UX consistency** > Performance > Developer convenience
4. **Performance** > Developer convenience

**When uncertain**: Return a safe, minimal response and ask a targeted follow-up question. Never guess with user data.

---

## Privacy & Security Standards

All features must satisfy:

- **Data Minimization**: Collect and store only what is strictly necessary
- **Encryption**: User data encrypted at rest; secrets in OS-managed keychains
- **Redaction**: PII and secrets automatically stripped from logs and external API calls
- **Least Privilege**: API keys and credentials scoped to minimum required permissions
- **Audit Trail**: Security-relevant actions logged (authentication, data access, deletions)

---

## Governance

This constitution supersedes all other development practices and is the authoritative source for design decisions.

**Amendment Process**:

1. Proposed changes documented with rationale and impact analysis
2. Sync impact report generated (affected templates, code, tests)
3. Version bump determined (MAJOR = breaking, MINOR = additive, PATCH = clarification)
4. All dependent templates and documentation updated before merge

**Versioning Policy**:

- **MAJOR**: Principle removed or redefined in backward-incompatible way (e.g., removing test requirement)
- **MINOR**: New principle added or existing principle materially expanded
- **PATCH**: Clarifications, wording improvements, typo fixes

**Compliance Review**:

- All feature specs must reference applicable principles in "Requirements" section
- All implementation plans must include "Constitution Check" gate (per plan-template.md)
- Code reviews verify compliance with applicable principles

**Version**: 1.0.0 | **Ratified**: 2026-01-28 | **Last Amended**: 2026-01-28
