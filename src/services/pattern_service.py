"""Pattern service for detecting and recording behavioral patterns."""

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import structlog

from src.config import get_settings
from src.database import get_pool

logger = structlog.get_logger(__name__)


class PatternService:
    """Detects and records behavioral patterns across conversations."""

    async def record_or_update_pattern(
        self,
        user_id: str,
        pattern_type: str,
        description: str,
        evidence: str,
        suggested_action: Optional[str] = None,
        confidence: float = 0.5,
    ) -> dict:
        """Record a new pattern or update an existing one.

        Matching logic: If a pattern with the same user_id + pattern_type already
        exists with a similar description, increment occurrence_count and append
        evidence. Otherwise, create a new pattern.

        Returns dict with pattern_id, occurrence_count, and threshold_reached flag.
        """
        pool = await get_pool()
        uid = UUID(user_id)
        now = datetime.now(timezone.utc)
        settings = get_settings()

        async with pool.acquire() as conn:
            # Look for an existing pattern with same type and similar description
            existing = await conn.fetchrow(
                """
                SELECT id, occurrence_count, evidence, confidence
                FROM observed_patterns
                WHERE user_id = $1 AND pattern_type = $2
                AND LOWER(description) = LOWER($3)
                """,
                uid,
                pattern_type,
                description,
            )

            if existing:
                # Update existing pattern
                old_evidence = existing["evidence"]
                if isinstance(old_evidence, str):
                    evidence_list = json.loads(old_evidence)
                else:
                    evidence_list = list(old_evidence) if old_evidence else []

                evidence_list.append({
                    "date": now.isoformat(),
                    "context": evidence,
                })

                new_count = existing["occurrence_count"] + 1
                new_confidence = max(existing["confidence"], confidence)

                await conn.execute(
                    """
                    UPDATE observed_patterns
                    SET occurrence_count = $1, evidence = $2, last_seen_at = $3,
                        confidence = $4, suggested_action = COALESCE($5, suggested_action)
                    WHERE id = $6
                    """,
                    new_count,
                    json.dumps(evidence_list),
                    now,
                    new_confidence,
                    suggested_action,
                    existing["id"],
                )

                pattern_id = str(existing["id"])
                occurrence_count = new_count

                logger.info(
                    "pattern_updated",
                    pattern_id=pattern_id,
                    user_id=user_id,
                    pattern_type=pattern_type,
                    occurrence_count=new_count,
                )
            else:
                # Create new pattern
                pattern_id_uuid = uuid4()
                evidence_list = [{"date": now.isoformat(), "context": evidence}]

                await conn.execute(
                    """
                    INSERT INTO observed_patterns
                    (id, user_id, pattern_type, description, evidence, occurrence_count,
                     first_seen_at, last_seen_at, suggested_action, confidence, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, 1, $6, $7, $8, $9, $10, $11)
                    """,
                    pattern_id_uuid,
                    uid,
                    pattern_type,
                    description,
                    json.dumps(evidence_list),
                    now,
                    now,
                    suggested_action,
                    confidence,
                    now,
                    now,
                )

                pattern_id = str(pattern_id_uuid)
                occurrence_count = 1

                logger.info(
                    "pattern_created",
                    pattern_id=pattern_id,
                    user_id=user_id,
                    pattern_type=pattern_type,
                )

        threshold = settings.pattern_occurrence_threshold
        return {
            "pattern_id": pattern_id,
            "occurrence_count": occurrence_count,
            "threshold_reached": occurrence_count >= threshold,
        }

    async def list_patterns(
        self,
        user_id: str,
        min_occurrences: int = 1,
    ) -> list[dict]:
        """List patterns for a user, optionally filtered by minimum occurrences."""
        pool = await get_pool()
        uid = UUID(user_id)

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, pattern_type, description, occurrence_count,
                       first_seen_at, last_seen_at, acted_on, suggested_action, confidence
                FROM observed_patterns
                WHERE user_id = $1 AND occurrence_count >= $2
                ORDER BY occurrence_count DESC, last_seen_at DESC
                """,
                uid,
                min_occurrences,
            )

        return [dict(row) for row in rows]

    async def get_actionable_patterns(self, user_id: str) -> list[dict]:
        """Get patterns that have reached the threshold and haven't been acted on."""
        settings = get_settings()
        pool = await get_pool()
        uid = UUID(user_id)

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, pattern_type, description, occurrence_count,
                       suggested_action, confidence
                FROM observed_patterns
                WHERE user_id = $1 AND acted_on = FALSE
                AND occurrence_count >= $2
                ORDER BY confidence DESC, occurrence_count DESC
                """,
                uid,
                settings.pattern_occurrence_threshold,
            )

        return [dict(row) for row in rows]
