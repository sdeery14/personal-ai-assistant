"""Knowledge graph models for entities and relationships."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """Valid entity types in the knowledge graph."""

    PERSON = "person"
    PROJECT = "project"
    TOOL = "tool"
    CONCEPT = "concept"
    ORGANIZATION = "organization"


class RelationshipType(str, Enum):
    """Valid relationship types between entities."""

    USES = "USES"  # User/project uses a tool
    PREFERS = "PREFERS"  # User prefers X (optionally over Y)
    DECIDED = "DECIDED"  # User made a decision about X
    WORKS_ON = "WORKS_ON"  # User/person works on project
    WORKS_WITH = "WORKS_WITH"  # User works with person
    KNOWS = "KNOWS"  # User knows person
    DEPENDS_ON = "DEPENDS_ON"  # Project/tool depends on another
    MENTIONED_IN = "MENTIONED_IN"  # Entity mentioned in episode
    PART_OF = "PART_OF"  # Entity is part of another


class Entity(BaseModel):
    """An entity in the knowledge graph (person, project, tool, etc.)."""

    id: UUID
    user_id: str
    name: str
    canonical_name: str
    type: EntityType
    aliases: list[str] = Field(default_factory=list)
    description: Optional[str] = None
    embedding: Optional[list[float]] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    mention_count: int = Field(default=1, ge=1)
    first_seen_message_id: Optional[UUID] = None
    first_seen_conversation_id: Optional[UUID] = None
    last_mentioned_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class Relationship(BaseModel):
    """A relationship between entities in the knowledge graph."""

    id: UUID
    user_id: str
    source_entity_id: UUID
    target_entity_id: Optional[UUID] = None  # Nullable for user-centric relationships
    relationship_type: RelationshipType
    context: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_message_id: Optional[UUID] = None
    source_conversation_id: Optional[UUID] = None
    created_at: datetime
    deleted_at: Optional[datetime] = None


class EntityCreateRequest(BaseModel):
    """Request to create or retrieve an entity."""

    name: str = Field(..., min_length=1, max_length=255, description="Entity name")
    type: EntityType = Field(..., description="Entity type")
    description: Optional[str] = Field(
        default=None, max_length=1000, description="Optional description/context"
    )
    confidence: float = Field(
        default=0.9, ge=0.0, le=1.0, description="Extraction confidence"
    )


class RelationshipCreateRequest(BaseModel):
    """Request to create a relationship between entities."""

    source_entity_name: str = Field(
        ..., min_length=1, description="Source entity name"
    )
    source_entity_type: EntityType = Field(..., description="Source entity type")
    target_entity_name: Optional[str] = Field(
        default=None, description="Target entity name (optional for user-centric)"
    )
    target_entity_type: Optional[EntityType] = Field(
        default=None, description="Target entity type"
    )
    relationship_type: RelationshipType = Field(..., description="Relationship type")
    context: Optional[str] = Field(
        default=None, max_length=500, description="Additional context"
    )
    confidence: float = Field(
        default=0.9, ge=0.0, le=1.0, description="Extraction confidence"
    )


class GraphQueryRequest(BaseModel):
    """Request for graph-based retrieval."""

    query: str = Field(..., min_length=1, description="Natural language query")
    entity_type: Optional[EntityType] = Field(
        default=None, description="Filter by entity type"
    )
    relationship_type: Optional[RelationshipType] = Field(
        default=None, description="Filter by relationship type"
    )
    limit: int = Field(default=10, ge=1, le=50, description="Max results to return")


class EntityWithRelationships(BaseModel):
    """An entity with its related entities and relationships."""

    entity: Entity
    relationships: list[Relationship] = Field(default_factory=list)
    related_entities: list[Entity] = Field(default_factory=list)


class GraphQueryResponse(BaseModel):
    """Response from graph-based retrieval."""

    entities: list[EntityWithRelationships] = Field(default_factory=list)
    total_entities: int = Field(default=0)
    total_relationships: int = Field(default=0)
    query_time_ms: int = Field(default=0, description="Query execution time")


class EntityToolResponse(BaseModel):
    """Response format for the save_entity agent tool."""

    success: bool
    entity_id: Optional[UUID] = None
    action: str = Field(
        description="Action taken: created, existing, rate_limited, error"
    )
    entity_name: str
    entity_type: EntityType
    message: str = Field(description="Human-readable description")


class RelationshipToolResponse(BaseModel):
    """Response format for the save_relationship agent tool."""

    success: bool
    relationship_id: Optional[UUID] = None
    action: str = Field(
        description="Action taken: created, reinforced, rate_limited, error"
    )
    source_entity: str
    target_entity: Optional[str] = None
    relationship_type: RelationshipType
    message: str = Field(description="Human-readable description")


class GraphToolResponse(BaseModel):
    """Response format for the query_graph agent tool."""

    entities: list[dict] = Field(
        description="List of entities with name, type, description, relationships"
    )
    metadata: dict = Field(
        description="Metadata including count, query_time_ms, truncated flag"
    )
