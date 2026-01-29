"""Unit tests for Pydantic models."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError


@pytest.fixture
def mock_settings():
    """Mock settings for validation tests."""
    with patch("src.models.request.get_settings") as mock:
        settings = MagicMock()
        settings.openai_model = "gpt-4"
        settings.max_tokens = 2000
        settings.allowed_models_list = ["gpt-4", "gpt-3.5-turbo"]
        mock.return_value = settings
        yield settings


class TestChatRequest:
    """Tests for ChatRequest model validation."""

    def test_valid_message(self, mock_settings):
        """Test valid message passes validation."""
        from src.models.request import ChatRequest

        request = ChatRequest(message="Hello, world!")
        assert request.message == "Hello, world!"

    def test_empty_message_fails(self, mock_settings):
        """Test empty message raises validation error."""
        from src.models.request import ChatRequest

        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="")

        errors = exc_info.value.errors()
        assert len(errors) >= 1
        # Should fail on min_length or empty check

    def test_whitespace_only_message_fails(self, mock_settings):
        """Test whitespace-only message raises validation error."""
        from src.models.request import ChatRequest

        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="   \t\n  ")

        errors = exc_info.value.errors()
        assert any(
            "empty" in str(e).lower() or "whitespace" in str(e).lower() for e in errors
        )

    def test_message_too_long_fails(self, mock_settings):
        """Test message exceeding 8000 chars raises validation error."""
        from src.models.request import ChatRequest

        long_message = "x" * 8001
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message=long_message)

        errors = exc_info.value.errors()
        assert len(errors) >= 1

    def test_message_at_limit_passes(self, mock_settings):
        """Test message at exactly 8000 chars passes validation."""
        from src.models.request import ChatRequest

        message = "x" * 8000
        request = ChatRequest(message=message)
        assert len(request.message) == 8000

    def test_invalid_model_fails(self, mock_settings):
        """Test invalid model raises validation error."""
        from src.models.request import ChatRequest

        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="Hello", model="gpt-99")

        errors = exc_info.value.errors()
        assert any("model" in str(e).lower() for e in errors)

    def test_valid_model_passes(self, mock_settings):
        """Test valid model passes validation."""
        from src.models.request import ChatRequest

        request = ChatRequest(message="Hello", model="gpt-4")
        assert request.model == "gpt-4"

    def test_max_tokens_too_low_fails(self, mock_settings):
        """Test max_tokens below 1 raises validation error."""
        from src.models.request import ChatRequest

        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="Hello", max_tokens=0)

        errors = exc_info.value.errors()
        assert len(errors) >= 1

    def test_max_tokens_too_high_fails(self, mock_settings):
        """Test max_tokens above 4000 raises validation error."""
        from src.models.request import ChatRequest

        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="Hello", max_tokens=5000)

        errors = exc_info.value.errors()
        assert len(errors) >= 1

    def test_max_tokens_at_limit_passes(self, mock_settings):
        """Test max_tokens at 4000 passes validation."""
        from src.models.request import ChatRequest

        request = ChatRequest(message="Hello", max_tokens=4000)
        assert request.max_tokens == 4000

    def test_message_strips_whitespace(self, mock_settings):
        """Test message is stripped of leading/trailing whitespace."""
        from src.models.request import ChatRequest

        request = ChatRequest(message="  Hello, world!  ")
        assert request.message == "Hello, world!"


class TestStreamChunk:
    """Tests for StreamChunk model."""

    def test_valid_chunk(self):
        """Test valid StreamChunk creation."""
        from uuid import uuid4
        from src.models.response import StreamChunk

        correlation_id = uuid4()
        chunk = StreamChunk(
            content="Hello",
            sequence=0,
            is_final=False,
            correlation_id=correlation_id,
        )
        assert chunk.content == "Hello"
        assert chunk.sequence == 0
        assert chunk.is_final is False

    def test_negative_sequence_fails(self):
        """Test negative sequence raises validation error."""
        from uuid import uuid4
        from src.models.response import StreamChunk

        with pytest.raises(ValidationError):
            StreamChunk(
                content="Hello",
                sequence=-1,
                is_final=False,
                correlation_id=uuid4(),
            )


class TestChatResponse:
    """Tests for ChatResponse model."""

    def test_success_response(self):
        """Test valid success response."""
        from uuid import uuid4
        from src.models.response import ChatResponse

        response = ChatResponse(
            correlation_id=uuid4(),
            status="success",
            duration_ms=1234,
            model_used="gpt-4",
            total_tokens=100,
        )
        assert response.status == "success"

    def test_error_requires_message(self):
        """Test error status requires error_message."""
        from uuid import uuid4
        from src.models.response import ChatResponse

        with pytest.raises(ValidationError) as exc_info:
            ChatResponse(
                correlation_id=uuid4(),
                status="error",
                duration_ms=1234,
                model_used="gpt-4",
            )

        errors = exc_info.value.errors()
        assert any("error_message" in str(e).lower() for e in errors)

    def test_error_with_message_passes(self):
        """Test error status with message passes."""
        from uuid import uuid4
        from src.models.response import ChatResponse

        response = ChatResponse(
            correlation_id=uuid4(),
            status="error",
            duration_ms=1234,
            model_used="gpt-4",
            error_message="Something went wrong",
        )
        assert response.status == "error"
        assert response.error_message == "Something went wrong"
