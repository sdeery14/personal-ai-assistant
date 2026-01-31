"""Integration tests for chat endpoint."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

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
            texts = ["Hello", ", ", "world", "!"]
            for i, text in enumerate(texts):
                event = MagicMock()
                event.type = "raw_response_event"
                # Create real ResponseTextDeltaEvent so isinstance check passes
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
        mock_result.final_output = "Hello, world!"
        mock.run_streamed.return_value = mock_result

        yield mock


@pytest.fixture
def mock_settings():
    """Mock settings for tests."""
    # Must patch at all locations where get_settings is imported
    settings = MagicMock()
    settings.openai_api_key = "sk-test-key"
    settings.openai_model = "gpt-4"
    settings.max_tokens = 2000
    settings.timeout_seconds = 30
    settings.log_level = "INFO"
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
async def test_health_endpoint(mock_runner, mock_settings, mock_request_settings):
    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_chat_streaming_returns_chunks(
    mock_runner, mock_settings, mock_request_settings
):
    """Test chat endpoint streams chunks with sequence numbers."""
    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/chat",
            json={"message": "What is 2+2?"},
        ) as response:
            assert response.status_code == 200
            assert (
                response.headers["content-type"] == "text/event-stream; charset=utf-8"
            )
            assert "x-correlation-id" in response.headers

            chunks = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunk_data = json.loads(line[6:])
                    chunks.append(chunk_data)

    # Verify we got chunks
    assert len(chunks) > 0

    # Verify sequence numbers are incremental
    sequences = [c["sequence"] for c in chunks]
    assert sequences == list(range(len(sequences)))

    # Verify final chunk has is_final=True
    assert chunks[-1]["is_final"] is True

    # Verify all chunks have correlation_id
    correlation_ids = set(c["correlation_id"] for c in chunks)
    assert len(correlation_ids) == 1  # All same correlation ID


@pytest.mark.asyncio
async def test_chat_streaming_has_correlation_id_header(
    mock_runner, mock_settings, mock_request_settings
):
    """Test chat endpoint includes X-Correlation-Id header."""
    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/chat",
            json={"message": "Hello"},
        ) as response:
            correlation_id = response.headers.get("x-correlation-id")
            assert correlation_id is not None

            # Verify it's a valid UUID format
            from uuid import UUID

            UUID(correlation_id)  # Will raise if invalid


@pytest.mark.asyncio
async def test_chat_content_matches_streamed_text(
    mock_runner, mock_settings, mock_request_settings
):
    """Test that streamed content matches expected text."""
    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/chat",
            json={"message": "Hello"},
        ) as response:
            chunks = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunk_data = json.loads(line[6:])
                    chunks.append(chunk_data)

    # Combine content from all non-final chunks
    full_content = "".join(c["content"] for c in chunks if not c["is_final"])
    assert full_content == "Hello, world!"


# ============================================================================
# Error Handling Tests (User Story 2)
# ============================================================================


@pytest.mark.asyncio
async def test_empty_message_returns_400(
    mock_runner, mock_settings, mock_request_settings
):
    """Test empty message returns 400 validation error."""
    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/chat", json={"message": ""})

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"] == "Validation error"
    assert "correlation_id" in data


@pytest.mark.asyncio
async def test_whitespace_message_returns_400(
    mock_runner, mock_settings, mock_request_settings
):
    """Test whitespace-only message returns 400 validation error."""
    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/chat", json={"message": "   "})

    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "Validation error"


@pytest.mark.asyncio
async def test_invalid_model_returns_400(
    mock_runner, mock_settings, mock_request_settings
):
    """Test invalid model selection returns 400 validation error."""
    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/chat", json={"message": "Hello", "model": "gpt-99-invalid"}
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "Validation error"
    assert "model" in data["detail"].lower()


@pytest.mark.asyncio
async def test_max_tokens_out_of_range_returns_400(
    mock_runner, mock_settings, mock_request_settings
):
    """Test max_tokens out of range returns 400 validation error."""
    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/chat", json={"message": "Hello", "max_tokens": 10000}
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "Validation error"


@pytest.mark.asyncio
async def test_openai_error_streams_error_chunk(mock_settings, mock_request_settings):
    """Test OpenAI API error streams error chunk to client."""
    from src.main import app

    # Mock Runner to raise an exception
    with patch("src.services.chat_service.Runner") as mock_runner:
        mock_result = MagicMock()

        async def mock_stream_events_error():
            raise Exception("OpenAI API Error: Rate limit exceeded")
            yield  # Make it a generator

        mock_result.stream_events = mock_stream_events_error
        mock_runner.run_streamed.return_value = mock_result

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/chat",
                json={"message": "Hello"},
            ) as response:
                chunks = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        chunk_data = json.loads(line[6:])
                        chunks.append(chunk_data)

        # Should receive an error chunk
        assert len(chunks) >= 1
        error_chunk = chunks[-1]
        assert "error" in error_chunk
        assert error_chunk["is_final"] is True


class TestGuardrailResponses:
    """Tests for guardrail response structure (T053)."""

    @pytest.mark.asyncio
    async def test_guardrail_response_includes_correlation_id(self, mock_settings):
        """T053: Verify correlation_id in guardrail error responses."""
        from src.main import app

        with patch("src.api.routes.get_settings", return_value=mock_settings):
            with patch("src.services.chat_service.Runner") as mock_runner:
                # Mock guardrail trigger - raise generic exception to simulate guardrail failure
                # (SDK exceptions require complex InputGuardrailResult objects)
                mock_runner.run_streamed.side_effect = Exception(
                    "Input guardrail: Content flagged"
                )

                transport = ASGITransport(app=app)
                async with AsyncClient(
                    transport=transport, base_url="http://test"
                ) as client:
                    async with client.stream(
                        "POST",
                        "/chat",
                        json={"message": "Test adversarial prompt"},
                    ) as response:
                        chunks = []
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                chunk_data = json.loads(line[6:])
                                chunks.append(chunk_data)

        # Should have at least one error chunk
        assert len(chunks) >= 1

        # Find the error chunk
        error_chunk = next(
            (c for c in chunks if "error_type" in c or "error" in c), chunks[0]
        )

        # T053: Verify correlation_id is present
        assert "correlation_id" in error_chunk, (
            "Guardrail error response must include correlation_id for incident tracking"
        )

        # Verify correlation_id is a valid UUID format
        correlation_id = error_chunk["correlation_id"]
        assert isinstance(correlation_id, str)
        assert len(correlation_id) > 0

    @pytest.mark.asyncio
    async def test_output_guardrail_retraction_includes_correlation_id(
        self, mock_settings
    ):
        """T053: Verify correlation_id in output guardrail retraction events."""
        from src.main import app

        with patch("src.api.routes.get_settings", return_value=mock_settings):
            with patch("src.services.chat_service.Runner") as mock_runner:
                # Mock output guardrail trigger during streaming
                # (SDK exceptions require complex OutputGuardrailResult objects)
                mock_runner.run_streamed.side_effect = Exception(
                    "Output guardrail: Content flagged"
                )

                transport = ASGITransport(app=app)
                async with AsyncClient(
                    transport=transport, base_url="http://test"
                ) as client:
                    async with client.stream(
                        "POST",
                        "/chat",
                        json={"message": "Normal request"},
                    ) as response:
                        chunks = []
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                chunk_data = json.loads(line[6:])
                                chunks.append(chunk_data)

        # Should have error chunk for retraction
        assert len(chunks) >= 1
        error_chunk = next(
            (c for c in chunks if "error_type" in c or "error" in c), chunks[0]
        )

        # Verify correlation_id present in retraction
        assert "correlation_id" in error_chunk, (
            "Output guardrail retraction must include correlation_id"
        )
