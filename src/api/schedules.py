"""Schedules API endpoints for Feature 011."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
import structlog

from src.api.dependencies import get_current_user
from src.models.user import User
from src.services.schedule_service import ScheduleService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/schedules", tags=["Schedules"])


def _format_task(task: dict) -> dict:
    """Format a task dict for API response."""
    return {
        "id": str(task["id"]),
        "name": task["name"],
        "description": task.get("description"),
        "task_type": task["task_type"],
        "schedule_cron": task.get("schedule_cron"),
        "scheduled_at": task["scheduled_at"].isoformat() if task.get("scheduled_at") else None,
        "timezone": task.get("timezone", "UTC"),
        "tool_name": task["tool_name"],
        "status": task["status"],
        "source": task.get("source", "user"),
        "next_run_at": task["next_run_at"].isoformat() if task.get("next_run_at") else None,
        "last_run_at": task["last_run_at"].isoformat() if task.get("last_run_at") else None,
        "run_count": task.get("run_count", 0),
        "fail_count": task.get("fail_count", 0),
        "created_at": task["created_at"].isoformat() if task.get("created_at") else None,
    }


def _format_run(run: dict) -> dict:
    """Format a task run dict for API response."""
    return {
        "id": str(run["id"]),
        "task_id": str(run["task_id"]),
        "started_at": run["started_at"].isoformat() if run.get("started_at") else None,
        "completed_at": run["completed_at"].isoformat() if run.get("completed_at") else None,
        "status": run["status"],
        "result": run.get("result"),
        "error": run.get("error"),
        "notification_id": str(run["notification_id"]) if run.get("notification_id") else None,
        "retry_count": run.get("retry_count", 0),
        "duration_ms": run.get("duration_ms"),
    }


@router.get("")
async def list_schedules(
    status: str | None = Query(default=None, description="Filter by status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
) -> dict:
    """List scheduled tasks for the authenticated user."""
    service = ScheduleService()
    tasks, total = await service.list_tasks(
        user_id=str(current_user.id),
        status_filter=status,
        limit=limit,
        offset=offset,
    )

    return {
        "items": [_format_task(t) for t in tasks],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{task_id}")
async def get_schedule(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get a single scheduled task with recent runs."""
    service = ScheduleService()
    task = await service.get_task(str(task_id), str(current_user.id))

    if task is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Also fetch recent runs
    runs, _ = await service.get_task_runs(
        str(task_id), str(current_user.id), limit=5
    )

    result = _format_task(task)
    result["recent_runs"] = [_format_run(r) for r in runs]
    return result


@router.get("/{task_id}/runs")
async def list_schedule_runs(
    task_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get run history for a scheduled task."""
    service = ScheduleService()
    runs, total = await service.get_task_runs(
        str(task_id), str(current_user.id), limit=limit, offset=offset
    )

    if total == 0:
        # Check if task exists
        task = await service.get_task(str(task_id), str(current_user.id))
        if task is None:
            raise HTTPException(status_code=404, detail="Schedule not found")

    return {
        "items": [_format_run(r) for r in runs],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
