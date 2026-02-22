"""Get user profile tool for the Agent to retrieve what it knows about the user."""

import json

import structlog
from agents import RunContextWrapper, function_tool

logger = structlog.get_logger(__name__)


@function_tool
async def get_user_profile(ctx: RunContextWrapper) -> str:
    """Retrieve a summary of what the assistant knows about the user.

    Use this when the user asks "what do you know about me?", "show me my profile",
    or similar requests. The response includes facts, preferences, patterns,
    key relationships, and proactiveness settings.

    Args:
        ctx: Runtime context containing user_id

    Returns:
        JSON string with user profile data
    """
    context = ctx.context if ctx else {}
    user_id = context.get("user_id") if context else None
    correlation_id = context.get("correlation_id") if context else None

    if not user_id:
        return json.dumps({
            "success": False,
            "action": "error",
            "message": "user_id not available in context",
        })

    try:
        from src.services.proactive_service import ProactiveService

        service = ProactiveService()
        profile = await service.get_user_profile(user_id)

        logger.info(
            "get_user_profile_success",
            user_id=user_id,
            fact_count=len(profile.get("facts", [])),
            preference_count=len(profile.get("preferences", [])),
            pattern_count=len(profile.get("patterns", [])),
            correlation_id=str(correlation_id) if correlation_id else None,
        )

        return json.dumps({
            "success": True,
            **profile,
        })

    except Exception as e:
        logger.error(
            "get_user_profile_error",
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__,
            correlation_id=str(correlation_id) if correlation_id else None,
        )
        return json.dumps({
            "success": False,
            "action": "error",
            "message": "Failed to retrieve user profile",
        })
