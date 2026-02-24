"""Unit tests for ProactiveService."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.services.proactive_service import ProactiveService


class MockPoolAcquire:
    """Mock async context manager for pool.acquire()."""

    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *args):
        pass


@pytest.fixture
def service():
    return ProactiveService()


@pytest.fixture
def user_id():
    return str(uuid4())


@pytest.fixture
def mock_pool():
    """Create mock database pool with proper async context manager."""
    conn = AsyncMock()
    conn.fetchrow = AsyncMock()
    conn.fetchval = AsyncMock()
    conn.execute = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])

    pool = MagicMock()
    pool.acquire.return_value = MockPoolAcquire(conn)
    return pool, conn


def _settings_row(is_onboarded=False, global_level=0.7, suppressed=None, boosted=None, override=None):
    """Helper to create a settings row dict."""
    return {
        "id": uuid4(),
        "user_id": uuid4(),
        "global_level": global_level,
        "suppressed_types": json.dumps(suppressed or []),
        "boosted_types": json.dumps(boosted or []),
        "user_override": override,
        "is_onboarded": is_onboarded,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


class TestGetOrCreateSettings:
    @pytest.mark.asyncio
    async def test_returns_existing_settings(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.fetchrow.return_value = _settings_row()

        with patch("src.services.proactive_service.get_pool", return_value=pool):
            result = await service.get_or_create_settings(user_id)

        assert result["global_level"] == 0.7
        assert result["is_onboarded"] is False
        conn.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_new_for_missing_user(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        # First SELECT returns None, then INSERT returns new row
        conn.fetchrow.side_effect = [None, _settings_row()]

        with patch("src.services.proactive_service.get_pool", return_value=pool):
            result = await service.get_or_create_settings(user_id)

        assert result["global_level"] == 0.7
        assert conn.fetchrow.call_count == 2


class TestIsOnboarded:
    @pytest.mark.asyncio
    async def test_returns_false_for_new_user(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.fetchrow.return_value = _settings_row(is_onboarded=False)

        with patch("src.services.proactive_service.get_pool", return_value=pool):
            assert await service.is_onboarded(user_id) is False

    @pytest.mark.asyncio
    async def test_returns_true_for_onboarded_user(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.fetchrow.return_value = _settings_row(is_onboarded=True)

        with patch("src.services.proactive_service.get_pool", return_value=pool):
            assert await service.is_onboarded(user_id) is True


class TestMarkOnboarded:
    @pytest.mark.asyncio
    async def test_sets_is_onboarded_true(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        # get_or_create_settings call inside update_settings, then update
        conn.fetchrow.side_effect = [
            _settings_row(is_onboarded=False),
            _settings_row(is_onboarded=True),
        ]

        with patch("src.services.proactive_service.get_pool", return_value=pool):
            await service.mark_onboarded(user_id)

        assert conn.fetchrow.call_count == 2


class TestUpdateSettings:
    @pytest.mark.asyncio
    async def test_updates_global_level(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.fetchrow.side_effect = [
            _settings_row(),
            _settings_row(global_level=0.9, override="more"),
        ]

        with patch("src.services.proactive_service.get_pool", return_value=pool):
            result = await service.update_settings(user_id, global_level=0.9, user_override="more")

        assert result["global_level"] == 0.9
        assert result["user_override"] == "more"

    @pytest.mark.asyncio
    async def test_ignores_invalid_fields(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        # get_or_create returns settings, then no update happens (no valid fields)
        conn.fetchrow.side_effect = [
            _settings_row(),  # get_or_create
            _settings_row(),  # get_or_create (second call in fallback)
        ]

        with patch("src.services.proactive_service.get_pool", return_value=pool):
            result = await service.update_settings(user_id, invalid_field="value")

        assert result["global_level"] == 0.7


class TestGetUserProfile:
    @pytest.mark.asyncio
    async def test_aggregates_profile_data(self, service, user_id, mock_pool):
        pool, conn = mock_pool

        # Memory items
        conn.fetch.side_effect = [
            [
                {"content": "Software engineer", "memory_type": "fact", "confidence": 0.95},
                {"content": "Prefers dark mode", "memory_type": "preference", "confidence": 0.9},
            ],
            # Patterns
            [{"description": "Asks about weather mornings", "occurrence_count": 5, "acted_on": True}],
            # Relationships
            [{"entity": "Sarah", "relationship": "WORKS_WITH", "mentions": 8}],
            # Engagement stats
            [{"suggestion_type": "meeting_prep", "count": 3}],
        ]

        conn.fetchrow.return_value = _settings_row(
            is_onboarded=True,
            suppressed=["weather_briefing"],
        )

        with patch("src.services.proactive_service.get_pool", return_value=pool):
            profile = await service.get_user_profile(user_id)

        assert len(profile["facts"]) == 1
        assert profile["facts"][0]["content"] == "Software engineer"
        assert len(profile["preferences"]) == 1
        assert profile["preferences"][0]["content"] == "Prefers dark mode"
        assert len(profile["patterns"]) == 1
        assert len(profile["key_relationships"]) == 1
        assert profile["proactiveness"]["global_level"] == 0.7

    @pytest.mark.asyncio
    async def test_handles_empty_data(self, service, user_id, mock_pool):
        pool, conn = mock_pool

        conn.fetch.side_effect = [[], [], [], []]
        conn.fetchrow.return_value = _settings_row()

        with patch("src.services.proactive_service.get_pool", return_value=pool):
            profile = await service.get_user_profile(user_id)

        assert profile["facts"] == []
        assert profile["preferences"] == []
        assert profile["patterns"] == []
        assert profile["key_relationships"] == []
