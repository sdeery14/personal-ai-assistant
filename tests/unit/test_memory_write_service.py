"""Unit tests for memory write service."""

import pytest
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.models.memory import (
    MemoryDeleteRequest,
    MemoryItem,
    MemoryQueryResponse,
    MemoryType,
    MemoryWriteRequest,
)


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    return MagicMock(
        memory_write_rate_per_conversation=10,
        memory_write_rate_per_hour=25,
        memory_duplicate_threshold=0.92,
        episode_user_message_threshold=8,
        episode_total_message_threshold=15,
        token_budget=1000,
        openai_api_key="test-key",
        openai_model="gpt-4",
        embedding_model="text-embedding-3-small",
        rrf_k=60,
    )


def _make_mock_pool(mock_conn):
    """Create a mock pool with proper async context manager for acquire()."""
    mock_pool = MagicMock()

    @asynccontextmanager
    async def mock_acquire():
        yield mock_conn

    mock_pool.acquire = mock_acquire
    return mock_pool


@pytest.fixture
def write_service(mock_settings):
    """Create MemoryWriteService with mocked dependencies."""
    with patch("src.services.memory_write_service.get_settings", return_value=mock_settings):
        from src.services.memory_write_service import MemoryWriteService
        service = MemoryWriteService()
        service.embedding_service = MagicMock()
        service.embedding_service.get_embedding = AsyncMock(return_value=[0.1] * 1536)
        service.redis_service = MagicMock()
        service.redis_service.check_write_rate_limit_conversation = AsyncMock(return_value=(True, 9))
        service.redis_service.check_write_rate_limit_hourly = AsyncMock(return_value=(True, 24))
        service.redis_service.check_episode_generated = AsyncMock(return_value=False)
        service.redis_service.set_episode_generated = AsyncMock(return_value=True)
        service.memory_service = MagicMock()
        service.memory_service.semantic_search = AsyncMock(return_value=[])
        service.memory_service.hybrid_search = AsyncMock(return_value=MemoryQueryResponse(
            items=[], total_count=0, query_embedding_ms=0, retrieval_ms=0, token_count=0, truncated=False,
        ))
        return service


class TestCreateMemory:
    """Tests for memory creation."""

    @pytest.mark.asyncio
    async def test_create_memory_success(self, write_service):
        """Test successful memory creation."""
        mock_conn = AsyncMock()
        mock_pool = _make_mock_pool(mock_conn)

        with patch("src.services.memory_write_service.get_pool", new_callable=AsyncMock, return_value=mock_pool):
            request = MemoryWriteRequest(
                user_id="test-user",
                content="User prefers dark mode",
                type=MemoryType.PREFERENCE,
                confidence=0.9,
            )

            result = await write_service.create_memory(request, uuid4())

            assert result.success is True
            assert result.action == "created"
            assert result.memory_id is not None
            assert mock_conn.execute.call_count == 2  # INSERT memory + INSERT audit

    @pytest.mark.asyncio
    async def test_create_memory_rate_limited_conversation(self, write_service):
        """Test rate limiting per conversation."""
        write_service.redis_service.check_write_rate_limit_conversation = AsyncMock(
            return_value=(False, 0)
        )

        request = MemoryWriteRequest(
            user_id="test-user",
            content="Some memory",
            type=MemoryType.FACT,
            source_conversation_id=uuid4(),
        )

        result = await write_service.create_memory(request)

        assert result.success is False
        assert result.action == "rate_limited"

    @pytest.mark.asyncio
    async def test_create_memory_rate_limited_hourly(self, write_service):
        """Test hourly rate limiting."""
        write_service.redis_service.check_write_rate_limit_hourly = AsyncMock(
            return_value=(False, 0)
        )

        request = MemoryWriteRequest(
            user_id="test-user",
            content="Some memory",
            type=MemoryType.FACT,
        )

        result = await write_service.create_memory(request)

        assert result.success is False
        assert result.action == "rate_limited"


