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

## Function Tools

Function tools let agents call Python functions during their execution. The SDK automatically extracts schemas from type hints and docstrings.

### Basic Usage with @function_tool

The simplest way to create a tool is with the `@function_tool` decorator:

```python
from agents import Agent, function_tool
from typing_extensions import TypedDict

class Location(TypedDict):
    lat: float
    long: float

@function_tool
async def fetch_weather(location: Location) -> str:
    """Fetch the weather for a given location.

    Args:
        location: The location to fetch the weather for.
    """
    # In real life, fetch from a weather API
    return "sunny"

agent = Agent(
    name="Weather Assistant",
    instructions="Help users check the weather.",
    model="gpt-4.1",
    tools=[fetch_weather],
)
```

**Key points:**

- Tool name = function name (override with `name_override`)
- Tool description = docstring (first line)
- Argument descriptions = parsed from docstring `Args:` section
- Supports Google, Sphinx, and NumPy docstring formats

### Accessing Run Context

Tools can access the run context via `RunContextWrapper`:

```python
from agents import function_tool, RunContextWrapper
from typing import Any

@function_tool
def read_file(ctx: RunContextWrapper[Any], path: str) -> str:
    """Read the contents of a file.

    Args:
        path: The path to the file to read.
    """
    # ctx provides access to context data
    return f"<contents of {path}>"
```

**Note:** The `ctx` parameter is automatically injected and NOT exposed to the LLM schema.

### Decorator Options

```python
@function_tool(
    name_override="get_data",           # Custom tool name
    description_override="Fetches...",  # Custom description
    use_docstring_info=True,            # Parse docstring (default: True)
    failure_error_function=my_handler,  # Custom error handler
)
def my_tool(arg: str) -> str:
    ...
```

### Supported Argument Types

The SDK supports various Python types for tool arguments:

| Type       | Example                        | Notes                  |
| ---------- | ------------------------------ | ---------------------- |
| Primitives | `str`, `int`, `float`, `bool`  | Direct mapping         |
| Optional   | `str \| None`, `Optional[int]` | Nullable in schema     |
| Lists      | `list[str]`, `List[int]`       | Array type             |
| TypedDict  | `class Loc(TypedDict): ...`    | Object with properties |
| Pydantic   | `class User(BaseModel): ...`   | Full validation        |
| Enums      | `Literal["a", "b", "c"]`       | Constrained values     |

### Custom FunctionTool (Advanced)

For more control, create `FunctionTool` directly:

```python
from pydantic import BaseModel
from agents import FunctionTool, RunContextWrapper
from typing import Any

class UserArgs(BaseModel):
    username: str
    age: int

async def process_user(ctx: RunContextWrapper[Any], args: str) -> str:
    parsed = UserArgs.model_validate_json(args)
    return f"{parsed.username} is {parsed.age} years old"

tool = FunctionTool(
    name="process_user",
    description="Processes user data",
    params_json_schema=UserArgs.model_json_schema(),
    on_invoke_tool=process_user,
)
```

### Error Handling in Tools

Default behavior sends error message to LLM. Customize with `failure_error_function`:

```python
from agents import function_tool, RunContextWrapper
from typing import Any

def handle_error(ctx: RunContextWrapper[Any], error: Exception) -> str:
    print(f"Tool failed: {error}")
    return "An error occurred. Please try again."

@function_tool(failure_error_function=handle_error)
def risky_operation(data: str) -> str:
    """A tool that might fail."""
    if not data:
        raise ValueError("Data required")
    return f"Processed: {data}"
```

Pass `failure_error_function=None` to re-raise exceptions for manual handling.

### Returning Images or Files

Tools can return rich content:

```python
from agents import function_tool
from agents.tool import ToolOutputImage, ToolOutputFileContent

@function_tool
def get_chart() -> ToolOutputImage:
    """Generate a chart image."""
    # Generate image bytes
    return ToolOutputImage(
        data=image_bytes,
        media_type="image/png",
    )

@function_tool
def get_report() -> ToolOutputFileContent:
    """Generate a report file."""
    return ToolOutputFileContent(
        data=file_bytes,
        media_type="application/pdf",
        file_name="report.pdf",
    )
```

### Agents as Tools

Use an agent as a tool for another agent:

