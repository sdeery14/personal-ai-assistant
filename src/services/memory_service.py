"""Memory retrieval service with hybrid search and RRF fusion."""

import hashlib
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import structlog
import tiktoken

from src.config import get_settings
from src.database import get_pool
from src.models.memory import (
    MemoryItem,
    MemoryQueryRequest,
    MemoryQueryResponse,
    MemoryType,
)
from src.services.embedding_service import EmbeddingService
from src.services.redis_service import RedisService

logger = structlog.get_logger(__name__)

# Tiktoken encoding for token counting
_encoding: Optional[tiktoken.Encoding] = None


def get_encoding() -> tiktoken.Encoding:
    """Get or create tiktoken encoding."""
    global _encoding
    if _encoding is None:
        _encoding = tiktoken.get_encoding("cl100k_base")
    return _encoding


class MemoryService:
    """Service for memory retrieval with hybrid search."""

    def __init__(self):
        self.settings = get_settings()
        self.embedding_service = EmbeddingService()
        self.redis_service = RedisService()

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken.

        Args:
            text: Text to count tokens for

        Returns:
            Token count
        """
        encoding = get_encoding()
        return len(encoding.encode(text))

    def enforce_token_budget(
        self,
        items: list[MemoryItem],
        budget: Optional[int] = None,
    ) -> tuple[list[MemoryItem], bool]:
        """Truncate memory items to fit within token budget.

        Args:
            items: List of memory items sorted by relevance
            budget: Token budget (defaults to config)

        Returns:
            Tuple of (truncated_items, was_truncated)
        """
        budget = budget or self.settings.token_budget
        result = []
        total_tokens = 0
        truncated = False

        for item in items:
            item_tokens = self.count_tokens(item.content)
            if total_tokens + item_tokens <= budget:
                result.append(item)
                total_tokens += item_tokens
            else:
                truncated = True
                break

        return result, truncated

    async def keyword_search(
        self,
        user_id: str,
        query: str,
        limit: int = 20,
        types: Optional[list[MemoryType]] = None,
    ) -> list[tuple[MemoryItem, int]]:
        """Perform full-text keyword search on memory items.

        Args:
            user_id: User ID for scoping (MANDATORY)
            query: Search query
            limit: Maximum results
            types: Optional filter by memory types

        Returns:
            List of (MemoryItem, rank) tuples, ordered by ts_rank
        """
        pool = await get_pool()

        # Build query with optional type filter
        type_filter = ""
        params = [user_id, query, limit]
        if types:
            type_values = [t.value for t in types]
            type_filter = f"AND type = ANY($4)"
            params.append(type_values)

        sql = f"""
            SELECT
                id, user_id, content, type, embedding, source_message_id,
                importance, created_at, expires_at,
                ts_rank(to_tsvector('english', content), plainto_tsquery('english', $2)) as rank
            FROM memory_items
            WHERE user_id = $1
              AND deleted_at IS NULL
              AND to_tsvector('english', content) @@ plainto_tsquery('english', $2)
              {type_filter}
            ORDER BY rank DESC
            LIMIT $3
        """

        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)

        results = []
        for idx, row in enumerate(rows):
            item = MemoryItem(
                id=row["id"],
                user_id=row["user_id"],
                content=row["content"],
                type=MemoryType(row["type"]),
                relevance_score=float(row["rank"]),
                source=str(row["source_message_id"]) if row["source_message_id"] else None,
                created_at=row["created_at"],
                importance=row["importance"],
            )
            results.append((item, idx + 1))  # 1-indexed rank

        return results

    async def semantic_search(
        self,
        user_id: str,
        embedding: list[float],
        limit: int = 20,
        types: Optional[list[MemoryType]] = None,
    ) -> list[tuple[MemoryItem, int]]:
        """Perform semantic similarity search on memory items.

        Args:
            user_id: User ID for scoping (MANDATORY)
            embedding: Query embedding vector
            limit: Maximum results
            types: Optional filter by memory types

        Returns:
            List of (MemoryItem, rank) tuples, ordered by cosine similarity
        """
        pool = await get_pool()

        # Build query with optional type filter
        type_filter = ""
        params = [user_id, embedding, limit]
        if types:
            type_values = [t.value for t in types]
            type_filter = f"AND type = ANY($4)"
            params.append(type_values)

        sql = f"""
            SELECT
                id, user_id, content, type, embedding, source_message_id,
                importance, created_at, expires_at,
                1 - (embedding <=> $2::vector) as similarity
            FROM memory_items
            WHERE user_id = $1
              AND deleted_at IS NULL
              AND embedding IS NOT NULL
              {type_filter}
            ORDER BY embedding <=> $2::vector
            LIMIT $3
        """

        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)

        results = []
        for idx, row in enumerate(rows):
            item = MemoryItem(
                id=row["id"],
                user_id=row["user_id"],
                content=row["content"],
                type=MemoryType(row["type"]),
                relevance_score=float(row["similarity"]),
                source=str(row["source_message_id"]) if row["source_message_id"] else None,
                created_at=row["created_at"],
                importance=row["importance"],
            )
            results.append((item, idx + 1))  # 1-indexed rank

        return results

    def rrf_fusion(
        self,
        keyword_results: list[tuple[MemoryItem, int]],
        semantic_results: list[tuple[MemoryItem, int]],
        k: int = 60,
    ) -> list[MemoryItem]:
        """Combine keyword and semantic search results using Reciprocal Rank Fusion.

        RRF formula: score(item) = Σ 1 / (k + rank_i)

        Args:
            keyword_results: List of (MemoryItem, rank) from keyword search
            semantic_results: List of (MemoryItem, rank) from semantic search
            k: RRF constant (default 60)

        Returns:
            List of MemoryItems sorted by combined RRF score
        """
        # Build score map keyed by item ID
        scores: dict[UUID, float] = {}
        items: dict[UUID, MemoryItem] = {}

        # Process keyword results
        for item, rank in keyword_results:
            score = 1.0 / (k + rank)
            scores[item.id] = scores.get(item.id, 0.0) + score
            items[item.id] = item

        # Process semantic results
        for item, rank in semantic_results:
            score = 1.0 / (k + rank)
            scores[item.id] = scores.get(item.id, 0.0) + score
            items[item.id] = item

        # Sort by combined score descending
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        # Build result list with updated relevance scores
        results = []
        for item_id in sorted_ids:
            item = items[item_id]
            # Normalize RRF score to 0-1 range (approximate)
            normalized_score = min(1.0, scores[item_id] * k)
            item.relevance_score = normalized_score
            results.append(item)

        return results

    async def hybrid_search(
        self,
        request: MemoryQueryRequest,
        correlation_id: Optional[UUID] = None,
    ) -> MemoryQueryResponse:
        """Perform hybrid search combining keyword and semantic retrieval.

        Args:
            request: Memory query request with user_id, query, etc.
            correlation_id: Optional correlation ID for logging

        Returns:
            MemoryQueryResponse with items and metadata
        """
        start_time = time.perf_counter()
        query_hash = hashlib.sha256(request.query.encode()).hexdigest()[:16]

        try:
            # Generate query embedding
            embed_start = time.perf_counter()
            query_embedding = await self.embedding_service.get_embedding(request.query)
            embed_ms = int((time.perf_counter() - embed_start) * 1000)

            # Run parallel searches
            retrieval_start = time.perf_counter()

            # Keyword search
            keyword_results = await self.keyword_search(
                user_id=request.user_id,
                query=request.query,
                limit=request.limit * 2,  # Fetch more for fusion
                types=request.types,
            )

            # Semantic search (only if embedding available)
            semantic_results = []
            if query_embedding is not None:
                semantic_results = await self.semantic_search(
                    user_id=request.user_id,
                    embedding=query_embedding,
                    limit=request.limit * 2,
                    types=request.types,
                )

            retrieval_ms = int((time.perf_counter() - retrieval_start) * 1000)

            # Fuse results with RRF
            fused_results = self.rrf_fusion(
                keyword_results,
                semantic_results,
                k=self.settings.rrf_k,
            )

            # Filter by min_score
            filtered_results = [
                item for item in fused_results
                if item.relevance_score >= request.min_score
            ]

            # Limit results
            limited_results = filtered_results[:request.limit]

            # Enforce token budget
            final_results, truncated = self.enforce_token_budget(limited_results)

            # Calculate total tokens
            total_tokens = sum(self.count_tokens(item.content) for item in final_results)

            # Log retrieval (with query hash, NOT raw query)
            total_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info(
                "memory_retrieval",
                correlation_id=str(correlation_id) if correlation_id else None,
                query_hash=query_hash,
                user_id=request.user_id,
                result_count=len(final_results),
                total_count=len(fused_results),
                latency_ms=total_ms,
                truncated=truncated,
                keyword_results=len(keyword_results),
                semantic_results=len(semantic_results),
            )

            return MemoryQueryResponse(
                items=final_results,
                total_count=len(fused_results),
                query_embedding_ms=embed_ms,
                retrieval_ms=retrieval_ms,
                token_count=total_tokens,
                truncated=truncated,
            )

        except Exception as e:
            # Fail closed: return empty results on error
            logger.error(
                "memory_retrieval_failed",
                correlation_id=str(correlation_id) if correlation_id else None,
                query_hash=query_hash,
                user_id=request.user_id,
                error=str(e),
                error_type=type(e).__name__,
            )

            return MemoryQueryResponse(
                items=[],
                total_count=0,
                query_embedding_ms=0,
                retrieval_ms=0,
                token_count=0,
                truncated=False,
            )
