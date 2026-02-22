"""Proactive service for user profile aggregation and proactiveness settings."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import structlog

from src.database import get_pool

logger = structlog.get_logger(__name__)


class ProactiveService:
    """Manages proactiveness settings and aggregates user profile data."""

    async def get_or_create_settings(self, user_id: str) -> dict:
        """Get proactiveness settings for a user, creating defaults if needed."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, global_level, suppressed_types, boosted_types,
                       user_override, is_onboarded, created_at, updated_at
                FROM proactiveness_settings
                WHERE user_id = $1
                """,
                UUID(user_id),
            )

            if row is None:
                now = datetime.now(timezone.utc)
                row = await conn.fetchrow(
                    """
                    INSERT INTO proactiveness_settings (user_id, created_at, updated_at)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id) DO UPDATE SET updated_at = EXCLUDED.updated_at
                    RETURNING id, user_id, global_level, suppressed_types, boosted_types,
                              user_override, is_onboarded, created_at, updated_at
                    """,
                    UUID(user_id),
                    now,
                    now,
                )

        return dict(row)

    async def update_settings(self, user_id: str, **updates) -> dict:
        """Update proactiveness settings for a user."""
        pool = await get_pool()

        # Ensure settings exist first
        await self.get_or_create_settings(user_id)

        set_clauses = []
        params = [UUID(user_id)]
        param_idx = 2

        allowed_fields = {
            "global_level", "suppressed_types", "boosted_types",
            "user_override", "is_onboarded",
        }

        for key, value in updates.items():
            if key in allowed_fields:
                set_clauses.append(f"{key} = ${param_idx}")
                params.append(value)
                param_idx += 1

        if not set_clauses:
            return await self.get_or_create_settings(user_id)

        set_clause = ", ".join(set_clauses)

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE proactiveness_settings
                SET {set_clause}
                WHERE user_id = $1
                RETURNING id, user_id, global_level, suppressed_types, boosted_types,
                          user_override, is_onboarded, created_at, updated_at
                """,
                *params,
            )

        logger.info("proactiveness_settings_updated", user_id=user_id, updates=list(updates.keys()))
        return dict(row)

    async def is_onboarded(self, user_id: str) -> bool:
        """Check if a user has completed or skipped onboarding."""
        settings = await self.get_or_create_settings(user_id)
        return settings["is_onboarded"]

    async def mark_onboarded(self, user_id: str) -> None:
        """Mark a user as having completed onboarding."""
        await self.update_settings(user_id, is_onboarded=True)
        logger.info("user_onboarded", user_id=user_id)

    async def get_user_profile(self, user_id: str) -> dict:
        """Aggregate user profile from memory, knowledge graph, patterns, and settings."""
        pool = await get_pool()
        uid = UUID(user_id)

        async with pool.acquire() as conn:
            # Get facts and preferences from memory
            memory_rows = await conn.fetch(
                """
                SELECT content, memory_type, confidence
                FROM memory_items
                WHERE user_id = $1 AND deleted_at IS NULL
                ORDER BY importance DESC, created_at DESC
                LIMIT 20
                """,
                uid,
            )

            facts = []
            preferences = []
            for row in memory_rows:
                item = {
                    "content": row["content"],
                    "type": row["memory_type"],
                    "confidence": row["confidence"],
                }
                if row["memory_type"] == "preference":
                    preferences.append(item)
                else:
                    facts.append(item)

            # Get observed patterns
            pattern_rows = await conn.fetch(
                """
                SELECT description, occurrence_count, acted_on
                FROM observed_patterns
                WHERE user_id = $1
                ORDER BY occurrence_count DESC, last_seen_at DESC
                LIMIT 10
                """,
                uid,
            )
            patterns = [
                {
                    "description": row["description"],
                    "occurrence_count": row["occurrence_count"],
                    "acted_on": row["acted_on"],
                }
                for row in pattern_rows
            ]

            # Get key relationships from knowledge graph
            relationship_rows = await conn.fetch(
                """
                SELECT e.name AS entity, r.relation_type AS relationship,
                       e.mention_count AS mentions
                FROM entities e
                JOIN relationships r ON (r.source_entity_id = e.id OR r.target_entity_id = e.id)
                WHERE e.user_id = $1 AND e.deleted_at IS NULL AND r.deleted_at IS NULL
                ORDER BY e.mention_count DESC
                LIMIT 10
                """,
                uid,
            )
            key_relationships = [
                {
                    "entity": row["entity"],
                    "relationship": row["relationship"],
                    "mentions": row["mentions"],
                }
                for row in relationship_rows
            ]

            # Get proactiveness settings
            settings = await self.get_or_create_settings(user_id)

            # Get engagement stats
            engaged_rows = await conn.fetch(
                """
                SELECT suggestion_type, COUNT(*) as count
                FROM engagement_events
                WHERE user_id = $1 AND action = 'engaged'
                GROUP BY suggestion_type
                ORDER BY count DESC
                LIMIT 5
                """,
                uid,
            )
            engaged_categories = [row["suggestion_type"] for row in engaged_rows]

        return {
            "facts": facts,
            "preferences": preferences,
            "patterns": patterns,
            "key_relationships": key_relationships,
            "proactiveness": {
                "global_level": settings["global_level"],
                "engaged_categories": engaged_categories,
                "suppressed_categories": settings["suppressed_types"],
            },
        }