```python
from agents import Agent

specialist = Agent(
    name="Translator",
    instructions="Translate text to Spanish.",
)

orchestrator = Agent(
    name="Coordinator",
    instructions="Help users with translations.",
    tools=[
        specialist.as_tool(
            tool_name="translate_spanish",
            tool_description="Translate text to Spanish",
        ),
    ],
)
```

**Advanced options:**

- `custom_output_extractor`: Transform agent output before returning
- `on_stream`: Handle streaming events from nested agent
- `is_enabled`: Conditionally enable/disable at runtime

---

## MCP Servers (Model Context Protocol)

MCP is an open protocol that standardizes how applications expose tools and context to LLMs. The SDK supports multiple MCP transports for connecting to external tool servers.

### Choosing an MCP Integration

| Use Case                | Class                     | When to Use                       |
| ----------------------- | ------------------------- | --------------------------------- |
| OpenAI-hosted execution | `HostedMCPTool`           | Public MCP server, no local infra |
| Self-hosted HTTP        | `MCPServerStreamableHttp` | Your server, low latency          |
| Legacy SSE transport    | `MCPServerSse`            | Existing SSE servers (deprecated) |
| Local subprocess        | `MCPServerStdio`          | CLI-based servers, quick PoCs     |

### Pattern 1: Hosted MCP Tool

Let OpenAI call a public MCP server on your behalf:

```python
from agents import Agent, HostedMCPTool, Runner

agent = Agent(
    name="Assistant",
    tools=[
        HostedMCPTool(
            tool_config={
                "type": "mcp",
                "server_label": "gitmcp",
                "server_url": "https://gitmcp.io/openai/codex",
                "require_approval": "never",
            }
        )
    ],
)

result = await Runner.run(agent, "Which language is this repository written in?")
```

**Key points:**

- Add to `tools=[]`, NOT `mcp_servers=[]`
- `require_approval`: `"never"`, `"always"`, or dict mapping tool names to policies
- Use `on_approval_request` callback for programmatic approval

### Pattern 2: Streamable HTTP Server

Connect to your own HTTP MCP server:

```python
from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp

async with MCPServerStreamableHttp(
    name="My MCP Server",
    params={
        "url": "http://localhost:8000/mcp",
        "headers": {"Authorization": f"Bearer {token}"},
        "timeout": 10,
    },
    cache_tools_list=True,
    max_retry_attempts=3,
) as server:
    agent = Agent(
        name="Assistant",
        instructions="Use MCP tools to help.",
        mcp_servers=[server],
    )
    result = await Runner.run(agent, "Add 7 and 22.")
```

**Constructor options:**

