"""Save memory tool for the Agent to persist important information."""

import json
from typing import Optional
from uuid import UUID

import structlog
from agents import RunContextWrapper, function_tool

from src.models.memory import MemoryType, MemoryWriteRequest
from src.services.memory_write_service import MemoryWriteService, schedule_write

logger = structlog.get_logger(__name__)


@function_tool
async def save_memory_tool(
    ctx: RunContextWrapper,
    content: str,
    memory_type: str,
    confidence: float = 0.8,
    importance: float = 0.5,
) -> str:
    """Save important information about the user to long-term memory.

    Use this when the user shares facts, preferences, decisions, or other
    information worth remembering for future conversations.

    Guidelines for what to save:
    - Personal facts: name, location, job, family, pets
    - Preferences: likes, dislikes, communication style, tool preferences
    - Decisions: choices made, plans, commitments
    - Notes: important context, project details, goals

    Guidelines for confidence:
    - 0.9-1.0: User explicitly states something ("My name is...", "I prefer...")
    - 0.7-0.9: Strongly implied from context
    - 0.5-0.7: Somewhat uncertain, ask user to confirm
    - Below 0.5: Too uncertain, don't save

    Args:
        ctx: Runtime context containing user_id, correlation_id, conversation_id
        content: The information to remember. Should be a clear, standalone statement.
        memory_type: Type of memory: "fact", "preference", "decision", or "note"
        confidence: How confident you are this should be saved (0.0-1.0).
                    Below 0.5 is discarded, 0.5-0.7 needs user confirmation, 0.7+ is saved.
        importance: How important this memory is (0.0-1.0). Default 0.5.

    Returns:
        JSON string with action taken and details
    """
    # Extract context
    context = ctx.context if ctx else {}
    user_id = context.get("user_id") if context else None
    correlation_id = context.get("correlation_id") if context else None
    conversation_id = context.get("conversation_id") if context else None

    # Validate user_id
    if not user_id:
        logger.warning(
            "save_memory_missing_user_id",
            correlation_id=str(correlation_id) if correlation_id else None,
        )
        return json.dumps({
            "success": False,
            "action": "error",
            "message": "user_id not available in context",
        })

    # Validate memory type
    valid_types = [t.value for t in MemoryType if t != MemoryType.EPISODE]
    if memory_type.lower() not in valid_types:
        return json.dumps({
            "success": False,
            "action": "error",
            "message": f"Invalid memory type. Use one of: {', '.join(valid_types)}",
        })

    # Confidence gating
    if confidence < 0.5:
        logger.debug(
            "save_memory_discarded_low_confidence",
            user_id=user_id,
            confidence=confidence,
            correlation_id=str(correlation_id) if correlation_id else None,
        )
        return json.dumps({
            "success": False,
            "action": "discarded",
            "message": "Confidence too low to save. Consider asking the user to confirm.",
        })

    if confidence < 0.7:
        return json.dumps({
            "success": False,
            "action": "confirm_needed",
            "content": content,
            "message": (
                "Confidence is moderate. Please ask the user to confirm "
                "before saving this memory."
            ),
        })

    # Build write request
    request = MemoryWriteRequest(
        user_id=user_id,
        content=content,
        type=MemoryType(memory_type.lower()),
        confidence=confidence,
        source_conversation_id=UUID(str(conversation_id)) if conversation_id else None,
        importance=importance,
    )

    # Schedule async write
    try:
        write_service = MemoryWriteService()
        corr_uuid = UUID(str(correlation_id)) if correlation_id else None

        # Fire and forget the write
        schedule_write(write_service.create_memory(request, corr_uuid))

        logger.info(
            "save_memory_queued",
            user_id=user_id,
            memory_type=memory_type,
            confidence=confidence,
            correlation_id=str(correlation_id) if correlation_id else None,
        )

        return json.dumps({
            "success": True,
            "action": "queued",
            "message": f"Saving to memory: {content[:80]}",
        })

    except Exception as e:
        logger.error(
            "save_memory_error",
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__,
            correlation_id=str(correlation_id) if correlation_id else None,
        )
        return json.dumps({
            "success": False,
            "action": "error",
            "message": "Failed to save memory",
        })
