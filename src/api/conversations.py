"""Conversation management API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
import structlog

from src.api.dependencies import get_current_user
from src.models.user import User
from src.services.conversation_service import ConversationService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("")
async def list_conversations(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
) -> dict:
    """List user's conversations ordered by most recently updated.

    Returns paginated list with message preview and count.
    """
    service = ConversationService()
    items, total = await service.list_conversations(
        user_id=str(current_user.id),
        limit=limit,
        offset=offset,
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    message_limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get a conversation with its messages."""
    service = ConversationService()
    conversation = await service.get_conversation(
        conversation_id=conversation_id,
        user_id=str(current_user.id),
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    messages = await service.get_conversation_messages(
        conversation_id=conversation_id,
        limit=message_limit,
    )

    return {
        "id": str(conversation.id),
        "title": conversation.title,
        "messages": [
            {
                "id": str(m.id),
                "role": m.role.value,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
    }


@router.patch("/{conversation_id}")
async def update_conversation(
    conversation_id: UUID,
    body: dict,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Update conversation title."""
    title = body.get("title")
    if title is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="title is required",
        )

    service = ConversationService()
    result = await service.update_conversation_title(
        conversation_id=conversation_id,
        user_id=str(current_user.id),
        title=title,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return result


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a conversation and its messages."""
    service = ConversationService()
    deleted = await service.delete_conversation(
        conversation_id=conversation_id,
        user_id=str(current_user.id),
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
