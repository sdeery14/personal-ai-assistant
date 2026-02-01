"""Query memory tool for the Agent to retrieve relevant past context."""

import json
from typing import Optional
from uuid import UUID

import structlog
from agents import RunContextWrapper, function_tool

from src.models.memory import MemoryQueryRequest, MemoryType
from src.services.memory_service import MemoryService
from src.services.redis_service import RedisService

logger = structlog.get_logger(__name__)


@function_tool
async def query_memory_tool(
    ctx: RunContextWrapper,
    query: str,
    types: Optional[list[str]] = None,
) -> str:
    """Retrieve relevant memories from the user's past conversations and stored context.

    Use this when the user's question may relate to something discussed previously
    or when personalization would improve the response.

    Args:
        ctx: Runtime context containing user_id and correlation_id
        query: Search query to find relevant memories. Should capture the semantic
               intent of what context would be helpful.
        types: Optional filter to specific memory types. Valid values:
               "fact", "preference", "decision", "note"

    Returns:
        JSON string with 'memories' array and 'metadata' object
    """
    # Extract context
    context = ctx.context if ctx else {}
    user_id = context.get("user_id") if context else None
    correlation_id = context.get("correlation_id") if context else None

    # Validate user_id is present (security requirement)
    if not user_id:
        logger.warning(
            "query_memory_missing_user_id",
            correlation_id=str(correlation_id) if correlation_id else None,
        )
        return json.dumps({
            "memories": [],
            "metadata": {
                "count": 0,
                "truncated": False,
                "error": "user_id not available in context",
            },
        })

    # Check rate limit
    redis_service = RedisService()
    allowed, remaining = await redis_service.check_rate_limit(user_id)

    if not allowed:
        logger.warning(
            "query_memory_rate_limited",
            user_id=user_id,
            correlation_id=str(correlation_id) if correlation_id else None,
        )
        return json.dumps({
            "memories": [],
            "metadata": {
                "count": 0,
                "truncated": False,
                "error": "rate limit exceeded",
                "remaining": 0,
            },
        })

    try:
        # Parse memory types if provided
        memory_types = None
        if types:
            valid_types = [m.value for m in MemoryType]
            memory_types = [MemoryType(t.lower()) for t in types if t.lower() in valid_types]

        # Build request
        request = MemoryQueryRequest(
            user_id=user_id,
            query=query,
            types=memory_types,
        )

        # Execute search
        memory_service = MemoryService()
        response = await memory_service.hybrid_search(
            request=request,
            correlation_id=UUID(str(correlation_id)) if correlation_id else None,
        )

        # Format response for Agent
        memories = [
            {
                "content": item.content,
                "type": item.type.value,
                "relevance": round(item.relevance_score, 3),
                "context": f"From {item.created_at.strftime('%Y-%m-%d')}" + (
                    f" (importance: {item.importance})" if item.importance > 0.5 else ""
                ),
            }
            for item in response.items
        ]

        logger.debug(
            "query_memory_success",
            user_id=user_id,
            correlation_id=str(correlation_id) if correlation_id else None,
            result_count=len(memories),
            truncated=response.truncated,
        )

        return json.dumps({
            "memories": memories,
            "metadata": {
                "count": len(memories),
                "truncated": response.truncated,
                "total_available": response.total_count,
                "remaining_rate_limit": remaining,
            },
        })

    except Exception as e:
        # Fail closed: return empty results on error
        logger.error(
            "query_memory_error",
            user_id=user_id,
            correlation_id=str(correlation_id) if correlation_id else None,
            error=str(e),
            error_type=type(e).__name__,
        )
        return json.dumps({
            "memories": [],
            "metadata": {
                "count": 0,
                "truncated": False,
                "error": "retrieval failed",
            },
        })
