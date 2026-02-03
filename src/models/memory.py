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
    EPISODE = "episode"


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
    source_conversation_id: Optional[UUID] = None
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    superseded_by: Optional[UUID] = None
    status: str = "active"


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


class MemoryWriteRequest(BaseModel):
    """Request to create a new memory item via agent extraction."""

    user_id: str = Field(..., description="User ID for scoping")
    content: str = Field(..., min_length=1, max_length=2000, description="Memory content")
    type: MemoryType = Field(..., description="Memory type category")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Extraction confidence")
    source_message_id: Optional[UUID] = None
    source_conversation_id: Optional[UUID] = None
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="Memory importance")


class MemoryDeleteRequest(BaseModel):
    """Request to delete a memory item."""

    user_id: str = Field(..., description="User ID for scoping")
    query: str = Field(..., min_length=1, description="Description of memory to delete")
    reason: Optional[str] = Field(default=None, description="Reason for deletion")


class MemoryWriteResponse(BaseModel):
    """Response from a memory write operation."""

    success: bool
    memory_id: Optional[UUID] = None
    action: str = Field(description="Action taken: queued, discarded, confirm_needed, deleted, not_found, error")
    message: str = Field(description="Human-readable description of what happened")


class MemoryWriteEvent(BaseModel):
    """Audit log entry for memory write operations."""

    id: UUID
    memory_item_id: Optional[UUID] = None
    user_id: str
    operation: str  # create, delete, supersede, episode
    confidence: Optional[float] = None
    extraction_type: str  # agent, episode, manual
    before_content: Optional[str] = None
    after_content: Optional[str] = None
    correlation_id: Optional[UUID] = None
    processing_time_ms: Optional[int] = None
    created_at: datetime