- `cache_tools_list`: Cache tool definitions (faster, set `True` if tools don't change)
- `max_retry_attempts`: Auto-retry failed tool calls
- `tool_filter`: Expose only subset of tools

### Pattern 3: stdio Server (Local Subprocess)

Spawn a local MCP server process:

```python
from pathlib import Path
from agents import Agent, Runner
from agents.mcp import MCPServerStdio

samples_dir = Path("/path/to/files")

async with MCPServerStdio(
    name="Filesystem Server",
    params={
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", str(samples_dir)],
    },
) as server:
    agent = Agent(
        name="Assistant",
        instructions="Use the filesystem to answer questions.",
        mcp_servers=[server],
    )
    result = await Runner.run(agent, "List the files available.")
```

**Use cases:**

- Quick prototyping
- CLI-only MCP servers
- Local development without network

### Managing Multiple Servers

Use `MCPServerManager` for multiple servers:

```python
from agents import Agent, Runner
from agents.mcp import MCPServerManager, MCPServerStreamableHttp

servers = [
    MCPServerStreamableHttp(name="calendar", params={"url": "http://localhost:8000/mcp"}),
    MCPServerStreamableHttp(name="docs", params={"url": "http://localhost:8001/mcp"}),
]

async with MCPServerManager(servers) as manager:
    agent = Agent(
        name="Assistant",
        mcp_servers=manager.active_servers,
    )
    result = await Runner.run(agent, "What MCP tools are available?")
```

**Manager features:**

- `active_servers`: Only successfully connected servers
- `failed_servers` / `errors`: Track failures
- `strict=True`: Raise on first connection failure
- `reconnect(failed_only=True)`: Retry failed servers

### Tool Filtering

Expose only specific tools from an MCP server:

```python
from agents.mcp import MCPServerStdio, create_static_tool_filter

# Static allow/block list
server = MCPServerStdio(
    params={"command": "npx", "args": [...]},
    tool_filter=create_static_tool_filter(
        allowed_tool_names=["read_file", "write_file"],
    ),
)

# Dynamic filter based on context
async def context_aware_filter(context, tool) -> bool:
    if context.agent.name == "Reader" and tool.name.startswith("write_"):
        return False
    return True

server = MCPServerStdio(
    params={"command": "npx", "args": [...]},
    tool_filter=context_aware_filter,
)
```

### Using MCP Prompts

MCP servers can provide dynamic prompt templates:

```python
prompt_result = await server.get_prompt(
    "generate_code_review_instructions",
    {"focus": "security", "language": "python"},
)

agent = Agent(
    name="Reviewer",
    instructions=prompt_result.messages[0].content.text,
    mcp_servers=[server],
)
```

### Caching Best Practices

```python
# Enable caching for stable tool definitions
server = MCPServerStreamableHttp(
    params={"url": "..."},
    cache_tools_list=True,  # Tools cached after first list_tools()
)

# Force refresh when needed
await server.invalidate_tools_cache()
```

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

### 4. Function Tool Docstrings

❌ **Wrong:**

```python
@function_tool
def get_weather(city: str) -> str:
    # No docstring - LLM won't know what the tool does
    return "sunny"
```

✅ **Correct:**

```python
@function_tool
def get_weather(city: str) -> str:
    """Get the current weather for a city.

    Args:
        city: The city name to get weather for.
    """
    return "sunny"
```

### 5. Context Parameter Not in Schema

The `ctx: RunContextWrapper` parameter is automatically excluded from the LLM schema:

```python
@function_tool
def my_tool(ctx: RunContextWrapper[Any], query: str) -> str:
    """Search for something.

    Args:
        query: The search query.
    """
    # ctx is injected by the SDK, query is exposed to LLM
    return "result"
```

### 6. Async vs Sync Tools

Both work, but async is preferred for I/O-bound operations:

```python
# Async - better for API calls, file I/O
@function_tool
async def fetch_data(url: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text

# Sync - fine for quick computations
@function_tool
def calculate(x: int, y: int) -> int:
    return x + y
```

### 7. MCP Server Context Manager

❌ **Wrong:**

```python
server = MCPServerStdio(params={...})
agent = Agent(mcp_servers=[server])  # Server not connected!
```

✅ **Correct:**

```python
async with MCPServerStdio(params={...}) as server:
    agent = Agent(mcp_servers=[server])
    result = await Runner.run(agent, "...")
```

### 8. HostedMCPTool vs mcp_servers

❌ **Wrong:**

```python
# HostedMCPTool goes in tools=[], NOT mcp_servers=[]
agent = Agent(
    mcp_servers=[HostedMCPTool(...)],  # Wrong!
)
```

✅ **Correct:**

```python
agent = Agent(
    tools=[HostedMCPTool(...)],  # Hosted = tools
    mcp_servers=[local_server],   # Local = mcp_servers
)
```

### 9. MCP Tool Caching

Enable `cache_tools_list=True` only when tool definitions are stable:

```python
# Good: Tools don't change
server = MCPServerStreamableHttp(params={...}, cache_tools_list=True)

# Bad: Dynamic tools that change per request
server = MCPServerStreamableHttp(params={...}, cache_tools_list=True)  # Stale tools!

# Solution: Invalidate cache when tools change
await server.invalidate_tools_cache()
```

---

## Resources

- [OpenAI Agents SDK GitHub](https://github.com/openai/openai-agents-python)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP specification
- [MCP Examples](https://github.com/openai/openai-agents-python/tree/main/examples/mcp) - stdio, SSE, HTTP samples

---

## Changelog

| Date       | Change                                             |
| ---------- | -------------------------------------------------- |
| 2026-01-28 | Add MCP Servers section with patterns & gotchas    |
| 2026-01-28 | Add Function Tools section with patterns & gotchas |
| 2026-01-28 | Initial guide created from Feature 001 learnings   |
