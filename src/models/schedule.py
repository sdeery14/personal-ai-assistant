"""Schedule models for Feature 011 — Proactive Assistant."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Scheduled task type."""

    ONE_TIME = "one_time"
    RECURRING = "recurring"


class TaskStatus(str, Enum):
    """Scheduled task status."""

    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class TaskSource(str, Enum):
    """Who created the task."""

    USER = "user"
    AGENT = "agent"


class RunStatus(str, Enum):
    """Task run execution status."""

    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class ScheduledTask(BaseModel):
    """A one-time or recurring scheduled task."""

    id: UUID
    user_id: UUID
    name: str
    description: Optional[str] = None
    task_type: TaskType
    schedule_cron: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    timezone: str = "UTC"
    tool_name: str
    tool_args: dict = Field(default_factory=dict)
    prompt_template: str
    status: TaskStatus = TaskStatus.ACTIVE
    source: TaskSource = TaskSource.USER
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    run_count: int = 0
    fail_count: int = 0
    max_retries: int = 3
    created_at: datetime
    updated_at: datetime


class TaskRun(BaseModel):
    """A single execution of a scheduled task."""

    id: UUID
    task_id: UUID
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: RunStatus = RunStatus.RUNNING
    result: Optional[str] = None
    error: Optional[str] = None
    notification_id: Optional[UUID] = None
    retry_count: int = 0
    duration_ms: Optional[int] = None
