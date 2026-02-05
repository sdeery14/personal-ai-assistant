"""
Sync wrapper for invoking the production agent during evaluation.

This module provides a synchronous interface to invoke the production
ChatService agent using asyncio.run() wrapping Runner.run(). The agent
configuration (tools, guardrails, instructions) comes from
ChatService.create_agent(), ensuring the eval tests the exact same agent
as production.

Database initialization and teardown is handled per invocation because
asyncpg.Pool is bound to the event loop that created it — and each
asyncio.run() creates a fresh loop. The ~50ms overhead per case is
negligible vs. LLM API latency.

MLflow tracing is enabled via mlflow.openai.autolog() to capture
detailed execution traces during evaluation.
"""

import asyncio
import json
import os
from uuid import uuid4

import mlflow
from agents import Runner
from agents.exceptions import (
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
)
from agents.items import ToolCallItem
from agents.result import RunResult

from eval.config import get_eval_settings

# Enable MLflow auto-tracing for OpenAI calls
# This captures traces for debugging failed cases and enables future trace-based scorers
mlflow.openai.autolog()

# Track whether migrations have been run (idempotent, only need to run once per process)
_db_migrated = False


def invoke_production_agent(
    prompt: str,
    model: str | None = None,
    api_key: str | None = None,
    user_id: str = "eval-user",
    max_turns: int = 5,
) -> RunResult:
    """
    Invoke the production agent synchronously, returning the full RunResult.

    Uses ChatService.create_agent() to get the exact same agent configuration
    as production (guardrails, tools, system prompts), then runs it with
    Runner.run_sync() for deterministic evaluation.

    Args:
        prompt: The user prompt to send to the assistant.
        model: Optional model override (defaults to OPENAI_MODEL env var).
        api_key: Optional OpenAI API key (defaults to OPENAI_API_KEY env var).
        user_id: User ID for memory scoping in tool calls.
        max_turns: Maximum agent turns (default 5). Prevents hangs when
            tools fail repeatedly in eval environments without full infra.

    Returns:
        RunResult with final_output, new_items (tool calls), and guardrail results.

    Raises:
        InputGuardrailTripwireTriggered: If input guardrail blocks the request.
        OutputGuardrailTripwireTriggered: If output guardrail blocks the response.
        MaxTurnsExceeded: If agent exceeds max_turns limit.
    """
    settings = get_eval_settings()
    actual_api_key = api_key or settings.openai_api_key

    # Ensure OPENAI_API_KEY is in environment (required by OpenAI SDK)
    os.environ["OPENAI_API_KEY"] = actual_api_key

    from src.services.chat_service import ChatService

    service = ChatService()
    agent = service.create_agent(model=model)

    context = {
        "user_id": user_id,
        "correlation_id": str(uuid4()),
        "conversation_id": None,
    }

    async def _run():
        global _db_migrated
        from src.database import init_database, run_migrations, close_database

        try:
            await init_database()
            if not _db_migrated:
                await run_migrations()
                _db_migrated = True
        except Exception:
            pass  # Graceful degradation — tools will fail individually

        try:
            return await Runner.run(
                agent, input=prompt, context=context, max_turns=max_turns
            )
        finally:
            try:
                await close_database()
            except Exception:
                pass

    return asyncio.run(_run())


def extract_tool_calls(result: RunResult) -> list[dict]:
    """
    Extract tool call details from a RunResult.

    Inspects the new_items list for ToolCallItem entries and returns
    structured information about each tool invocation.

    Args:
        result: RunResult from Runner.run_sync().

    Returns:
        List of dicts with 'name' and 'arguments' keys for each tool call.
    """
    tool_calls = []
    for item in result.new_items:
        if isinstance(item, ToolCallItem):
            raw = item.raw_item
            name = getattr(raw, 'name', None)
            arguments = getattr(raw, 'arguments', '{}')
            try:
                args_dict = json.loads(arguments) if isinstance(arguments, str) else arguments
            except (json.JSONDecodeError, TypeError):
                args_dict = {"raw": str(arguments)}
            tool_calls.append({"name": name, "arguments": args_dict})
    return tool_calls
