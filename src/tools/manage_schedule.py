"""Manage schedule tool for the Agent to pause/resume/cancel scheduled tasks."""

import json

import structlog
from agents import RunContextWrapper, function_tool

logger = structlog.get_logger(__name__)


@function_tool
async def manage_schedule(
    ctx: RunContextWrapper,
    task_id: str,
    action: str,
) -> str:
    """Modify an existing scheduled task — pause, resume, or cancel it.

    Args:
        ctx: Runtime context containing user_id
        task_id: UUID of the task to modify
        action: "pause" to pause, "resume" to reactivate, or "cancel" to stop permanently

    Returns:
        JSON string with updated task status
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

    valid_actions = ["pause", "resume", "cancel"]
    if action not in valid_actions:
        return json.dumps({
            "success": False,
            "action": "error",
            "message": f"Invalid action. Use one of: {', '.join(valid_actions)}",
        })

    # Map action to new status
    status_map = {
        "pause": "paused",
        "resume": "active",
        "cancel": "cancelled",
    }
    new_status = status_map[action]

    try:
        from src.services.schedule_service import ScheduleService

        service = ScheduleService()
        result = await service.update_status(
            task_id=task_id,
            user_id=user_id,
            new_status=new_status,
        )

        if result is None:
            return json.dumps({
                "success": False,
                "action": "error",
                "message": f"Task {task_id} not found or not owned by you",
            })

        logger.info(
            "manage_schedule_success",
            user_id=user_id,
            task_id=task_id,
            action=action,
            new_status=new_status,
            correlation_id=str(correlation_id) if correlation_id else None,
        )

        return json.dumps({
            "success": True,
            "task_id": str(result["id"]),
            "name": result["name"],
            "status": result["status"],
        })

    except Exception as e:
        logger.error(
            "manage_schedule_error",
            user_id=user_id,
            task_id=task_id,
            error=str(e),
            error_type=type(e).__name__,
            correlation_id=str(correlation_id) if correlation_id else None,
        )
        return json.dumps({
            "success": False,
            "action": "error",
            "message": "Failed to update schedule",
        })
