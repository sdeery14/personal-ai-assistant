"""Send notification tool for the Agent to create persistent notifications."""

import json

import structlog
from agents import RunContextWrapper, function_tool

logger = structlog.get_logger(__name__)

VALID_TYPES = {"reminder", "info", "warning"}


@function_tool
async def send_notification(
    ctx: RunContextWrapper,
    message: str,
    type: str = "info",
) -> str:
    """Send a notification to the user.

    Use this when the user asks to be reminded about something, when you
    identify information worth flagging for later, or when you want to
    surface a warning. Notifications persist beyond the current conversation
    and can be delivered via email if the user has opted in.

    Args:
        ctx: Runtime context containing user_id, conversation_id, correlation_id
        message: The notification message (1-500 characters)
        type: Notification type: "reminder", "info", or "warning". Default: "info"

    Returns:
        JSON string with action taken and details
    """
    context = ctx.context if ctx else {}
    user_id = context.get("user_id")
    conversation_id = context.get("conversation_id")
    correlation_id = context.get("correlation_id")

    # Validate user context
    if not user_id:
        return json.dumps({
            "success": False,
            "action": "error",
            "message": "Missing user_id in context",
        })

    # Validate message
    if not message or not message.strip():
        return json.dumps({
            "success": False,
            "action": "validation_error",
            "message": "Message must not be empty",
        })

    if len(message) > 500:
        return json.dumps({
            "success": False,
            "action": "validation_error",
            "message": "Message must be between 1 and 500 characters",
        })

    # Validate type
    if type not in VALID_TYPES:
        return json.dumps({
            "success": False,
            "action": "validation_error",
            "message": f"Invalid type '{type}'. Must be one of: reminder, info, warning",
        })

    try:
        from src.services.notification_service import NotificationService

        service = NotificationService()

        # Check rate limit
        allowed = await service.check_rate_limit(user_id)
        if not allowed:
            logger.warning(
                "notification_rate_limited",
                user_id=user_id,
                correlation_id=correlation_id,
            )
            return json.dumps({
                "success": False,
                "action": "rate_limited",
                "message": "Notification rate limit exceeded. Try again later.",
            })

        # Create the notification
        notification = await service.create_notification(
            user_id=user_id,
            message=message.strip(),
            notification_type=type,
            conversation_id=conversation_id,
        )

        logger.info(
            "notification_tool_success",
            notification_id=str(notification.id),
            user_id=user_id,
            type=type,
            correlation_id=correlation_id,
        )

        # Truncate message for preview
        preview = message[:80] + "..." if len(message) > 80 else message

        return json.dumps({
            "success": True,
            "action": "notification_created",
            "message": f"Notification created: {preview}",
            "notification_id": str(notification.id),
            "type": type,
        })

    except Exception as e:
        logger.error(
            "notification_tool_error",
            error=str(e),
            user_id=user_id,
            correlation_id=correlation_id,
        )
        return json.dumps({
            "success": False,
            "action": "error",
            "message": f"Failed to create notification: {str(e)}",
        })


# Export for tool registration
send_notification_tool = send_notification
