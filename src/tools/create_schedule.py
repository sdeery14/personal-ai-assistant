"""Create schedule tool for the Agent to set up scheduled tasks."""

import json
from typing import Optional

import structlog
from agents import RunContextWrapper, function_tool

logger = structlog.get_logger(__name__)


@function_tool
async def create_schedule(
    ctx: RunContextWrapper,
    name: str,
    task_type: str,
    tool_name: str,
    prompt_template: str,
    description: Optional[str] = None,
    schedule_cron: Optional[str] = None,
    scheduled_at: Optional[str] = None,
    timezone: str = "UTC",
    tool_args: Optional[str] = None,
) -> str:
    """Create a new scheduled task for the user.

    Use this when the user wants something done on a schedule ("remind me every morning",
    "send me weather at 7am") or at a specific time ("remind me at 3pm today").

    Args:
        ctx: Runtime context containing user_id
        name: Human-readable task name (e.g., "Morning weather briefing")
        task_type: "one_time" for single execution, "recurring" for repeated
        tool_name: Which tool to invoke (e.g., "get_weather")
        prompt_template: Prompt for the agent when executing this task
        description: Optional detailed description
        schedule_cron: Cron expression for recurring tasks (e.g., "0 7 * * *")
        scheduled_at: ISO datetime string for one-time tasks
        timezone: User's timezone (default: UTC)
        tool_args: JSON string of arguments to pass to the tool (e.g., '{"location": "Seattle"}')

    Returns:
        JSON string with task_id, next_run_at, and status
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

    valid_types = ["one_time", "recurring"]
    if task_type not in valid_types:
        return json.dumps({
            "success": False,
            "action": "error",
            "message": f"Invalid task_type. Use one of: {', '.join(valid_types)}",
        })

    # Validate cron expression for recurring tasks
    if task_type == "recurring":
        if not schedule_cron:
            return json.dumps({
                "success": False,
                "action": "error",
                "message": "schedule_cron is required for recurring tasks",
            })
        try:
            from croniter import croniter
            croniter(schedule_cron)
        except (ValueError, KeyError):
            return json.dumps({
                "success": False,
                "action": "error",
                "message": f"Invalid cron expression: {schedule_cron}",
            })

    if task_type == "one_time" and not scheduled_at:
        return json.dumps({
            "success": False,
            "action": "error",
            "message": "scheduled_at is required for one_time tasks",
        })

    # Parse scheduled_at if provided
    parsed_scheduled_at = None
    if scheduled_at:
        try:
            from datetime import datetime as dt, timezone as tz
            parsed_scheduled_at = dt.fromisoformat(scheduled_at)
            if parsed_scheduled_at.tzinfo is None:
                parsed_scheduled_at = parsed_scheduled_at.replace(tzinfo=tz.utc)
        except ValueError:
            return json.dumps({
                "success": False,
                "action": "error",
                "message": f"Invalid datetime format: {scheduled_at}. Use ISO format.",
            })

    try:
        from src.services.schedule_service import ScheduleService

        service = ScheduleService()
        result = await service.create_task(
            user_id=user_id,
            name=name,
            task_type=task_type,
            tool_name=tool_name,
            prompt_template=prompt_template,
            description=description,
            schedule_cron=schedule_cron,
            scheduled_at=parsed_scheduled_at,
            tz=timezone,
            tool_args=json.loads(tool_args) if tool_args else None,
        )

        logger.info(
            "create_schedule_success",
            user_id=user_id,
            task_id=result["task_id"],
            task_type=task_type,
            correlation_id=str(correlation_id) if correlation_id else None,
        )

        return json.dumps({"success": True, **result})

    except Exception as e:
        logger.error(
            "create_schedule_error",
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__,
            correlation_id=str(correlation_id) if correlation_id else None,
        )
        return json.dumps({
            "success": False,
            "action": "error",
            "message": "Failed to create schedule",
        })
