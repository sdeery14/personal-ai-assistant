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


def invoke_onboarding_conversation(
    user_turns: list[str],
    model: str | None = None,
    api_key: str | None = None,
    user_id: str = "eval-onboarding-user",
    max_turns: int = 10,
) -> tuple[list[tuple[str, RunResult]], list[dict]]:
    """
    Run a multi-turn onboarding conversation against the production agent.

    Creates the agent with is_onboarded=False, sends a greeting trigger,
    then sends each user turn with accumulated conversation history.
    Each turn uses a fresh asyncio event loop (same pattern as
    invoke_production_agent).

    Args:
        user_turns: Pre-scripted user messages for the conversation.
        model: Optional model override (defaults to OPENAI_MODEL env var).
        api_key: Optional OpenAI API key (defaults to OPENAI_API_KEY env var).
        user_id: User ID for memory scoping in tool calls.
        max_turns: Maximum agent turns per message (default 10).

    Returns:
        Tuple of:
        - List of (turn_label, RunResult) tuples for each turn
        - Aggregated list of all tool call dicts across the conversation
    """
    settings = get_eval_settings()
    actual_api_key = api_key or settings.openai_api_key

    # Ensure OPENAI_API_KEY is in environment (required by OpenAI SDK)
    os.environ["OPENAI_API_KEY"] = actual_api_key

    from src.services.chat_service import ChatService

    service = ChatService()
    agent = service.create_agent(model=model, is_onboarded=False)

    context = {
        "user_id": user_id,
        "correlation_id": str(uuid4()),
        "conversation_id": None,
    }

    turn_results: list[tuple[str, RunResult]] = []
    all_tool_calls: list[dict] = []
    conversation_history: list[dict] = []

    # Turn 0: System greeting trigger
    greeting_input = "[System: New user session started. Greet the user warmly and begin onboarding.]"

    def _run_turn(input_data, history):
        """Run a single turn with a fresh event loop."""
        global _db_migrated

        async def _run():
            global _db_migrated
            from src.database import init_database, run_migrations, close_database

            try:
                await init_database()
                if not _db_migrated:
                    await run_migrations()
                    _db_migrated = True
            except Exception:
                pass

            try:
                # Build input as conversation history + new message
                if history:
                    messages = list(history)
                    if isinstance(input_data, str):
                        messages.append({"role": "user", "content": input_data})
                    return await Runner.run(
                        agent, input=messages, context=context, max_turns=max_turns
                    )
                else:
                    return await Runner.run(
                        agent, input=input_data, context=context, max_turns=max_turns
                    )
            finally:
                try:
                    await close_database()
                except Exception:
                    pass

        return asyncio.run(_run())

    # Run greeting turn
    try:
        result = _run_turn(greeting_input, [])
        turn_results.append(("greeting", result))
        tool_calls = extract_tool_calls(result)
        all_tool_calls.extend(tool_calls)

        # Add to conversation history
        conversation_history.append({"role": "user", "content": greeting_input})
        conversation_history.append({"role": "assistant", "content": result.final_output})
    except Exception as e:
        # If greeting fails, still try user turns
        conversation_history.append({"role": "user", "content": greeting_input})
        conversation_history.append({"role": "assistant", "content": f"[ERROR: {str(e)}]"})

    # Run user turns
    for idx, user_message in enumerate(user_turns):
        try:
            result = _run_turn(user_message, conversation_history)
            turn_results.append((f"turn-{idx + 1}", result))
            tool_calls = extract_tool_calls(result)
            all_tool_calls.extend(tool_calls)

            # Add to conversation history
            conversation_history.append({"role": "user", "content": user_message})
            conversation_history.append({"role": "assistant", "content": result.final_output})
        except Exception as e:
            conversation_history.append({"role": "user", "content": user_message})
            conversation_history.append({"role": "assistant", "content": f"[ERROR: {str(e)}]"})

    return turn_results, all_tool_calls


def cleanup_onboarding_eval_data(user_id: str) -> None:
    """
    Delete all memories and entities for an eval user before running a case.

    Prevents cross-contamination from previous eval runs.

    Args:
        user_id: The eval user ID to clean up.
    """
    async def _cleanup():
        from src.database import init_database, run_migrations, close_database

        global _db_migrated

        try:
            pool = await init_database()
            if not _db_migrated:
                await run_migrations()
                _db_migrated = True
        except Exception:
            return

        try:
            for table in ("memory_items", "entities", "relationships"):
                try:
                    await pool.execute(
                        f"UPDATE {table} SET deleted_at = NOW() "
                        f"WHERE user_id = $1 AND deleted_at IS NULL",
                        user_id,
                    )
                except Exception:
                    pass  # Table may not exist yet
        finally:
            await close_database()

    asyncio.run(_cleanup())


def query_saved_onboarding_data(user_id: str) -> tuple[list[str], list[str]]:
    """
    Query the database for memories and entities saved during an onboarding conversation.

    Because the orchestrator delegates to specialist sub-agents, tool calls for
    save_memory/save_entity don't appear in the top-level RunResult.new_items.
    Instead, we query the database directly for what was actually persisted.

    Args:
        user_id: The user ID used during the onboarding conversation.

    Returns:
        Tuple of (memory_contents, entity_names) actually saved to the database.
    """
    async def _query():
        from src.database import init_database, close_database

        try:
            pool = await init_database()
        except Exception:
            return [], []

        try:
            # Query memory_items for this user
            memory_rows = await pool.fetch(
                """
                SELECT content FROM memory_items
                WHERE user_id = $1 AND deleted_at IS NULL
                ORDER BY created_at DESC
                """,
                user_id,
            )
            memory_contents = [row["content"] for row in memory_rows]

            # Query entities for this user
            entity_rows = await pool.fetch(
                """
                SELECT name FROM entities
                WHERE user_id = $1 AND deleted_at IS NULL
                ORDER BY created_at DESC
                """,
                user_id,
            )
            entity_names = [row["name"] for row in entity_rows]

            return memory_contents, entity_names
        finally:
            await close_database()

    return asyncio.run(_query())


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
