"""Scheduler service for executing scheduled tasks on their schedule."""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import structlog
from croniter import croniter

from src.config import get_settings
from src.database import get_pool

logger = structlog.get_logger(__name__)


class SchedulerService:
    """Polls for due tasks and executes them."""

    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._running = False

    def start(self):
        """Start the scheduler loop as an asyncio background task."""
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("scheduler_started")

    async def stop(self):
        """Stop the scheduler loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("scheduler_stopped")

    async def _poll_loop(self):
        """Main scheduler loop — polls for due tasks at configured interval."""
        settings = get_settings()
        interval = settings.scheduler_poll_interval_seconds

        while self._running:
            try:
                await self._poll_once()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("scheduler_poll_error", error=str(e))

            try:
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break

    async def _poll_once(self):
        """Find and execute all due tasks."""
        settings = get_settings()
        now = datetime.now(timezone.utc)
        pool = await get_pool()

        async with pool.acquire() as conn:
            due_tasks = await conn.fetch(
                """
                SELECT id, user_id, name, tool_name, tool_args, prompt_template,
                       task_type, schedule_cron, max_retries
                FROM scheduled_tasks
                WHERE status = 'active'
                AND next_run_at IS NOT NULL
                AND next_run_at <= $1
                ORDER BY next_run_at ASC
                LIMIT $2
                """,
                now,
                settings.scheduler_max_concurrent_tasks,
            )

        if not due_tasks:
            return

        logger.info("scheduler_found_due_tasks", count=len(due_tasks))

        # Execute tasks concurrently up to the limit
        tasks = [self._execute_task(dict(task)) for task in due_tasks]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute_task(self, task: dict) -> None:
        """Execute a single scheduled task."""
        task_id = str(task["id"])
        user_id = str(task["user_id"])
        run_id = uuid4()
        start_time = time.perf_counter()

        logger.info(
            "task_execution_started",
            task_id=task_id,
            task_name=task["name"],
            tool_name=task["tool_name"],
        )

        pool = await get_pool()

        # Create run record
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO task_runs (id, task_id, started_at, status)
                VALUES ($1, $2, NOW(), 'running')
                """,
                run_id,
                task["id"],
            )

        try:
            # Execute via production agent (non-streamed)
            result_text = await self._invoke_agent(
                user_id=user_id,
                prompt=task["prompt_template"],
            )

            duration_ms = int((time.perf_counter() - start_time) * 1000)

            # Create notification for the result
            notification_id = await self._create_notification(
                user_id=user_id,
                task_name=task["name"],
                result=result_text,
            )

            # Update run record as success
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE task_runs
                    SET status = 'success', completed_at = NOW(),
                        result = $1, notification_id = $2, duration_ms = $3
                    WHERE id = $4
                    """,
                    result_text,
                    notification_id,
                    duration_ms,
                    run_id,
                )

                # Update task: run_count, last_run_at, next_run_at
                if task["task_type"] == "recurring" and task["schedule_cron"]:
                    now = datetime.now(timezone.utc)
                    cron = croniter(task["schedule_cron"], now)
                    next_run = cron.get_next(datetime)
                    await conn.execute(
                        """
                        UPDATE scheduled_tasks
                        SET run_count = run_count + 1, last_run_at = NOW(),
                            next_run_at = $1, updated_at = NOW()
                        WHERE id = $2
                        """,
                        next_run,
                        task["id"],
                    )
                else:
                    # One-time task: mark as completed
                    await conn.execute(
                        """
                        UPDATE scheduled_tasks
                        SET run_count = run_count + 1, last_run_at = NOW(),
                            status = 'completed', next_run_at = NULL, updated_at = NOW()
                        WHERE id = $1
                        """,
                        task["id"],
                    )

            logger.info(
                "task_execution_success",
                task_id=task_id,
                run_id=str(run_id),
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)

            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE task_runs
                    SET status = 'failed', completed_at = NOW(),
                        error = $1, duration_ms = $2
                    WHERE id = $3
                    """,
                    str(e),
                    duration_ms,
                    run_id,
                )
                await conn.execute(
                    """
                    UPDATE scheduled_tasks
                    SET fail_count = fail_count + 1, updated_at = NOW()
                    WHERE id = $1
                    """,
                    task["id"],
                )

            logger.error(
                "task_execution_failed",
                task_id=task_id,
                run_id=str(run_id),
                error=str(e),
                duration_ms=duration_ms,
            )

    async def _invoke_agent(self, user_id: str, prompt: str) -> str:
        """Invoke the production agent with a prompt (non-streamed)."""
        from agents import Runner
        from src.services.chat_service import ChatService

        chat_service = ChatService()
        agent = chat_service.create_agent(user_id=user_id, is_onboarded=True)

        context = {
            "user_id": user_id,
            "correlation_id": uuid4(),
            "conversation_id": None,
        }

        result = await Runner.run(agent, input=prompt, context=context)
        return result.final_output

    async def _create_notification(
        self, user_id: str, task_name: str, result: str
    ) -> Optional[UUID]:
        """Create a notification for a task execution result."""
        try:
            from src.services.notification_service import NotificationService

            service = NotificationService()
            message = f"[{task_name}] {result[:400]}"
            notification = await service.create_notification(
                user_id=user_id,
                message=message,
                notification_type="info",
            )
            return notification.id if notification else None
        except Exception as e:
            logger.warning(
                "task_notification_failed",
                user_id=user_id,
                task_name=task_name,
                error=str(e),
            )
            return None
