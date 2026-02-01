"""Embedding generation service with caching."""

from typing import Optional

import structlog
from openai import AsyncOpenAI

from src.config import get_settings
from src.services.redis_service import RedisService

logger = structlog.get_logger(__name__)

# Maximum characters for embedding input (text-embedding-3-small limit)
MAX_EMBEDDING_CHARS = 8192


class EmbeddingService:
    """Service for generating and caching text embeddings."""

    def __init__(self):
        self.settings = get_settings()
        self.redis_service = RedisService()
        self._client: Optional[AsyncOpenAI] = None

    @property
    def client(self) -> AsyncOpenAI:
        """Lazy-load OpenAI client."""
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        return self._client

    async def generate_embedding(self, text: str) -> Optional[list[float]]:
        """Generate embedding for text via OpenAI API.

        Args:
            text: Text to embed (will be truncated if too long)

        Returns:
            Embedding vector or None if generation fails
        """
        # Truncate if necessary
        if len(text) > MAX_EMBEDDING_CHARS:
            logger.warning(
                "embedding_text_truncated",
                original_length=len(text),
                truncated_to=MAX_EMBEDDING_CHARS,
            )
            text = text[:MAX_EMBEDDING_CHARS]

        try:
            response = await self.client.embeddings.create(
                input=text,
                model=self.settings.embedding_model,
            )
            embedding = response.data[0].embedding
            logger.debug(
                "embedding_generated",
                model=self.settings.embedding_model,
                dimensions=len(embedding),
            )
            return embedding
        except Exception as e:
            logger.error(
                "embedding_generation_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    async def get_embedding(self, text: str) -> Optional[list[float]]:
        """Get embedding for text, using cache if available.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if unavailable
        """
        # Compute content hash for caching
        content_hash = RedisService.compute_content_hash(text)

        # Try cache first
        cached = await self.redis_service.get_cached_embedding(content_hash)
        if cached is not None:
            logger.debug("embedding_cache_hit", content_hash=content_hash[:16])
            return cached

        # Generate new embedding
        embedding = await self.generate_embedding(text)
        if embedding is None:
            return None

        # Cache the result
        await self.redis_service.cache_embedding(content_hash, embedding)
        logger.debug("embedding_cached", content_hash=content_hash[:16])

        return embedding

    async def get_embeddings_batch(
        self, texts: list[str]
    ) -> list[Optional[list[float]]]:
        """Get embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings (None for any that failed)
        """
        results = []
        for text in texts:
            embedding = await self.get_embedding(text)
            results.append(embedding)
        return results
