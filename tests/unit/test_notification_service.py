"""Unit tests for NotificationService."""

import json
from datetime import datetime, time, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.models.notification import (
    DeliveryChannel,
    NotificationPreferences,
    NotificationPreferencesUpdate,
    NotificationType,
)
from src.services.notification_service import NotificationService


class MockPoolAcquire:
    """Mock async context manager for pool.acquire()."""

    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def mock_pool():
    """Create mock database pool with proper async context manager."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock()
    mock_conn.fetchval = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])

    mock_p = MagicMock()
    mock_p.acquire.return_value = MockPoolAcquire(mock_conn)
    return mock_p, mock_conn


@pytest.fixture
def service():
    return NotificationService()


class TestCreateNotification:
    @pytest.mark.asyncio
    async def test_creates_notification_and_returns_model(self, service, mock_pool):
        pool, conn = mock_pool
        user_id = str(uuid4())

        with patch("src.services.notification_service.get_pool", return_value=pool):
            result = await service.create_notification(
                user_id=user_id,
                message="Don't forget your dentist appointment",
                notification_type="reminder",
                conversation_id=str(uuid4()),
            )

        assert result.message == "Don't forget your dentist appointment"
        assert result.type == NotificationType.REMINDER
        assert result.is_read is False
        assert result.user_id == UUID(user_id)
        conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_notification_with_defaults(self, service, mock_pool):
        pool, conn = mock_pool
        user_id = str(uuid4())

        with patch("src.services.notification_service.get_pool", return_value=pool):
            result = await service.create_notification(
                user_id=user_id,
                message="Some info",
            )

        assert result.type == NotificationType.INFO
        assert result.conversation_id is None


class TestListNotifications:
    @pytest.mark.asyncio
    async def test_list_returns_paginated_results(self, service, mock_pool):
        pool, conn = mock_pool
        user_id = str(uuid4())
        notification_id = uuid4()

        conn.fetchval.return_value = 1
        conn.fetch.return_value = [
            {
                "id": notification_id,
                "user_id": UUID(user_id),
                "conversation_id": None,
                "message": "Test",
                "type": "info",
                "is_read": False,
                "created_at": datetime.now(timezone.utc),
            }
        ]

        with patch("src.services.notification_service.get_pool", return_value=pool):
            notifications, total = await service.list_notifications(user_id)

        assert total == 1
        assert len(notifications) == 1
        assert notifications[0].id == notification_id

    @pytest.mark.asyncio
    async def test_list_with_type_filter(self, service, mock_pool):
        pool, conn = mock_pool
        user_id = str(uuid4())
        conn.fetchval.return_value = 0
        conn.fetch.return_value = []

        with patch("src.services.notification_service.get_pool", return_value=pool):
            _, total = await service.list_notifications(
                user_id, type_filter="warning"
            )

        assert total == 0
        # Verify the type filter was included in the query
        call_args = conn.fetchval.call_args
        assert "type = $" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_list_with_is_read_filter(self, service, mock_pool):
        pool, conn = mock_pool
        user_id = str(uuid4())
        conn.fetchval.return_value = 0
        conn.fetch.return_value = []

        with patch("src.services.notification_service.get_pool", return_value=pool):
            _, total = await service.list_notifications(
                user_id, is_read_filter=False
            )

        assert total == 0
        call_args = conn.fetchval.call_args
        assert "is_read = $" in call_args[0][0]


class TestGetUnreadCount:
    @pytest.mark.asyncio
    async def test_returns_count(self, service, mock_pool):
        pool, conn = mock_pool
        conn.fetchval.return_value = 5

        with patch("src.services.notification_service.get_pool", return_value=pool):
            count = await service.get_unread_count(str(uuid4()))

        assert count == 5

    @pytest.mark.asyncio
    async def test_returns_zero_when_none(self, service, mock_pool):
        pool, conn = mock_pool
        conn.fetchval.return_value = None

        with patch("src.services.notification_service.get_pool", return_value=pool):
            count = await service.get_unread_count(str(uuid4()))

        assert count == 0


class TestMarkAsRead:
    @pytest.mark.asyncio
    async def test_mark_as_read_returns_updated_notification(self, service, mock_pool):
        pool, conn = mock_pool
        notification_id = uuid4()
        user_id = str(uuid4())

        conn.fetchrow.return_value = {
            "id": notification_id,
            "user_id": UUID(user_id),
            "conversation_id": None,
            "message": "Test",
            "type": "info",
            "is_read": True,
            "created_at": datetime.now(timezone.utc),
        }

        with patch("src.services.notification_service.get_pool", return_value=pool):
            result = await service.mark_as_read(notification_id, user_id)

        assert result is not None
        assert result.is_read is True

    @pytest.mark.asyncio
    async def test_mark_as_read_returns_none_for_wrong_user(self, service, mock_pool):
        pool, conn = mock_pool
        conn.fetchrow.return_value = None

        with patch("src.services.notification_service.get_pool", return_value=pool):
            result = await service.mark_as_read(uuid4(), str(uuid4()))

        assert result is None


class TestMarkAllAsRead:
    @pytest.mark.asyncio
    async def test_returns_updated_count(self, service, mock_pool):
        pool, conn = mock_pool
        conn.execute.return_value = "UPDATE 3"

        with patch("src.services.notification_service.get_pool", return_value=pool):
            count = await service.mark_all_as_read(str(uuid4()))

        assert count == 3


class TestDismissNotification:
    @pytest.mark.asyncio
    async def test_dismiss_returns_true(self, service, mock_pool):
        pool, conn = mock_pool
        conn.execute.return_value = "UPDATE 1"

        with patch("src.services.notification_service.get_pool", return_value=pool):
            result = await service.dismiss_notification(uuid4(), str(uuid4()))

        assert result is True

    @pytest.mark.asyncio
    async def test_dismiss_returns_false_for_wrong_user(self, service, mock_pool):
        pool, conn = mock_pool
        conn.execute.return_value = "UPDATE 0"

        with patch("src.services.notification_service.get_pool", return_value=pool):
            result = await service.dismiss_notification(uuid4(), str(uuid4()))

        assert result is False


class TestGetPreferences:
    @pytest.mark.asyncio
    async def test_returns_defaults_when_no_row(self, service, mock_pool):
        pool, conn = mock_pool
        conn.fetchrow.return_value = None

        with patch("src.services.notification_service.get_pool", return_value=pool):
            prefs = await service.get_preferences(str(uuid4()))

        assert prefs.delivery_channel == DeliveryChannel.IN_APP
        assert prefs.quiet_hours_start is None
        assert prefs.quiet_hours_end is None

    @pytest.mark.asyncio
    async def test_returns_saved_preferences(self, service, mock_pool):
        pool, conn = mock_pool
        conn.fetchrow.return_value = {
            "delivery_channel": "both",
            "quiet_hours_start": time(22, 0),
            "quiet_hours_end": time(7, 0),
            "quiet_hours_timezone": "America/New_York",
        }

        with patch("src.services.notification_service.get_pool", return_value=pool):
            prefs = await service.get_preferences(str(uuid4()))

        assert prefs.delivery_channel == DeliveryChannel.BOTH
        assert prefs.quiet_hours_start == time(22, 0)
        assert prefs.quiet_hours_end == time(7, 0)
        assert prefs.quiet_hours_timezone == "America/New_York"


class TestUpdatePreferences:
    @pytest.mark.asyncio
    async def test_upsert_creates_preferences(self, service, mock_pool):
        pool, conn = mock_pool
        conn.fetchrow.return_value = {
            "delivery_channel": "email",
            "quiet_hours_start": None,
            "quiet_hours_end": None,
            "quiet_hours_timezone": "UTC",
        }

        update = NotificationPreferencesUpdate(
            delivery_channel=DeliveryChannel.EMAIL
        )

        with patch("src.services.notification_service.get_pool", return_value=pool):
            prefs = await service.update_preferences(str(uuid4()), update)

        assert prefs.delivery_channel == DeliveryChannel.EMAIL
        conn.fetchrow.assert_called_once()


class TestCheckRateLimit:
    @pytest.mark.asyncio
    async def test_returns_true_under_limit(self, service):
        mock_redis = AsyncMock()
        mock_redis.get.return_value = b"5"

        with patch("src.services.notification_service.get_settings") as mock_settings:
            mock_settings.return_value.notification_rate_limit_per_hour = 10
            mock_settings.return_value.redis_url = "redis://localhost:6379/0"
            with patch("redis.asyncio.from_url", return_value=mock_redis):
                result = await service.check_rate_limit(str(uuid4()))

        assert result is True
        mock_redis.incr.assert_called_once()
        mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_over_limit(self, service):
        mock_redis = AsyncMock()
        mock_redis.get.return_value = b"10"

        with patch("src.services.notification_service.get_settings") as mock_settings:
            mock_settings.return_value.notification_rate_limit_per_hour = 10
            mock_settings.return_value.redis_url = "redis://localhost:6379/0"
            with patch("redis.asyncio.from_url", return_value=mock_redis):
                result = await service.check_rate_limit(str(uuid4()))

        assert result is False
