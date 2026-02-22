"""Unit tests for SchedulerService."""

import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.services.scheduler_service import SchedulerService


class MockPoolAcquire:
    """Mock async context manager for pool.acquire()."""

    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *args):
        pass


@pytest.fixture
def service():
    return SchedulerService()


@pytest.fixture
def mock_pool():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock()
    conn.fetchval = AsyncMock()
    conn.execute = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])

    pool = MagicMock()
    pool.acquire.return_value = MockPoolAcquire(conn)
    return pool, conn


class TestPollOnce:
    @pytest.mark.asyncio
    async def test_finds_due_tasks(self, service, mock_pool):
        pool, conn = mock_pool
        task_id = uuid4()
        user_id = uuid4()
        conn.fetch.return_value = [
            {
                "id": task_id,
                "user_id": user_id,
                "name": "Morning weather",
                "tool_name": "get_weather",
                "tool_args": "{}",
                "prompt_template": "Get weather",
                "task_type": "recurring",
                "schedule_cron": "0 7 * * *",
                "max_retries": 3,
            }
        ]

        with (
            patch("src.services.scheduler_service.get_pool", return_value=pool),
            patch.object(service, "_execute_task", new_callable=AsyncMock) as mock_exec,
        ):
            await service._poll_once()

        mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_due_tasks(self, service, mock_pool):
        pool, conn = mock_pool
        conn.fetch.return_value = []

        with patch("src.services.scheduler_service.get_pool", return_value=pool):
            await service._poll_once()

        # Should not raise


class TestExecuteTask:
    @pytest.mark.asyncio
    async def test_successful_execution(self, service, mock_pool):
        pool, conn = mock_pool
        task = {
            "id": uuid4(),
            "user_id": uuid4(),
            "name": "Test task",
            "tool_name": "get_weather",
            "tool_args": "{}",
            "prompt_template": "Get weather update",
            "task_type": "recurring",
            "schedule_cron": "0 7 * * *",
            "max_retries": 3,
        }

        mock_notification_id = uuid4()

        with (
            patch("src.services.scheduler_service.get_pool", return_value=pool),
            patch.object(
                service, "_invoke_agent",
                new_callable=AsyncMock,
                return_value="Weather is sunny and 72F",
            ),
            patch.object(
                service, "_create_notification",
                new_callable=AsyncMock,
                return_value=mock_notification_id,
            ),
        ):
            await service._execute_task(task)

        # Should have: insert run, update run to success, update task
        assert conn.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_one_time_task_marked_completed(self, service, mock_pool):
        pool, conn = mock_pool
        task = {
            "id": uuid4(),
            "user_id": uuid4(),
            "name": "One-time reminder",
            "tool_name": "send_notification",
            "tool_args": "{}",
            "prompt_template": "Remind about meeting",
            "task_type": "one_time",
            "schedule_cron": None,
            "max_retries": 3,
        }

        with (
            patch("src.services.scheduler_service.get_pool", return_value=pool),
            patch.object(
                service, "_invoke_agent",
                new_callable=AsyncMock,
                return_value="Reminder sent",
            ),
            patch.object(
                service, "_create_notification",
                new_callable=AsyncMock,
                return_value=uuid4(),
            ),
        ):
            await service._execute_task(task)

        # Check that the completed status update was called
        calls = conn.execute.call_args_list
        # Last call should be the task update with status = 'completed'
        last_task_update = calls[-1][0][0]
        assert "completed" in last_task_update

    @pytest.mark.asyncio
    async def test_failed_execution_records_error(self, service, mock_pool):
        pool, conn = mock_pool
        task = {
            "id": uuid4(),
            "user_id": uuid4(),
            "name": "Failing task",
            "tool_name": "get_weather",
            "tool_args": "{}",
            "prompt_template": "Get weather",
            "task_type": "recurring",
            "schedule_cron": "0 7 * * *",
            "max_retries": 3,
        }

        with (
            patch("src.services.scheduler_service.get_pool", return_value=pool),
            patch.object(
                service, "_invoke_agent",
                new_callable=AsyncMock,
                side_effect=Exception("Agent failed"),
            ),
        ):
            await service._execute_task(task)

        # Should have: insert run, update run to failed, update task fail_count
        assert conn.execute.call_count == 3


class TestCreateNotification:
    @pytest.mark.asyncio
    async def test_creates_notification(self, service):
        mock_notif_service = AsyncMock()
        mock_notification = MagicMock()
        mock_notification.id = uuid4()
        mock_notif_service.create_notification.return_value = mock_notification

        with patch(
            "src.services.notification_service.NotificationService",
            return_value=mock_notif_service,
        ):
            result = await service._create_notification(
                user_id=str(uuid4()),
                task_name="Weather",
                result="It's sunny",
            )

        assert result == mock_notification.id

    @pytest.mark.asyncio
    async def test_handles_notification_failure(self, service):
        with patch(
            "src.services.notification_service.NotificationService",
            side_effect=Exception("Service unavailable"),
        ):
            result = await service._create_notification(
                user_id=str(uuid4()),
                task_name="Weather",
                result="It's sunny",
            )

        assert result is None


class TestStartStop:
    @pytest.mark.asyncio
    async def test_start_and_stop(self, service):
        with patch.object(service, "_poll_loop", new_callable=AsyncMock):
            service.start()
            assert service._running is True
            assert service._task is not None

            await service.stop()
            assert service._running is False
