"""Redis service for session state, rate limiting, and embedding cache."""

import hashlib
import json
from typing import Optional

import redis.asyncio as redis
import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)

# Global Redis client
_redis_client: Optional[redis.Redis] = None


async def get_redis() -> Optional[redis.Redis]:
    """Get or create the Redis client.

    Returns:
        Redis client or None if connection fails (graceful degradation)
    """
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    settings = get_settings()

    try:
        _redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        # Test connection
        await _redis_client.ping()
        logger.info("redis_connected", url=settings.redis_url.split("@")[-1])
        return _redis_client
    except Exception as e:
        logger.warning("redis_connection_failed", error=str(e))
        _redis_client = None
        return None


async def close_redis() -> None:
    """Close the Redis connection."""
    global _redis_client

    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("redis_connection_closed")


class RedisService:
    """Service for Redis operations: session state, rate limiting, embedding cache."""

    def __init__(self):
        self.settings = get_settings()

    async def get_session(
        self, user_id: str, conversation_id: str
    ) -> Optional[dict]:
        """Retrieve session state for a user's conversation.

        Args:
            user_id: User identifier
            conversation_id: Conversation identifier

        Returns:
            Session state dict or None if not found/Redis unavailable
        """
        client = await get_redis()
        if client is None:
            return None

        try:
            key = f"session:{user_id}:{conversation_id}"
            data = await client.hgetall(key)
            if data:
                # Parse JSON values
                return {k: json.loads(v) if v.startswith(('[', '{')) else v for k, v in data.items()}
            return None
        except Exception as e:
            logger.warning("redis_get_session_failed", error=str(e), user_id=user_id)
            return None

    async def set_session(
        self, user_id: str, conversation_id: str, state: dict
    ) -> bool:
        """Store session state for a user's conversation.

        Args:
            user_id: User identifier
            conversation_id: Conversation identifier
            state: Session state to store

        Returns:
            True if successful, False otherwise
        """
        client = await get_redis()
        if client is None:
            return False

        try:
            key = f"session:{user_id}:{conversation_id}"
            # Serialize complex values to JSON
            serialized = {k: json.dumps(v) if isinstance(v, (list, dict)) else str(v) for k, v in state.items()}
            await client.hset(key, mapping=serialized)
            await client.expire(key, self.settings.session_ttl)
            return True
        except Exception as e:
            logger.warning("redis_set_session_failed", error=str(e), user_id=user_id)
            return False

    async def check_rate_limit(
        self, user_id: str, limit: Optional[int] = None
    ) -> tuple[bool, int]:
        """Check and increment rate limit counter for a user.

        Args:
            user_id: User identifier
            limit: Optional custom limit (defaults to config)

        Returns:
            Tuple of (allowed: bool, remaining: int)
        """
        client = await get_redis()
        if client is None:
            # Graceful degradation: allow if Redis unavailable
            return True, -1

        limit = limit or self.settings.memory_rate_limit

        try:
            key = f"rate_limit:{user_id}"
            current = await client.get(key)

            if current is None:
                # First request in window
                await client.setex(key, 60, "1")  # 60 second window
                return True, limit - 1

            count = int(current)
            if count >= limit:
                return False, 0

            await client.incr(key)
            return True, limit - count - 1
        except Exception as e:
            logger.warning("redis_rate_limit_failed", error=str(e), user_id=user_id)
            # Graceful degradation: allow if error
            return True, -1

    async def get_rate_limit_remaining(self, user_id: str) -> int:
        """Get remaining rate limit quota for a user.

        Args:
            user_id: User identifier

        Returns:
            Remaining requests or -1 if Redis unavailable
        """
        client = await get_redis()
        if client is None:
            return -1

        try:
            key = f"rate_limit:{user_id}"
            current = await client.get(key)
            if current is None:
                return self.settings.memory_rate_limit
            return max(0, self.settings.memory_rate_limit - int(current))
        except Exception as e:
            logger.warning("redis_get_rate_limit_failed", error=str(e), user_id=user_id)
            return -1

    async def get_cached_embedding(self, content_hash: str) -> Optional[list[float]]:
        """Retrieve cached embedding by content hash.

        Args:
            content_hash: SHA256 hash of the content

        Returns:
            Embedding vector or None if not cached
        """
        client = await get_redis()
        if client is None:
            return None

        try:
            key = f"embedding_cache:{content_hash}"
            data = await client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning("redis_get_embedding_failed", error=str(e))
            return None

    async def cache_embedding(
        self, content_hash: str, embedding: list[float]
    ) -> bool:
        """Cache an embedding with TTL.

        Args:
            content_hash: SHA256 hash of the content
            embedding: Embedding vector to cache

        Returns:
            True if successful, False otherwise
        """
        client = await get_redis()
        if client is None:
            return False

        try:
            key = f"embedding_cache:{content_hash}"
            await client.setex(
                key,
                self.settings.embedding_cache_ttl,
                json.dumps(embedding),
            )
            return True
        except Exception as e:
            logger.warning("redis_cache_embedding_failed", error=str(e))
            return False

    @staticmethod
    def compute_content_hash(content: str) -> str:
        """Compute SHA256 hash of content for caching.

        Args:
            content: Text content to hash

        Returns:
            Hex-encoded SHA256 hash
        """
        return hashlib.sha256(content.encode()).hexdigest()

    # Weather cache methods (Feature 005)

    async def get_weather_cache(
        self, location: str, query_type: str
    ) -> Optional[dict | list]:
        """Retrieve cached weather data.

        Args:
            location: Normalized location string
            query_type: Type of query ('current' or 'forecast_N')

        Returns:
            Cached weather data or None if not cached
        """
        client = await get_redis()
        if client is None:
            return None

        try:
            key = f"weather:{location}:{query_type}"
            data = await client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning("redis_get_weather_cache_failed", error=str(e))
            return None

    async def set_weather_cache(
        self, location: str, query_type: str, data: dict | list, ttl: int
    ) -> bool:
        """Cache weather data with TTL.

        Args:
            location: Normalized location string
            query_type: Type of query ('current' or 'forecast_N')
            data: Weather data to cache
            ttl: Time-to-live in seconds

        Returns:
            True if successful, False otherwise
        """
        client = await get_redis()
        if client is None:
            return False

        try:
            key = f"weather:{location}:{query_type}"
            await client.setex(key, ttl, json.dumps(data, default=str))
            logger.debug("weather_cached", location=location, query_type=query_type, ttl=ttl)
            return True
        except Exception as e:
            logger.warning("redis_set_weather_cache_failed", error=str(e))
            return False