class TestDuplicateDetection:
    """Tests for duplicate memory detection."""

    @pytest.mark.asyncio
    async def test_duplicate_detected(self, write_service):
        """Test that duplicates are rejected."""
        now = datetime.now(timezone.utc)
        duplicate_item = MemoryItem(
            id=uuid4(),
            user_id="test-user",
            content="User prefers dark mode",
            type=MemoryType.PREFERENCE,
            relevance_score=0.95,  # Above threshold
            created_at=now,
        )
        write_service.memory_service.semantic_search = AsyncMock(
            return_value=[(duplicate_item, 1)]
        )

        request = MemoryWriteRequest(
            user_id="test-user",
            content="User prefers dark mode",
            type=MemoryType.PREFERENCE,
        )

        result = await write_service.create_memory(request)

        assert result.success is False
        assert result.action == "duplicate"

    @pytest.mark.asyncio
    async def test_non_duplicate_allowed(self, write_service):
        """Test that non-duplicates pass through."""
        now = datetime.now(timezone.utc)
        different_item = MemoryItem(
            id=uuid4(),
            user_id="test-user",
            content="User likes Python",
            type=MemoryType.PREFERENCE,
            relevance_score=0.5,  # Below threshold
            created_at=now,
        )
        write_service.memory_service.semantic_search = AsyncMock(
            return_value=[(different_item, 1)]
        )

        mock_conn = AsyncMock()
        mock_pool = _make_mock_pool(mock_conn)

        with patch("src.services.memory_write_service.get_pool", new_callable=AsyncMock, return_value=mock_pool):
            request = MemoryWriteRequest(
                user_id="test-user",
                content="User prefers Rust",
                type=MemoryType.PREFERENCE,
            )

            result = await write_service.create_memory(request)

            assert result.success is True
            assert result.action == "created"


class TestDeleteMemory:
    """Tests for memory deletion."""

    @pytest.mark.asyncio
    async def test_delete_memory_success(self, write_service):
        """Test successful memory deletion."""
        now = datetime.now(timezone.utc)
        items = [
            MemoryItem(
                id=uuid4(),
                user_id="test-user",
                content="User lives in Portland",
                type=MemoryType.FACT,
                relevance_score=0.8,
                created_at=now,
            )
        ]
        write_service.memory_service.hybrid_search = AsyncMock(
            return_value=MemoryQueryResponse(
                items=items, total_count=1, query_embedding_ms=10,
                retrieval_ms=20, token_count=5, truncated=False,
            )
        )

        mock_conn = AsyncMock()
        mock_pool = _make_mock_pool(mock_conn)

        with patch("src.services.memory_write_service.get_pool", new_callable=AsyncMock, return_value=mock_pool):
            request = MemoryDeleteRequest(
                user_id="test-user",
                query="Portland location",
                reason="User moved",
            )

            result = await write_service.delete_memory(request, uuid4())

            assert result.success is True
            assert result.action == "deleted"
            assert "1" in result.message

    @pytest.mark.asyncio
    async def test_delete_memory_not_found(self, write_service):
        """Test deletion when no matching memories found."""
        request = MemoryDeleteRequest(
            user_id="test-user",
            query="nonexistent memory",
        )

        result = await write_service.delete_memory(request)

        assert result.success is False
        assert result.action == "not_found"


