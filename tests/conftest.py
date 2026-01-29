"""Pytest configuration and fixtures."""

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# Will be imported after models are created
# from src.main import app


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
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for integration tests."""
    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
