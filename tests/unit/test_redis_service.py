"""Unit tests for Redis service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.redis_service import RedisService


@pytest.fixture
def redis_service():
    """Create Redis service instance for testing."""
    return RedisService()


@pytest.fixture
def mock_redis_client():
    """Create mock Redis client."""
    client = AsyncMock()
    return client


class TestRateLimiting:
    """Tests for rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_check_rate_limit_allows_under_limit(self, redis_service, mock_redis_client):
        """Test that requests under rate limit are allowed."""
        with patch("src.services.redis_service.get_redis", return_value=mock_redis_client):
            mock_redis_client.get.return_value = "5"  # 5 requests made
            mock_redis_client.incr.return_value = 6

            allowed, remaining = await redis_service.check_rate_limit("test-user", limit=10)

            assert allowed is True
            assert remaining == 4  # 10 - 5 - 1 = 4

    @pytest.mark.asyncio
    async def test_check_rate_limit_blocks_over_limit(self, redis_service, mock_redis_client):
        """Test that requests over rate limit are blocked."""
        with patch("src.services.redis_service.get_redis", return_value=mock_redis_client):
            mock_redis_client.get.return_value = "10"  # Already at limit

            allowed, remaining = await redis_service.check_rate_limit("test-user", limit=10)

            assert allowed is False
            assert remaining == 0

    @pytest.mark.asyncio
    async def test_check_rate_limit_first_request(self, redis_service, mock_redis_client):
        """Test first request in rate limit window."""
        with patch("src.services.redis_service.get_redis", return_value=mock_redis_client):
            mock_redis_client.get.return_value = None  # No existing counter

            allowed, remaining = await redis_service.check_rate_limit("test-user", limit=10)

            assert allowed is True
            assert remaining == 9
            mock_redis_client.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_unavailable_graceful_degradation(self, redis_service):
        """Test graceful degradation when Redis is unavailable."""
        with patch("src.services.redis_service.get_redis", return_value=None):
            allowed, remaining = await redis_service.check_rate_limit("test-user")

            # Should allow request when Redis is unavailable
            assert allowed is True
            assert remaining == -1


class TestSessionStorage:
    """Tests for session state storage."""

    @pytest.mark.asyncio
    async def test_session_storage_and_retrieval(self, redis_service, mock_redis_client):
        """Test session state can be stored and retrieved."""
        with patch("src.services.redis_service.get_redis", return_value=mock_redis_client):
            # Test set
            mock_redis_client.hset.return_value = True
            mock_redis_client.expire.return_value = True

            state = {"last_message": "hello", "messages": ["msg1", "msg2"]}
            result = await redis_service.set_session("user1", "conv1", state)
            assert result is True

            # Test get
            mock_redis_client.hgetall.return_value = {
                "last_message": "hello",
                "messages": '["msg1", "msg2"]',
            }
            retrieved = await redis_service.get_session("user1", "conv1")
            assert retrieved is not None
            assert retrieved["last_message"] == "hello"

    @pytest.mark.asyncio
    async def test_session_not_found(self, redis_service, mock_redis_client):
        """Test session retrieval when not found."""
        with patch("src.services.redis_service.get_redis", return_value=mock_redis_client):
            mock_redis_client.hgetall.return_value = {}

            result = await redis_service.get_session("user1", "conv1")
            assert result is None


class TestEmbeddingCache:
    """Tests for embedding cache functionality."""

    @pytest.mark.asyncio
    async def test_cache_embedding_and_retrieve(self, redis_service, mock_redis_client):
        """Test embedding can be cached and retrieved."""
        with patch("src.services.redis_service.get_redis", return_value=mock_redis_client):
            embedding = [0.1, 0.2, 0.3]
            content_hash = "abc123"

            # Test cache
            mock_redis_client.setex.return_value = True
            result = await redis_service.cache_embedding(content_hash, embedding)
            assert result is True

            # Test retrieve
            mock_redis_client.get.return_value = "[0.1, 0.2, 0.3]"
            retrieved = await redis_service.get_cached_embedding(content_hash)
            assert retrieved == embedding

    @pytest.mark.asyncio
    async def test_cache_miss(self, redis_service, mock_redis_client):
        """Test cache miss returns None."""
        with patch("src.services.redis_service.get_redis", return_value=mock_redis_client):
            mock_redis_client.get.return_value = None

            result = await redis_service.get_cached_embedding("nonexistent")
            assert result is None


