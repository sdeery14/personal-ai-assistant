"""Agent tool for saving relationships to the knowledge graph."""

from typing import Optional
from uuid import UUID

import structlog
from agents import RunContextWrapper, function_tool

from src.models.graph import (
    EntityType,
    RelationshipToolResponse,
    RelationshipType,
)

logger = structlog.get_logger(__name__)


@function_tool
async def save_relationship(
    ctx: RunContextWrapper,
    source_entity_name: str,
    source_entity_type: str,
    relationship_type: str,
    target_entity_name: Optional[str] = None,
    target_entity_type: Optional[str] = None,
    context: Optional[str] = None,
    confidence: float = 0.9,
) -> str:
    """Save a relationship between entities in the knowledge graph.

    Use this tool when the user expresses relationships like:
    - "I use FastAPI" → source: user, relationship: USES, target: FastAPI (tool)
    - "I prefer Python over JavaScript" → source: user, relationship: PREFERS, target: Python (tool)
    - "I work with Sarah" → source: user, relationship: WORKS_WITH, target: Sarah (person)
    - "Project Phoenix uses PostgreSQL" → source: Phoenix (project), relationship: USES, target: PostgreSQL (tool)

    Relationship types:
    - USES: User/project uses a tool or technology
    - PREFERS: User prefers something (optionally over another)
    - DECIDED: User made a decision about something
    - WORKS_ON: User/person works on a project
    - WORKS_WITH: User works with a person
    - KNOWS: User knows a person
    - DEPENDS_ON: Project/tool depends on another
    - PART_OF: Entity is part of another

    Args:
        ctx: Run context (injected automatically)
        source_entity_name: Name of the source entity
        source_entity_type: Type of source entity (person, project, tool, concept, organization)
        relationship_type: One of: USES, PREFERS, DECIDED, WORKS_ON, WORKS_WITH, KNOWS, DEPENDS_ON, PART_OF
        target_entity_name: Name of the target entity (optional for some relationships)
        target_entity_type: Type of target entity
        context: Additional context about the relationship
        confidence: How confident you are about this extraction (0.0-1.0)

    Returns:
        JSON response indicating success/failure and relationship details
    """
    # Extract context
    run_context = ctx.context or {}
    user_id = run_context.get("user_id", "anonymous")
    correlation_id = run_context.get("correlation_id")
    conversation_id = run_context.get("conversation_id")

    # Validate user_id
    if user_id == "anonymous":
        logger.warning(
            "save_relationship_anonymous_user",
            correlation_id=str(correlation_id) if correlation_id else None,
        )
        return RelationshipToolResponse(
            success=False,
            action="error",
            source_entity=source_entity_name,
            target_entity=target_entity_name,
            relationship_type=RelationshipType.USES,
            message="Cannot save relationship for anonymous user",
        ).model_dump_json()

    # Validate entity types
    try:
        validated_source_type = EntityType(source_entity_type.lower())
    except ValueError:
        valid_types = [t.value for t in EntityType]
        return RelationshipToolResponse(
            success=False,
            action="error",
            source_entity=source_entity_name,
            target_entity=target_entity_name,
            relationship_type=RelationshipType.USES,
            message=f"Invalid source entity type '{source_entity_type}'. Must be one of: {valid_types}",
        ).model_dump_json()

    validated_target_type = None
    if target_entity_name and target_entity_type:
        try:
            validated_target_type = EntityType(target_entity_type.lower())
        except ValueError:
            valid_types = [t.value for t in EntityType]
            return RelationshipToolResponse(
                success=False,
                action="error",
                source_entity=source_entity_name,
                target_entity=target_entity_name,
                relationship_type=RelationshipType.USES,
                message=f"Invalid target entity type '{target_entity_type}'. Must be one of: {valid_types}",
            ).model_dump_json()

    # Validate relationship type
    try:
        validated_rel_type = RelationshipType(relationship_type.upper())
    except ValueError:
        valid_types = [t.value for t in RelationshipType]
        return RelationshipToolResponse(
            success=False,
            action="error",
            source_entity=source_entity_name,
            target_entity=target_entity_name,
            relationship_type=RelationshipType.USES,
            message=f"Invalid relationship type '{relationship_type}'. Must be one of: {valid_types}",
        ).model_dump_json()

    # Check rate limits
    try:
        from src.services.redis_service import check_graph_relationship_rate_limit

        allowed, reason = await check_graph_relationship_rate_limit(
            user_id, conversation_id
        )
        if not allowed:
            logger.info(
                "save_relationship_rate_limited",
                user_id=user_id,
                reason=reason,
                correlation_id=str(correlation_id) if correlation_id else None,
            )
            return RelationshipToolResponse(
                success=False,
                action="rate_limited",
                source_entity=source_entity_name,
                target_entity=target_entity_name,
                relationship_type=validated_rel_type,
                message=f"Rate limit reached: {reason}",
            ).model_dump_json()
    except Exception as e:
        # Redis unavailable - proceed without rate limiting
        logger.warning("rate_limit_check_failed", error=str(e))

    # Check confidence threshold
    from src.config import get_settings

    settings = get_settings()
    if confidence < settings.graph_entity_confidence_threshold:
        logger.debug(
            "save_relationship_low_confidence",
            source=source_entity_name,
            target=target_entity_name,
            relationship_type=relationship_type,
            confidence=confidence,
        )
        return RelationshipToolResponse(
            success=False,
            action="skipped",
            source_entity=source_entity_name,
            target_entity=target_entity_name,
            relationship_type=validated_rel_type,
            message=f"Confidence {confidence:.2f} below threshold",
        ).model_dump_json()

    # Create entities and relationship
    try:
        from src.services.graph_service import GraphService

        graph_service = GraphService()
        conv_uuid = UUID(conversation_id) if conversation_id else None

        # Get or create source entity
        source_entity, _ = await graph_service.get_or_create_entity(
            user_id=user_id,
            name=source_entity_name,
            entity_type=validated_source_type,
            confidence=confidence,
            conversation_id=conv_uuid,
        )

        # Get or create target entity if specified
        target_entity = None
        if target_entity_name and validated_target_type:
            target_entity, _ = await graph_service.get_or_create_entity(
                user_id=user_id,
                name=target_entity_name,
                entity_type=validated_target_type,
                confidence=confidence,
                conversation_id=conv_uuid,
            )

        # Create relationship
        relationship, created = await graph_service.get_or_create_relationship(
            user_id=user_id,
            source_entity_id=source_entity.id,
            target_entity_id=target_entity.id if target_entity else None,
            relationship_type=validated_rel_type,
            context=context,
            confidence=confidence,
            conversation_id=conv_uuid,
        )

        action = "created" if created else "reinforced"
        if target_entity_name:
            message = (
                f"{'Created' if created else 'Reinforced'} relationship: "
                f"{source_entity_name} {validated_rel_type.value} {target_entity_name}"
            )
        else:
            message = (
                f"{'Created' if created else 'Reinforced'} relationship: "
                f"{source_entity_name} {validated_rel_type.value}"
            )

        logger.info(
            "save_relationship_success",
            relationship_id=str(relationship.id),
            user_id=user_id,
            source=source_entity_name,
            target=target_entity_name,
            relationship_type=validated_rel_type.value,
            action=action,
            correlation_id=str(correlation_id) if correlation_id else None,
        )

        return RelationshipToolResponse(
            success=True,
            relationship_id=relationship.id,
            action=action,
            source_entity=source_entity_name,
            target_entity=target_entity_name,
            relationship_type=validated_rel_type,
            message=message,
        ).model_dump_json()

    except Exception as e:
        logger.error(
            "save_relationship_error",
            source=source_entity_name,
            target=target_entity_name,
            relationship_type=relationship_type,
            error=str(e),
            correlation_id=str(correlation_id) if correlation_id else None,
        )
        return RelationshipToolResponse(
            success=False,
            action="error",
            source_entity=source_entity_name,
            target_entity=target_entity_name,
            relationship_type=validated_rel_type,
            message=f"Failed to save relationship: {str(e)}",
        ).model_dump_json()


# Export the tool for registration
save_relationship_tool = save_relationship
