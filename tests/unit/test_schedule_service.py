"""Unit tests for ScheduleService."""

import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.services.schedule_service import ScheduleService


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
    return ScheduleService()


@pytest.fixture
def user_id():
    return str(uuid4())


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


class TestCreateTask:
    @pytest.mark.asyncio
    async def test_creates_recurring_task(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        task_id = uuid4()
        now = datetime.now(timezone.utc)
        conn.fetchrow.return_value = {
            "id": task_id,
            "name": "Morning weather",
            "task_type": "recurring",
            "status": "active",
            "next_run_at": now + timedelta(hours=12),
            "created_at": now,
        }

        with patch("src.services.schedule_service.get_pool", return_value=pool):
            result = await service.create_task(
                user_id=user_id,
                name="Morning weather",
                task_type="recurring",
                tool_name="get_weather",
                prompt_template="Give weather for Seattle",
                schedule_cron="0 7 * * *",
            )

        assert result["name"] == "Morning weather"
        assert result["task_type"] == "recurring"
        assert result["status"] == "active"
        assert result["task_id"] == str(task_id)

    @pytest.mark.asyncio
    async def test_creates_one_time_task(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        task_id = uuid4()
        now = datetime.now(timezone.utc)
        scheduled = now + timedelta(hours=2)
        conn.fetchrow.return_value = {
            "id": task_id,
            "name": "Reminder",
            "task_type": "one_time",
            "status": "active",
            "next_run_at": scheduled,
            "created_at": now,
        }

        with patch("src.services.schedule_service.get_pool", return_value=pool):
            result = await service.create_task(
                user_id=user_id,
                name="Reminder",
                task_type="one_time",
                tool_name="send_notification",
                prompt_template="Remind user about meeting",
                scheduled_at=scheduled,
            )

        assert result["task_type"] == "one_time"
        assert result["next_run_at"] is not None


class TestCalculateNextRun:
    def test_recurring_with_cron(self):
        result = ScheduleService.calculate_next_run(
            task_type="recurring",
            schedule_cron="0 7 * * *",
        )
        assert result is not None
        assert result > datetime.now(timezone.utc)

    def test_one_time_with_scheduled_at(self):
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        result = ScheduleService.calculate_next_run(
            task_type="one_time",
            scheduled_at=future,
        )
        assert result == future

    def test_returns_none_without_params(self):
        result = ScheduleService.calculate_next_run(task_type="recurring")
        assert result is None


class TestListTasks:
    @pytest.mark.asyncio
    async def test_lists_all_tasks(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        task_id = uuid4()
        now = datetime.now(timezone.utc)
        conn.fetch.return_value = [
            {
                "id": task_id,
                "name": "Weather",
                "description": None,
                "task_type": "recurring",
                "schedule_cron": "0 7 * * *",
                "scheduled_at": None,
                "timezone": "UTC",
                "tool_name": "get_weather",
                "status": "active",
                "source": "user",
                "next_run_at": now,
                "last_run_at": None,
                "run_count": 0,
                "fail_count": 0,
                "created_at": now,
            }
        ]
        conn.fetchval.return_value = 1

        with patch("src.services.schedule_service.get_pool", return_value=pool):
            tasks, total = await service.list_tasks(user_id)

        assert len(tasks) == 1
        assert total == 1
        assert tasks[0]["name"] == "Weather"

    @pytest.mark.asyncio
    async def test_filters_by_status(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.fetch.return_value = []
        conn.fetchval.return_value = 0

        with patch("src.services.schedule_service.get_pool", return_value=pool):
            tasks, total = await service.list_tasks(
                user_id, status_filter="paused"
            )

        assert tasks == []
        assert total == 0


class TestUpdateStatus:
    @pytest.mark.asyncio
    async def test_pauses_task(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        task_id = str(uuid4())
        conn.fetchrow.return_value = {
            "id": uuid4(),
            "name": "Weather",
            "status": "paused",
            "next_run_at": None,
        }

        with patch("src.services.schedule_service.get_pool", return_value=pool):
            result = await service.update_status(task_id, user_id, "paused")

        assert result is not None
        assert result["status"] == "paused"

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        conn.fetchrow.return_value = None

        with patch("src.services.schedule_service.get_pool", return_value=pool):
            result = await service.update_status(str(uuid4()), user_id, "paused")

        assert result is None


class TestGetTaskRuns:
    @pytest.mark.asyncio
    async def test_returns_runs(self, service, user_id, mock_pool):
        pool, conn = mock_pool
        task_id = str(uuid4())
        run_id = uuid4()
        now = datetime.now(timezone.utc)

        conn.fetchval.side_effect = [
            uuid4(),  # owner check — returns any UUID (matches after str comparison)
            1,        # count
        ]
        # Override: make the owner check return matching user_id
        uid_obj = None

        async def mock_fetchval(query, *args):
            if "user_id FROM scheduled_tasks" in query:
                from uuid import UUID
                return UUID(user_id)
            return 1

        conn.fetchval.side_effect = None
        conn.fetchval = AsyncMock(side_effect=mock_fetchval)

        conn.fetch.return_value = [
            {
                "id": run_id,
                "task_id": uuid4(),
                "started_at": now,
                "completed_at": now,
                "status": "success",
                "result": "Weather is sunny",
                "error": None,
                "notification_id": None,
                "retry_count": 0,
                "duration_ms": 1500,
            }
        ]

        with patch("src.services.schedule_service.get_pool", return_value=pool):
            runs, total = await service.get_task_runs(task_id, user_id)

        assert len(runs) == 1
        assert runs[0]["status"] == "success"

    @pytest.mark.asyncio
    async def test_returns_empty_for_wrong_user(self, service, mock_pool):
        pool, conn = mock_pool
        task_id = str(uuid4())
        other_user = str(uuid4())

        # Owner is a different user
        async def mock_fetchval(query, *args):
            if "user_id FROM scheduled_tasks" in query:
                return uuid4()  # different from other_user
            return 0

        conn.fetchval = AsyncMock(side_effect=mock_fetchval)

        with patch("src.services.schedule_service.get_pool", return_value=pool):
            runs, total = await service.get_task_runs(task_id, other_user)

        assert runs == []
        assert total == 0
