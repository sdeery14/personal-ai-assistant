"""Delete memory tool for the Agent to remove outdated or incorrect memories."""

import json
from uuid import UUID

import structlog
from agents import RunContextWrapper, function_tool

from src.models.memory import MemoryDeleteRequest
from src.services.memory_write_service import MemoryWriteService, schedule_write

logger = structlog.get_logger(__name__)


@function_tool
async def delete_memory_tool(
    ctx: RunContextWrapper,
    description: str,
    confirm: bool = False,
) -> str:
    """Delete memories that are outdated, incorrect, or no longer relevant.

    This is a two-step process:
    1. First call with confirm=False to search for matching memories
    2. Then call with confirm=True to actually delete them

    Use this when the user says something like:
    - "Forget that I like X" / "I no longer prefer X"
    - "That's wrong, please remove it"
    - "Delete what you know about my job"

    Args:
        ctx: Runtime context containing user_id and correlation_id
        description: Description of the memory to delete (e.g., "my preference for dark mode")
        confirm: If False, returns matching memories for review.
                 If True, proceeds with deletion.

    Returns:
        JSON string with matching memories (search mode) or deletion result (confirm mode)
    """
    # Extract context
    context = ctx.context if ctx else {}
    user_id = context.get("user_id") if context else None
    correlation_id = context.get("correlation_id") if context else None

    # Validate user_id
    if not user_id:
        logger.warning(
            "delete_memory_missing_user_id",
            correlation_id=str(correlation_id) if correlation_id else None,
        )
        return json.dumps({
            "success": False,
            "action": "error",
            "message": "user_id not available in context",
        })

    write_service = MemoryWriteService()
    corr_uuid = UUID(str(correlation_id)) if correlation_id else None

    if not confirm:
        # Search mode: find matching memories to present to user
        try:
            candidates = await write_service.search_memories(
                user_id=user_id,
                query=description,
                correlation_id=corr_uuid,
            )

            if not candidates:
                return json.dumps({
                    "success": False,
                    "action": "not_found",
                    "message": "No matching memories found",
                    "candidates": [],
                })

            return json.dumps({
                "success": True,
                "action": "candidates_found",
                "message": f"Found {len(candidates)} matching memories. Ask the user which to delete, then call again with confirm=True.",
                "candidates": candidates,
            })

        except Exception as e:
            logger.error(
                "delete_memory_search_error",
                user_id=user_id,
                error=str(e),
                correlation_id=str(correlation_id) if correlation_id else None,
            )
            return json.dumps({
                "success": False,
                "action": "error",
                "message": "Failed to search for memories",
            })
    else:
        # Confirm mode: perform deletion
        try:
            request = MemoryDeleteRequest(
                user_id=user_id,
                query=description,
                reason="User requested deletion via assistant",
            )

            # Fire and forget the delete
            schedule_write(write_service.delete_memory(request, corr_uuid))

            logger.info(
                "delete_memory_queued",
                user_id=user_id,
                description=description[:80],
                correlation_id=str(correlation_id) if correlation_id else None,
            )

            return json.dumps({
                "success": True,
                "action": "deletion_queued",
                "message": f"Deleting memories matching: {description[:80]}",
            })

        except Exception as e:
            logger.error(
                "delete_memory_error",
                user_id=user_id,
                error=str(e),
                correlation_id=str(correlation_id) if correlation_id else None,
            )
            return json.dumps({
                "success": False,
                "action": "error",
                "message": "Failed to delete memories",
            })
