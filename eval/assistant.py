"""
Sync wrapper for Feature 001 assistant.

This module provides a synchronous interface to invoke the Feature 001
ChatService for evaluation purposes. It uses Runner.run_sync() for
non-streaming, deterministic evaluation.

MLflow tracing is enabled via mlflow.openai.autolog() to capture
detailed execution traces during evaluation.
"""

import os

import mlflow
from agents import Agent, Runner

from eval.config import get_eval_settings

# Enable MLflow auto-tracing for OpenAI calls
# This captures traces for debugging failed cases and enables future trace-based scorers
mlflow.openai.autolog()


def get_response(
    prompt: str, model: str | None = None, api_key: str | None = None
) -> str:
    """
    Get a complete assistant response synchronously.

    This function invokes the Feature 001 assistant using Runner.run_sync()
    (non-streaming) for deterministic evaluation. It reuses the same agent
    configuration as the main application.

    Args:
        prompt: The user prompt to send to the assistant.
        model: Optional model override (defaults to OPENAI_MODEL env var).
        api_key: Optional OpenAI API key (defaults to OPENAI_API_KEY env var).
                 Required when running in MLflow context where env vars may not be available.

    Returns:
        The complete assistant response as a string.

    Raises:
        Exception: If the assistant fails to generate a response.
    """
    settings = get_eval_settings()
    actual_model = model or settings.openai_model
    actual_api_key = api_key or settings.openai_api_key

    # Ensure OPENAI_API_KEY is in environment (required by OpenAI SDK)
    # This is critical for MLflow predict_fn which doesn't preserve environment
    os.environ["OPENAI_API_KEY"] = actual_api_key

    # Create agent with deterministic settings (temperature=0)
    agent = Agent(
        name="Assistant",
        instructions="You are a helpful assistant.",
        model=actual_model,
    )

    # Use run_sync for synchronous, non-streaming execution
    result = Runner.run_sync(agent, input=prompt)

    return result.final_output


def get_response_with_metadata(
    prompt: str, model: str | None = None
) -> dict[str, str | int]:
    """
    Get assistant response with additional metadata.

    Args:
        prompt: The user prompt to send to the assistant.
        model: Optional model override.

    Returns:
        Dictionary with 'response', 'model', and 'prompt_length' keys.
    """
    settings = get_eval_settings()
    actual_model = model or settings.openai_model
    response = get_response(prompt, model=actual_model)

    return {
        "response": response,
        "model": actual_model,
        "prompt_length": len(prompt),
        "response_length": len(response),
    }
