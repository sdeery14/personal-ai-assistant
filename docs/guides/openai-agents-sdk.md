# OpenAI Agents SDK Guide

**Last Updated**: 2026-01-28
**SDK Version**: openai-agents (latest)
**Purpose**: Capture best practices and lessons learned for the OpenAI Agents SDK

---

## Overview

The OpenAI Agents SDK (`openai-agents` package) provides a higher-level abstraction over the OpenAI API for building agent-based applications. This guide documents patterns we've validated in this project.

---

## Installation

```bash
pip install openai-agents
```

Requires `OPENAI_API_KEY` environment variable.

---

## Core Concepts

### Agent

An `Agent` defines the LLM configuration and behavior:

```python
from agents import Agent

agent = Agent(
    name="Assistant",
    instructions="You are a helpful assistant.",
    model="gpt-4.1",
)
```

**Key parameters:**

- `name`: Identifier for the agent (used in logs/traces)
- `instructions`: System prompt defining behavior
- `model`: OpenAI model to use

### Runner

The `Runner` executes agents. Two main patterns:

#### Streaming (for real-time responses)

```python
from agents import Agent, Runner
from openai.types.responses import ResponseTextDeltaEvent

agent = Agent(name="Assistant", instructions="...", model="gpt-4.1")

result = Runner.run_streamed(agent, input="Hello")

async for event in result.stream_events():
    if event.type == "raw_response_event" and isinstance(
        event.data, ResponseTextDeltaEvent
    ):
        print(event.data.delta, end="", flush=True)
```

#### Synchronous (for batch/evaluation)

```python
from agents import Agent, Runner

agent = Agent(name="Assistant", instructions="...", model="gpt-4.1")

result = Runner.run_sync(agent, input="Hello")
print(result.final_output)
```

---

## Patterns We Use

### Pattern 1: Streaming Chat Service

Used in Feature 001 for real-time SSE responses:

```python
async def stream_completion(self, message: str) -> AsyncGenerator[str, None]:
    agent = Agent(
        name="Assistant",
        instructions="You are a helpful assistant.",
        model=self.settings.openai_model,
    )

    result = Runner.run_streamed(agent, input=message)

    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(
            event.data, ResponseTextDeltaEvent
        ):
            yield event.data.delta
```

**Key learnings:**

- Filter events by `event.type == "raw_response_event"`
- Check `isinstance(event.data, ResponseTextDeltaEvent)` for text chunks
- Access content via `event.data.delta`

### Pattern 2: Sync Adapter for Evaluation

Used in Feature 002 for deterministic evaluation:

```python
def get_response(prompt: str, model: str) -> str:
    """Get complete response (non-streaming) for evaluation."""
    agent = Agent(
        name="Assistant",
        instructions="You are a helpful assistant.",
        model=model,
    )

    result = Runner.run_sync(agent, input=prompt)
    return result.final_output
```

**Key learnings:**

- Use `Runner.run_sync()` when streaming isn't needed
- Access final text via `result.final_output`
- Simpler error handling than async streaming

---

## Error Handling

### Common Exceptions

```python
from openai import AuthenticationError, RateLimitError, APIError

try:
    result = Runner.run_sync(agent, input=prompt)
except AuthenticationError:
    # Invalid API key
    pass
except RateLimitError:
    # Rate limited - implement backoff
    pass
except APIError as e:
    # General API error
    log.error("API error", status=e.status_code, message=str(e))
```

### Retry Pattern

```python
import time
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def call_with_retry(agent: Agent, prompt: str) -> str:
    result = Runner.run_sync(agent, input=prompt)
    return result.final_output
```

---

## Testing

### Mocking the Agent/Runner

```python
from unittest.mock import MagicMock, patch
from openai.types.responses import ResponseTextDeltaEvent

# Create real event objects (not MagicMock with spec)
def create_text_delta_event(text: str) -> ResponseTextDeltaEvent:
    return ResponseTextDeltaEvent(
        type="response.output_text.delta",
        delta=text,
        output_index=0,
        content_index=0,
        item_id="item_123",
    )

# Mock the stream
@patch("agents.Runner.run_streamed")
async def test_streaming(mock_run):
    mock_result = MagicMock()
    mock_result.stream_events = async_generator_from([
        MagicMock(type="raw_response_event", data=create_text_delta_event("Hello")),
        MagicMock(type="raw_response_event", data=create_text_delta_event(" world")),
    ])
    mock_run.return_value = mock_result
    # ... test code
```

**Key learnings:**

- Use real `ResponseTextDeltaEvent` objects, not `MagicMock(spec=...)`
- `isinstance()` checks fail with MagicMock specs
- Create helper functions for test fixtures

---

## Configuration Best Practices

### Temperature Settings

| Use Case           | Temperature | Rationale                 |
| ------------------ | ----------- | ------------------------- |
| Evaluation/Testing | 0           | Reproducible outputs      |
| Chat/Creative      | 0.7-1.0     | Varied, natural responses |
| Code generation    | 0-0.3       | Precise, consistent       |

### Model Selection

| Model       | Best For              | Notes                               |
| ----------- | --------------------- | ----------------------------------- |
| gpt-4.1     | Default, best quality | Non-reasoning, fastest high-quality |
| gpt-4o      | Multimodal            | Vision + text                       |
| gpt-4o-mini | Cost-sensitive        | Good balance                        |
| o1/o3       | Complex reasoning     | Slower, more expensive              |

---

## Gotchas & Lessons Learned

### 1. Event Type Checking

❌ **Wrong:**

```python
if isinstance(event, ResponseTextDeltaEvent):  # Won't match!
```

✅ **Correct:**

```python
if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
```

### 2. Async Generator Consumption

❌ **Wrong:**

```python
result = Runner.run_streamed(agent, input=prompt)
events = list(result.stream_events())  # Doesn't work with async
```

✅ **Correct:**

```python
result = Runner.run_streamed(agent, input=prompt)
async for event in result.stream_events():
    # Process each event
```

### 3. Agent Reuse

The `Agent` object is lightweight and can be recreated per-request with different parameters:

```python
# OK to create new agent with different model per request
agent = Agent(
    name="Assistant",
    instructions="...",
    model=request.model or default_model,
)
```

---

## Resources

- [OpenAI Agents SDK GitHub](https://github.com/openai/openai-agents-python)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)

---

## Changelog

| Date       | Change                                           |
| ---------- | ------------------------------------------------ |
| 2026-01-28 | Initial guide created from Feature 001 learnings |
