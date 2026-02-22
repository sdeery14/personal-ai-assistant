"""Engagement service for tracking user responses to proactive suggestions."""

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import structlog

from src.config import get_settings
from src.database import get_pool

logger = structlog.get_logger(__name__)

# Number of dismissals of same type before suppression
SUPPRESSION_THRESHOLD = 3
# Number of engagements of same type before boosting
BOOST_THRESHOLD = 3


class EngagementService:
    """Tracks engagement events and manages automatic calibration."""

    async def record_event(
        self,
        user_id: str,
        suggestion_type: str,
        action: str,
        source: str,
        context: Optional[dict] = None,
    ) -> dict:
        """Record a user's response to a proactive suggestion.

        After recording, checks if suppression or boosting thresholds are reached
        and updates proactiveness_settings accordingly.
        """
        event_id = uuid4()
        now = datetime.now(timezone.utc)
        pool = await get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO engagement_events (id, user_id, suggestion_type, action, source, context, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                event_id,
                UUID(user_id),
                suggestion_type,
                action,
                source,
                json.dumps(context or {}),
                now,
            )

        logger.info(
            "engagement_event_recorded",
            event_id=str(event_id),
            user_id=user_id,
            suggestion_type=suggestion_type,
            action=action,
            source=source,
        )

        # Check thresholds and update settings as side effect
        await self._check_thresholds(user_id, suggestion_type, action)

        return {
            "event_id": str(event_id),
            "suggestion_type": suggestion_type,
            "action": action,
        }

    async def _check_thresholds(
        self, user_id: str, suggestion_type: str, action: str
    ) -> None:
        """Check if suppression or boosting thresholds are reached and update settings."""
        pool = await get_pool()
        uid = UUID(user_id)

        async with pool.acquire() as conn:
            if action == "dismissed":
                # Count recent dismissals of this type
                dismiss_count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM engagement_events
                    WHERE user_id = $1 AND suggestion_type = $2 AND action = 'dismissed'
                    """,
                    uid,
                    suggestion_type,
                )

                if dismiss_count >= SUPPRESSION_THRESHOLD:
                    # Add to suppressed_types if not already there
                    current = await conn.fetchval(
                        "SELECT suppressed_types FROM proactiveness_settings WHERE user_id = $1",
                        uid,
                    )
                    if current is not None:
                        suppressed = json.loads(current) if isinstance(current, str) else current
                        if suggestion_type not in suppressed:
                            suppressed.append(suggestion_type)
                            await conn.execute(
                                """
                                UPDATE proactiveness_settings
                                SET suppressed_types = $1
                                WHERE user_id = $2
                                """,
                                json.dumps(suppressed),
                                uid,
                            )
                            logger.info(
                                "suggestion_type_suppressed",
                                user_id=user_id,
                                suggestion_type=suggestion_type,
                                dismiss_count=dismiss_count,
                            )

            elif action == "engaged":
                # Count recent engagements of this type
                engage_count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM engagement_events
                    WHERE user_id = $1 AND suggestion_type = $2 AND action = 'engaged'
                    """,
                    uid,
                    suggestion_type,
                )

                if engage_count >= BOOST_THRESHOLD:
                    # Add to boosted_types if not already there
                    current = await conn.fetchval(
                        "SELECT boosted_types FROM proactiveness_settings WHERE user_id = $1",
                        uid,
                    )
                    if current is not None:
                        boosted = json.loads(current) if isinstance(current, str) else current
                        if suggestion_type not in boosted:
                            boosted.append(suggestion_type)
                            await conn.execute(
                                """
                                UPDATE proactiveness_settings
                                SET boosted_types = $1
                                WHERE user_id = $2
                                """,
                                json.dumps(boosted),
                                uid,
                            )
                            logger.info(
                                "suggestion_type_boosted",
                                user_id=user_id,
                                suggestion_type=suggestion_type,
                                engage_count=engage_count,
                            )

    async def get_engagement_stats(
        self, user_id: str, suggestion_type: Optional[str] = None
    ) -> dict:
        """Get engagement statistics for a user, optionally filtered by type."""
        pool = await get_pool()
        uid = UUID(user_id)

        async with pool.acquire() as conn:
            if suggestion_type:
                engaged = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM engagement_events
                    WHERE user_id = $1 AND suggestion_type = $2 AND action = 'engaged'
                    """,
                    uid,
                    suggestion_type,
                )
                dismissed = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM engagement_events
                    WHERE user_id = $1 AND suggestion_type = $2 AND action = 'dismissed'
                    """,
                    uid,
                    suggestion_type,
                )
            else:
                engaged = await conn.fetchval(
                    "SELECT COUNT(*) FROM engagement_events WHERE user_id = $1 AND action = 'engaged'",
                    uid,
                )
                dismissed = await conn.fetchval(
                    "SELECT COUNT(*) FROM engagement_events WHERE user_id = $1 AND action = 'dismissed'",
                    uid,
                )

        total = (engaged or 0) + (dismissed or 0)
        engagement_rate = (engaged or 0) / total if total > 0 else 0.0

        return {
            "engaged": engaged or 0,
            "dismissed": dismissed or 0,
            "total": total,
            "engagement_rate": round(engagement_rate, 2),
        }

    async def check_suppression(self, user_id: str, suggestion_type: str) -> bool:
        """Check if a suggestion type is suppressed for this user. Returns True if suppressed."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            suppressed = await conn.fetchval(
                "SELECT suppressed_types FROM proactiveness_settings WHERE user_id = $1",
                UUID(user_id),
            )

        if suppressed is None:
            return False

        types = json.loads(suppressed) if isinstance(suppressed, str) else suppressed
        return suggestion_type in types

    async def check_boost(self, user_id: str, suggestion_type: str) -> bool:
        """Check if a suggestion type is boosted for this user. Returns True if boosted."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            boosted = await conn.fetchval(
                "SELECT boosted_types FROM proactiveness_settings WHERE user_id = $1",
                UUID(user_id),
            )

        if boosted is None:
            return False

        types = json.loads(boosted) if isinstance(boosted, str) else boosted
        return suggestion_type in types
