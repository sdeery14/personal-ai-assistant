"use client";

import type { ScheduledTask } from "@/types/schedule";

interface ScheduleCardProps {
  task: ScheduledTask;
}

const statusConfig: Record<string, { label: string; className: string }> = {
  active: {
    label: "Active",
    className:
      "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  },
  paused: {
    label: "Paused",
    className:
      "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  },
  cancelled: {
    label: "Cancelled",
    className:
      "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  },
  completed: {
    label: "Completed",
    className:
      "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400",
  },
};

const typeConfig: Record<string, { label: string; className: string }> = {
  one_time: {
    label: "One-time",
    className:
      "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  },
  recurring: {
    label: "Recurring",
    className:
      "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  },
};

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

function formatFutureTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();

  if (diffMs < 0) return "overdue";

  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 60) return `in ${diffMins}m`;
  if (diffHours < 24) return `in ${diffHours}h`;
  if (diffDays < 7) return `in ${diffDays}d`;
  return date.toLocaleDateString();
}

export function ScheduleCard({ task }: ScheduleCardProps) {
  const statusStyle = statusConfig[task.status] || statusConfig.active;
  const typeStyle = typeConfig[task.task_type] || typeConfig.one_time;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">
          {task.name}
        </h3>
        <div className="flex gap-1.5 shrink-0">
          <span
            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${typeStyle.className}`}
          >
            {typeStyle.label}
          </span>
          <span
            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${statusStyle.className}`}
          >
            {statusStyle.label}
          </span>
        </div>
      </div>

      {task.description && (
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          {task.description}
        </p>
      )}

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
        {task.schedule_cron && (
          <span title="Cron schedule">
            Schedule: <code className="text-gray-700 dark:text-gray-300">{task.schedule_cron}</code>
          </span>
        )}

        {task.next_run_at && (
          <span>
            Next run: {formatFutureTime(task.next_run_at)}
          </span>
        )}

        {task.last_run_at && (
          <span>
            Last run: {formatRelativeTime(task.last_run_at)}
          </span>
        )}

        <span>
          Runs: {task.run_count}
          {task.fail_count > 0 && (
            <span className="text-red-500 dark:text-red-400">
              {" "}({task.fail_count} failed)
            </span>
          )}
        </span>
      </div>
    </div>
  );
}
