"""Schedule service for managing scheduled tasks."""

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import structlog
from croniter import croniter

from src.database import get_pool

logger = structlog.get_logger(__name__)


class ScheduleService:
    """Manages scheduled task CRUD operations."""

    async def create_task(
        self,
        user_id: str,
        name: str,
        task_type: str,
        tool_name: str,
        prompt_template: str,
        description: Optional[str] = None,
        schedule_cron: Optional[str] = None,
        scheduled_at: Optional[datetime] = None,
        tz: str = "UTC",
        tool_args: Optional[dict] = None,
        source: str = "user",
    ) -> dict:
        """Create a new scheduled task.

        For recurring tasks, schedule_cron is required.
        For one_time tasks, scheduled_at is required.
        """
        task_id = uuid4()
        now = datetime.now(timezone.utc)
        pool = await get_pool()

        # Calculate next_run_at
        next_run = self.calculate_next_run(
            task_type=task_type,
            schedule_cron=schedule_cron,
            scheduled_at=scheduled_at,
        )

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO scheduled_tasks
                (id, user_id, name, description, task_type, schedule_cron, scheduled_at,
                 timezone, tool_name, tool_args, prompt_template, source, next_run_at,
                 created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                RETURNING id, name, task_type, status, next_run_at, created_at
                """,
                task_id,
                UUID(user_id),
                name,
                description,
                task_type,
                schedule_cron,
                scheduled_at,
                tz,
                tool_name,
                json.dumps(tool_args or {}),
                prompt_template,
                source,
                next_run,
                now,
                now,
            )

        logger.info(
            "scheduled_task_created",
            task_id=str(task_id),
            user_id=user_id,
            task_type=task_type,
            tool_name=tool_name,
            next_run_at=next_run.isoformat() if next_run else None,
        )

        return {
            "task_id": str(row["id"]),
            "name": row["name"],
            "task_type": row["task_type"],
            "status": row["status"],
            "next_run_at": row["next_run_at"].isoformat() if row["next_run_at"] else None,
            "created_at": row["created_at"].isoformat(),
        }

    async def get_task(self, task_id: str, user_id: str) -> Optional[dict]:
        """Get a single task by ID, scoped to user."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, name, description, task_type, schedule_cron,
                       scheduled_at, timezone, tool_name, tool_args, prompt_template,
                       status, source, next_run_at, last_run_at, run_count, fail_count,
                       max_retries, created_at, updated_at
                FROM scheduled_tasks
                WHERE id = $1 AND user_id = $2
                """,
                UUID(task_id),
                UUID(user_id),
            )

        if row is None:
            return None

        return dict(row)

    async def list_tasks(
        self,
        user_id: str,
        status_filter: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """List tasks for a user with optional status filter and pagination."""
        pool = await get_pool()
        uid = UUID(user_id)

        async with pool.acquire() as conn:
            if status_filter:
                rows = await conn.fetch(
                    """
                    SELECT id, name, description, task_type, schedule_cron, scheduled_at,
                           timezone, tool_name, status, source, next_run_at, last_run_at,
                           run_count, fail_count, created_at
                    FROM scheduled_tasks
                    WHERE user_id = $1 AND status = $2
                    ORDER BY created_at DESC
                    LIMIT $3 OFFSET $4
                    """,
                    uid,
                    status_filter,
                    limit,
                    offset,
                )
                total = await conn.fetchval(
                    "SELECT COUNT(*) FROM scheduled_tasks WHERE user_id = $1 AND status = $2",
                    uid,
                    status_filter,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, name, description, task_type, schedule_cron, scheduled_at,
                           timezone, tool_name, status, source, next_run_at, last_run_at,
                           run_count, fail_count, created_at
                    FROM scheduled_tasks
                    WHERE user_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                    """,
                    uid,
                    limit,
                    offset,
                )
                total = await conn.fetchval(
                    "SELECT COUNT(*) FROM scheduled_tasks WHERE user_id = $1",
                    uid,
                )

        return [dict(row) for row in rows], total

    async def update_status(
        self, task_id: str, user_id: str, new_status: str
    ) -> Optional[dict]:
        """Update task status (pause, resume, cancel, complete)."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE scheduled_tasks
                SET status = $1, updated_at = NOW()
                WHERE id = $2 AND user_id = $3
                RETURNING id, name, status, next_run_at
                """,
                new_status,
                UUID(task_id),
                UUID(user_id),
            )

        if row is None:
            return None

        logger.info(
            "scheduled_task_status_updated",
            task_id=task_id,
            user_id=user_id,
            new_status=new_status,
        )

        return dict(row)

    async def get_task_runs(
        self, task_id: str, user_id: str, limit: int = 20, offset: int = 0
    ) -> tuple[list[dict], int]:
        """Get run history for a task, verifying user ownership."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            # Verify ownership
            owner = await conn.fetchval(
                "SELECT user_id FROM scheduled_tasks WHERE id = $1",
                UUID(task_id),
            )
            if owner is None or str(owner) != user_id:
                return [], 0

            rows = await conn.fetch(
                """
                SELECT id, task_id, started_at, completed_at, status,
                       result, error, notification_id, retry_count, duration_ms
                FROM task_runs
                WHERE task_id = $1
                ORDER BY started_at DESC
                LIMIT $2 OFFSET $3
                """,
                UUID(task_id),
                limit,
                offset,
            )
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM task_runs WHERE task_id = $1",
                UUID(task_id),
            )

        return [dict(row) for row in rows], total

    @staticmethod
    def calculate_next_run(
        task_type: str,
        schedule_cron: Optional[str] = None,
        scheduled_at: Optional[datetime] = None,
    ) -> Optional[datetime]:
        """Calculate the next run time for a task."""
        if task_type == "recurring" and schedule_cron:
            now = datetime.now(timezone.utc)
            cron = croniter(schedule_cron, now)
            return cron.get_next(datetime)
        elif task_type == "one_time" and scheduled_at:
            return scheduled_at
        return None
