"""Email service for sending notification emails with quiet hours support."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import structlog

from src.config import get_settings
from src.database import get_pool
from src.models.notification import Notification, NotificationPreferences

logger = structlog.get_logger(__name__)


class EmailService:
    """Service for sending notification emails and managing deferred delivery."""

    async def send_notification_email(
        self,
        to_email: str,
        notification: Notification,
    ) -> bool:
        """Send a notification email via SMTP.

        Returns True on success, False on failure.
        """
        settings = get_settings()

        try:
            import aiosmtplib

            subject_map = {
                "reminder": "Reminder",
                "info": "Info",
                "warning": "Warning",
            }
            subject_prefix = subject_map.get(notification.type.value, "Notification")
            subject = f"[AI Assistant] {subject_prefix}: {notification.message[:50]}"

            body = (
                f"You have a new {notification.type.value} notification:\n\n"
                f"{notification.message}\n\n"
                f"---\n"
                f"This notification was sent by your AI Assistant."
            )

            message = (
                f"From: {settings.notification_email_from}\r\n"
                f"To: {to_email}\r\n"
                f"Subject: {subject}\r\n"
                f"Content-Type: text/plain; charset=utf-8\r\n"
                f"\r\n"
                f"{body}"
            )

            await aiosmtplib.send(
                message,
                hostname=settings.notification_smtp_host,
                port=settings.notification_smtp_port,
                username=settings.notification_smtp_username or None,
                password=settings.notification_smtp_password or None,
                use_tls=settings.notification_smtp_use_tls,
            )

            logger.info(
                "notification_email_sent",
                to=to_email,
                notification_id=str(notification.id),
                type=notification.type.value,
            )
            return True

        except Exception as e:
            logger.error(
                "notification_email_failed",
                to=to_email,
                notification_id=str(notification.id),
                error=str(e),
            )
            return False

    def is_in_quiet_hours(self, preferences: NotificationPreferences) -> bool:
        """Check if current time falls within quiet hours.

        Handles cross-midnight windows (e.g., 22:00 to 07:00).
        Returns False if no quiet hours are configured.
        """
        if preferences.quiet_hours_start is None or preferences.quiet_hours_end is None:
            return False

        try:
            from zoneinfo import ZoneInfo

            tz = ZoneInfo(preferences.quiet_hours_timezone or "UTC")
            now = datetime.now(tz).time()
        except Exception:
            now = datetime.now(timezone.utc).time()

        start = preferences.quiet_hours_start
        end = preferences.quiet_hours_end

        if start <= end:
            # Simple range: e.g., 08:00 to 17:00
            return start <= now <= end
        else:
            # Cross-midnight range: e.g., 22:00 to 07:00
            return now >= start or now <= end

    async def defer_email(
        self,
        notification_id: UUID,
        user_id: str,
        deliver_after: datetime,
    ) -> None:
        """Insert a deferred email record for later delivery."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO deferred_emails (id, notification_id, user_id, deliver_after, created_at)
                VALUES ($1, $2, $3, $4, $5)
                """,
                uuid4(),
                notification_id,
                UUID(user_id),
                deliver_after,
                datetime.now(timezone.utc),
            )

        logger.info(
            "email_deferred",
            notification_id=str(notification_id),
            user_id=user_id,
            deliver_after=deliver_after.isoformat(),
        )

    async def process_deferred_emails(self) -> int:
        """Process pending deferred emails that are past their deliver_after time.

        Returns count of emails processed.
        """
        pool = await get_pool()
        now = datetime.now(timezone.utc)
        processed = 0

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT de.id, de.notification_id, de.user_id,
                       n.message, n.type, n.is_read, n.created_at as notification_created_at,
                       n.conversation_id,
                       u.email
                FROM deferred_emails de
                JOIN notifications n ON n.id = de.notification_id
                JOIN users u ON u.id = de.user_id
                WHERE de.delivered_at IS NULL
                  AND de.failed_at IS NULL
                  AND de.deliver_after <= $1
                ORDER BY de.deliver_after ASC
                LIMIT 50
                """,
                now,
            )

        for row in rows:
            if not row["email"]:
                # Mark as failed if user has no email
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE deferred_emails
                        SET failed_at = $1, error_message = $2
                        WHERE id = $3
                        """,
                        now,
                        "User has no email address",
                        row["id"],
                    )
                continue

            notification = Notification(
                id=row["notification_id"],
                user_id=row["user_id"],
                conversation_id=row["conversation_id"],
                message=row["message"],
                type=row["type"],
                is_read=row["is_read"],
                created_at=row["notification_created_at"],
            )

            success = await self.send_notification_email(row["email"], notification)

            async with pool.acquire() as conn:
                if success:
                    await conn.execute(
                        "UPDATE deferred_emails SET delivered_at = $1 WHERE id = $2",
                        now,
                        row["id"],
                    )
                    processed += 1
                else:
                    await conn.execute(
                        """
                        UPDATE deferred_emails
                        SET failed_at = $1, error_message = $2
                        WHERE id = $3
                        """,
                        now,
                        "SMTP send failed",
                        row["id"],
                    )

        if processed > 0:
            logger.info("deferred_emails_processed", count=processed)

        return processed
