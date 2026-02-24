"""Engagement and proactiveness models for Feature 011 — Proactive Assistant."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EngagementAction(str, Enum):
    """User response to a proactive suggestion."""

    ENGAGED = "engaged"
    DISMISSED = "dismissed"


class SuggestionSource(str, Enum):
    """Where the suggestion was delivered."""

    CONVERSATION = "conversation"
    NOTIFICATION = "notification"
    SCHEDULE = "schedule"


class EngagementEvent(BaseModel):
    """A record of the user's response to a proactive suggestion."""

    id: UUID
    user_id: UUID
    suggestion_type: str
    action: EngagementAction
    source: SuggestionSource
    context: dict = Field(default_factory=dict)
    created_at: datetime


class ProactivenessSettings(BaseModel):
    """Per-user calibration state for proactive behavior."""

    id: UUID
    user_id: UUID
    global_level: float = 0.7
    suppressed_types: list = Field(default_factory=list)
    boosted_types: list = Field(default_factory=list)
    user_override: Optional[str] = None
    is_onboarded: bool = False
    created_at: datetime
    updated_at: datetime
