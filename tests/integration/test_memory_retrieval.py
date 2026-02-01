"""Integration tests for memory retrieval functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestHealthEndpointWithMemory:
    """Tests for health endpoint with memory infrastructure."""

    @pytest.mark.asyncio
    async def test_health_includes_database_status(self, async_client):
        """Test that health endpoint includes database status."""
        response = await async_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "redis" in data

    @pytest.mark.asyncio
    async def test_health_graceful_when_database_unavailable(self, async_client):
        """Test health endpoint works even when database is unavailable."""
        with patch(
            "src.api.routes.db_health_check",
            side_effect=Exception("Connection failed"),
        ):
            response = await async_client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"


class TestChatEndpointWithMemory:
    """Tests for chat endpoint with memory features."""

    @pytest.mark.asyncio
    async def test_chat_accepts_user_id(self, async_client):
        """Test that chat endpoint accepts user_id parameter."""
        with patch("src.services.chat_service.ChatService") as mock_service_class:
            mock_service = MagicMock()

            async def mock_stream():
                from src.models.response import StreamChunk
                from uuid import uuid4

                yield StreamChunk(
                    content="Hello",
                    sequence=0,
                    is_final=False,
                    correlation_id=uuid4(),
                )
                yield StreamChunk(
                    content="",
                    sequence=1,
                    is_final=True,
                    correlation_id=uuid4(),
                )

            mock_service.stream_completion = mock_stream
            mock_service_class.return_value = mock_service

            response = await async_client.post(
                "/chat",
                json={
                    "message": "Hello",
                    "user_id": "test-user-123",
                },
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_chat_accepts_conversation_id(self, async_client):
        """Test that chat endpoint accepts conversation_id parameter."""
        with patch("src.services.chat_service.ChatService") as mock_service_class:
            mock_service = MagicMock()

            async def mock_stream():
                from src.models.response import StreamChunk
                from uuid import uuid4

                yield StreamChunk(
                    content="Hi",
                    sequence=0,
                    is_final=False,
                    correlation_id=uuid4(),
                )
                yield StreamChunk(
                    content="",
                    sequence=1,
                    is_final=True,
                    correlation_id=uuid4(),
                )

            mock_service.stream_completion = mock_stream
            mock_service_class.return_value = mock_service

            response = await async_client.post(
                "/chat",
                json={
                    "message": "Hello",
                    "user_id": "test-user",
                    "conversation_id": "12345678-1234-5678-1234-567812345678",
                },
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_chat_rejects_invalid_conversation_id(self, async_client):
        """Test that invalid conversation_id is rejected."""
        response = await async_client.post(
            "/chat",
            json={
                "message": "Hello",
                "conversation_id": "not-a-valid-uuid",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "conversation_id" in data.get("detail", "").lower()


class TestEmptyMemoryStore:
    """Tests for handling empty memory store gracefully."""

    @pytest.mark.asyncio
    async def test_empty_memory_store_no_errors(self, async_client):
        """Test that first-time user with no memories doesn't cause errors."""
        # This tests the graceful degradation when memory store is empty
        with patch("src.services.chat_service.ChatService") as mock_service_class:
            mock_service = MagicMock()
            mock_service._database_available = False

            async def mock_stream():
                from src.models.response import StreamChunk
                from uuid import uuid4

                yield StreamChunk(
                    content="Hello! I'm here to help.",
                    sequence=0,
                    is_final=False,
                    correlation_id=uuid4(),
                )
                yield StreamChunk(
                    content="",
                    sequence=1,
                    is_final=True,
                    correlation_id=uuid4(),
                )

            mock_service.stream_completion = mock_stream
            mock_service_class.return_value = mock_service

            response = await async_client.post(
                "/chat",
                json={
                    "message": "Hi, I'm new here",
                    "user_id": "brand-new-user",
                },
            )

            assert response.status_code == 200
