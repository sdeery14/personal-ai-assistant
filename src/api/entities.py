"""Knowledge graph entity browsing API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
import structlog

from src.api.dependencies import get_current_user
from src.models.user import User
from src.services.graph_service import GraphService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/entities", tags=["Knowledge Graph"])


@router.get("")
async def list_entities(
    q: str | None = Query(default=None, description="Search by entity name"),
    type: str | None = Query(default=None, description="Filter by entity type"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Search or list user's entities with optional filters."""
    user_id = str(current_user.id)
    graph_service = GraphService()

    # Use existing search_entities method for filtered queries
    entities = await graph_service.search_entities(
        user_id=user_id,
        name_pattern=q,
        entity_type=type,
        limit=limit + offset,  # Over-fetch to handle offset
    )

    # Manual offset since search_entities doesn't support it
    paginated = entities[offset : offset + limit]
    total = len(entities)  # Approximate — search_entities caps at limit

    items = [
        {
            "id": str(e.id),
            "name": e.name,
            "type": e.type.value if hasattr(e.type, "value") else str(e.type),
            "description": e.description,
            "aliases": e.aliases or [],
            "confidence": float(e.confidence),
            "mention_count": e.mention_count,
            "created_at": e.created_at.isoformat(),
            "last_mentioned_at": e.last_mentioned_at.isoformat() if e.last_mentioned_at else None,
        }
        for e in paginated
    ]

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{entity_id}/relationships")
async def get_entity_relationships(
    entity_id: UUID,
    type: str | None = Query(default=None, description="Filter by relationship type"),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Get relationships for an entity."""
    user_id = str(current_user.id)
    graph_service = GraphService()

    # Verify entity exists and belongs to user
    entity = await graph_service.get_entity_by_id(entity_id, user_id)
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found",
        )

    relationships = await graph_service.get_entity_relationships(
        entity_id=entity_id,
        user_id=user_id,
        relationship_type=type,
    )

    result = []
    for rel in relationships:
        # Fetch source and target entities for the response
        source = await graph_service.get_entity_by_id(rel.source_entity_id, user_id)
        target = None
        if rel.target_entity_id:
            target = await graph_service.get_entity_by_id(rel.target_entity_id, user_id)

        def entity_dict(e):
            if e is None:
                return None
            return {
                "id": str(e.id),
                "name": e.name,
                "type": e.type.value if hasattr(e.type, "value") else str(e.type),
                "description": e.description,
                "aliases": e.aliases or [],
                "confidence": float(e.confidence),
                "mention_count": e.mention_count,
                "created_at": e.created_at.isoformat(),
                "last_mentioned_at": e.last_mentioned_at.isoformat() if e.last_mentioned_at else None,
            }

        result.append({
            "id": str(rel.id),
            "source_entity": entity_dict(source),
            "target_entity": entity_dict(target),
            "relationship_type": rel.relationship_type.value if hasattr(rel.relationship_type, "value") else str(rel.relationship_type),
            "context": rel.context,
            "confidence": float(rel.confidence),
            "created_at": rel.created_at.isoformat(),
        })

    return result
