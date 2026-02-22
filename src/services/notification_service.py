"""Notification service for creating, listing, and managing notifications."""

import asyncio
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import structlog

from src.config import get_settings
from src.database import get_pool
from src.models.notification import (
    DeliveryChannel,
    Notification,
    NotificationPreferences,
    NotificationPreferencesUpdate,
    NotificationType,
)

logger = structlog.get_logger(__name__)


class NotificationService:
    """Service for notification CRUD, preferences, and rate limiting."""

    async def create_notification(
        self,
        user_id: str,
        message: str,
        notification_type: str = "info",
        conversation_id: Optional[str] = None,
    ) -> Notification:
        """Create a new notification for a user."""
        notification_id = uuid4()
        now = datetime.now(timezone.utc)
        conv_id = UUID(conversation_id) if conversation_id else None

        pool = await get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO notifications (id, user_id, conversation_id, message, type, is_read, created_at)
                VALUES ($1, $2, $3, $4, $5, FALSE, $6)
                """,
                notification_id,
                UUID(user_id),
                conv_id,
                message,
                notification_type,
                now,
            )

        logger.info(
            "notification_created",
            notification_id=str(notification_id),
            user_id=user_id,
            type=notification_type,
            conversation_id=conversation_id,
        )

        notification = Notification(
            id=notification_id,
            user_id=UUID(user_id),
            conversation_id=conv_id,
            message=message,
            type=NotificationType(notification_type),
            is_read=False,
            created_at=now,
        )

        # Fire-and-forget email delivery if enabled
        settings = get_settings()
        if settings.notification_email_enabled:
            asyncio.create_task(
                self._try_send_email(notification, user_id, pool)
            )

        return notification

    async def _try_send_email(self, notification: Notification, user_id: str, pool) -> None:
        """Attempt to send email for a notification. Failures are logged but don't affect in-app delivery."""
        try:
            from src.services.email_service import EmailService

            prefs = await self.get_preferences(user_id)
            if prefs.delivery_channel not in (DeliveryChannel.EMAIL, DeliveryChannel.BOTH):
                return

            # Get user email
            async with pool.acquire() as conn:
                email = await conn.fetchval(
                    "SELECT email FROM users WHERE id = $1",
                    UUID(user_id),
                )

            if not email:
                logger.warning(
                    "notification_email_skipped_no_email",
                    user_id=user_id,
                    notification_id=str(notification.id),
                )
                return

            email_service = EmailService()

            if email_service.is_in_quiet_hours(prefs):
                # Defer email until quiet hours end
                from datetime import time as time_type
                from zoneinfo import ZoneInfo

                tz = ZoneInfo(prefs.quiet_hours_timezone or "UTC")
                now_local = datetime.now(tz)
                end_time = prefs.quiet_hours_end

                # Calculate deliver_after as the next occurrence of quiet_hours_end
                deliver_after = now_local.replace(
                    hour=end_time.hour,
                    minute=end_time.minute,
                    second=0,
                    microsecond=0,
                )
                if deliver_after <= now_local:
                    from datetime import timedelta
                    deliver_after += timedelta(days=1)

                # Convert to UTC for storage
                deliver_after_utc = deliver_after.astimezone(timezone.utc)

                await email_service.defer_email(
                    notification.id, user_id, deliver_after_utc
                )
                logger.info(
                    "notification_email_deferred",
                    user_id=user_id,
                    notification_id=str(notification.id),
                    deliver_after=deliver_after_utc.isoformat(),
                )
            else:
                await email_service.send_notification_email(email, notification)

        except Exception as e:
            logger.error(
                "notification_email_error",
                user_id=user_id,
                notification_id=str(notification.id),
                error=str(e),
            )

    async def list_notifications(
        self,
        user_id: str,
        type_filter: Optional[str] = None,
        is_read_filter: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Notification], int]:
        """List notifications for a user, excluding dismissed ones."""
        pool = await get_pool()

        conditions = ["user_id = $1", "dismissed_at IS NULL"]
        params: list = [UUID(user_id)]
        param_idx = 2

        if type_filter is not None:
            conditions.append(f"type = ${param_idx}")
            params.append(type_filter)
            param_idx += 1

        if is_read_filter is not None:
            conditions.append(f"is_read = ${param_idx}")
            params.append(is_read_filter)
            param_idx += 1

        where_clause = " AND ".join(conditions)

        async with pool.acquire() as conn:
            total = await conn.fetchval(
                f"SELECT COUNT(*) FROM notifications WHERE {where_clause}",
                *params,
            )

            rows = await conn.fetch(
                f"""
                SELECT id, user_id, conversation_id, message, type, is_read, created_at
                FROM notifications
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_idx} OFFSET ${param_idx + 1}
                """,
                *params,
                limit,
                offset,
            )

        notifications = [
            Notification(
                id=row["id"],
                user_id=row["user_id"],
                conversation_id=row["conversation_id"],
                message=row["message"],
                type=NotificationType(row["type"]),
                is_read=row["is_read"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

        return notifications, total

    async def get_unread_count(self, user_id: str) -> int:
        """Get count of unread, non-dismissed notifications for a user."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM notifications
                WHERE user_id = $1 AND is_read = FALSE AND dismissed_at IS NULL
                """,
                UUID(user_id),
            )

        return count or 0

    async def mark_as_read(
        self, notification_id: UUID, user_id: str
    ) -> Optional[Notification]:
        """Mark a single notification as read. Returns None if not found."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE notifications
                SET is_read = TRUE
                WHERE id = $1 AND user_id = $2 AND dismissed_at IS NULL
                RETURNING id, user_id, conversation_id, message, type, is_read, created_at
                """,
                notification_id,
                UUID(user_id),
            )

        if row is None:
            return None

        logger.info(
            "notification_marked_read",
            notification_id=str(notification_id),
            user_id=user_id,
        )

        return Notification(
            id=row["id"],
            user_id=row["user_id"],
            conversation_id=row["conversation_id"],
            message=row["message"],
            type=NotificationType(row["type"]),
            is_read=row["is_read"],
            created_at=row["created_at"],
        )

    async def mark_all_as_read(self, user_id: str) -> int:
        """Mark all non-dismissed notifications as read. Returns count updated."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE notifications
                SET is_read = TRUE
                WHERE user_id = $1 AND is_read = FALSE AND dismissed_at IS NULL
                """,
                UUID(user_id),
            )

        # result is like "UPDATE N"
        count = int(result.split()[-1])

        logger.info(
            "notifications_marked_all_read",
            user_id=user_id,
            count=count,
        )

        return count

    async def dismiss_notification(
        self, notification_id: UUID, user_id: str
    ) -> bool:
        """Dismiss (soft-delete) a notification. Also marks it as read."""
        now = datetime.now(timezone.utc)
        pool = await get_pool()

        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE notifications
                SET dismissed_at = $1, is_read = TRUE
                WHERE id = $2 AND user_id = $3 AND dismissed_at IS NULL
                """,
                now,
                notification_id,
                UUID(user_id),
            )

        if result == "UPDATE 1":
            logger.info(
                "notification_dismissed",
                notification_id=str(notification_id),
                user_id=user_id,
            )
            return True
        return False

    async def get_preferences(self, user_id: str) -> NotificationPreferences:
        """Get notification preferences for a user, or defaults if not configured."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT delivery_channel, quiet_hours_start, quiet_hours_end, quiet_hours_timezone
                FROM notification_preferences
                WHERE user_id = $1
                """,
                UUID(user_id),
            )

        if row is None:
            return NotificationPreferences()

        return NotificationPreferences(
            delivery_channel=DeliveryChannel(row["delivery_channel"]),
            quiet_hours_start=row["quiet_hours_start"],
            quiet_hours_end=row["quiet_hours_end"],
            quiet_hours_timezone=row["quiet_hours_timezone"],
        )

    async def update_preferences(
        self, user_id: str, prefs: NotificationPreferencesUpdate
    ) -> NotificationPreferences:
        """Create or update notification preferences (upsert)."""
        pool = await get_pool()
        now = datetime.now(timezone.utc)

        # Build the values to upsert
        channel = prefs.delivery_channel.value if prefs.delivery_channel else "in_app"
        qh_start = prefs.quiet_hours_start
        qh_end = prefs.quiet_hours_end
        qh_tz = prefs.quiet_hours_timezone or "UTC"

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO notification_preferences
                    (id, user_id, delivery_channel, quiet_hours_start, quiet_hours_end, quiet_hours_timezone, created_at, updated_at)
                VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (user_id) DO UPDATE SET
                    delivery_channel = EXCLUDED.delivery_channel,
                    quiet_hours_start = EXCLUDED.quiet_hours_start,
                    quiet_hours_end = EXCLUDED.quiet_hours_end,
                    quiet_hours_timezone = EXCLUDED.quiet_hours_timezone,
                    updated_at = EXCLUDED.updated_at
                RETURNING delivery_channel, quiet_hours_start, quiet_hours_end, quiet_hours_timezone
                """,
                UUID(user_id),
                channel,
                qh_start,
                qh_end,
                qh_tz,
                now,
                now,
            )

        logger.info("notification_preferences_updated", user_id=user_id)

        return NotificationPreferences(
            delivery_channel=DeliveryChannel(row["delivery_channel"]),
            quiet_hours_start=row["quiet_hours_start"],
            quiet_hours_end=row["quiet_hours_end"],
            quiet_hours_timezone=row["quiet_hours_timezone"],
        )

    async def check_rate_limit(self, user_id: str) -> bool:
        """Check if user is within notification rate limit. Returns True if allowed."""
        import redis.asyncio as aioredis

        settings = get_settings()
        client = aioredis.from_url(settings.redis_url)
        key = f"notification_rate:{user_id}"

        try:
            current = await client.get(key)
            if current is not None and int(current) >= settings.notification_rate_limit_per_hour:
                logger.warning(
                    "notification_rate_limit_hit",
                    user_id=user_id,
                    current=int(current),
                    limit=settings.notification_rate_limit_per_hour,
                )
                return False

            await client.incr(key)
            await client.expire(key, 3600)  # 1 hour TTL
            return True
        finally:
            await client.aclose()
