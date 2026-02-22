"""Notification models for Feature 010."""

from datetime import datetime, time
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationType(str, Enum):
    """Valid notification types."""

    REMINDER = "reminder"
    INFO = "info"
    WARNING = "warning"


class DeliveryChannel(str, Enum):
    """Notification delivery channel options."""

    IN_APP = "in_app"
    EMAIL = "email"
    BOTH = "both"


class Notification(BaseModel):
    """A notification from the agent to a user."""

    id: UUID
    user_id: UUID
    conversation_id: Optional[UUID] = None
    message: str
    type: NotificationType
    is_read: bool = False
    created_at: datetime


class NotificationPreferences(BaseModel):
    """Per-user notification delivery settings."""

    delivery_channel: DeliveryChannel = DeliveryChannel.IN_APP
    quiet_hours_start: Optional[time] = None
    quiet_hours_end: Optional[time] = None
    quiet_hours_timezone: Optional[str] = "UTC"


class NotificationPreferencesUpdate(BaseModel):
    """Request model for updating notification preferences."""

    delivery_channel: Optional[DeliveryChannel] = None
    quiet_hours_start: Optional[time] = None
    quiet_hours_end: Optional[time] = None
    quiet_hours_timezone: Optional[str] = None


class CreateNotificationRequest(BaseModel):
    """Validated input for creating a notification."""

    message: str = Field(..., min_length=1, max_length=500)
    type: NotificationType = NotificationType.INFO
