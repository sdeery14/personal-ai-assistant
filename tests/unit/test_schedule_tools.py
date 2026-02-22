"""Unit tests for create_schedule and manage_schedule tools."""

import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.tools.create_schedule import create_schedule
from src.tools.manage_schedule import manage_schedule


@pytest.fixture
def mock_ctx():
    ctx = MagicMock()
    ctx.context = {
        "user_id": str(uuid4()),
        "correlation_id": uuid4(),
        "conversation_id": str(uuid4()),
    }
    return ctx


@pytest.fixture
def mock_ctx_no_user():
    ctx = MagicMock()
    ctx.context = {}
    return ctx


class TestCreateScheduleTool:
    @pytest.mark.asyncio
    async def test_creates_recurring_schedule(self, mock_ctx):
        mock_service = AsyncMock()
        mock_service.create_task.return_value = {
            "task_id": str(uuid4()),
            "name": "Morning weather",
            "task_type": "recurring",
            "status": "active",
            "next_run_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        with patch(
            "src.services.schedule_service.ScheduleService",
            return_value=mock_service,
        ):
            result_str = await create_schedule.on_invoke_tool(
                mock_ctx,
                json.dumps({
                    "name": "Morning weather",
                    "task_type": "recurring",
                    "schedule_cron": "0 7 * * *",
                    "tool_name": "get_weather",
                    "prompt_template": "Give weather update",
                }),
            )

        result = json.loads(result_str)
        assert result["success"] is True
        assert result["task_type"] == "recurring"

    @pytest.mark.asyncio
    async def test_creates_one_time_schedule(self, mock_ctx):
        mock_service = AsyncMock()
        future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        mock_service.create_task.return_value = {
            "task_id": str(uuid4()),
            "name": "Reminder",
            "task_type": "one_time",
            "status": "active",
            "next_run_at": future,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        with patch(
            "src.services.schedule_service.ScheduleService",
            return_value=mock_service,
        ):
            result_str = await create_schedule.on_invoke_tool(
                mock_ctx,
                json.dumps({
                    "name": "Reminder",
                    "task_type": "one_time",
                    "scheduled_at": future,
                    "tool_name": "send_notification",
                    "prompt_template": "Remind about meeting",
                }),
            )

        result = json.loads(result_str)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_invalid_cron_expression(self, mock_ctx):
        result_str = await create_schedule.on_invoke_tool(
            mock_ctx,
            json.dumps({
                "name": "Bad cron",
                "task_type": "recurring",
                "schedule_cron": "not a cron",
                "tool_name": "get_weather",
                "prompt_template": "test",
            }),
        )

        result = json.loads(result_str)
        assert result["success"] is False
        assert "Invalid cron" in result["message"]

    @pytest.mark.asyncio
    async def test_missing_cron_for_recurring(self, mock_ctx):
        result_str = await create_schedule.on_invoke_tool(
            mock_ctx,
            json.dumps({
                "name": "No cron",
                "task_type": "recurring",
                "tool_name": "get_weather",
                "prompt_template": "test",
            }),
        )

        result = json.loads(result_str)
        assert result["success"] is False
        assert "schedule_cron is required" in result["message"]

    @pytest.mark.asyncio
    async def test_missing_scheduled_at_for_one_time(self, mock_ctx):
        result_str = await create_schedule.on_invoke_tool(
            mock_ctx,
            json.dumps({
                "name": "No time",
                "task_type": "one_time",
                "tool_name": "get_weather",
                "prompt_template": "test",
            }),
        )

        result = json.loads(result_str)
        assert result["success"] is False
        assert "scheduled_at is required" in result["message"]

    @pytest.mark.asyncio
    async def test_missing_user_id(self, mock_ctx_no_user):
        result_str = await create_schedule.on_invoke_tool(
            mock_ctx_no_user,
            json.dumps({
                "name": "test",
                "task_type": "recurring",
                "schedule_cron": "0 7 * * *",
                "tool_name": "get_weather",
                "prompt_template": "test",
            }),
        )

        result = json.loads(result_str)
        assert result["success"] is False
        assert "user_id" in result["message"]

    @pytest.mark.asyncio
    async def test_invalid_task_type(self, mock_ctx):
        result_str = await create_schedule.on_invoke_tool(
            mock_ctx,
            json.dumps({
                "name": "test",
                "task_type": "invalid",
                "tool_name": "get_weather",
                "prompt_template": "test",
            }),
        )

        result = json.loads(result_str)
        assert result["success"] is False
        assert "Invalid task_type" in result["message"]


class TestManageScheduleTool:
    @pytest.mark.asyncio
    async def test_pause_task(self, mock_ctx):
        mock_service = AsyncMock()
        task_id = str(uuid4())
        mock_service.update_status.return_value = {
            "id": uuid4(),
            "name": "Weather",
            "status": "paused",
            "next_run_at": None,
        }

        with patch(
            "src.services.schedule_service.ScheduleService",
            return_value=mock_service,
        ):
            result_str = await manage_schedule.on_invoke_tool(
                mock_ctx,
                json.dumps({
                    "task_id": task_id,
                    "action": "pause",
                }),
            )

        result = json.loads(result_str)
        assert result["success"] is True
        assert result["status"] == "paused"

    @pytest.mark.asyncio
    async def test_resume_task(self, mock_ctx):
        mock_service = AsyncMock()
        mock_service.update_status.return_value = {
            "id": uuid4(),
            "name": "Weather",
            "status": "active",
            "next_run_at": None,
        }

        with patch(
            "src.services.schedule_service.ScheduleService",
            return_value=mock_service,
        ):
            result_str = await manage_schedule.on_invoke_tool(
                mock_ctx,
                json.dumps({
                    "task_id": str(uuid4()),
                    "action": "resume",
                }),
            )

        result = json.loads(result_str)
        assert result["success"] is True
        assert result["status"] == "active"

    @pytest.mark.asyncio
    async def test_cancel_task(self, mock_ctx):
        mock_service = AsyncMock()
        mock_service.update_status.return_value = {
            "id": uuid4(),
            "name": "Weather",
            "status": "cancelled",
            "next_run_at": None,
        }

        with patch(
            "src.services.schedule_service.ScheduleService",
            return_value=mock_service,
        ):
            result_str = await manage_schedule.on_invoke_tool(
                mock_ctx,
                json.dumps({
                    "task_id": str(uuid4()),
                    "action": "cancel",
                }),
            )

        result = json.loads(result_str)
        assert result["success"] is True
        assert result["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_task_not_found(self, mock_ctx):
        mock_service = AsyncMock()
        mock_service.update_status.return_value = None

        with patch(
            "src.services.schedule_service.ScheduleService",
            return_value=mock_service,
        ):
            result_str = await manage_schedule.on_invoke_tool(
                mock_ctx,
                json.dumps({
                    "task_id": str(uuid4()),
                    "action": "pause",
                }),
            )

        result = json.loads(result_str)
        assert result["success"] is False
        assert "not found" in result["message"]

    @pytest.mark.asyncio
    async def test_invalid_action(self, mock_ctx):
        result_str = await manage_schedule.on_invoke_tool(
            mock_ctx,
            json.dumps({
                "task_id": str(uuid4()),
                "action": "delete",
            }),
        )

        result = json.loads(result_str)
        assert result["success"] is False
        assert "Invalid action" in result["message"]

    @pytest.mark.asyncio
    async def test_missing_user_id(self, mock_ctx_no_user):
        result_str = await manage_schedule.on_invoke_tool(
            mock_ctx_no_user,
            json.dumps({
                "task_id": str(uuid4()),
                "action": "pause",
            }),
        )

        result = json.loads(result_str)
        assert result["success"] is False
        assert "user_id" in result["message"]
