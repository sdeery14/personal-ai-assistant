"""Security guardrails for input/output validation using OpenAI Agents SDK.

Implements content safety validation using OpenAI Moderation API with:
- Proper SDK guardrail decorators (@input_guardrail, @output_guardrail)
- GuardrailFunctionOutput return type with tripwire mechanism
- Exponential backoff retry logic
- Fail-closed behavior on API errors
- Privacy-safe logging (content hashes only)
"""

import asyncio
import hashlib
import time
from typing import Optional
from uuid import UUID

import structlog
from openai import AsyncOpenAI
from agents import (
    Agent,
    GuardrailFunctionOutput,
    RunContextWrapper,
    TResponseInputItem,
    input_guardrail as sdk_input_guardrail,
    output_guardrail as sdk_output_guardrail,
)

from src.config import get_settings

logger = structlog.get_logger(__name__)


class GuardrailViolation(Exception):
    """Exception raised when content fails guardrail validation.

    Note: When using SDK guardrails, InputGuardrailTripwireTriggered or
    OutputGuardrailTripwireTriggered exceptions are raised instead.
    This class is kept for route handler compatibility.

    Attributes:
        guardrail_type: "input" or "output"
        violation_category: Category from moderation API (e.g., "harassment", "violence")
        content_hash: SHA256 hash of blocked content (for logging, not raw content)
        correlation_id: Request tracking ID
    """

    def __init__(
        self,
        guardrail_type: str,
        violation_category: str,
        content_hash: str,
        correlation_id: UUID,
    ):
        self.guardrail_type = guardrail_type
        self.violation_category = violation_category
        self.content_hash = content_hash
        self.correlation_id = correlation_id
        super().__init__(f"{guardrail_type} guardrail violation: {violation_category}")


async def moderate_with_retry(
    text: str,
    correlation_id: UUID,
    max_retries: int = 3,
) -> tuple[bool, Optional[str], int]:
    """Call OpenAI Moderation API with exponential backoff retry.

    Args:
        text: Content to moderate
        correlation_id: Request correlation UUID
        max_retries: Maximum retry attempts (default 3)

    Returns:
        Tuple of (is_flagged, category_or_none, retry_count)
        - is_flagged: True if content violates policies
        - category_or_none: Violation category if flagged, else None
        - retry_count: Number of retries performed
    """
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    retry_delays = [0, 0.1, 0.5, 1.0]  # Exponential backoff: 0s, 100ms, 500ms, 1s
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            start_time = time.perf_counter()
            response = await client.moderations.create(input=text)
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            result = response.results[0]
            is_flagged = result.flagged
            category = None

            if is_flagged:
                # Find first flagged category
                for cat_name, cat_value in result.categories.model_dump().items():
                    if cat_value:
                        category = cat_name
                        break

            # Hash content for privacy-safe logging
            content_hash = hashlib.sha256(text.encode()).hexdigest()

            logger.info(
                "moderation_check",
                correlation_id=str(correlation_id),
                is_flagged=is_flagged,
                category=category,
                content_hash=content_hash,
                content_length=len(text),
                latency_ms=latency_ms,
                retry_count=attempt,
            )

            return (is_flagged, category, attempt)

        except Exception as e:
            last_error = e
            logger.warning(
                "moderation_retry",
                correlation_id=str(correlation_id),
                attempt=attempt,
                error_type=type(e).__name__,
                error_message=str(e),
            )

            if attempt < max_retries:
                await asyncio.sleep(retry_delays[attempt])
            else:
                # Fail closed: treat as violation after exhausting retries
                content_hash = hashlib.sha256(text.encode()).hexdigest()
                logger.error(
                    "moderation_failed_closed",
                    correlation_id=str(correlation_id),
                    content_hash=content_hash,
                    retry_count=attempt,
                    error_type=type(last_error).__name__,
                )
                return (True, "moderation_api_failure", attempt)

    # Unreachable but satisfies type checker
    return (True, "unknown_error", max_retries)


@sdk_input_guardrail(
    run_in_parallel=False
)  # Blocking mode - prevents token consumption
async def validate_input(
    ctx: RunContextWrapper,
    agent: Agent,
    input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    """Input guardrail using OpenAI Moderation API.

    Runs in blocking mode to prevent agent execution if content is flagged.
    This integrates with the OpenAI Agents SDK guardrail system.

    Args:
        ctx: Run context wrapper with correlation_id stored
        agent: The agent being guarded
        input: User's input (string or list of input items)

    Returns:
        GuardrailFunctionOutput with tripwire_triggered=True if content flagged
    """
    # Extract text from input
    text = input if isinstance(input, str) else str(input)

    # Get correlation_id from context (stored by chat service)
    correlation_id = ctx.context.get("correlation_id") if ctx.context else None
    if not correlation_id:
        correlation_id = UUID(int=0)  # Fallback UUID

    is_flagged, category, retry_count = await moderate_with_retry(text, correlation_id)

    if is_flagged:
        content_hash = hashlib.sha256(text.encode()).hexdigest()
        logger.info(
            "input_guardrail_triggered",
            correlation_id=str(correlation_id),
            category=category,
            content_hash=content_hash,
            content_length=len(text),
            retry_count=retry_count,
        )
        # Store violation details in context for route handler to access
        if ctx.context:
            ctx.context["guardrail_violation"] = {
                "type": "input",
                "category": category or "unknown",
                "content_hash": content_hash,
            }

        return GuardrailFunctionOutput(
            output_info={"category": category, "retry_count": retry_count},
            tripwire_triggered=True,
        )

    return GuardrailFunctionOutput(
        output_info={"retry_count": retry_count},
        tripwire_triggered=False,
    )


@sdk_output_guardrail
async def validate_output(
    ctx: RunContextWrapper,
    agent: Agent,
    output: str,
) -> GuardrailFunctionOutput:
    """Output guardrail using OpenAI Moderation API.

    Runs after agent completes to validate the generated output.
    This integrates with the OpenAI Agents SDK guardrail system.

    Args:
        ctx: Run context wrapper with correlation_id stored
        agent: The agent being guarded
        output: Agent's output text

    Returns:
        GuardrailFunctionOutput with tripwire_triggered=True if content flagged
    """
    # Get correlation_id from context
    correlation_id = ctx.context.get("correlation_id") if ctx.context else None
    if not correlation_id:
        correlation_id = UUID(int=0)  # Fallback UUID

    is_flagged, category, retry_count = await moderate_with_retry(
        output, correlation_id
    )

    if is_flagged:
        content_hash = hashlib.sha256(output.encode()).hexdigest()
        logger.info(
            "output_guardrail_triggered",
            correlation_id=str(correlation_id),
            category=category,
            content_hash=content_hash,
            content_length=len(output),
            retry_count=retry_count,
        )
        # Store violation details in context
        if ctx.context:
            ctx.context["guardrail_violation"] = {
                "type": "output",
                "category": category or "unknown",
                "content_hash": content_hash,
            }

        return GuardrailFunctionOutput(
            output_info={"category": category, "retry_count": retry_count},
            tripwire_triggered=True,
        )

    return GuardrailFunctionOutput(
        output_info={"retry_count": retry_count},
        tripwire_triggered=False,
    )
