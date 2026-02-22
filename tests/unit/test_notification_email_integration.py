"""Unit tests for email integration in NotificationService (T034).

Tests the _try_send_email method and email delivery logic
within create_notification.
"""

from datetime import datetime, time, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.models.notification import (
    DeliveryChannel,
    NotificationPreferences,
    NotificationType,
)
from src.services.notification_service import NotificationService


class MockPoolAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *args):
        pass


@pytest.fixture
def mock_pool():
    conn = AsyncMock()
    pool = MagicMock()
    pool.acquire.return_value = MockPoolAcquire(conn)
    return pool, conn


@pytest.fixture
def service():
    return NotificationService()


class TestEmailIntegration:
    @pytest.mark.asyncio
    async def test_sends_email_when_preference_is_email(self, service, mock_pool):
        pool, conn = mock_pool
        user_id = str(uuid4())
        conn.fetchval.return_value = "user@example.com"

        prefs = NotificationPreferences(
            delivery_channel=DeliveryChannel.EMAIL,
            quiet_hours_start=None,
            quiet_hours_end=None,
        )

        mock_email_service = MagicMock()
        mock_email_service.is_in_quiet_hours.return_value = False
        mock_email_service.send_notification_email = AsyncMock(return_value=True)

        with (
            patch("src.services.notification_service.get_pool", return_value=pool),
            patch("src.services.notification_service.get_settings") as mock_settings,
            patch.object(service, "get_preferences", new_callable=AsyncMock, return_value=prefs),
            patch("src.services.email_service.EmailService", return_value=mock_email_service),
        ):
            mock_settings.return_value.notification_email_enabled = True
            mock_settings.return_value.notification_rate_limit_per_hour = 10

            notification = await service.create_notification(
                user_id=user_id,
                message="Test email notification",
            )

            # Give the fire-and-forget task a moment to execute
            import asyncio
            await asyncio.sleep(0.1)

        # The email should have been sent
        mock_email_service.send_notification_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_does_not_send_when_preference_is_in_app(self, service, mock_pool):
        pool, conn = mock_pool
        user_id = str(uuid4())

        prefs = NotificationPreferences(
            delivery_channel=DeliveryChannel.IN_APP,
            quiet_hours_start=None,
            quiet_hours_end=None,
        )

        mock_email_service = MagicMock()
        mock_email_service.send_notification_email = AsyncMock()

        with (
            patch("src.services.notification_service.get_pool", return_value=pool),
            patch("src.services.notification_service.get_settings") as mock_settings,
            patch.object(service, "get_preferences", new_callable=AsyncMock, return_value=prefs),
            patch("src.services.email_service.EmailService", return_value=mock_email_service),
        ):
            mock_settings.return_value.notification_email_enabled = True

            await service.create_notification(
                user_id=user_id,
                message="In-app only notification",
            )

            import asyncio
            await asyncio.sleep(0.1)

        # Email should not have been sent
        mock_email_service.send_notification_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_email_when_no_email_address(self, service, mock_pool):
        pool, conn = mock_pool
        user_id = str(uuid4())
        conn.fetchval.return_value = None  # No email on file

        prefs = NotificationPreferences(
            delivery_channel=DeliveryChannel.EMAIL,
            quiet_hours_start=None,
            quiet_hours_end=None,
        )

        mock_email_service = MagicMock()
        mock_email_service.send_notification_email = AsyncMock()

        with (
            patch("src.services.notification_service.get_pool", return_value=pool),
            patch("src.services.notification_service.get_settings") as mock_settings,
            patch.object(service, "get_preferences", new_callable=AsyncMock, return_value=prefs),
            patch("src.services.email_service.EmailService", return_value=mock_email_service),
        ):
            mock_settings.return_value.notification_email_enabled = True

            await service.create_notification(
                user_id=user_id,
                message="No email on file",
            )

            import asyncio
            await asyncio.sleep(0.1)

        mock_email_service.send_notification_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_email_not_sent_when_feature_disabled(self, service, mock_pool):
        pool, conn = mock_pool
        user_id = str(uuid4())

        mock_email_service = MagicMock()
        mock_email_service.send_notification_email = AsyncMock()

        with (
            patch("src.services.notification_service.get_pool", return_value=pool),
            patch("src.services.notification_service.get_settings") as mock_settings,
            patch("src.services.email_service.EmailService", return_value=mock_email_service),
        ):
            mock_settings.return_value.notification_email_enabled = False

            await service.create_notification(
                user_id=user_id,
                message="Email disabled",
            )

            import asyncio
            await asyncio.sleep(0.1)

        mock_email_service.send_notification_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_email_failure_does_not_block_notification(self, service, mock_pool):
        pool, conn = mock_pool
        user_id = str(uuid4())
        conn.fetchval.return_value = "user@example.com"

        prefs = NotificationPreferences(
            delivery_channel=DeliveryChannel.BOTH,
            quiet_hours_start=None,
            quiet_hours_end=None,
        )

        mock_email_service = MagicMock()
        mock_email_service.is_in_quiet_hours.return_value = False
        mock_email_service.send_notification_email = AsyncMock(
            side_effect=Exception("SMTP timeout")
        )

        with (
            patch("src.services.notification_service.get_pool", return_value=pool),
            patch("src.services.notification_service.get_settings") as mock_settings,
            patch.object(service, "get_preferences", new_callable=AsyncMock, return_value=prefs),
            patch("src.services.email_service.EmailService", return_value=mock_email_service),
        ):
            mock_settings.return_value.notification_email_enabled = True

            # This should NOT raise even though email fails
            notification = await service.create_notification(
                user_id=user_id,
                message="Email will fail",
            )

            import asyncio
            await asyncio.sleep(0.1)

        # Notification should still be created successfully
        assert notification is not None
        assert notification.message == "Email will fail"
