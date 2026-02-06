"""Knowledge graph service for entity and relationship management."""

import re
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import structlog

from src.database import get_pool
from src.models.graph import (
    Entity,
    EntityType,
    Relationship,
    RelationshipType,
)
from src.services.embedding_service import EmbeddingService

logger = structlog.get_logger(__name__)


def normalize_entity_name(name: str) -> str:
    """Normalize entity name for deduplication.

    Converts to lowercase, strips whitespace, and handles common variations.

    Args:
        name: Raw entity name

    Returns:
        Normalized canonical name for comparison
    """
    if not name:
        return ""

    # Lowercase and strip whitespace
    canonical = name.lower().strip()

    # Remove extra whitespace
    canonical = re.sub(r"\s+", " ", canonical)

    # Remove common prefixes that don't affect identity
    prefixes = ["the ", "a ", "an "]
    for prefix in prefixes:
        if canonical.startswith(prefix):
            canonical = canonical[len(prefix) :]

    return canonical


def embedding_to_pgvector(embedding: list[float] | None) -> str | None:
    """Convert embedding list to pgvector string format."""
    if embedding is None:
        return None
    return "[" + ",".join(str(x) for x in embedding) + "]"


def pgvector_to_embedding(pgvector_str: str | None) -> list[float] | None:
    """Convert pgvector string format back to embedding list."""
    if pgvector_str is None:
        return None
    if isinstance(pgvector_str, list):
        return pgvector_str
    inner = pgvector_str.strip("[]")
    if not inner:
        return []
    return [float(x) for x in inner.split(",")]


