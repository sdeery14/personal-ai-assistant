"""Agent tool for querying the knowledge graph."""

import time
from typing import Optional

import structlog
from agents import RunContextWrapper, function_tool

from src.models.graph import EntityType, GraphToolResponse, RelationshipType

logger = structlog.get_logger(__name__)


@function_tool
async def query_graph(
    ctx: RunContextWrapper,
    query: str,
    entity_type: Optional[str] = None,
    relationship_type: Optional[str] = None,
    limit: int = 10,
) -> str:
    """Query the knowledge graph for entities and relationships.

    Use this tool when the user asks relationship questions like:
    - "What tools do I use?" → query about USES relationships with tool entities
    - "Who do I work with?" → query about WORKS_WITH relationships with person entities
    - "What projects am I working on?" → query about WORKS_ON relationships with project entities
    - "What does project X use?" → query about a specific entity's relationships

    Args:
        ctx: Run context (injected automatically)
        query: Natural language query or entity name to search for
        entity_type: Optional filter: person, project, tool, concept, organization
        relationship_type: Optional filter: USES, PREFERS, DECIDED, WORKS_ON, WORKS_WITH, KNOWS, DEPENDS_ON, PART_OF
        limit: Maximum number of results (1-50)

    Returns:
        JSON response with matching entities and their relationships
    """
    start_time = time.perf_counter()

    # Extract context
    context = ctx.context or {}
    user_id = context.get("user_id", "anonymous")
    correlation_id = context.get("correlation_id")

    # Validate user_id
    if user_id == "anonymous":
        logger.warning(
            "query_graph_anonymous_user",
            correlation_id=str(correlation_id) if correlation_id else None,
        )
        return GraphToolResponse(
            entities=[],
            metadata={
                "count": 0,
                "query": query,
                "error": "Cannot query graph for anonymous user",
            },
        ).model_dump_json()

    # Validate entity_type if provided
    validated_entity_type = None
    if entity_type:
        try:
            validated_entity_type = EntityType(entity_type.lower())
        except ValueError:
            valid_types = [t.value for t in EntityType]
            return GraphToolResponse(
                entities=[],
                metadata={
                    "count": 0,
                    "query": query,
                    "error": f"Invalid entity type '{entity_type}'. Must be one of: {valid_types}",
                },
            ).model_dump_json()

    # Validate relationship_type if provided
    validated_rel_type = None
    if relationship_type:
        try:
            validated_rel_type = RelationshipType(relationship_type.upper())
        except ValueError:
            valid_types = [t.value for t in RelationshipType]
            return GraphToolResponse(
                entities=[],
                metadata={
                    "count": 0,
                    "query": query,
                    "error": f"Invalid relationship type '{relationship_type}'. Must be one of: {valid_types}",
                },
            ).model_dump_json()

    try:
        from src.services.graph_service import GraphService

        graph_service = GraphService()

        # Search for entities matching the query
        entities = await graph_service.search_entities(
            user_id=user_id,
            name_pattern=query,
            entity_type=validated_entity_type,
            limit=limit,
        )

        # Build response with relationships for each entity
        entity_results = []
        total_relationships = 0

        for entity in entities:
            # Get relationships for this entity
            relationships = await graph_service.get_entity_relationships(
                entity_id=entity.id,
                user_id=user_id,
                relationship_type=validated_rel_type,
            )

            # Get related entities
            related_entities = await graph_service.get_related_entities(
                entity_id=entity.id,
                user_id=user_id,
                relationship_type=validated_rel_type,
            )

            # Format for response
            entity_dict = {
                "name": entity.name,
                "type": entity.type.value,
                "description": entity.description,
                "mention_count": entity.mention_count,
                "confidence": entity.confidence,
                "relationships": [
                    {
                        "type": rel.relationship_type.value,
                        "target": next(
                            (
                                e.name
                                for e in related_entities
                                if e.id == rel.target_entity_id
                            ),
                            None,
                        ),
                        "context": rel.context,
                    }
                    for rel in relationships
                    if rel.source_entity_id == entity.id
                ],
                "related_to": [
                    {
                        "name": e.name,
                        "type": e.type.value,
                    }
                    for e in related_entities
                ],
            }
            entity_results.append(entity_dict)
            total_relationships += len(relationships)

        query_time_ms = int((time.perf_counter() - start_time) * 1000)

        logger.info(
            "query_graph_success",
            user_id=user_id,
            query=query,
            entity_count=len(entities),
            relationship_count=total_relationships,
            query_time_ms=query_time_ms,
            correlation_id=str(correlation_id) if correlation_id else None,
        )

        return GraphToolResponse(
            entities=entity_results,
            metadata={
                "count": len(entities),
                "total_relationships": total_relationships,
                "query": query,
                "entity_type_filter": entity_type,
                "relationship_type_filter": relationship_type,
                "query_time_ms": query_time_ms,
                "truncated": len(entities) >= limit,
            },
        ).model_dump_json()

    except Exception as e:
        logger.error(
            "query_graph_error",
            query=query,
            error=str(e),
            correlation_id=str(correlation_id) if correlation_id else None,
        )
        return GraphToolResponse(
            entities=[],
            metadata={
                "count": 0,
                "query": query,
                "error": f"Failed to query graph: {str(e)}",
            },
        ).model_dump_json()


# Export the tool for registration
query_graph_tool = query_graph
