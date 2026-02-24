"""Pattern models for Feature 011 — Proactive Assistant."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PatternType(str, Enum):
    """Types of observed behavioral patterns."""

    RECURRING_QUERY = "recurring_query"
    TIME_BASED = "time_based"
    TOPIC_INTEREST = "topic_interest"


class ObservedPattern(BaseModel):
    """A behavioral pattern detected across conversations."""

    id: UUID
    user_id: UUID
    pattern_type: PatternType
    description: str
    evidence: list = Field(default_factory=list)
    occurrence_count: int = 1
    first_seen_at: datetime
    last_seen_at: datetime
    acted_on: bool = False
    suggested_action: Optional[str] = None
    confidence: float = 0.5
    created_at: datetime
    updated_at: datetime
