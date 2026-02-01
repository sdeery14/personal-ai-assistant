"""Pytest configuration and fixtures."""

import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# Set test environment variables before importing app
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key-for-testing")
os.environ.setdefault("POSTGRES_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings() -> MagicMock:
    """Mock settings for tests without real environment variables."""
    settings = MagicMock()
    settings.openai_api_key = "sk-test-key-for-testing"
    settings.openai_model = "gpt-4"
    settings.max_tokens = 2000
    settings.timeout_seconds = 30
    settings.log_level = "INFO"
    settings.allowed_models_list = ["gpt-4", "gpt-3.5-turbo"]
    # Memory settings
    settings.postgres_url = "postgresql://test:test@localhost:5432/test"
    settings.redis_url = "redis://localhost:6379/0"
    settings.embedding_model = "text-embedding-3-small"
    settings.token_budget = 1000
    settings.min_relevance = 0.3
    settings.max_results = 10
    settings.memory_rate_limit = 10
    settings.embedding_cache_ttl = 604800
    settings.session_ttl = 86400
    settings.rrf_k = 60
    return settings


@pytest.fixture
def mock_agent_runner() -> Generator[MagicMock, None, None]:
    """Mock agents.Runner for testing without real OpenAI calls."""
    with patch("agents.Runner") as mock_runner:
        # Create mock result with stream_events
        mock_result = MagicMock()

        async def mock_stream_events():
            """Simulate streaming events from agent."""
            # Create mock ResponseTextDeltaEvent
            for i, text in enumerate(["Hello", ", ", "world", "!"]):
                event = MagicMock()
                event.type = "raw_response_event"
                event.data = MagicMock()
                event.data.delta = text
                # Mark as ResponseTextDeltaEvent
                event.data.__class__.__name__ = "ResponseTextDeltaEvent"
                yield event

        mock_result.stream_events = mock_stream_events
        mock_result.final_output = "Hello, world!"
        mock_runner.run_streamed.return_value = mock_result

        yield mock_runner


@pytest.fixture
def mock_database_pool() -> Generator[MagicMock, None, None]:
    """Mock database pool for testing without real Postgres."""
    with patch("src.database.get_pool") as mock_get_pool:
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_get_pool.return_value = mock_pool
        yield mock_pool, mock_conn


@pytest.fixture
def mock_redis() -> Generator[MagicMock, None, None]:
    """Mock Redis client for testing without real Redis."""
    with patch("src.services.redis_service.get_redis") as mock_get_redis:
        mock_client = AsyncMock()
        mock_get_redis.return_value = mock_client
        yield mock_client


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for integration tests."""
    # Mock database and redis before importing app
    with patch("src.database.init_database", new_callable=AsyncMock):
        with patch("src.database.run_migrations", new_callable=AsyncMock):
            with patch("src.services.redis_service.get_redis", return_value=None):
                from src.main import app

                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    yield client
