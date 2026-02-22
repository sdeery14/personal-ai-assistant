"""Unit tests for EmailService (T033)."""

from datetime import datetime, time, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.models.notification import (
    DeliveryChannel,
    Notification,
    NotificationPreferences,
    NotificationType,
)
from src.services.email_service import EmailService


class MockPoolAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *args):
        pass


@pytest.fixture
def service():
    return EmailService()


@pytest.fixture
def mock_pool():
    conn = AsyncMock()
    pool = MagicMock()
    pool.acquire.return_value = MockPoolAcquire(conn)
    return pool, conn


def _make_notification(**kwargs):
    defaults = {
        "id": uuid4(),
        "user_id": uuid4(),
        "message": "Test notification",
        "type": NotificationType.INFO,
        "is_read": False,
        "conversation_id": None,
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    return Notification(**defaults)


class TestSendNotificationEmail:
    @pytest.mark.asyncio
    async def test_sends_email_successfully(self, service):
        notification = _make_notification()

        with patch("src.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value.notification_email_from = "test@example.com"
            mock_settings.return_value.notification_smtp_host = "smtp.example.com"
            mock_settings.return_value.notification_smtp_port = 587
            mock_settings.return_value.notification_smtp_username = "user"
            mock_settings.return_value.notification_smtp_password = "pass"
            mock_settings.return_value.notification_smtp_use_tls = True

            with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
                result = await service.send_notification_email(
                    "user@example.com", notification
                )

        assert result is True
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_on_failure(self, service):
        notification = _make_notification()

        with patch("src.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value.notification_email_from = "test@example.com"
            mock_settings.return_value.notification_smtp_host = "smtp.example.com"
            mock_settings.return_value.notification_smtp_port = 587
            mock_settings.return_value.notification_smtp_username = ""
            mock_settings.return_value.notification_smtp_password = ""
            mock_settings.return_value.notification_smtp_use_tls = True

            with patch(
                "aiosmtplib.send",
                new_callable=AsyncMock,
                side_effect=Exception("SMTP connection failed"),
            ):
                result = await service.send_notification_email(
                    "user@example.com", notification
                )

        assert result is False


def _mock_now(hour, minute=0):
    """Create a mock datetime.now() return value with a working .time() method."""
    mock_now = MagicMock()
    mock_now.time.return_value = time(hour, minute)
    return mock_now


class TestIsInQuietHours:
    def test_returns_false_when_no_quiet_hours(self, service):
        prefs = NotificationPreferences(
            delivery_channel=DeliveryChannel.BOTH,
            quiet_hours_start=None,
            quiet_hours_end=None,
        )
        assert service.is_in_quiet_hours(prefs) is False

    def test_returns_true_during_quiet_hours(self, service):
        # Set quiet hours 22:00-07:00 and mock current time to 23:00
        prefs = NotificationPreferences(
            delivery_channel=DeliveryChannel.BOTH,
            quiet_hours_start=time(22, 0),
            quiet_hours_end=time(7, 0),
            quiet_hours_timezone="UTC",
        )

        with patch("src.services.email_service.datetime") as mock_dt:
            mock_dt.now.return_value = _mock_now(23, 0)
            result = service.is_in_quiet_hours(prefs)

        assert result is True

    def test_handles_cross_midnight_window(self, service):
        # 22:00-07:00, currently 03:00 (should be in quiet hours)
        prefs = NotificationPreferences(
            delivery_channel=DeliveryChannel.BOTH,
            quiet_hours_start=time(22, 0),
            quiet_hours_end=time(7, 0),
            quiet_hours_timezone="UTC",
        )

        with patch("src.services.email_service.datetime") as mock_dt:
            mock_dt.now.return_value = _mock_now(3, 0)
            result = service.is_in_quiet_hours(prefs)

        assert result is True

    def test_returns_false_outside_quiet_hours(self, service):
        # 22:00-07:00, currently 12:00 (should NOT be in quiet hours)
        prefs = NotificationPreferences(
            delivery_channel=DeliveryChannel.BOTH,
            quiet_hours_start=time(22, 0),
            quiet_hours_end=time(7, 0),
            quiet_hours_timezone="UTC",
        )

        with patch("src.services.email_service.datetime") as mock_dt:
            mock_dt.now.return_value = _mock_now(12, 0)
            result = service.is_in_quiet_hours(prefs)

        assert result is False

    def test_simple_range_in_hours(self, service):
        # 08:00-17:00, currently 12:00 (should be in quiet hours)
        prefs = NotificationPreferences(
            delivery_channel=DeliveryChannel.BOTH,
            quiet_hours_start=time(8, 0),
            quiet_hours_end=time(17, 0),
            quiet_hours_timezone="UTC",
        )

        with patch("src.services.email_service.datetime") as mock_dt:
            mock_dt.now.return_value = _mock_now(12, 0)
            result = service.is_in_quiet_hours(prefs)

        assert result is True


class TestDeferEmail:
    @pytest.mark.asyncio
    async def test_inserts_deferred_email_row(self, service, mock_pool):
        pool, conn = mock_pool
        notification_id = uuid4()
        user_id = str(uuid4())
        deliver_after = datetime.now(timezone.utc)

        with patch("src.services.email_service.get_pool", return_value=pool):
            await service.defer_email(notification_id, user_id, deliver_after)

        conn.execute.assert_called_once()
        call_args = conn.execute.call_args[0]
        assert "INSERT INTO deferred_emails" in call_args[0]


class TestProcessDeferredEmails:
    @pytest.mark.asyncio
    async def test_sends_pending_emails(self, service, mock_pool):
        pool, conn = mock_pool
        notification_id = uuid4()
        user_id = uuid4()

        conn.fetch.return_value = [
            {
                "id": uuid4(),
                "notification_id": notification_id,
                "user_id": user_id,
                "message": "Test",
                "type": "info",
                "is_read": False,
                "notification_created_at": datetime.now(timezone.utc),
                "conversation_id": None,
                "email": "user@example.com",
            }
        ]

        with patch("src.services.email_service.get_pool", return_value=pool):
            with patch.object(
                service, "send_notification_email", new_callable=AsyncMock, return_value=True
            ):
                count = await service.process_deferred_emails()

        assert count == 1
        # Should have marked as delivered
        assert conn.execute.call_count >= 1

    @pytest.mark.asyncio
    async def test_marks_failed_on_send_error(self, service, mock_pool):
        pool, conn = mock_pool
        notification_id = uuid4()
        user_id = uuid4()

        conn.fetch.return_value = [
            {
                "id": uuid4(),
                "notification_id": notification_id,
                "user_id": user_id,
                "message": "Test",
                "type": "info",
                "is_read": False,
                "notification_created_at": datetime.now(timezone.utc),
                "conversation_id": None,
                "email": "user@example.com",
            }
        ]

        with patch("src.services.email_service.get_pool", return_value=pool):
            with patch.object(
                service, "send_notification_email", new_callable=AsyncMock, return_value=False
            ):
                count = await service.process_deferred_emails()

        assert count == 0
        # Should have marked as failed
        last_call = conn.execute.call_args[0]
        assert "failed_at" in last_call[0]
