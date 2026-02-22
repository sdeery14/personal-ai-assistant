"""Notification API endpoints for Feature 010."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
import structlog

from src.api.dependencies import get_current_user
from src.models.notification import (
    NotificationPreferencesUpdate,
)
from src.models.user import User
from src.services.notification_service import NotificationService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
async def list_notifications(
    type: str | None = Query(default=None, description="Filter by notification type"),
    is_read: bool | None = Query(default=None, description="Filter by read status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
) -> dict:
    """List notifications for the authenticated user, excluding dismissed ones."""
    service = NotificationService()
    notifications, total = await service.list_notifications(
        user_id=str(current_user.id),
        type_filter=type,
        is_read_filter=is_read,
        limit=limit,
        offset=offset,
    )

    return {
        "items": [
            {
                "id": str(n.id),
                "message": n.message,
                "type": n.type.value,
                "is_read": n.is_read,
                "conversation_id": str(n.conversation_id) if n.conversation_id else None,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifications
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get count of unread, non-dismissed notifications."""
    service = NotificationService()
    count = await service.get_unread_count(str(current_user.id))
    return {"count": count}


@router.patch("/{notification_id}/read")
async def mark_as_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Mark a single notification as read."""
    service = NotificationService()
    notification = await service.mark_as_read(notification_id, str(current_user.id))

    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {
        "id": str(notification.id),
        "message": notification.message,
        "type": notification.type.value,
        "is_read": notification.is_read,
        "conversation_id": str(notification.conversation_id) if notification.conversation_id else None,
        "created_at": notification.created_at.isoformat(),
    }


@router.patch("/read-all")
async def mark_all_as_read(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Mark all non-dismissed notifications as read."""
    service = NotificationService()
    count = await service.mark_all_as_read(str(current_user.id))
    return {"updated_count": count}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
) -> None:
    """Dismiss (soft-delete) a notification."""
    service = NotificationService()
    result = await service.dismiss_notification(notification_id, str(current_user.id))

    if not result:
        raise HTTPException(status_code=404, detail="Notification not found")


@router.get("/preferences")
async def get_preferences(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get notification preferences for the authenticated user."""
    service = NotificationService()
    prefs = await service.get_preferences(str(current_user.id))

    return {
        "delivery_channel": prefs.delivery_channel.value,
        "quiet_hours_start": prefs.quiet_hours_start.isoformat() if prefs.quiet_hours_start else None,
        "quiet_hours_end": prefs.quiet_hours_end.isoformat() if prefs.quiet_hours_end else None,
        "quiet_hours_timezone": prefs.quiet_hours_timezone,
    }


@router.put("/preferences")
async def update_preferences(
    body: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Create or update notification preferences."""
    # Validate quiet hours: both must be set or both must be null
    has_start = body.quiet_hours_start is not None
    has_end = body.quiet_hours_end is not None
    if has_start != has_end:
        raise HTTPException(
            status_code=422,
            detail="quiet_hours_start and quiet_hours_end must both be set or both be null",
        )

    service = NotificationService()
    prefs = await service.update_preferences(str(current_user.id), body)

    return {
        "delivery_channel": prefs.delivery_channel.value,
        "quiet_hours_start": prefs.quiet_hours_start.isoformat() if prefs.quiet_hours_start else None,
        "quiet_hours_end": prefs.quiet_hours_end.isoformat() if prefs.quiet_hours_end else None,
        "quiet_hours_timezone": prefs.quiet_hours_timezone,
    }
