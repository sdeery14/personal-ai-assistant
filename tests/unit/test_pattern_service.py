"""Unit tests for PatternService."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.services.pattern_service import PatternService


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
    return PatternService()


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


class TestRecordOrUpdatePattern:
    @pytest.mark.asyncio
    async def test_creates_new_pattern(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.fetchrow.return_value = None  # No existing pattern

        with patch("src.services.pattern_service.get_pool", return_value=pool):
            result = await service.record_or_update_pattern(
                user_id=user_id,
                pattern_type="recurring_query",
                description="Asks about weather",
                evidence="User asked about weather in Seattle",
            )

        assert result["occurrence_count"] == 1
        assert result["threshold_reached"] is False
        assert "pattern_id" in result
        conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_updates_existing_pattern(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        pattern_id = uuid4()
        conn.fetchrow.return_value = {
            "id": pattern_id,
            "occurrence_count": 2,
            "evidence": json.dumps([{"date": "2026-01-01", "context": "old evidence"}]),
            "confidence": 0.5,
        }

        with patch("src.services.pattern_service.get_pool", return_value=pool):
            result = await service.record_or_update_pattern(
                user_id=user_id,
                pattern_type="recurring_query",
                description="Asks about weather",
                evidence="Asked about weather again",
                confidence=0.7,
            )

        assert result["occurrence_count"] == 3
        assert result["pattern_id"] == str(pattern_id)
        assert result["threshold_reached"] is True  # 3 >= default threshold of 3
        conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_increments_occurrence_count(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.fetchrow.return_value = {
            "id": uuid4(),
            "occurrence_count": 1,
            "evidence": json.dumps([]),
            "confidence": 0.4,
        }

        with patch("src.services.pattern_service.get_pool", return_value=pool):
            result = await service.record_or_update_pattern(
                user_id=user_id,
                pattern_type="topic_interest",
                description="Interested in Python",
                evidence="Mentioned Python project",
                confidence=0.6,
            )

        assert result["occurrence_count"] == 2
        assert result["threshold_reached"] is False

    @pytest.mark.asyncio
    async def test_takes_max_confidence(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.fetchrow.return_value = {
            "id": uuid4(),
            "occurrence_count": 1,
            "evidence": json.dumps([]),
            "confidence": 0.8,
        }

        with patch("src.services.pattern_service.get_pool", return_value=pool):
            await service.record_or_update_pattern(
                user_id=user_id,
                pattern_type="recurring_query",
                description="Asks about weather",
                evidence="test",
                confidence=0.5,
            )

        # Should keep the higher confidence (0.8)
        # call_args[0] = (sql, new_count, evidence, now, confidence, suggested_action, id)
        call_args = conn.execute.call_args[0]
        assert call_args[4] == 0.8  # new_confidence = max(0.8, 0.5)

    @pytest.mark.asyncio
    async def test_appends_evidence(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        old_evidence = [{"date": "2026-01-01", "context": "first observation"}]
        conn.fetchrow.return_value = {
            "id": uuid4(),
            "occurrence_count": 1,
            "evidence": json.dumps(old_evidence),
            "confidence": 0.5,
        }

        with patch("src.services.pattern_service.get_pool", return_value=pool):
            await service.record_or_update_pattern(
                user_id=user_id,
                pattern_type="recurring_query",
                description="Asks about weather",
                evidence="second observation",
            )

        # call_args[0] = (sql, new_count, evidence, now, confidence, suggested_action, id)
        call_args = conn.execute.call_args[0]
        new_evidence = json.loads(call_args[2])
        assert len(new_evidence) == 2
        assert new_evidence[1]["context"] == "second observation"


class TestListPatterns:
    @pytest.mark.asyncio
    async def test_returns_patterns(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.fetch.return_value = [
            {
                "id": uuid4(),
                "pattern_type": "recurring_query",
                "description": "Weather questions",
                "occurrence_count": 5,
                "first_seen_at": datetime.now(timezone.utc),
                "last_seen_at": datetime.now(timezone.utc),
                "acted_on": False,
                "suggested_action": "Schedule weather",
                "confidence": 0.8,
            }
        ]

        with patch("src.services.pattern_service.get_pool", return_value=pool):
            patterns = await service.list_patterns(user_id)

        assert len(patterns) == 1
        assert patterns[0]["description"] == "Weather questions"

    @pytest.mark.asyncio
    async def test_filters_by_min_occurrences(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.fetch.return_value = []

        with patch("src.services.pattern_service.get_pool", return_value=pool):
            patterns = await service.list_patterns(user_id, min_occurrences=3)

        assert patterns == []
        # Verify the min_occurrences was passed to the query
        call_args = conn.fetch.call_args[0]
        assert call_args[2] == 3  # $2 parameter

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_patterns(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.fetch.return_value = []

        with patch("src.services.pattern_service.get_pool", return_value=pool):
            patterns = await service.list_patterns(user_id)

        assert patterns == []


class TestGetActionablePatterns:
    @pytest.mark.asyncio
    async def test_returns_actionable_patterns(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.fetch.return_value = [
            {
                "id": uuid4(),
                "pattern_type": "recurring_query",
                "description": "Checks weather daily",
                "occurrence_count": 5,
                "suggested_action": "Schedule daily weather briefing",
                "confidence": 0.8,
            }
        ]

        with patch("src.services.pattern_service.get_pool", return_value=pool):
            actionable = await service.get_actionable_patterns(user_id)

        assert len(actionable) == 1
        assert actionable[0]["suggested_action"] == "Schedule daily weather briefing"

    @pytest.mark.asyncio
    async def test_returns_empty_when_all_acted_on(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.fetch.return_value = []  # Query filters acted_on = FALSE

        with patch("src.services.pattern_service.get_pool", return_value=pool):
            actionable = await service.get_actionable_patterns(user_id)

        assert actionable == []
