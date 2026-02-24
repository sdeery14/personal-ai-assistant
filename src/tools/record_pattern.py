"""Record pattern tool for the Agent to track behavioral observations."""

import json
from typing import Optional

import structlog
from agents import RunContextWrapper, function_tool

logger = structlog.get_logger(__name__)


@function_tool
async def record_pattern(
    ctx: RunContextWrapper,
    pattern_type: str,
    description: str,
    evidence: str,
    suggested_action: Optional[str] = None,
    confidence: float = 0.5,
) -> str:
    """Record or update an observed behavioral pattern for the user.

    Use this when you notice recurring topics, time-based behaviors, or
    frequently mentioned entities across conversations. If the same pattern
    has been recorded before, it will be updated with new evidence and the
    occurrence count will increase.

    Args:
        ctx: Runtime context containing user_id, correlation_id
        pattern_type: Category of pattern: "recurring_query", "time_based", or "topic_interest"
        description: Human-readable description (e.g., "Asks about weather most mornings")
        evidence: Context of the current observation
        suggested_action: What you could do about this pattern (e.g., "Schedule daily weather at 7am")
        confidence: Confidence in the pattern (0.0-1.0, default 0.5)

    Returns:
        JSON string with pattern_id, occurrence_count, and threshold_reached flag
    """
    context = ctx.context if ctx else {}
    user_id = context.get("user_id") if context else None
    correlation_id = context.get("correlation_id") if context else None

    if not user_id:
        logger.warning(
            "record_pattern_missing_user_id",
            correlation_id=str(correlation_id) if correlation_id else None,
        )
        return json.dumps({
            "success": False,
            "action": "error",
            "message": "user_id not available in context",
        })

    valid_types = ["recurring_query", "time_based", "topic_interest"]
    if pattern_type not in valid_types:
        return json.dumps({
            "success": False,
            "action": "error",
            "message": f"Invalid pattern_type. Use one of: {', '.join(valid_types)}",
        })

    if confidence < 0.0 or confidence > 1.0:
        return json.dumps({
            "success": False,
            "action": "error",
            "message": "Confidence must be between 0.0 and 1.0",
        })

    try:
        from src.services.pattern_service import PatternService

        service = PatternService()
        result = await service.record_or_update_pattern(
            user_id=user_id,
            pattern_type=pattern_type,
            description=description,
            evidence=evidence,
            suggested_action=suggested_action,
            confidence=confidence,
        )

        logger.info(
            "record_pattern_success",
            user_id=user_id,
            pattern_type=pattern_type,
            pattern_id=result["pattern_id"],
            occurrence_count=result["occurrence_count"],
            threshold_reached=result["threshold_reached"],
            correlation_id=str(correlation_id) if correlation_id else None,
        )

        return json.dumps({
            "success": True,
            **result,
        })

    except Exception as e:
        logger.error(
            "record_pattern_error",
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__,
            correlation_id=str(correlation_id) if correlation_id else None,
        )
        return json.dumps({
            "success": False,
            "action": "error",
            "message": "Failed to record pattern",
        })
