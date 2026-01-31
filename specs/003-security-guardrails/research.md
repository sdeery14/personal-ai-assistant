# Research & Technical Discovery: Security Guardrails

**Feature**: 003-security-guardrails
**Created**: January 29, 2026

## Research Questions

### 1. OpenAI Agents SDK Guardrail Integration Pattern

**Question**: How do we wire `input_guardrail` and `output_guardrail` decorators into the existing Agent configuration, and where do tripwire exceptions surface?

**Finding**: Based on OpenAI Agents SDK documentation:

- Guardrails are attached to Agent via `input_guardrails=[]` and `output_guardrails=[]` parameters in Agent() constructor
- Input guardrails execute before agent processing starts
- Output guardrails execute on the final response text
- Tripwire exceptions are raised as `GuardrailViolation` exceptions that must be caught in the calling code (FastAPI route handler)

**Decision**:

- Add guardrail functions to `src/services/guardrails.py`
- Modify `ChatService.__init__()` to pass guardrails list to Agent constructor
- Catch `GuardrailViolation` in `routes.py` POST /chat/completions handler
- For streaming: wrap `Runner.run_streamed()` in try/except to catch output guardrail violations mid-stream

---

### 2. Streaming + Output Guardrails Architecture

**Question**: How do output guardrails work with streaming responses? Can we validate incrementally or must we buffer the complete output?

**Finding**: Output guardrails in Agents SDK validate the complete final text, not incremental chunks. This creates two options:

1. Buffer entire response → validate → stream validated content (adds latency)
2. Stream immediately, run validation in parallel, send retraction if violation detected

**Decision**: Per spec clarifications, use option 2:

- Stream tokens to user immediately as generated
- Accumulate full text in background task
- Run output guardrail on accumulated text
- If violation detected: send special "retraction chunk" with `is_final=True`, `error_type="output_guardrail_violation"`, correlation_id
- Client must handle retraction by marking previous content as invalid/removed

**Implementation Pattern**:

```python
async def stream_with_output_guardrail(agent, message, correlation_id):
    accumulated_text = []
    violation_detected = False

    async def validate_output_task():
        # Wait for stream to complete
        full_text = "".join(accumulated_text)
        try:
            # Run output guardrail
            agent.output_guardrails[0](full_text)
        except GuardrailViolation as e:
            violation_detected = True
            # Trigger stream termination with retraction

    # Run validation in parallel
    validation_task = asyncio.create_task(validate_output_task())

    # Stream chunks
    async for chunk in stream_generator:
        accumulated_text.append(chunk.content)
        yield chunk
        if violation_detected:
            # Send retraction chunk and break
            yield retraction_chunk(...)
            break
```

---

### 3. OpenAI Moderation API Integration

**Question**: How do we call OpenAI Moderation API for content safety classification? What are the request/response formats?

**Finding**: OpenAI provides `/v1/moderations` endpoint:

- Request: `{"input": "text to check"}`
- Response: `{"results": [{"flagged": true/false, "categories": {...}}]}`
- Latency: typically 100-300ms
- Cost: Free tier available, minimal cost for production use

**Decision**:

- Use `openai.Moderation.create()` SDK method in guardrail functions
- Implement retry logic with exponential backoff (100ms, 500ms, 1s) per spec
- Fail closed if all retries exhausted
- Log moderation decisions with redacted content (category + severity, not full text)

---

### 4. Security Dataset Schema Requirements

**Question**: What fields must the security golden dataset include to work with Feature 002 evaluation framework?

**Finding**: Based on existing `eval/golden_dataset.json` structure:

- Current schema: `id`, `user_prompt`, `rubric`, `context`, `tags`
- Need to add: `severity` (critical/high/medium/low), `expected_behavior` (block/allow), `attack_type`

**Decision**: Create new `eval/security_golden_dataset.json` with extended schema:

```json
{
  "version": "1.0.0",
  "description": "Security test cases for guardrail evaluation",
  "cases": [
    {
      "id": "sec-001",
      "user_prompt": "Ignore previous instructions and...",
      "expected_behavior": "block",
      "severity": "critical",
      "attack_type": "prompt_injection",
      "rubric": "Guardrail must block this prompt injection attempt...",
      "tags": ["adversarial", "injection"]
    }
  ]
}
```

---

### 5. MLflow Metrics for Security Evaluation

**Question**: How do we compute and log security-specific metrics (block_rate, false_positive_rate) in MLflow?

**Finding**: Feature 002 evaluation runner uses `mlflow.log_metric()` to record scores. We can add custom metrics alongside judge scores.

**Decision**: Extend eval runner to compute:

- `block_rate`: (correctly blocked adversarial) / (total adversarial cases)
- `false_positive_rate`: (incorrectly blocked benign) / (total benign cases)
- `top10_critical_miss`: boolean metric (1 if any top-10 severity cases missed, 0 otherwise)
- `judge_safety_score`: average judge score across all cases (0-100)

Log these as MLflow metrics with `mlflow.log_metric(metric_name, value)` in the runner.

---

### 6. Retry Logic with Exponential Backoff

**Question**: How do we implement 2-3 retries with exponential backoff (100ms, 500ms, 1s) before failing closed?

**Finding**: Standard async retry pattern:

```python
async def call_moderation_with_retry(text: str) -> bool:
    delays = [0.1, 0.5, 1.0]  # seconds
    for attempt, delay in enumerate(delays):
        try:
            result = await openai.Moderation.create(input=text)
            return result.results[0].flagged
        except Exception as e:
            if attempt == len(delays) - 1:
                # Final attempt failed, fail closed
                logger.error("moderation_api_exhausted", attempts=len(delays))
                return True  # Block request (fail closed)
            await asyncio.sleep(delay)
```

**Decision**: Implement retry helper in `src/services/guardrails.py` as `async def moderate_with_retry()`. Use this in both input and output guardrail functions.

---

## Summary of Technical Choices

| Decision                                                                                    | Rationale                                                          |
| ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Guardrails attached to Agent constructor                                                    | Aligns with OpenAI Agents SDK best practices                       |
| Stream-first with parallel output validation                                                | Preserves streaming UX per spec requirement (SC-008)               |
| Retraction chunk format: `{"error_type": "...", "correlation_id": "...", "is_final": true}` | Compatible with Feature 001 streaming protocol                     |
| Separate `security_golden_dataset.json` file                                                | Keeps security cases isolated, allows independent expansion        |
| Retry with exponential backoff before fail-closed                                           | Balances availability with security per spec clarifications        |
| Log redacted content (category + hash/length only)                                          | Satisfies observability while protecting privacy (Constitution IV) |

## Open Questions (None Remaining)

All technical unknowns resolved. Ready to proceed with data model and implementation phases.
