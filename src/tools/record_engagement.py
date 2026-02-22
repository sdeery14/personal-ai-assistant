"""Record engagement tool for the Agent to track user responses to suggestions."""

import json

import structlog
from agents import RunContextWrapper, function_tool

logger = structlog.get_logger(__name__)


@function_tool
async def record_engagement(
    ctx: RunContextWrapper,
    suggestion_type: str,
    action: str,
    source: str,
) -> str:
    """Record the user's response to a proactive suggestion.

    Use this when the user engages with or dismisses a proactive suggestion
    you've made. This helps calibrate future suggestions.

    Args:
        ctx: Runtime context containing user_id, correlation_id
        suggestion_type: Category of the suggestion (e.g., "weather_briefing", "meeting_prep")
        action: "engaged" if the user accepted/used the suggestion, "dismissed" if they declined
        source: Where the suggestion was delivered: "conversation", "notification", or "schedule"

    Returns:
        JSON string with success status and event details
    """
    context = ctx.context if ctx else {}
    user_id = context.get("user_id") if context else None
    correlation_id = context.get("correlation_id") if context else None

    if not user_id:
        logger.warning(
            "record_engagement_missing_user_id",
            correlation_id=str(correlation_id) if correlation_id else None,
        )
        return json.dumps({
            "success": False,
            "action": "error",
            "message": "user_id not available in context",
        })

    valid_actions = ["engaged", "dismissed"]
    if action not in valid_actions:
        return json.dumps({
            "success": False,
            "action": "error",
            "message": f"Invalid action. Use one of: {', '.join(valid_actions)}",
        })

    valid_sources = ["conversation", "notification", "schedule"]
    if source not in valid_sources:
        return json.dumps({
            "success": False,
            "action": "error",
            "message": f"Invalid source. Use one of: {', '.join(valid_sources)}",
        })

    try:
        from src.services.engagement_service import EngagementService

        service = EngagementService()
        result = await service.record_event(
            user_id=user_id,
            suggestion_type=suggestion_type,
            action=action,
            source=source,
        )

        logger.info(
            "record_engagement_success",
            user_id=user_id,
            suggestion_type=suggestion_type,
            action=action,
            source=source,
            event_id=result["event_id"],
            correlation_id=str(correlation_id) if correlation_id else None,
        )

        return json.dumps({
            "success": True,
            **result,
        })

    except Exception as e:
        logger.error(
            "record_engagement_error",
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__,
            correlation_id=str(correlation_id) if correlation_id else None,
        )
        return json.dumps({
            "success": False,
            "action": "error",
            "message": "Failed to record engagement",
        })
