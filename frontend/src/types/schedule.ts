export type TaskType = "one_time" | "recurring";

export type TaskStatus = "active" | "paused" | "cancelled" | "completed";

export type TaskSource = "user" | "agent";

export interface ScheduledTask {
  id: string;
  name: string;
  description: string | null;
  task_type: TaskType;
  schedule_cron: string | null;
  scheduled_at: string | null;
  timezone: string;
  tool_name: string;
  status: TaskStatus;
  source: TaskSource;
  next_run_at: string | null;
  last_run_at: string | null;
  run_count: number;
  fail_count: number;
  created_at: string;
}

export interface TaskRun {
  id: string;
  task_id: string;
  started_at: string;
  completed_at: string | null;
  status: "running" | "success" | "failed" | "retrying";
  result: string | null;
  error: string | null;
  notification_id: string | null;
  retry_count: number;
  duration_ms: number | null;
}

export interface PaginatedSchedules {
  items: ScheduledTask[];
  total: number;
  limit: number;
  offset: number;
}