class GraphService:
    """Service for knowledge graph operations."""

    def __init__(self):
        self.embedding_service = EmbeddingService()

    # =========================================================================
    # Entity Operations
    # =========================================================================

    async def get_entity_by_id(self, entity_id: UUID, user_id: str) -> Optional[Entity]:
        """Get an entity by ID with user scoping.

        Args:
            entity_id: Entity UUID
            user_id: User ID for security scoping

        Returns:
            Entity or None if not found
        """
        pool = await get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, name, canonical_name, type, aliases, description,
                       embedding, confidence, mention_count, first_seen_message_id,
                       first_seen_conversation_id, last_mentioned_at, created_at,
                       updated_at, deleted_at
                FROM entities
                WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL
                """,
                entity_id,
                user_id,
            )

        if row:
            return self._row_to_entity(row)
        return None

    async def get_entity_by_canonical_name(
        self, canonical_name: str, entity_type: EntityType, user_id: str
    ) -> Optional[Entity]:
        """Get an entity by canonical name and type.

        Args:
            canonical_name: Normalized entity name
            entity_type: Entity type
            user_id: User ID for scoping

        Returns:
            Entity or None if not found
        """
        pool = await get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, name, canonical_name, type, aliases, description,
                       embedding, confidence, mention_count, first_seen_message_id,
                       first_seen_conversation_id, last_mentioned_at, created_at,
                       updated_at, deleted_at
                FROM entities
                WHERE canonical_name = $1 AND type = $2 AND user_id = $3
                      AND deleted_at IS NULL
                """,
                canonical_name,
                entity_type.value,
                user_id,
            )

        if row:
            return self._row_to_entity(row)
        return None

    async def create_entity(
        self,
        user_id: str,
        name: str,
        entity_type: EntityType,
        description: Optional[str] = None,
        confidence: float = 1.0,
        message_id: Optional[UUID] = None,
        conversation_id: Optional[UUID] = None,
    ) -> Entity:
        """Create a new entity.

        Args:
            user_id: User ID for scoping
            name: Display name
            entity_type: Entity type
            description: Optional description
            confidence: Extraction confidence
            message_id: Source message ID
            conversation_id: Source conversation ID

        Returns:
            Created Entity

        Raises:
            Exception: If entity creation fails (caller should handle race conditions)
        """
        pool = await get_pool()
        entity_id = uuid4()
        now = datetime.now(timezone.utc)
        canonical_name = normalize_entity_name(name)

        # Generate embedding for the entity
        embedding_text = f"{name}: {description}" if description else name
        embedding = await self.embedding_service.get_embedding(embedding_text)
        embedding_str = embedding_to_pgvector(embedding)

        async with pool.acquire() as conn:
            # Use ON CONFLICT to handle race conditions
            row = await conn.fetchrow(
                """
                INSERT INTO entities (
                    id, user_id, name, canonical_name, type, description,
                    embedding, confidence, mention_count, first_seen_message_id,
                    first_seen_conversation_id, last_mentioned_at, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 1, $9, $10, $11, $12, $13)
                ON CONFLICT (user_id, canonical_name, type) WHERE deleted_at IS NULL
                DO UPDATE SET
                    mention_count = entities.mention_count + 1,
                    last_mentioned_at = EXCLUDED.last_mentioned_at,
                    updated_at = EXCLUDED.updated_at
                RETURNING id, mention_count, created_at
                """,
                entity_id,
                user_id,
                name,
                canonical_name,
                entity_type.value,
                description,
                embedding_str,
                confidence,
                message_id,
                conversation_id,
                now,
                now,
                now,
            )

        # Check if this was an insert or update
        actual_id = row["id"]
        was_created = actual_id == entity_id

        if was_created:
            logger.info(
                "entity_created",
                entity_id=str(actual_id),
                user_id=user_id,
                name=name,
                type=entity_type.value,
                confidence=confidence,
            )
        else:
            logger.debug(
                "entity_updated_on_conflict",
                entity_id=str(actual_id),
                user_id=user_id,
                name=name,
                mention_count=row["mention_count"],
            )

        return Entity(
            id=actual_id,
            user_id=user_id,
            name=name,
            canonical_name=canonical_name,
            type=entity_type,
            aliases=[],
            description=description,
            embedding=embedding,
            confidence=confidence,
            mention_count=row["mention_count"],
            first_seen_message_id=message_id,
            first_seen_conversation_id=conversation_id,
            last_mentioned_at=now,
            created_at=row["created_at"],
            updated_at=now,
            deleted_at=None,
        )

    async def get_or_create_entity(
        self,
        user_id: str,
        name: str,
        entity_type: EntityType,
        description: Optional[str] = None,
        confidence: float = 1.0,
        message_id: Optional[UUID] = None,
        conversation_id: Optional[UUID] = None,
    ) -> tuple[Entity, bool]:
        """Get existing entity or create new one.

        Args:
            user_id: User ID for scoping
            name: Entity name
            entity_type: Entity type
            description: Optional description
            confidence: Extraction confidence
            message_id: Source message ID
            conversation_id: Source conversation ID

        Returns:
            Tuple of (Entity, created: bool)
        """
        canonical_name = normalize_entity_name(name)

        # Try to find existing entity
        existing = await self.get_entity_by_canonical_name(
            canonical_name, entity_type, user_id
        )

        if existing:
            # Update mention count and last_mentioned_at
            await self.update_entity_mention(existing.id, user_id)
            # Refresh to get updated values
            updated = await self.get_entity_by_id(existing.id, user_id)
            return updated or existing, False

        # Create new entity
        entity = await self.create_entity(
            user_id=user_id,
            name=name,
            entity_type=entity_type,
            description=description,
            confidence=confidence,
            message_id=message_id,
            conversation_id=conversation_id,
        )
        return entity, True

    async def update_entity_mention(self, entity_id: UUID, user_id: str) -> None:
        """Update entity mention count and last_mentioned_at.

        Args:
            entity_id: Entity ID
            user_id: User ID for scoping
        """
        pool = await get_pool()
        now = datetime.now(timezone.utc)

        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE entities
                SET mention_count = mention_count + 1,
                    last_mentioned_at = $1,
                    updated_at = $2
                WHERE id = $3 AND user_id = $4 AND deleted_at IS NULL
                """,
                now,
                now,
                entity_id,
                user_id,
            )

    async def search_entities(
        self,
        user_id: str,
        name_pattern: Optional[str] = None,
        entity_type: Optional[EntityType] = None,
        limit: int = 10,
    ) -> list[Entity]:
        """Search entities by name pattern and/or type.

        Args:
            user_id: User ID for scoping
            name_pattern: Optional name pattern to match
            entity_type: Optional type filter
            limit: Max results

        Returns:
            List of matching entities
        """
        pool = await get_pool()

        query = """
            SELECT id, user_id, name, canonical_name, type, aliases, description,
                   embedding, confidence, mention_count, first_seen_message_id,
                   first_seen_conversation_id, last_mentioned_at, created_at,
                   updated_at, deleted_at
            FROM entities
            WHERE user_id = $1 AND deleted_at IS NULL
        """
        params: list = [user_id]
        param_idx = 2

        if name_pattern:
            query += f" AND canonical_name ILIKE ${param_idx}"
            params.append(f"%{normalize_entity_name(name_pattern)}%")
            param_idx += 1

        if entity_type:
            query += f" AND type = ${param_idx}"
            params.append(entity_type.value)
            param_idx += 1

        query += f" ORDER BY mention_count DESC, last_mentioned_at DESC LIMIT ${param_idx}"
        params.append(limit)

        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [self._row_to_entity(row) for row in rows]

    async def soft_delete_entity(self, entity_id: UUID, user_id: str) -> bool:
        """Soft delete an entity.

        Args:
            entity_id: Entity ID
            user_id: User ID for scoping

        Returns:
            True if entity was deleted, False if not found
        """
        pool = await get_pool()
        now = datetime.now(timezone.utc)

        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE entities
                SET deleted_at = $1
                WHERE id = $2 AND user_id = $3 AND deleted_at IS NULL
                """,
                now,
                entity_id,
                user_id,
            )

        deleted = result == "UPDATE 1"
        if deleted:
            logger.info(
                "entity_deleted",
                entity_id=str(entity_id),
                user_id=user_id,
            )
        return deleted

    # =========================================================================
    # Relationship Operations
    # =========================================================================

    async def get_existing_relationship(
        self,
        user_id: str,
        source_entity_id: UUID,
        target_entity_id: Optional[UUID],
        relationship_type: RelationshipType,
    ) -> Optional[Relationship]:
        """Check if a relationship already exists.

        Args:
            user_id: User ID for scoping
            source_entity_id: Source entity ID
            target_entity_id: Target entity ID (nullable)
            relationship_type: Relationship type

        Returns:
            Existing Relationship or None
        """
        pool = await get_pool()

        if target_entity_id:
            query = """
                SELECT id, user_id, source_entity_id, target_entity_id, relationship_type,
                       context, confidence, source_message_id, source_conversation_id,
                       created_at, deleted_at
                FROM entity_relationships
                WHERE user_id = $1 AND source_entity_id = $2 AND target_entity_id = $3
                      AND relationship_type = $4 AND deleted_at IS NULL
            """
            params = [user_id, source_entity_id, target_entity_id, relationship_type.value]
        else:
            query = """
                SELECT id, user_id, source_entity_id, target_entity_id, relationship_type,
                       context, confidence, source_message_id, source_conversation_id,
                       created_at, deleted_at
                FROM entity_relationships
                WHERE user_id = $1 AND source_entity_id = $2 AND target_entity_id IS NULL
                      AND relationship_type = $3 AND deleted_at IS NULL
            """
            params = [user_id, source_entity_id, relationship_type.value]

        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)

        if row:
            return self._row_to_relationship(row)
        return None

    async def create_relationship(
        self,
        user_id: str,
        source_entity_id: UUID,
        target_entity_id: Optional[UUID],
        relationship_type: RelationshipType,
        context: Optional[str] = None,
        confidence: float = 1.0,
        message_id: Optional[UUID] = None,
        conversation_id: Optional[UUID] = None,
    ) -> Relationship:
        """Create a new relationship.

        Args:
            user_id: User ID for scoping
            source_entity_id: Source entity ID
            target_entity_id: Target entity ID (nullable)
            relationship_type: Relationship type
            context: Optional context
            confidence: Extraction confidence
            message_id: Source message ID
            conversation_id: Source conversation ID

        Returns:
            Created Relationship
        """
        pool = await get_pool()
        relationship_id = uuid4()
        now = datetime.now(timezone.utc)

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO entity_relationships (
                    id, user_id, source_entity_id, target_entity_id, relationship_type,
                    context, confidence, source_message_id, source_conversation_id, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                relationship_id,
                user_id,
                source_entity_id,
                target_entity_id,
                relationship_type.value,
                context,
                confidence,
                message_id,
                conversation_id,
                now,
            )

        logger.info(
            "relationship_created",
            relationship_id=str(relationship_id),
            user_id=user_id,
            source_entity_id=str(source_entity_id),
            target_entity_id=str(target_entity_id) if target_entity_id else None,
            relationship_type=relationship_type.value,
        )

        return Relationship(
            id=relationship_id,
            user_id=user_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relationship_type=relationship_type,
            context=context,
            confidence=confidence,
            source_message_id=message_id,
            source_conversation_id=conversation_id,
            created_at=now,
            deleted_at=None,
        )

    async def reinforce_relationship(
        self, relationship_id: UUID, user_id: str, boost: float = 0.05
    ) -> None:
        """Reinforce an existing relationship by increasing confidence.

        Args:
            relationship_id: Relationship ID
            user_id: User ID for scoping
            boost: Amount to increase confidence (capped at 1.0)
        """
        pool = await get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE entity_relationships
                SET confidence = LEAST(confidence + $1, 1.0)
                WHERE id = $2 AND user_id = $3 AND deleted_at IS NULL
                """,
                boost,
                relationship_id,
                user_id,
            )

        logger.debug(
            "relationship_reinforced",
            relationship_id=str(relationship_id),
            boost=boost,
        )

    async def get_or_create_relationship(
        self,
        user_id: str,
        source_entity_id: UUID,
        target_entity_id: Optional[UUID],
        relationship_type: RelationshipType,
        context: Optional[str] = None,
        confidence: float = 1.0,
        message_id: Optional[UUID] = None,
        conversation_id: Optional[UUID] = None,
    ) -> tuple[Relationship, bool]:
        """Get existing relationship or create new one.

        If relationship exists, reinforces it instead of creating duplicate.

        Args:
            user_id: User ID for scoping
            source_entity_id: Source entity ID
            target_entity_id: Target entity ID (nullable)
            relationship_type: Relationship type
            context: Optional context
            confidence: Extraction confidence
            message_id: Source message ID
            conversation_id: Source conversation ID

        Returns:
            Tuple of (Relationship, created: bool)
        """
        existing = await self.get_existing_relationship(
            user_id, source_entity_id, target_entity_id, relationship_type
        )

        if existing:
            await self.reinforce_relationship(existing.id, user_id)
            return existing, False

        relationship = await self.create_relationship(
            user_id=user_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relationship_type=relationship_type,
            context=context,
            confidence=confidence,
            message_id=message_id,
            conversation_id=conversation_id,
        )
        return relationship, True

    async def get_entity_relationships(
        self,
        entity_id: UUID,
        user_id: str,
        relationship_type: Optional[RelationshipType] = None,
        as_source: bool = True,
        as_target: bool = True,
    ) -> list[Relationship]:
        """Get all relationships for an entity.

        Args:
            entity_id: Entity ID
            user_id: User ID for scoping
            relationship_type: Optional type filter
            as_source: Include relationships where entity is source
            as_target: Include relationships where entity is target

        Returns:
            List of relationships
        """
        pool = await get_pool()
        relationships = []

        async with pool.acquire() as conn:
            if as_source:
                query = """
                    SELECT id, user_id, source_entity_id, target_entity_id, relationship_type,
                           context, confidence, source_message_id, source_conversation_id,
                           created_at, deleted_at
                    FROM entity_relationships
                    WHERE source_entity_id = $1 AND user_id = $2 AND deleted_at IS NULL
                """
                params = [entity_id, user_id]

                if relationship_type:
                    query += " AND relationship_type = $3"
                    params.append(relationship_type.value)

                rows = await conn.fetch(query, *params)
                relationships.extend([self._row_to_relationship(row) for row in rows])

            if as_target:
                query = """
                    SELECT id, user_id, source_entity_id, target_entity_id, relationship_type,
                           context, confidence, source_message_id, source_conversation_id,
                           created_at, deleted_at
                    FROM entity_relationships
                    WHERE target_entity_id = $1 AND user_id = $2 AND deleted_at IS NULL
                """
                params = [entity_id, user_id]

                if relationship_type:
                    query += " AND relationship_type = $3"
                    params.append(relationship_type.value)

                rows = await conn.fetch(query, *params)
                relationships.extend([self._row_to_relationship(row) for row in rows])

        return relationships

    async def get_related_entities(
        self,
        entity_id: UUID,
        user_id: str,
        relationship_type: Optional[RelationshipType] = None,
    ) -> list[Entity]:
        """Get all entities related to a given entity.

        Args:
            entity_id: Source entity ID
            user_id: User ID for scoping
            relationship_type: Optional type filter

        Returns:
            List of related entities
        """
        relationships = await self.get_entity_relationships(
            entity_id, user_id, relationship_type
        )

        related_ids = set()
        for rel in relationships:
            if rel.source_entity_id != entity_id:
                related_ids.add(rel.source_entity_id)
            if rel.target_entity_id and rel.target_entity_id != entity_id:
                related_ids.add(rel.target_entity_id)

        entities = []
        for related_id in related_ids:
            entity = await self.get_entity_by_id(related_id, user_id)
            if entity:
                entities.append(entity)

        return entities

    async def soft_delete_relationship(
        self, relationship_id: UUID, user_id: str
    ) -> bool:
        """Soft delete a relationship.

        Args:
            relationship_id: Relationship ID
            user_id: User ID for scoping

        Returns:
            True if deleted, False if not found
        """
        pool = await get_pool()
        now = datetime.now(timezone.utc)

        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE entity_relationships
                SET deleted_at = $1
                WHERE id = $2 AND user_id = $3 AND deleted_at IS NULL
                """,
                now,
                relationship_id,
                user_id,
            )

        return result == "UPDATE 1"

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _row_to_entity(self, row) -> Entity:
        """Convert database row to Entity model."""
        return Entity(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            canonical_name=row["canonical_name"],
            type=EntityType(row["type"]),
            aliases=row["aliases"] or [],
            description=row["description"],
            embedding=pgvector_to_embedding(row["embedding"]),
            confidence=row["confidence"],
            mention_count=row["mention_count"],
            first_seen_message_id=row["first_seen_message_id"],
            first_seen_conversation_id=row["first_seen_conversation_id"],
            last_mentioned_at=row["last_mentioned_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            deleted_at=row["deleted_at"],
        )

    def _row_to_relationship(self, row) -> Relationship:
        """Convert database row to Relationship model."""
        return Relationship(
            id=row["id"],
            user_id=row["user_id"],
            source_entity_id=row["source_entity_id"],
            target_entity_id=row["target_entity_id"],
            relationship_type=RelationshipType(row["relationship_type"]),
            context=row["context"],
            confidence=row["confidence"],
            source_message_id=row["source_message_id"],
            source_conversation_id=row["source_conversation_id"],
            created_at=row["created_at"],
            deleted_at=row["deleted_at"],
        )