class TestWriteRateLimiting:
    """Tests for memory write rate limiting (Feature 006)."""

    @pytest.mark.asyncio
    async def test_conversation_write_rate_limit_allows(self, redis_service, mock_redis_client):
        """Test conversation write rate limit allows under limit."""
        with patch("src.services.redis_service.get_redis", return_value=mock_redis_client):
            mock_redis_client.get.return_value = "3"
            mock_redis_client.incr.return_value = 4

            allowed, remaining = await redis_service.check_write_rate_limit_conversation(
                "conv-123", limit=10
            )

            assert allowed is True
            assert remaining == 6

    @pytest.mark.asyncio
    async def test_conversation_write_rate_limit_blocks(self, redis_service, mock_redis_client):
        """Test conversation write rate limit blocks at limit."""
        with patch("src.services.redis_service.get_redis", return_value=mock_redis_client):
            mock_redis_client.get.return_value = "10"

            allowed, remaining = await redis_service.check_write_rate_limit_conversation(
                "conv-123", limit=10
            )

            assert allowed is False
            assert remaining == 0

    @pytest.mark.asyncio
    async def test_conversation_write_rate_first_write(self, redis_service, mock_redis_client):
        """Test first write in a conversation."""
        with patch("src.services.redis_service.get_redis", return_value=mock_redis_client):
            mock_redis_client.get.return_value = None

            allowed, remaining = await redis_service.check_write_rate_limit_conversation(
                "conv-123", limit=10
            )

            assert allowed is True
            assert remaining == 9
            mock_redis_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_hourly_write_rate_limit_allows(self, redis_service, mock_redis_client):
        """Test hourly write rate limit allows under limit."""
        with patch("src.services.redis_service.get_redis", return_value=mock_redis_client):
            mock_redis_client.get.return_value = "5"
            mock_redis_client.incr.return_value = 6

            allowed, remaining = await redis_service.check_write_rate_limit_hourly(
                "test-user", limit=25
            )

            assert allowed is True
            assert remaining == 19

    @pytest.mark.asyncio
    async def test_hourly_write_rate_limit_blocks(self, redis_service, mock_redis_client):
        """Test hourly write rate limit blocks at limit."""
        with patch("src.services.redis_service.get_redis", return_value=mock_redis_client):
            mock_redis_client.get.return_value = "25"

            allowed, remaining = await redis_service.check_write_rate_limit_hourly(
                "test-user", limit=25
            )

            assert allowed is False
            assert remaining == 0

    @pytest.mark.asyncio
    async def test_hourly_write_rate_first_request(self, redis_service, mock_redis_client):
        """Test first hourly write request."""
        with patch("src.services.redis_service.get_redis", return_value=mock_redis_client):
            mock_redis_client.get.return_value = None

            allowed, remaining = await redis_service.check_write_rate_limit_hourly(
                "test-user", limit=25
            )

            assert allowed is True
            assert remaining == 24
            mock_redis_client.setex.assert_called_once_with(
                "memory_write:hourly:test-user", 3600, "1"
            )

    @pytest.mark.asyncio
    async def test_write_rate_limit_graceful_degradation(self, redis_service):
        """Test graceful degradation when Redis unavailable."""
        with patch("src.services.redis_service.get_redis", return_value=None):
            allowed, remaining = await redis_service.check_write_rate_limit_conversation("conv-123")
            assert allowed is True
            assert remaining == -1

            allowed, remaining = await redis_service.check_write_rate_limit_hourly("test-user")
            assert allowed is True
            assert remaining == -1


class TestEpisodeFlag:
    """Tests for episode generation flag (Feature 006)."""

    @pytest.mark.asyncio
    async def test_check_episode_not_generated(self, redis_service, mock_redis_client):
        """Test checking when episode not yet generated."""
        with patch("src.services.redis_service.get_redis", return_value=mock_redis_client):
            mock_redis_client.exists.return_value = 0

            result = await redis_service.check_episode_generated("conv-123")
            assert result is False

    @pytest.mark.asyncio
    async def test_check_episode_already_generated(self, redis_service, mock_redis_client):
        """Test checking when episode already generated."""
        with patch("src.services.redis_service.get_redis", return_value=mock_redis_client):
            mock_redis_client.exists.return_value = 1

            result = await redis_service.check_episode_generated("conv-123")
            assert result is True

    @pytest.mark.asyncio
    async def test_set_episode_generated(self, redis_service, mock_redis_client):
        """Test marking episode as generated."""
        with patch("src.services.redis_service.get_redis", return_value=mock_redis_client):
            result = await redis_service.set_episode_generated("conv-123")
            assert result is True
            mock_redis_client.setex.assert_called_once()


class TestContentHash:
    """Tests for content hash computation."""

    def test_compute_content_hash_deterministic(self):
        """Test that same content produces same hash."""
        content = "test content"
        hash1 = RedisService.compute_content_hash(content)
        hash2 = RedisService.compute_content_hash(content)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex

    def test_compute_content_hash_different_content(self):
        """Test that different content produces different hash."""
        hash1 = RedisService.compute_content_hash("content 1")
        hash2 = RedisService.compute_content_hash("content 2")

        assert hash1 != hash2
