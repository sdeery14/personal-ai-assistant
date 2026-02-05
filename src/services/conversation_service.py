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
