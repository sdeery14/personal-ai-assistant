"""Memory write service for agent-driven memory extraction and lifecycle management."""

import asyncio
import time
from typing import Optional
from uuid import UUID, uuid4

import structlog

from src.config import get_settings
from src.database import get_pool
from src.models.memory import (
    MemoryDeleteRequest,
    MemoryQueryRequest,
    MemoryType,
    MemoryWriteRequest,
    MemoryWriteResponse,
)
from src.services.embedding_service import EmbeddingService
from src.services.memory_service import MemoryService, embedding_to_pgvector
from src.services.redis_service import RedisService

logger = structlog.get_logger(__name__)

# Module-level background task tracking
_pending_tasks: set[asyncio.Task] = set()


def schedule_write(coro) -> asyncio.Task:
    """Schedule a background write task.

    Creates an asyncio task, tracks it in the module-level set,
    and registers a cleanup callback.

    Args:
        coro: Coroutine to run in the background

    Returns:
        The created asyncio Task
    """
    task = asyncio.create_task(coro)
    _pending_tasks.add(task)
    task.add_done_callback(_pending_tasks.discard)
    return task


async def await_pending_writes(timeout: float = 5.0) -> None:
    """Wait for all pending background write tasks to complete.

    Called during application shutdown to drain pending writes.

    Args:
        timeout: Maximum seconds to wait for pending tasks
    """
    if not _pending_tasks:
        return

    logger.info("draining_pending_writes", count=len(_pending_tasks))
    try:
        await asyncio.wait_for(
            asyncio.gather(*_pending_tasks, return_exceptions=True),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "pending_writes_timeout",
            remaining=len(_pending_tasks),
            timeout=timeout,
        )


