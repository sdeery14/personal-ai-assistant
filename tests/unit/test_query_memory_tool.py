"""Unit tests for query_memory tool logic.

Note: The @function_tool decorator from agents SDK wraps the function
in a FunctionTool object. We test the underlying logic by testing the
components (MemoryService, RedisService) that the tool uses.
"""

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.memory import MemoryItem, MemoryQueryRequest, MemoryQueryResponse, MemoryType


@pytest.fixture
def sample_memory_response():
    """Create sample memory query response."""
    now = datetime.now(timezone.utc)
    items = [
        MemoryItem(
            id=uuid4(),
            user_id="test-user",
            content="User prefers uv over pip",
            type=MemoryType.PREFERENCE,
            relevance_score=0.9,
            created_at=now,
            importance=0.8,
        ),
    ]
    return MemoryQueryResponse(
        items=items,
        total_count=1,
        query_embedding_ms=50,
        retrieval_ms=100,
        token_count=10,
        truncated=False,
    )


class TestMemoryServiceIntegration:
    """Tests for memory service used by query_memory tool."""

    @pytest.mark.asyncio
    async def test_memory_service_called_with_user_id(self, sample_memory_response):
        """Test that memory service enforces user_id scoping."""
        from src.services.memory_service import MemoryService

        with patch("src.services.memory_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                token_budget=1000,
                min_relevance=0.3,
                max_results=10,
                rrf_k=60,
                openai_api_key="test-key",
                embedding_model="text-embedding-3-small",
            )

            service = MemoryService()

            with patch.object(
                service.embedding_service, "get_embedding", return_value=[0.1] * 1536
            ):
                with patch.object(
                    service, "keyword_search", return_value=[]
                ) as mock_keyword:
                    with patch.object(
                        service, "semantic_search", return_value=[]
                    ) as mock_semantic:
                        request = MemoryQueryRequest(
                            user_id="test-user",
                            query="test query",
                        )

                        await service.hybrid_search(request)

                        # Verify user_id is passed (CRITICAL for security)
                        mock_keyword.assert_called_once()
                        assert mock_keyword.call_args.kwargs["user_id"] == "test-user"


class TestRedisRateLimiting:
    """Tests for rate limiting used by query_memory tool."""

    @pytest.mark.asyncio
    async def test_rate_limit_check(self):
        """Test that rate limit is checked before query."""
        from src.services.redis_service import RedisService

        service = RedisService()

        with patch("src.services.redis_service.get_redis") as mock_get_redis:
            mock_client = AsyncMock()
            mock_client.get.return_value = "5"  # 5 requests made
            mock_client.incr.return_value = 6
            mock_get_redis.return_value = mock_client

            allowed, remaining = await service.check_rate_limit("test-user", limit=10)

            assert allowed is True
            assert remaining == 4

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        """Test that rate limit blocks when exceeded."""
        from src.services.redis_service import RedisService

        service = RedisService()

        with patch("src.services.redis_service.get_redis") as mock_get_redis:
            mock_client = AsyncMock()
            mock_client.get.return_value = "10"  # At limit
            mock_get_redis.return_value = mock_client

            allowed, remaining = await service.check_rate_limit("test-user", limit=10)

            assert allowed is False
            assert remaining == 0


class TestToolResponseFormat:
    """Tests for expected tool response format."""

    def test_memory_item_serialization(self):
        """Test that memory items can be serialized to expected format."""
        now = datetime.now(timezone.utc)
        item = MemoryItem(
            id=uuid4(),
            user_id="test-user",
            content="Test content",
            type=MemoryType.PREFERENCE,
            relevance_score=0.9,
            created_at=now,
            importance=0.8,
        )

        # Format as expected by tool
        formatted = {
            "content": item.content,
            "type": item.type.value,
            "relevance": round(item.relevance_score, 3),
            "context": f"From {item.created_at.strftime('%Y-%m-%d')}" + (
                f" (importance: {item.importance})" if item.importance > 0.5 else ""
            ),
        }

        assert formatted["content"] == "Test content"
        assert formatted["type"] == "preference"
        assert formatted["relevance"] == 0.9
        assert "importance" in formatted["context"]

    def test_tool_response_structure(self, sample_memory_response):
        """Test expected response structure matches spec."""
        # Build response as tool would
        memories = [
            {
                "content": item.content,
                "type": item.type.value,
                "relevance": round(item.relevance_score, 3),
                "context": f"From {item.created_at.strftime('%Y-%m-%d')}",
            }
            for item in sample_memory_response.items
        ]

        response = {
            "memories": memories,
            "metadata": {
                "count": len(memories),
                "truncated": sample_memory_response.truncated,
                "total_available": sample_memory_response.total_count,
            },
        }

        # Verify JSON serializable
        json_str = json.dumps(response)
        parsed = json.loads(json_str)

        assert "memories" in parsed
        assert "metadata" in parsed
        assert isinstance(parsed["memories"], list)
        assert parsed["metadata"]["count"] == 1
        assert parsed["metadata"]["truncated"] is False


class TestFailClosedBehavior:
    """Tests for fail-closed behavior on errors."""

    @pytest.mark.asyncio
    async def test_memory_service_returns_empty_on_error(self):
        """Test that memory service returns empty response on error."""
        from src.services.memory_service import MemoryService

        with patch("src.services.memory_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                token_budget=1000,
                min_relevance=0.3,
                max_results=10,
                rrf_k=60,
                openai_api_key="test-key",
                embedding_model="text-embedding-3-small",
            )

            service = MemoryService()

            with patch.object(
                service.embedding_service, "get_embedding", return_value=[0.1] * 1536
            ):
                with patch.object(
                    service, "keyword_search", side_effect=Exception("DB Error")
                ):
                    request = MemoryQueryRequest(
                        user_id="test-user",
                        query="test query",
                    )

                    response = await service.hybrid_search(request)

                    # Should return empty, not raise
                    assert response.items == []
                    assert response.total_count == 0
