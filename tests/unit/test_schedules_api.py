"""Unit tests for schedules API endpoints."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.schedules import router
from src.models.user import User


@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.username = "testuser"
    user.is_admin = False
    return user


@pytest.fixture
def mock_service():
    return AsyncMock()


@pytest.fixture
def app(mock_user):
    """Create a test FastAPI app with auth dependency overridden."""
    from fastapi import FastAPI
    from src.api.dependencies import get_current_user

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestListSchedules:
    def test_returns_paginated_list(self, client, mock_service):
        now = datetime.now(timezone.utc)
        task_id = uuid4()
        mock_service.list_tasks.return_value = (
            [
                {
                    "id": task_id,
                    "name": "Morning weather",
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
            ],
            1,
        )

        with patch(
            "src.api.schedules.ScheduleService",
            return_value=mock_service,
        ):
            response = client.get("/schedules")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Morning weather"

    def test_empty_list(self, client, mock_service):
        mock_service.list_tasks.return_value = ([], 0)

        with patch(
            "src.api.schedules.ScheduleService",
            return_value=mock_service,
        ):
            response = client.get("/schedules")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []


class TestGetSchedule:
    def test_returns_task_with_runs(self, client, mock_service):
        now = datetime.now(timezone.utc)
        task_id = uuid4()
        mock_service.get_task.return_value = {
            "id": task_id,
            "name": "Weather",
            "description": "Daily weather",
            "task_type": "recurring",
            "schedule_cron": "0 7 * * *",
            "scheduled_at": None,
            "timezone": "UTC",
            "tool_name": "get_weather",
            "status": "active",
            "source": "user",
            "next_run_at": now,
            "last_run_at": now,
            "run_count": 5,
            "fail_count": 0,
            "created_at": now,
        }
        mock_service.get_task_runs.return_value = (
            [
                {
                    "id": uuid4(),
                    "task_id": task_id,
                    "started_at": now,
                    "completed_at": now,
                    "status": "success",
                    "result": "Sunny, 72F",
                    "error": None,
                    "notification_id": None,
                    "retry_count": 0,
                    "duration_ms": 1200,
                }
            ],
            1,
        )

        with patch(
            "src.api.schedules.ScheduleService",
            return_value=mock_service,
        ):
            response = client.get(f"/schedules/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Weather"
        assert len(data["recent_runs"]) == 1

    def test_404_for_nonexistent(self, client, mock_service):
        mock_service.get_task.return_value = None

        with patch(
            "src.api.schedules.ScheduleService",
            return_value=mock_service,
        ):
            response = client.get(f"/schedules/{uuid4()}")

        assert response.status_code == 404


class TestListScheduleRuns:
    def test_returns_runs(self, client, mock_service):
        now = datetime.now(timezone.utc)
        task_id = uuid4()
        mock_service.get_task_runs.return_value = (
            [
                {
                    "id": uuid4(),
                    "task_id": task_id,
                    "started_at": now,
                    "completed_at": now,
                    "status": "success",
                    "result": "Done",
                    "error": None,
                    "notification_id": None,
                    "retry_count": 0,
                    "duration_ms": 500,
                }
            ],
            1,
        )

        with patch(
            "src.api.schedules.ScheduleService",
            return_value=mock_service,
        ):
            response = client.get(f"/schedules/{task_id}/runs")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_404_for_nonexistent_task(self, client, mock_service):
        mock_service.get_task_runs.return_value = ([], 0)
        mock_service.get_task.return_value = None

        with patch(
            "src.api.schedules.ScheduleService",
            return_value=mock_service,
        ):
            response = client.get(f"/schedules/{uuid4()}/runs")

        assert response.status_code == 404
