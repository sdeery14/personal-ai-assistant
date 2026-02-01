"""Unit tests for conversation service."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.conversation_service import ConversationService


@pytest.fixture
def mock_embedding_service():
    """Create mock embedding service."""
    mock = MagicMock()
    mock.get_embedding = AsyncMock(return_value=[0.1] * 1536)
    return mock


@pytest.fixture
def conversation_service(mock_embedding_service):
    """Create conversation service instance for testing."""
    service = ConversationService()
    service.embedding_service = mock_embedding_service
    return service


@pytest.fixture
def mock_pool():
    """Create mock database pool with proper async context manager."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])

    # Create a context manager mock
    class MockPoolAcquire:
        async def __aenter__(self):
            return mock_conn

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_pool = MagicMock()
    mock_pool.acquire.return_value = MockPoolAcquire()

    return mock_pool, mock_conn


class TestGetOrCreateConversation:
    """Tests for conversation creation and retrieval."""

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_creates_new(
        self, conversation_service, mock_pool
    ):
        """Test that new conversation is created when none exists."""
        pool, conn = mock_pool
        conn.fetchrow.return_value = None  # No existing conversation

        with patch("src.services.conversation_service.get_pool", return_value=pool):
            result = await conversation_service.get_or_create_conversation(
                user_id="test-user",
                conversation_id=None,
            )

            assert result is not None
            assert result.user_id == "test-user"
            conn.execute.assert_called()  # INSERT was called

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_returns_existing(
        self, conversation_service, mock_pool
    ):
        """Test that existing conversation is returned when found."""
        pool, conn = mock_pool
        conv_id = uuid4()
        now = datetime.now(timezone.utc)

        conn.fetchrow.return_value = {
            "id": conv_id,
            "user_id": "test-user",
            "title": "Test Conversation",
            "created_at": now,
            "updated_at": now,
        }

        with patch("src.services.conversation_service.get_pool", return_value=pool):
            result = await conversation_service.get_or_create_conversation(
                user_id="test-user",
                conversation_id=str(conv_id),
            )

            assert result is not None
            assert result.id == conv_id
            assert result.title == "Test Conversation"


class TestAddMessage:
    """Tests for message creation."""

    @pytest.mark.asyncio
    async def test_add_message_persists_correctly(
        self, conversation_service, mock_pool
    ):
        """Test that message is persisted with all fields."""
        pool, conn = mock_pool
        conv_id = uuid4()
        corr_id = uuid4()

        with patch("src.services.conversation_service.get_pool", return_value=pool):
            result = await conversation_service.add_message(
                conversation_id=conv_id,
                role="user",
                content="Test message",
                correlation_id=corr_id,
            )

            assert result is not None
            assert result.conversation_id == conv_id
            assert result.role.value == "user"
            assert result.content == "Test message"
            assert result.correlation_id == corr_id

            # Verify INSERT was called
            conn.execute.assert_called()

    @pytest.mark.asyncio
    async def test_add_message_without_embedding(
        self, conversation_service, mock_pool
    ):
        """Test adding message without generating embedding."""
        pool, conn = mock_pool
        conv_id = uuid4()
        corr_id = uuid4()

        # Reset the mock to track calls
        conversation_service.embedding_service.get_embedding.reset_mock()

        with patch("src.services.conversation_service.get_pool", return_value=pool):
            result = await conversation_service.add_message(
                conversation_id=conv_id,
                role="assistant",
                content="Test response",
                correlation_id=corr_id,
                generate_embedding=False,
            )

            assert result is not None
            assert result.embedding is None
            conversation_service.embedding_service.get_embedding.assert_not_called()


class TestDatabaseErrors:
    """Tests for database error handling."""

    @pytest.mark.asyncio
    async def test_database_unavailable_raises_exception(self, conversation_service):
        """Test that database errors are raised (fail closed)."""
        with patch(
            "src.services.conversation_service.get_pool",
            side_effect=RuntimeError("Database pool not initialized"),
        ):
            with pytest.raises(RuntimeError):
                await conversation_service.get_or_create_conversation(
                    user_id="test-user",
                    conversation_id=None,
                )
