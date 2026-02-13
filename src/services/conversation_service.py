"""Conversation and message persistence service."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import structlog

from src.database import get_pool
from src.models.memory import Conversation, Message, MessageRole
from src.services.embedding_service import EmbeddingService

logger = structlog.get_logger(__name__)


def embedding_to_pgvector(embedding: list[float] | None) -> str | None:
    """Convert embedding list to pgvector string format.

    pgvector expects embeddings as '[0.1, 0.2, ...]' string format.
    """
    if embedding is None:
        return None
    return "[" + ",".join(str(x) for x in embedding) + "]"


def pgvector_to_embedding(pgvector_str: str | None) -> list[float] | None:
    """Convert pgvector string format back to embedding list.

    asyncpg returns pgvector columns as strings like '[0.1,0.2,...]'.
    This parses them back to Python lists.
    """
    if pgvector_str is None:
        return None
    # Handle both string and list (in case asyncpg behavior changes)
    if isinstance(pgvector_str, list):
        return pgvector_str
    # Strip brackets and split by comma
    inner = pgvector_str.strip("[]")
    if not inner:
        return []
    return [float(x) for x in inner.split(",")]


class ConversationService:
    """Service for conversation and message CRUD operations."""

    def __init__(self):
        self.embedding_service = EmbeddingService()

    async def get_or_create_conversation(
        self,
        user_id: str,
        conversation_id: Optional[str] = None,
    ) -> Conversation:
        """Get existing conversation or create a new one.

        Args:
            user_id: User identifier (required for scoping)
            conversation_id: Optional existing conversation ID

        Returns:
            Conversation object

        Raises:
            RuntimeError: If database operation fails
        """
        pool = await get_pool()

        async with pool.acquire() as conn:
            if conversation_id:
                # Try to get existing conversation
                conv_uuid = UUID(conversation_id)
                row = await conn.fetchrow(
                    """
                    SELECT id, user_id, title, created_at, updated_at
                    FROM conversations
                    WHERE id = $1 AND user_id = $2
                    """,
                    conv_uuid,
                    user_id,
                )
                if row:
                    return Conversation(
                        id=row["id"],
                        user_id=row["user_id"],
                        title=row["title"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                # Fall through to create new if not found

            # Create new conversation
            new_id = uuid4()
            now = datetime.now(timezone.utc)
            await conn.execute(
                """
                INSERT INTO conversations (id, user_id, created_at, updated_at)
                VALUES ($1, $2, $3, $4)
                """,
                new_id,
                user_id,
                now,
                now,
            )

            logger.info(
                "conversation_created",
                conversation_id=str(new_id),
                user_id=user_id,
            )

            return Conversation(
                id=new_id,
                user_id=user_id,
                title=None,
                created_at=now,
                updated_at=now,
            )

    async def add_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        correlation_id: UUID,
        generate_embedding: bool = True,
    ) -> Message:
        """Add a message to a conversation.

        Args:
            conversation_id: Parent conversation ID
            role: Message role (user, assistant, system)
            content: Message content
            correlation_id: Request correlation ID
            generate_embedding: Whether to generate embedding for the message

        Returns:
            Created Message object

        Raises:
            RuntimeError: If database operation fails
        """
        pool = await get_pool()
        message_id = uuid4()
        now = datetime.now(timezone.utc)

        # Generate embedding if requested
        embedding = None
        if generate_embedding:
            embedding = await self.embedding_service.get_embedding(content)

        async with pool.acquire() as conn:
            # Insert message
            # Convert embedding to pgvector string format
            embedding_str = embedding_to_pgvector(embedding)
            await conn.execute(
                """
                INSERT INTO messages (id, conversation_id, role, content, embedding, correlation_id, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                message_id,
                conversation_id,
                role,
                content,
                embedding_str,
                correlation_id,
                now,
            )

            # Update conversation's updated_at
            await conn.execute(
                """
                UPDATE conversations SET updated_at = $1 WHERE id = $2
                """,
                now,
                conversation_id,
            )

        logger.debug(
            "message_added",
            message_id=str(message_id),
            conversation_id=str(conversation_id),
            role=role,
            content_length=len(content),
            has_embedding=embedding is not None,
        )

        return Message(
            id=message_id,
            conversation_id=conversation_id,
            role=MessageRole(role),
            content=content,
            embedding=embedding,
            correlation_id=correlation_id,
            created_at=now,
        )

    async def get_conversation_messages(
        self,
        conversation_id: UUID,
        limit: int = 20,
    ) -> list[Message]:
        """Get recent messages from a conversation.

        Args:
            conversation_id: Conversation ID
            limit: Maximum messages to return

        Returns:
            List of messages, ordered by created_at ascending
        """
        pool = await get_pool()

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, conversation_id, role, content, embedding, correlation_id, created_at
                FROM messages
                WHERE conversation_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                conversation_id,
                limit,
            )

        # Return in chronological order (reverse the DESC order)
        messages = [
            Message(
                id=row["id"],
                conversation_id=row["conversation_id"],
                role=MessageRole(row["role"]),
                content=row["content"],
                embedding=pgvector_to_embedding(row["embedding"]),
                correlation_id=row["correlation_id"],
                created_at=row["created_at"],
            )
            for row in reversed(rows)
        ]

        return messages

    async def get_conversation(
        self,
        conversation_id: UUID,
        user_id: str,
    ) -> Optional[Conversation]:
        """Get a conversation by ID with user scoping.

        Args:
            conversation_id: Conversation ID
            user_id: User ID for security scoping

        Returns:
            Conversation or None if not found
        """
        pool = await get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, title, created_at, updated_at
                FROM conversations
                WHERE id = $1 AND user_id = $2
                """,
                conversation_id,
                user_id,
            )

        if row:
            return Conversation(
                id=row["id"],
                user_id=row["user_id"],
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        return None

    async def list_conversations(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """List conversations for a user, ordered by most recently updated.

        Args:
            user_id: User ID for scoping
            limit: Maximum conversations to return
            offset: Pagination offset

        Returns:
            Tuple of (conversation summaries with message preview, total count)
        """
        pool = await get_pool()

        async with pool.acquire() as conn:
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM conversations WHERE user_id = $1",
                user_id,
            )

            rows = await conn.fetch(
                """
                SELECT
                    c.id, c.title, c.created_at, c.updated_at,
                    (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) as message_count,
                    (SELECT SUBSTRING(content, 1, 100) FROM messages
                     WHERE conversation_id = c.id AND role = 'user'
                     ORDER BY created_at ASC LIMIT 1) as message_preview
                FROM conversations c
                WHERE c.user_id = $1
                ORDER BY c.updated_at DESC
                LIMIT $2 OFFSET $3
                """,
                user_id,
                limit,
                offset,
            )

        items = [
            {
                "id": str(row["id"]),
                "title": row["title"],
                "message_preview": row["message_preview"] or "",
                "message_count": row["message_count"],
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
            }
            for row in rows
        ]

        return items, total

    async def update_conversation_title(
        self,
        conversation_id: UUID,
        user_id: str,
        title: str,
    ) -> Optional[dict]:
        """Update a conversation's title.

        Args:
            conversation_id: Conversation ID
            user_id: User ID for security scoping
            title: New title

        Returns:
            Updated conversation summary or None if not found
        """
        pool = await get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE conversations
                SET title = $1, updated_at = NOW()
                WHERE id = $2 AND user_id = $3
                RETURNING id, user_id, title, created_at, updated_at
                """,
                title,
                conversation_id,
                user_id,
            )

        if row is None:
            return None

        # Get message count and preview
        async with pool.acquire() as conn:
            stats = await conn.fetchrow(
                """
                SELECT
                    (SELECT COUNT(*) FROM messages WHERE conversation_id = $1) as message_count,
                    (SELECT SUBSTRING(content, 1, 100) FROM messages
                     WHERE conversation_id = $1 AND role = 'user'
                     ORDER BY created_at ASC LIMIT 1) as message_preview
                """,
                conversation_id,
            )

        return {
            "id": str(row["id"]),
            "title": row["title"],
            "message_preview": stats["message_preview"] or "" if stats else "",
            "message_count": stats["message_count"] if stats else 0,
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        }

    async def delete_conversation(
        self,
        conversation_id: UUID,
        user_id: str,
    ) -> bool:
        """Delete a conversation and its messages.

        Args:
            conversation_id: Conversation ID
            user_id: User ID for security scoping

        Returns:
            True if deleted, False if not found
        """
        pool = await get_pool()

        async with pool.acquire() as conn:
            # Messages have ON DELETE CASCADE (or we delete manually)
            await conn.execute(
                "DELETE FROM messages WHERE conversation_id = $1",
                conversation_id,
            )
            result = await conn.execute(
                "DELETE FROM conversations WHERE id = $1 AND user_id = $2",
                conversation_id,
                user_id,
            )

        deleted = result == "DELETE 1"
        if deleted:
            logger.info(
                "conversation_deleted",
                conversation_id=str(conversation_id),
                user_id=user_id,
            )
        return deleted

    async def set_auto_title(
        self,
        conversation_id: UUID,
        user_id: str,
        first_message: str,
    ) -> None:
        """Set conversation title from first user message if title is null.

        Args:
            conversation_id: Conversation ID
            user_id: User ID for scoping
            first_message: First user message to derive title from
        """
        # Truncate to ~80 chars at word boundary
        title = first_message[:80]
        if len(first_message) > 80:
            last_space = title.rfind(" ")
            if last_space > 40:
                title = title[:last_space]
            title += "..."

        pool = await get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE conversations
                SET title = $1
                WHERE id = $2 AND user_id = $3 AND title IS NULL
                """,
                title,
                conversation_id,
                user_id,
            )