class MemoryWriteService:
    """Service for creating, deleting, and managing memory items."""

    def __init__(self):
        self.settings = get_settings()
        self.embedding_service = EmbeddingService()
        self.memory_service = MemoryService()
        self.redis_service = RedisService()

    async def create_memory(
        self,
        request: MemoryWriteRequest,
        correlation_id: Optional[UUID] = None,
    ) -> MemoryWriteResponse:
        """Create a new memory item with duplicate detection and rate limiting.

        Args:
            request: Memory write request
            correlation_id: Request correlation ID for logging

        Returns:
            MemoryWriteResponse with result of the operation
        """
        start_time = time.perf_counter()

        try:
            # Check conversation rate limit
            if request.source_conversation_id:
                conv_allowed, _ = await self.redis_service.check_write_rate_limit_conversation(
                    str(request.source_conversation_id)
                )
                if not conv_allowed:
                    logger.warning(
                        "memory_write_rate_limited_conversation",
                        user_id=request.user_id,
                        conversation_id=str(request.source_conversation_id),
                        correlation_id=str(correlation_id) if correlation_id else None,
                    )
                    return MemoryWriteResponse(
                        success=False,
                        action="rate_limited",
                        message="Too many memories saved in this conversation",
                    )

            # Check hourly rate limit
            hourly_allowed, _ = await self.redis_service.check_write_rate_limit_hourly(
                request.user_id
            )
            if not hourly_allowed:
                logger.warning(
                    "memory_write_rate_limited_hourly",
                    user_id=request.user_id,
                    correlation_id=str(correlation_id) if correlation_id else None,
                )
                return MemoryWriteResponse(
                    success=False,
                    action="rate_limited",
                    message="Hourly memory save limit reached",
                )

            # Generate embedding
            embedding = await self.embedding_service.get_embedding(request.content)
            if embedding is None:
                return MemoryWriteResponse(
                    success=False,
                    action="error",
                    message="Failed to generate embedding for memory",
                )

            # Check for duplicates via semantic similarity
            is_duplicate = await self._check_duplicate(
                request.user_id, embedding
            )
            if is_duplicate:
                logger.info(
                    "memory_write_duplicate_detected",
                    user_id=request.user_id,
                    correlation_id=str(correlation_id) if correlation_id else None,
                )
                return MemoryWriteResponse(
                    success=False,
                    action="duplicate",
                    message="A very similar memory already exists",
                )

            # Insert memory item
            memory_id = uuid4()
            pool = await get_pool()
            embedding_str = embedding_to_pgvector(embedding)

            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO memory_items (
                        id, user_id, content, type, embedding,
                        source_message_id, source_conversation_id,
                        importance, confidence, status, created_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'active', NOW())
                    """,
                    memory_id,
                    request.user_id,
                    request.content,
                    request.type.value,
                    embedding_str,
                    request.source_message_id,
                    request.source_conversation_id,
                    request.importance,
                    request.confidence,
                )

                # Audit event
                processing_ms = int((time.perf_counter() - start_time) * 1000)
                await conn.execute(
                    """
                    INSERT INTO memory_write_events (
                        id, memory_item_id, user_id, operation, confidence,
                        extraction_type, after_content, correlation_id,
                        processing_time_ms, created_at
                    )
                    VALUES ($1, $2, $3, 'create', $4, 'agent', $5, $6, $7, NOW())
                    """,
                    uuid4(),
                    memory_id,
                    request.user_id,
                    request.confidence,
                    request.content,
                    correlation_id,
                    processing_ms,
                )

            logger.info(
                "memory_created",
                memory_id=str(memory_id),
                user_id=request.user_id,
                type=request.type.value,
                confidence=request.confidence,
                processing_ms=processing_ms,
                correlation_id=str(correlation_id) if correlation_id else None,
            )

            return MemoryWriteResponse(
                success=True,
                memory_id=memory_id,
                action="created",
                message=f"Memory saved: {request.content[:50]}...",
            )

        except Exception as e:
            logger.error(
                "memory_write_failed",
                user_id=request.user_id,
                error=str(e),
                error_type=type(e).__name__,
                correlation_id=str(correlation_id) if correlation_id else None,
            )
            return MemoryWriteResponse(
                success=False,
                action="error",
                message="Failed to save memory",
            )

    async def _check_duplicate(
        self,
        user_id: str,
        embedding: list[float],
    ) -> bool:
        """Check if a similar memory already exists via cosine similarity.

        Args:
            user_id: User ID for scoping
            embedding: Embedding of the new memory content

        Returns:
            True if a duplicate (similarity > threshold) exists
        """
        try:
            results = await self.memory_service.semantic_search(
                user_id=user_id,
                embedding=embedding,
                limit=1,
            )
            if results:
                _, _ = results[0]
                item, _rank = results[0]
                if item.relevance_score >= self.settings.memory_duplicate_threshold:
                    return True
        except Exception as e:
            logger.warning(
                "duplicate_check_failed",
                user_id=user_id,
                error=str(e),
            )
        return False

    async def delete_memory(
        self,
        request: MemoryDeleteRequest,
        correlation_id: Optional[UUID] = None,
    ) -> MemoryWriteResponse:
        """Soft-delete memories matching a description.

        Args:
            request: Delete request with query description
            correlation_id: Request correlation ID

        Returns:
            MemoryWriteResponse with result
        """
        start_time = time.perf_counter()

        try:
            # Search for matching memories
            query_request = MemoryQueryRequest(
                user_id=request.user_id,
                query=request.query,
                limit=5,
                min_score=0.5,
            )
            search_result = await self.memory_service.hybrid_search(
                query_request, correlation_id
            )

            if not search_result.items:
                return MemoryWriteResponse(
                    success=False,
                    action="not_found",
                    message="No matching memories found to delete",
                )

            # Soft-delete matching memories
            pool = await get_pool()
            deleted_ids = []

            async with pool.acquire() as conn:
                for item in search_result.items:
                    await conn.execute(
                        """
                        UPDATE memory_items
                        SET status = 'deleted', deleted_at = NOW()
                        WHERE id = $1 AND user_id = $2
                        """,
                        item.id,
                        request.user_id,
                    )
                    deleted_ids.append(item.id)

                    # Audit event
                    processing_ms = int((time.perf_counter() - start_time) * 1000)
                    await conn.execute(
                        """
                        INSERT INTO memory_write_events (
                            id, memory_item_id, user_id, operation,
                            extraction_type, before_content, correlation_id,
                            processing_time_ms, created_at
                        )
                        VALUES ($1, $2, $3, 'delete', 'agent', $4, $5, $6, NOW())
                        """,
                        uuid4(),
                        item.id,
                        request.user_id,
                        item.content,
                        correlation_id,
                        processing_ms,
                    )

            logger.info(
                "memories_deleted",
                user_id=request.user_id,
                deleted_count=len(deleted_ids),
                reason=request.reason,
                correlation_id=str(correlation_id) if correlation_id else None,
            )

            return MemoryWriteResponse(
                success=True,
                action="deleted",
                message=f"Deleted {len(deleted_ids)} matching memories",
            )

        except Exception as e:
            logger.error(
                "memory_delete_failed",
                user_id=request.user_id,
                error=str(e),
                error_type=type(e).__name__,
                correlation_id=str(correlation_id) if correlation_id else None,
            )
            return MemoryWriteResponse(
                success=False,
                action="error",
                message="Failed to delete memories",
            )

    async def supersede_memory(
        self,
        old_memory_id: UUID,
        new_content: str,
        user_id: str,
        memory_type: MemoryType,
        confidence: float = 0.8,
        correlation_id: Optional[UUID] = None,
        source_conversation_id: Optional[UUID] = None,
    ) -> MemoryWriteResponse:
        """Supersede an existing memory with new content.

        Marks the old memory as superseded and creates a new one.

        Args:
            old_memory_id: ID of the memory to supersede
            new_content: Updated content
            user_id: User ID for scoping
            memory_type: Type of the new memory
            confidence: Confidence for the new memory
            correlation_id: Request correlation ID
            source_conversation_id: Source conversation

        Returns:
            MemoryWriteResponse with the new memory ID
        """
        start_time = time.perf_counter()

        try:
            # Generate embedding for new content
            embedding = await self.embedding_service.get_embedding(new_content)
            if embedding is None:
                return MemoryWriteResponse(
                    success=False,
                    action="error",
                    message="Failed to generate embedding",
                )

            new_memory_id = uuid4()
            pool = await get_pool()
            embedding_str = embedding_to_pgvector(embedding)

            async with pool.acquire() as conn:
                # Get old content for audit
                old_row = await conn.fetchrow(
                    "SELECT content FROM memory_items WHERE id = $1 AND user_id = $2",
                    old_memory_id,
                    user_id,
                )
                if not old_row:
                    return MemoryWriteResponse(
                        success=False,
                        action="not_found",
                        message="Original memory not found",
                    )

                old_content = old_row["content"]

                # Create new memory
                await conn.execute(
                    """
                    INSERT INTO memory_items (
                        id, user_id, content, type, embedding,
                        source_conversation_id, importance, confidence,
                        status, created_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, 0.5, $7, 'active', NOW())
                    """,
                    new_memory_id,
                    user_id,
                    new_content,
                    memory_type.value,
                    embedding_str,
                    source_conversation_id,
                    confidence,
                )

                # Mark old as superseded
                await conn.execute(
                    """
                    UPDATE memory_items
                    SET status = 'superseded', superseded_by = $1
                    WHERE id = $2 AND user_id = $3
                    """,
                    new_memory_id,
                    old_memory_id,
                    user_id,
                )

                # Audit event
                processing_ms = int((time.perf_counter() - start_time) * 1000)
                await conn.execute(
                    """
                    INSERT INTO memory_write_events (
                        id, memory_item_id, user_id, operation, confidence,
                        extraction_type, before_content, after_content,
                        correlation_id, processing_time_ms, created_at
                    )
                    VALUES ($1, $2, $3, 'supersede', $4, 'agent', $5, $6, $7, $8, NOW())
                    """,
                    uuid4(),
                    new_memory_id,
                    user_id,
                    confidence,
                    old_content,
                    new_content,
                    correlation_id,
                    processing_ms,
                )

            logger.info(
                "memory_superseded",
                old_memory_id=str(old_memory_id),
                new_memory_id=str(new_memory_id),
                user_id=user_id,
                correlation_id=str(correlation_id) if correlation_id else None,
            )

            return MemoryWriteResponse(
                success=True,
                memory_id=new_memory_id,
                action="superseded",
                message=f"Updated memory: {new_content[:50]}...",
            )

        except Exception as e:
            logger.error(
                "memory_supersede_failed",
                user_id=user_id,
                error=str(e),
                correlation_id=str(correlation_id) if correlation_id else None,
            )
            return MemoryWriteResponse(
                success=False,
                action="error",
                message="Failed to update memory",
            )

    async def create_episode_summary(
        self,
        conversation_id: UUID,
        user_id: str,
        correlation_id: Optional[UUID] = None,
    ) -> MemoryWriteResponse:
        """Generate and store an episode summary for a conversation.

        Fetches messages, checks thresholds, generates a summary via LLM,
        and creates an EPISODE type memory.

        Args:
            conversation_id: Conversation to summarize
            user_id: User ID for scoping
            correlation_id: Request correlation ID

        Returns:
            MemoryWriteResponse with result
        """
        start_time = time.perf_counter()

        try:
            # Check if already generated
            already_generated = await self.redis_service.check_episode_generated(
                str(conversation_id)
            )
            if already_generated:
                return MemoryWriteResponse(
                    success=False,
                    action="already_exists",
                    message="Episode summary already generated for this conversation",
                )

            # Fetch messages
            from src.services.conversation_service import ConversationService
            conv_service = ConversationService()
            messages = await conv_service.get_conversation_messages(
                conversation_id, limit=50
            )

            # Check thresholds
            user_msg_count = sum(1 for m in messages if m.role.value == "user")
            total_msg_count = len(messages)

            if (
                user_msg_count < self.settings.episode_user_message_threshold
                and total_msg_count < self.settings.episode_total_message_threshold
            ):
                return MemoryWriteResponse(
                    success=False,
                    action="threshold_not_met",
                    message="Conversation too short for episode summary",
                )

            # Build conversation text for summarization
            conversation_text = "\n".join(
                f"{m.role.value}: {m.content}" for m in messages
            )

            # Generate summary via OpenAI
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.settings.openai_api_key)

            summary_response = await client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Summarize this conversation into a concise episode summary. "
                            "Focus on: key topics discussed, decisions made, user preferences "
                            "expressed, and any action items. Keep it under 200 words."
                        ),
                    },
                    {"role": "user", "content": conversation_text},
                ],
                max_tokens=300,
            )

            summary = summary_response.choices[0].message.content
            if not summary:
                return MemoryWriteResponse(
                    success=False,
                    action="error",
                    message="Failed to generate episode summary",
                )

            # Create episode memory
            write_request = MemoryWriteRequest(
                user_id=user_id,
                content=summary,
                type=MemoryType.EPISODE,
                confidence=1.0,
                source_conversation_id=conversation_id,
                importance=0.6,
            )
            result = await self.create_memory(write_request, correlation_id)

            # Mark as generated in Redis
            if result.success:
                await self.redis_service.set_episode_generated(str(conversation_id))

                # Log audit event specifically for episode
                processing_ms = int((time.perf_counter() - start_time) * 1000)
                pool = await get_pool()
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO memory_write_events (
                            id, memory_item_id, user_id, operation,
                            extraction_type, after_content, correlation_id,
                            processing_time_ms, created_at
                        )
                        VALUES ($1, $2, $3, 'episode', 'episode', $4, $5, $6, NOW())
                        """,
                        uuid4(),
                        result.memory_id,
                        user_id,
                        summary,
                        correlation_id,
                        processing_ms,
                    )

            return result

        except Exception as e:
            logger.error(
                "episode_summary_failed",
                conversation_id=str(conversation_id),
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
                correlation_id=str(correlation_id) if correlation_id else None,
            )
            return MemoryWriteResponse(
                success=False,
                action="error",
                message="Failed to generate episode summary",
            )

    async def search_memories(
        self,
        user_id: str,
        query: str,
        correlation_id: Optional[UUID] = None,
    ) -> list[dict]:
        """Search for memories matching a description.

        Used by delete_memory_tool to show candidates before deletion.

        Args:
            user_id: User ID for scoping
            query: Search query
            correlation_id: Request correlation ID

        Returns:
            List of matching memory dicts with id, content, type
        """
        try:
            request = MemoryQueryRequest(
                user_id=user_id,
                query=query,
                limit=5,
                min_score=0.3,
            )
            result = await self.memory_service.hybrid_search(request, correlation_id)

            return [
                {
                    "id": str(item.id),
                    "content": item.content,
                    "type": item.type.value,
                    "relevance": round(item.relevance_score, 3),
                }
                for item in result.items
            ]
        except Exception as e:
            logger.error(
                "memory_search_failed",
                user_id=user_id,
                error=str(e),
                correlation_id=str(correlation_id) if correlation_id else None,
            )
            return []
