"""Adjust proactiveness tool for explicit user calibration."""

import json

import structlog
from agents import RunContextWrapper, function_tool

logger = structlog.get_logger(__name__)


@function_tool
async def adjust_proactiveness(
    ctx: RunContextWrapper,
    direction: str,
) -> str:
    """Adjust the user's proactiveness level based on their explicit instruction.

    Use this when the user says "be more proactive", "be less proactive",
    "stop suggesting things", or similar calibration requests.

    Args:
        ctx: Runtime context containing user_id
        direction: "more" to increase proactiveness, "less" to decrease

    Returns:
        JSON string with new global_level and confirmation
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

    valid_directions = ["more", "less"]
    if direction not in valid_directions:
        return json.dumps({
            "success": False,
            "action": "error",
            "message": f"Invalid direction. Use one of: {', '.join(valid_directions)}",
        })

    try:
        from src.services.proactive_service import ProactiveService

        service = ProactiveService()
        settings = await service.get_or_create_settings(user_id)
        current_level = settings["global_level"]

        if direction == "more":
            new_level = min(1.0, current_level + 0.2)
            updates = {
                "global_level": new_level,
                "user_override": "more",
                "suppressed_types": json.dumps([]),
            }
        else:
            new_level = max(0.0, current_level - 0.2)
            updates = {
                "global_level": new_level,
                "user_override": "less",
            }

        result = await service.update_settings(user_id, **updates)

        logger.info(
            "proactiveness_adjusted",
            user_id=user_id,
            direction=direction,
            old_level=current_level,
            new_level=new_level,
            correlation_id=str(correlation_id) if correlation_id else None,
        )

        return json.dumps({
            "success": True,
            "direction": direction,
            "previous_level": round(current_level, 2),
            "new_level": round(new_level, 2),
            "message": f"Proactiveness {'increased' if direction == 'more' else 'decreased'} to {round(new_level, 2)}",
        })

    except Exception as e:
        logger.error(
            "adjust_proactiveness_error",
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__,
            correlation_id=str(correlation_id) if correlation_id else None,
        )
        return json.dumps({
            "success": False,
            "action": "error",
            "message": "Failed to adjust proactiveness",
        })
