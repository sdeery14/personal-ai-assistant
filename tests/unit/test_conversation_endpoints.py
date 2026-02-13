"""Unit tests for conversation API endpoints (T051).

Tests /conversations CRUD endpoints with mocked ConversationService
and dependency overrides for authentication.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.models.memory import Conversation, Message, MessageRole
from src.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(
    user_id=None,
    username="testuser",
    display_name="Test User",
    is_admin=False,
    is_active=True,
):
    """Create a User model for test assertions."""
    now = datetime.now(timezone.utc)
    return User(
        id=user_id or uuid4(),
        username=username,
        display_name=display_name,
        is_admin=is_admin,
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )


def _make_conversation(conv_id=None, user_id=None, title=None):
    """Create a Conversation model for test data."""
    now = datetime.now(timezone.utc)
    return Conversation(
        id=conv_id or uuid4(),
        user_id=user_id or str(uuid4()),
        title=title,
        created_at=now,
        updated_at=now,
    )


def _make_message(msg_id=None, conversation_id=None, role="user", content="Hello"):
    """Create a Message model for test data."""
    now = datetime.now(timezone.utc)
    return Message(
        id=msg_id or uuid4(),
        conversation_id=conversation_id or uuid4(),
        role=MessageRole(role),
        content=content,
        correlation_id=uuid4(),
        created_at=now,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def current_user():
    """A pre-built authenticated user."""
    return _make_user(username="alice", display_name="Alice")


@pytest.fixture
def client(current_user):
    """Create a TestClient with lifespan mocked and auth overridden.

    All conversation endpoints are authenticated as current_user.
    """
    with (
        patch("src.database.init_database", new_callable=AsyncMock),
        patch("src.database.run_migrations", new_callable=AsyncMock),
        patch("src.services.redis_service.get_redis", new_callable=AsyncMock),
        patch("src.database.close_database", new_callable=AsyncMock),
        patch("src.services.redis_service.close_redis", new_callable=AsyncMock),
        patch("src.services.memory_write_service.await_pending_writes", new_callable=AsyncMock),
    ):
        from fastapi.testclient import TestClient
        from src.api.dependencies import get_current_user
        from src.main import app

        app.dependency_overrides[get_current_user] = lambda: current_user

        with TestClient(app) as tc:
            yield tc

        app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# GET /conversations
# ---------------------------------------------------------------------------

class TestListConversations:
    """Tests for GET /conversations."""

    def test_returns_paginated_list(self, client, current_user):
        items = [
            {
                "id": str(uuid4()),
                "title": "Chat about Python",
                "message_preview": "How do I use asyncio?",
                "message_count": 5,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": str(uuid4()),
                "title": "Weather discussion",
                "message_preview": "What's the weather?",
                "message_count": 2,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        ]

        with patch("src.api.conversations.ConversationService") as MockService:
            svc = MockService.return_value
            svc.list_conversations = AsyncMock(return_value=(items, 2))

            response = client.get("/conversations")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        assert len(body["items"]) == 2
        assert body["items"][0]["title"] == "Chat about Python"
        assert body["items"][1]["title"] == "Weather discussion"
        assert body["limit"] == 50
        assert body["offset"] == 0

    def test_returns_empty_list_for_new_user(self, client, current_user):
        with patch("src.api.conversations.ConversationService") as MockService:
            svc = MockService.return_value
            svc.list_conversations = AsyncMock(return_value=([], 0))

            response = client.get("/conversations")

        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0


# ---------------------------------------------------------------------------
# GET /conversations/{id}
# ---------------------------------------------------------------------------

class TestGetConversation:
    """Tests for GET /conversations/{id}."""

    def test_returns_conversation_with_messages(self, client, current_user):
        conv_id = uuid4()
        conversation = _make_conversation(
            conv_id=conv_id,
            user_id=str(current_user.id),
            title="Test Chat",
        )
        messages = [
            _make_message(
                conversation_id=conv_id,
                role="user",
                content="Hello there",
            ),
            _make_message(
                conversation_id=conv_id,
                role="assistant",
                content="Hi! How can I help?",
            ),
        ]

        with patch("src.api.conversations.ConversationService") as MockService:
            svc = MockService.return_value
            svc.get_conversation = AsyncMock(return_value=conversation)
            svc.get_conversation_messages = AsyncMock(return_value=messages)

            response = client.get(f"/conversations/{conv_id}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(conv_id)
        assert body["title"] == "Test Chat"
        assert len(body["messages"]) == 2
        assert body["messages"][0]["role"] == "user"
        assert body["messages"][0]["content"] == "Hello there"
        assert body["messages"][1]["role"] == "assistant"
        assert body["messages"][1]["content"] == "Hi! How can I help?"

    def test_returns_404_for_nonexistent_conversation(self, client, current_user):
        nonexistent_id = uuid4()

        with patch("src.api.conversations.ConversationService") as MockService:
            svc = MockService.return_value
            svc.get_conversation = AsyncMock(return_value=None)

            response = client.get(f"/conversations/{nonexistent_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_returns_404_when_accessing_other_users_conversation(self, client, current_user):
        """User isolation: service returns None when user_id doesn't match."""
        other_conv_id = uuid4()

        with patch("src.api.conversations.ConversationService") as MockService:
            svc = MockService.return_value
            # Service returns None because user_id filter excludes this conversation
            svc.get_conversation = AsyncMock(return_value=None)

            response = client.get(f"/conversations/{other_conv_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# PATCH /conversations/{id}
# ---------------------------------------------------------------------------

class TestUpdateConversation:
    """Tests for PATCH /conversations/{id}."""

    def test_updates_title(self, client, current_user):
        conv_id = uuid4()
        updated = {
            "id": str(conv_id),
            "title": "Renamed Chat",
            "message_preview": "Hello",
            "message_count": 3,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        with patch("src.api.conversations.ConversationService") as MockService:
            svc = MockService.return_value
            svc.update_conversation_title = AsyncMock(return_value=updated)

            response = client.patch(
                f"/conversations/{conv_id}",
                json={"title": "Renamed Chat"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["title"] == "Renamed Chat"

    def test_returns_404_for_nonexistent_conversation(self, client, current_user):
        nonexistent_id = uuid4()

        with patch("src.api.conversations.ConversationService") as MockService:
            svc = MockService.return_value
            svc.update_conversation_title = AsyncMock(return_value=None)

            response = client.patch(
                f"/conversations/{nonexistent_id}",
                json={"title": "New Title"},
            )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# DELETE /conversations/{id}
# ---------------------------------------------------------------------------

class TestDeleteConversation:
    """Tests for DELETE /conversations/{id}."""

    def test_deletes_conversation(self, client, current_user):
        conv_id = uuid4()

        with patch("src.api.conversations.ConversationService") as MockService:
            svc = MockService.return_value
            svc.delete_conversation = AsyncMock(return_value=True)

            response = client.delete(f"/conversations/{conv_id}")

        assert response.status_code == 204

    def test_returns_404_for_nonexistent_conversation(self, client, current_user):
        nonexistent_id = uuid4()

        with patch("src.api.conversations.ConversationService") as MockService:
            svc = MockService.return_value
            svc.delete_conversation = AsyncMock(return_value=False)

            response = client.delete(f"/conversations/{nonexistent_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