class TestSupersedeMemory:
    """Tests for memory supersession."""

    @pytest.mark.asyncio
    async def test_supersede_memory_success(self, write_service):
        """Test successful memory supersession."""
        old_id = uuid4()
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {"content": "Old content"}
        mock_pool = _make_mock_pool(mock_conn)

        with patch("src.services.memory_write_service.get_pool", new_callable=AsyncMock, return_value=mock_pool):
            result = await write_service.supersede_memory(
                old_memory_id=old_id,
                new_content="Updated content",
                user_id="test-user",
                memory_type=MemoryType.FACT,
                confidence=0.9,
                correlation_id=uuid4(),
            )

            assert result.success is True
            assert result.action == "superseded"
            assert result.memory_id is not None
            # Should have: INSERT new + UPDATE old + INSERT audit = 3 execute calls
            assert mock_conn.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_supersede_memory_old_not_found(self, write_service):
        """Test supersession when old memory doesn't exist."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None
        mock_pool = _make_mock_pool(mock_conn)

        with patch("src.services.memory_write_service.get_pool", new_callable=AsyncMock, return_value=mock_pool):
            result = await write_service.supersede_memory(
                old_memory_id=uuid4(),
                new_content="Updated content",
                user_id="test-user",
                memory_type=MemoryType.FACT,
            )

            assert result.success is False
            assert result.action == "not_found"


class TestFailClosed:
    """Tests for fail-closed behavior on errors."""

    @pytest.mark.asyncio
    async def test_create_memory_returns_error_on_exception(self, write_service):
        """Test that exceptions result in error response, not exception propagation."""
        write_service.embedding_service.get_embedding = AsyncMock(side_effect=Exception("API error"))

        request = MemoryWriteRequest(
            user_id="test-user",
            content="Some content",
            type=MemoryType.FACT,
        )

        result = await write_service.create_memory(request)

        assert result.success is False
        assert result.action == "error"

    @pytest.mark.asyncio
    async def test_embedding_failure_returns_error(self, write_service):
        """Test that embedding generation failure returns error."""
        write_service.embedding_service.get_embedding = AsyncMock(return_value=None)

        request = MemoryWriteRequest(
            user_id="test-user",
            content="Some content",
            type=MemoryType.FACT,
        )

        result = await write_service.create_memory(request)

        assert result.success is False
        assert result.action == "error"


class TestCrossUserBlocking:
    """Tests for cross-user security."""

    @pytest.mark.asyncio
    async def test_delete_only_own_memories(self, write_service):
        """Test that delete is scoped to user_id."""
        now = datetime.now(timezone.utc)
        items = [
            MemoryItem(
                id=uuid4(),
                user_id="test-user",
                content="User data",
                type=MemoryType.FACT,
                relevance_score=0.8,
                created_at=now,
            )
        ]
        write_service.memory_service.hybrid_search = AsyncMock(
            return_value=MemoryQueryResponse(
                items=items, total_count=1, query_embedding_ms=0,
                retrieval_ms=0, token_count=0, truncated=False,
            )
        )

        mock_conn = AsyncMock()
        mock_pool = _make_mock_pool(mock_conn)

        with patch("src.services.memory_write_service.get_pool", new_callable=AsyncMock, return_value=mock_pool):
            request = MemoryDeleteRequest(
                user_id="test-user",
                query="User data",
            )

            await write_service.delete_memory(request)

            # Verify the SQL includes user_id scoping
            update_call = mock_conn.execute.call_args_list[0]
            sql = update_call[0][0]
            assert "user_id = $2" in sql


class TestEpisodeSummary:
    """Tests for episode summarization."""

    @pytest.mark.asyncio
    async def test_episode_below_threshold(self, write_service):
        """Test that episode is not generated below message thresholds."""
        mock_messages = [
            MagicMock(role=MagicMock(value="user"), content="Hello"),
            MagicMock(role=MagicMock(value="assistant"), content="Hi!"),
        ]

        # The function does `from src.services.conversation_service import ConversationService`
        # locally. We need to mock the module's ConversationService class.
        mock_conv_service = MagicMock()
        mock_conv_service.get_conversation_messages = AsyncMock(return_value=mock_messages)

        mock_conv_module = MagicMock()
        mock_conv_module.ConversationService.return_value = mock_conv_service

        import sys
        with patch.dict(sys.modules, {"src.services.conversation_service": mock_conv_module}):
            result = await write_service.create_episode_summary(
                conversation_id=uuid4(),
                user_id="test-user",
            )

            assert result.success is False
            assert result.action == "threshold_not_met"

    @pytest.mark.asyncio
    async def test_episode_already_generated(self, write_service):
        """Test that duplicate episode generation is prevented."""
        write_service.redis_service.check_episode_generated = AsyncMock(return_value=True)

        result = await write_service.create_episode_summary(
            conversation_id=uuid4(),
            user_id="test-user",
        )

        assert result.success is False
        assert result.action == "already_exists"
