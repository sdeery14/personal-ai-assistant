"""Memory-related models for conversations, messages, and memory items."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Valid message roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MemoryType(str, Enum):
    """Valid memory item types."""

    FACT = "fact"
    PREFERENCE = "preference"
    DECISION = "decision"
    NOTE = "note"


class Conversation(BaseModel):
    """A logical grouping of messages between a user and the assistant."""

    id: UUID
    user_id: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class Message(BaseModel):
    """A single turn in a conversation."""

    id: UUID
    conversation_id: UUID
    role: MessageRole
    content: str
    embedding: Optional[list[float]] = None
    correlation_id: UUID
    created_at: datetime


class MemoryItem(BaseModel):
    """A typed, curated piece of information from memory store."""

    id: UUID
    user_id: str
    content: str
    type: MemoryType
    relevance_score: float = Field(ge=0.0, le=1.0, default=0.0)
    source: Optional[str] = None  # Reference to source message if available
    created_at: datetime
    importance: float = Field(ge=0.0, le=1.0, default=0.5)


class MemoryQueryRequest(BaseModel):
    """Request for memory retrieval."""

    user_id: str = Field(..., description="Required: scoped retrieval")
    query: str = Field(..., description="The search query")
    limit: int = Field(default=10, ge=1, le=50)
    types: Optional[list[MemoryType]] = Field(
        default=None,
        description="Filter by memory type (optional)",
    )
    min_score: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum relevance threshold",
    )


class MemoryQueryResponse(BaseModel):
    """Response from memory retrieval."""

    items: list[MemoryItem]
    total_count: int
    query_embedding_ms: int = Field(
        description="Time to generate query embedding"
    )
    retrieval_ms: int = Field(description="Time for database retrieval")
    token_count: int = Field(description="Estimated tokens in returned content")
    truncated: bool = Field(
        description="Whether results were truncated for budget"
    )


class MemoryToolResponse(BaseModel):
    """Response format for the query_memory Agent tool."""

    memories: list[dict] = Field(
        description="List of memory items with content, type, relevance, context"
    )
    metadata: dict = Field(
        description="Metadata including count and truncated flag"
    )
