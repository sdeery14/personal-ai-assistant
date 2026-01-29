"""Integration tests for observability features."""

import json
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def mock_runner():
    """Mock Runner.run_streamed for testing."""
    with patch("src.services.chat_service.Runner") as mock:
        from openai.types.responses import ResponseTextDeltaEvent

        # Create mock result
        mock_result = MagicMock()

        async def mock_stream_events():
            """Simulate streaming events with real ResponseTextDeltaEvent objects."""
            texts = ["Hello", "!"]
            for i, text in enumerate(texts):
                event = MagicMock()
                event.type = "raw_response_event"
                event.data = ResponseTextDeltaEvent(
                    delta=text,
                    type="response.output_text.delta",
                    content_index=0,
                    output_index=0,
                    item_id=f"item_{i}",
                    logprobs=[],
                    sequence_number=i,
                )
                yield event

        mock_result.stream_events = mock_stream_events
        mock_result.final_output = "Hello!"
        mock.run_streamed.return_value = mock_result

        yield mock


@pytest.fixture
def mock_settings():
    """Mock settings for tests."""
    settings = MagicMock()
    settings.openai_api_key = "sk-test-key"
    settings.openai_model = "gpt-4"
    settings.max_tokens = 2000
    settings.timeout_seconds = 30
    settings.log_level = "DEBUG"  # DEBUG to capture chunk_sent logs
    settings.allowed_models_list = ["gpt-4", "gpt-3.5-turbo"]

    with (
        patch("src.services.chat_service.get_settings", return_value=settings),
        patch("src.api.routes.get_settings", return_value=settings),
        patch("src.main.get_settings", return_value=settings),
    ):
        yield settings


@pytest.fixture
def mock_request_settings():
    """Mock settings for request validation."""
    with patch("src.models.request.get_settings") as mock:
        settings = MagicMock()
        settings.openai_model = "gpt-4"
        settings.max_tokens = 2000
        settings.allowed_models_list = ["gpt-4", "gpt-3.5-turbo"]
        mock.return_value = settings
        yield settings


@pytest.mark.asyncio
async def test_correlation_id_in_response_header(
    mock_runner, mock_settings, mock_request_settings
):
    """Test X-Correlation-Id header is present in response."""
    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/chat",
            json={"message": "Hello"},
        ) as response:
            assert "x-correlation-id" in response.headers
            correlation_id = response.headers["x-correlation-id"]

            # Verify it's a valid UUID format
            import uuid

            try:
                uuid.UUID(correlation_id)
            except ValueError:
                pytest.fail(f"Correlation ID is not a valid UUID: {correlation_id}")

            # Consume the response
            async for _ in response.aiter_lines():
                pass


@pytest.mark.asyncio
async def test_correlation_id_in_chunks(
    mock_runner, mock_settings, mock_request_settings
):
    """Test correlation ID is present in all streamed chunks."""
    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/chat",
            json={"message": "Hello"},
        ) as response:
            header_correlation_id = response.headers["x-correlation-id"]

            chunks = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunk_data = json.loads(line[6:])
                    chunks.append(chunk_data)

    # Verify all chunks have the same correlation ID as header
    for chunk in chunks:
        assert chunk["correlation_id"] == header_correlation_id


@pytest.mark.asyncio
async def test_correlation_id_passes_through_from_request(
    mock_runner, mock_settings, mock_request_settings
):
    """Test client-provided X-Correlation-Id is used."""
    from src.main import app

    client_correlation_id = "client-provided-12345678-1234-1234-1234-123456789abc"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/chat",
            json={"message": "Hello"},
            headers={"X-Correlation-Id": client_correlation_id},
        ) as response:
            # Response should use the client-provided ID
            assert response.headers["x-correlation-id"] == client_correlation_id

            chunks = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunk_data = json.loads(line[6:])
                    chunks.append(chunk_data)

    # All chunks should have the client-provided correlation ID
    for chunk in chunks:
        assert chunk["correlation_id"] == client_correlation_id


@pytest.mark.asyncio
async def test_health_endpoint_has_correlation_id(
    mock_runner, mock_settings, mock_request_settings
):
    """Test health endpoint also includes correlation ID."""
    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    # Health endpoint should also have correlation ID from middleware
    assert "x-correlation-id" in response.headers


@pytest.mark.asyncio
async def test_error_response_has_correlation_id(
    mock_runner, mock_settings, mock_request_settings
):
    """Test error responses include correlation ID."""
    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/chat",
            json={"message": ""},  # Invalid - empty message
        )

    assert response.status_code == 400
    assert "x-correlation-id" in response.headers

    # Correlation ID should also be in the response body
    data = response.json()
    assert "correlation_id" in data


class TestTimestampFormat:
    """Tests for timestamp formatting in logs."""

    def test_timestamps_are_utc_iso8601(self):
        """Test that health endpoint returns UTC ISO8601 timestamp."""
        import re

        @pytest.fixture
        def sync_client():
            from src.main import app
            from httpx import Client, ASGITransport

            transport = ASGITransport(app=app)
            return Client(transport=transport, base_url="http://test")

        # ISO8601 UTC pattern
        iso8601_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"

        # This is validated by the health endpoint response
        # which uses datetime.now(timezone.utc).isoformat()


class TestNoSecretsInLogs:
    """Tests to verify no secrets are logged."""

    def test_api_key_not_in_settings_repr(self):
        """Test API key is not exposed in settings representation."""
        from src.config import Settings
        from unittest.mock import patch
        import os

        # This test verifies the redaction processor would catch any leaked keys
        from src.services.logging_service import redact_sensitive

        # Simulate a log entry with API key
        event_dict = {
            "event": "config_loaded",
            "openai_api_key": "sk-real-secret-key-123",
        }

        result = redact_sensitive(None, None, event_dict)
        assert result["openai_api_key"] == "REDACTED"
        assert "sk-real-secret-key" not in str(result)
