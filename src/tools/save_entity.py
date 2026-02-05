"""Agent tool for saving entities to the knowledge graph."""

from typing import Optional
from uuid import UUID

import structlog
from agents import RunContextWrapper, function_tool

from src.models.graph import EntityCreateRequest, EntityToolResponse, EntityType

logger = structlog.get_logger(__name__)


@function_tool
async def save_entity(
    ctx: RunContextWrapper,
    name: str,
    entity_type: str,
    description: Optional[str] = None,
    confidence: float = 0.9,
) -> str:
    """Save an entity (person, project, tool, concept, organization) to the knowledge graph.

    Use this tool when the user mentions specific:
    - People: colleagues, friends, family members (type: "person")
    - Projects: repos, initiatives, apps they're building (type: "project")
    - Tools: programming languages, frameworks, services (type: "tool")
    - Concepts: methodologies, topics, ideas (type: "concept")
    - Organizations: companies, teams, groups (type: "organization")

    Args:
        ctx: Run context (injected automatically)
        name: The entity name as mentioned by the user
        entity_type: One of: person, project, tool, concept, organization
        description: Optional context about the entity
        confidence: How confident you are about this extraction (0.0-1.0)

    Returns:
        JSON response indicating success/failure and entity details
    """
    # Extract context
    context = ctx.context or {}
    user_id = context.get("user_id", "anonymous")
    correlation_id = context.get("correlation_id")
    conversation_id = context.get("conversation_id")

    # Validate user_id
    if user_id == "anonymous":
        logger.warning(
            "save_entity_anonymous_user",
            correlation_id=str(correlation_id) if correlation_id else None,
        )
        return EntityToolResponse(
            success=False,
            action="error",
            entity_name=name,
            entity_type=EntityType.TOOL,  # Default for error case
            message="Cannot save entity for anonymous user",
        ).model_dump_json()

    # Validate entity type
    try:
        validated_type = EntityType(entity_type.lower())
    except ValueError:
        valid_types = [t.value for t in EntityType]
        return EntityToolResponse(
            success=False,
            action="error",
            entity_name=name,
            entity_type=EntityType.TOOL,
            message=f"Invalid entity type '{entity_type}'. Must be one of: {valid_types}",
        ).model_dump_json()

    # Check rate limits
    try:
        from src.services.redis_service import check_graph_entity_rate_limit

        allowed, reason = await check_graph_entity_rate_limit(
            user_id, conversation_id
        )
        if not allowed:
            logger.info(
                "save_entity_rate_limited",
                user_id=user_id,
                reason=reason,
                correlation_id=str(correlation_id) if correlation_id else None,
            )
            return EntityToolResponse(
                success=False,
                action="rate_limited",
                entity_name=name,
                entity_type=validated_type,
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
            "save_entity_low_confidence",
            name=name,
            entity_type=entity_type,
            confidence=confidence,
            threshold=settings.graph_entity_confidence_threshold,
        )
        return EntityToolResponse(
            success=False,
            action="skipped",
            entity_name=name,
            entity_type=validated_type,
            message=f"Confidence {confidence:.2f} below threshold {settings.graph_entity_confidence_threshold}",
        ).model_dump_json()

    # Create or retrieve entity
    try:
        from src.services.graph_service import GraphService

        graph_service = GraphService()

        # Parse conversation_id if present
        conv_uuid = UUID(conversation_id) if conversation_id else None

        entity, created = await graph_service.get_or_create_entity(
            user_id=user_id,
            name=name,
            entity_type=validated_type,
            description=description,
            confidence=confidence,
            message_id=None,  # Would need message_id from context
            conversation_id=conv_uuid,
        )

        action = "created" if created else "existing"
        message = (
            f"Created new {validated_type.value} entity: {name}"
            if created
            else f"Found existing {validated_type.value} entity: {name} (mention #{entity.mention_count})"
        )

        logger.info(
            "save_entity_success",
            entity_id=str(entity.id),
            user_id=user_id,
            name=name,
            entity_type=validated_type.value,
            action=action,
            correlation_id=str(correlation_id) if correlation_id else None,
        )

        return EntityToolResponse(
            success=True,
            entity_id=entity.id,
            action=action,
            entity_name=entity.name,
            entity_type=validated_type,
            message=message,
        ).model_dump_json()

    except Exception as e:
        logger.error(
            "save_entity_error",
            name=name,
            entity_type=entity_type,
            error=str(e),
            correlation_id=str(correlation_id) if correlation_id else None,
        )
        return EntityToolResponse(
            success=False,
            action="error",
            entity_name=name,
            entity_type=validated_type,
            message=f"Failed to save entity: {str(e)}",
        ).model_dump_json()


# Export the tool for registration
save_entity_tool = save_entity
