"""Unit tests for embedding service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.embedding_service import EmbeddingService, MAX_EMBEDDING_CHARS


@pytest.fixture
def embedding_service():
    """Create embedding service instance for testing."""
    with patch("src.services.embedding_service.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(
            openai_api_key="test-key",
            embedding_model="text-embedding-3-small",
        )
        return EmbeddingService()


@pytest.fixture
def mock_openai_response():
    """Create mock OpenAI embedding response."""
    response = MagicMock()
    response.data = [MagicMock(embedding=[0.1] * 1536)]
    return response


class TestGenerateEmbedding:
    """Tests for embedding generation."""

    @pytest.mark.asyncio
    async def test_generate_embedding_calls_openai(self, embedding_service, mock_openai_response):
        """Test that generate_embedding calls OpenAI API."""
        with patch.object(
            embedding_service, "_client", new_callable=MagicMock
        ) as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_openai_response)

            result = await embedding_service.generate_embedding("test text")

            assert result is not None
            assert len(result) == 1536
            mock_client.embeddings.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_embedding_truncates_long_text(self, embedding_service, mock_openai_response):
        """Test that long text is truncated."""
        long_text = "x" * (MAX_EMBEDDING_CHARS + 1000)

        with patch.object(
            embedding_service, "_client", new_callable=MagicMock
        ) as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_openai_response)

            result = await embedding_service.generate_embedding(long_text)

            assert result is not None
            # Verify the API was called with truncated text
            call_args = mock_client.embeddings.create.call_args
            assert len(call_args.kwargs["input"]) == MAX_EMBEDDING_CHARS

    @pytest.mark.asyncio
    async def test_generate_embedding_handles_api_error(self, embedding_service):
        """Test graceful handling of API errors."""
        with patch.object(
            embedding_service, "_client", new_callable=MagicMock
        ) as mock_client:
            mock_client.embeddings.create = AsyncMock(side_effect=Exception("API Error"))

            result = await embedding_service.generate_embedding("test text")

            assert result is None


class TestGetEmbedding:
    """Tests for embedding retrieval with caching."""

    @pytest.mark.asyncio
    async def test_get_embedding_cache_hit(self, embedding_service):
        """Test that cache hit skips API call."""
        cached_embedding = [0.2] * 1536

        with patch.object(
            embedding_service.redis_service,
            "get_cached_embedding",
            return_value=cached_embedding,
        ):
            with patch.object(
                embedding_service, "generate_embedding"
            ) as mock_generate:
                result = await embedding_service.get_embedding("test text")

                assert result == cached_embedding
                mock_generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_embedding_cache_miss(self, embedding_service, mock_openai_response):
        """Test that cache miss calls API and caches result."""
        with patch.object(
            embedding_service.redis_service,
            "get_cached_embedding",
            return_value=None,
        ):
            with patch.object(
                embedding_service.redis_service,
                "cache_embedding",
                return_value=True,
            ) as mock_cache:
                with patch.object(
                    embedding_service, "_client", new_callable=MagicMock
                ) as mock_client:
                    mock_client.embeddings.create = AsyncMock(return_value=mock_openai_response)

                    result = await embedding_service.get_embedding("test text")

                    assert result is not None
                    assert len(result) == 1536
                    mock_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_embedding_generation_fails(self, embedding_service):
        """Test handling when embedding generation fails."""
        with patch.object(
            embedding_service.redis_service,
            "get_cached_embedding",
            return_value=None,
        ):
            with patch.object(
                embedding_service,
                "generate_embedding",
                return_value=None,
            ):
                result = await embedding_service.get_embedding("test text")

                assert result is None
