"""Unit tests for memory browsing API endpoints (T069).

Tests /memories endpoints with mocked asyncpg pool
and dependency overrides for authentication.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

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


def _make_memory_row(
    memory_id=None,
    content="User likes Python",
    mem_type="preference",
    importance=0.8,
    confidence=0.9,
    source_conversation_id=None,
):
    """Create a mock asyncpg Row-like dict for memory items."""
    return {
        "id": memory_id or uuid4(),
        "content": content,
        "type": mem_type,
        "importance": importance,
        "confidence": confidence,
        "source_conversation_id": source_conversation_id,
        "created_at": datetime.now(timezone.utc),
    }


class MockPoolAcquire:
    """Mock for asyncpg pool.acquire() async context manager."""

    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *args):
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def current_user():
    """A pre-built authenticated user."""
    return _make_user(username="alice", display_name="Alice")


@pytest.fixture
def mock_conn():
    """Create a mock asyncpg connection."""
    conn = MagicMock()
    conn.fetchval = AsyncMock()
    conn.fetch = AsyncMock()
    conn.execute = AsyncMock()
    return conn


@pytest.fixture
def mock_pool(mock_conn):
    """Create a mock asyncpg pool that returns mock_conn on acquire."""
    pool = MagicMock()
    pool.acquire.return_value = MockPoolAcquire(mock_conn)
    return pool


@pytest.fixture
def client(current_user, mock_pool):
    """Create a TestClient with lifespan mocked, auth overridden, and pool mocked."""
    with (
        patch("src.database.init_database", new_callable=AsyncMock),
        patch("src.database.run_migrations", new_callable=AsyncMock),
        patch("src.services.redis_service.get_redis", new_callable=AsyncMock),
        patch("src.database.close_database", new_callable=AsyncMock),
        patch("src.services.redis_service.close_redis", new_callable=AsyncMock),
        patch("src.services.memory_write_service.await_pending_writes", new_callable=AsyncMock),
        patch("src.api.memories.get_pool", new_callable=AsyncMock, return_value=mock_pool),
    ):
        from fastapi.testclient import TestClient
        from src.api.dependencies import get_current_user
        from src.main import app

        app.dependency_overrides[get_current_user] = lambda: current_user

        with TestClient(app) as tc:
            yield tc

        app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# GET /memories
# ---------------------------------------------------------------------------

class TestListMemories:
    """Tests for GET /memories."""

    def test_returns_paginated_list(self, client, mock_conn):
        rows = [
            _make_memory_row(content="User likes Python", mem_type="preference"),
            _make_memory_row(content="Meeting on Friday", mem_type="fact"),
        ]
        mock_conn.fetchval.return_value = 2
        mock_conn.fetch.return_value = rows

        response = client.get("/memories")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        assert len(body["items"]) == 2
        assert body["items"][0]["content"] == "User likes Python"
        assert body["items"][1]["content"] == "Meeting on Friday"
        assert body["limit"] == 50
        assert body["offset"] == 0

    def test_filters_by_search_query(self, client, mock_conn):
        rows = [
            _make_memory_row(content="User likes Python", mem_type="preference"),
        ]
        mock_conn.fetchval.return_value = 1
        mock_conn.fetch.return_value = rows

        response = client.get("/memories?q=Python")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert len(body["items"]) == 1
        assert body["items"][0]["content"] == "User likes Python"

    def test_filters_by_type(self, client, mock_conn):
        rows = [
            _make_memory_row(content="Prefers dark mode", mem_type="preference"),
        ]
        mock_conn.fetchval.return_value = 1
        mock_conn.fetch.return_value = rows

        response = client.get("/memories?type=preference")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["type"] == "preference"

    def test_returns_empty_list_when_no_memories(self, client, mock_conn):
        mock_conn.fetchval.return_value = 0
        mock_conn.fetch.return_value = []

        response = client.get("/memories")

        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_user_isolation_scoped_to_current_user(self, client, mock_conn, current_user):
        """Verify that the query includes user_id filtering."""
        mock_conn.fetchval.return_value = 0
        mock_conn.fetch.return_value = []

        response = client.get("/memories")

        assert response.status_code == 200
        # Verify fetchval was called with user_id as the first param
        call_args = mock_conn.fetchval.call_args
        assert str(current_user.id) in call_args.args


# ---------------------------------------------------------------------------
# DELETE /memories/{id}
# ---------------------------------------------------------------------------

class TestDeleteMemory:
    """Tests for DELETE /memories/{id}."""

    def test_returns_204_on_success(self, client, mock_conn):
        memory_id = uuid4()
        mock_conn.execute.return_value = "UPDATE 1"

        response = client.delete(f"/memories/{memory_id}")

        assert response.status_code == 204

    def test_returns_404_when_not_found(self, client, mock_conn):
        memory_id = uuid4()
        mock_conn.execute.return_value = "UPDATE 0"

        response = client.delete(f"/memories/{memory_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
