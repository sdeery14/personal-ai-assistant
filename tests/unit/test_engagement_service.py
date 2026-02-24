"""Unit tests for EngagementService."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.services.engagement_service import EngagementService, SUPPRESSION_THRESHOLD, BOOST_THRESHOLD


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
    return EngagementService()


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


class TestRecordEvent:
    @pytest.mark.asyncio
    async def test_records_dismissed_event(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.execute.return_value = None
        # _check_thresholds: dismiss count below threshold
        conn.fetchval.return_value = 1

        with patch("src.services.engagement_service.get_pool", return_value=pool):
            result = await service.record_event(
                user_id=user_id,
                suggestion_type="weather_briefing",
                action="dismissed",
                source="conversation",
            )

        assert result["suggestion_type"] == "weather_briefing"
        assert result["action"] == "dismissed"
        assert "event_id" in result

    @pytest.mark.asyncio
    async def test_records_engaged_event_with_context(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.execute.return_value = None
        conn.fetchval.return_value = 1

        context = {"suggestion_text": "Check weather?", "pattern_id": str(uuid4())}

        with patch("src.services.engagement_service.get_pool", return_value=pool):
            result = await service.record_event(
                user_id=user_id,
                suggestion_type="weather_briefing",
                action="engaged",
                source="notification",
                context=context,
            )

        assert result["action"] == "engaged"


class TestSuppressionThreshold:
    @pytest.mark.asyncio
    async def test_suppresses_after_threshold_dismissals(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.execute.return_value = None

        # _check_thresholds: dismiss count at threshold, then current suppressed_types
        conn.fetchval.side_effect = [
            SUPPRESSION_THRESHOLD,  # dismiss count
            json.dumps([]),  # current suppressed_types
        ]

        with patch("src.services.engagement_service.get_pool", return_value=pool):
            await service.record_event(
                user_id=user_id,
                suggestion_type="weather_briefing",
                action="dismissed",
                source="conversation",
            )

        # insert + update suppressed_types
        assert conn.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_no_suppression_below_threshold(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.execute.return_value = None
        conn.fetchval.return_value = SUPPRESSION_THRESHOLD - 1

        with patch("src.services.engagement_service.get_pool", return_value=pool):
            await service.record_event(
                user_id=user_id,
                suggestion_type="weather_briefing",
                action="dismissed",
                source="conversation",
            )

        # Only the insert, no update
        conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_duplicate_suppression(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.execute.return_value = None

        conn.fetchval.side_effect = [
            SUPPRESSION_THRESHOLD,  # dismiss count at threshold
            json.dumps(["weather_briefing"]),  # already suppressed
        ]

        with patch("src.services.engagement_service.get_pool", return_value=pool):
            await service.record_event(
                user_id=user_id,
                suggestion_type="weather_briefing",
                action="dismissed",
                source="conversation",
            )

        # Only the insert, no update (already suppressed)
        conn.execute.assert_called_once()


class TestBoostThreshold:
    @pytest.mark.asyncio
    async def test_boosts_after_threshold_engagements(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.execute.return_value = None

        conn.fetchval.side_effect = [
            BOOST_THRESHOLD,  # engage count
            json.dumps([]),  # current boosted_types
        ]

        with patch("src.services.engagement_service.get_pool", return_value=pool):
            await service.record_event(
                user_id=user_id,
                suggestion_type="meeting_prep",
                action="engaged",
                source="conversation",
            )

        # insert + update boosted_types
        assert conn.execute.call_count == 2


class TestEngagementStats:
    @pytest.mark.asyncio
    async def test_returns_stats(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.fetchval.side_effect = [5, 2]

        with patch("src.services.engagement_service.get_pool", return_value=pool):
            stats = await service.get_engagement_stats(user_id)

        assert stats["engaged"] == 5
        assert stats["dismissed"] == 2
        assert stats["total"] == 7
        assert stats["engagement_rate"] == 0.71

    @pytest.mark.asyncio
    async def test_returns_stats_by_type(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.fetchval.side_effect = [3, 1]

        with patch("src.services.engagement_service.get_pool", return_value=pool):
            stats = await service.get_engagement_stats(user_id, suggestion_type="weather_briefing")

        assert stats["engaged"] == 3
        assert stats["total"] == 4
        assert stats["engagement_rate"] == 0.75

    @pytest.mark.asyncio
    async def test_handles_no_events(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.fetchval.side_effect = [0, 0]

        with patch("src.services.engagement_service.get_pool", return_value=pool):
            stats = await service.get_engagement_stats(user_id)

        assert stats["total"] == 0
        assert stats["engagement_rate"] == 0.0


class TestCheckSuppression:
    @pytest.mark.asyncio
    async def test_true_for_suppressed_type(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.fetchval.return_value = json.dumps(["weather_briefing", "daily_summary"])

        with patch("src.services.engagement_service.get_pool", return_value=pool):
            assert await service.check_suppression(user_id, "weather_briefing") is True

    @pytest.mark.asyncio
    async def test_false_for_non_suppressed_type(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.fetchval.return_value = json.dumps(["weather_briefing"])

        with patch("src.services.engagement_service.get_pool", return_value=pool):
            assert await service.check_suppression(user_id, "meeting_prep") is False

    @pytest.mark.asyncio
    async def test_false_when_no_settings(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.fetchval.return_value = None

        with patch("src.services.engagement_service.get_pool", return_value=pool):
            assert await service.check_suppression(user_id, "weather_briefing") is False


class TestCheckBoost:
    @pytest.mark.asyncio
    async def test_true_for_boosted_type(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.fetchval.return_value = json.dumps(["meeting_prep"])

        with patch("src.services.engagement_service.get_pool", return_value=pool):
            assert await service.check_boost(user_id, "meeting_prep") is True
