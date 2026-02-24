"use client";

import type { ScheduledTask } from "@/types/schedule";
import { ScheduleCard } from "./ScheduleCard";
import { Button } from "@/components/ui";

interface ScheduleListProps {
  schedules: ScheduledTask[];
  total: number;
  isLoading: boolean;
  statusFilter: string | null;
  onFilterChange: (status: string | null) => void;
  onLoadMore: () => void;
}

const filterTabs = [
  { value: null, label: "All" },
  { value: "active", label: "Active" },
  { value: "paused", label: "Paused" },
  { value: "completed", label: "Completed" },
];

export function ScheduleList({
  schedules,
  total,
  isLoading,
  statusFilter,
  onFilterChange,
  onLoadMore,
}: ScheduleListProps) {
  const hasMore = schedules.length < total;

  return (
    <div className="flex flex-col gap-3">
      {/* Filter tabs */}
      <div className="flex gap-1 border-b border-gray-200 dark:border-gray-700 pb-2">
        {filterTabs.map((tab) => (
          <button
            key={tab.label}
            onClick={() => onFilterChange(tab.value)}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              statusFilter === tab.value
                ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Schedule cards */}
      {isLoading && schedules.length === 0 ? (
        <div className="py-8 text-center text-sm text-gray-500 dark:text-gray-400">
          Loading schedules...
        </div>
      ) : schedules.length === 0 ? (
        <div className="py-8 text-center text-sm text-gray-500 dark:text-gray-400">
          No scheduled tasks yet. Ask the assistant to schedule something for you!
        </div>
      ) : (
        <>
          <div className="flex flex-col gap-2">
            {schedules.map((task) => (
              <ScheduleCard key={task.id} task={task} />
            ))}
          </div>

          {hasMore && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onLoadMore}
              disabled={isLoading}
              className="self-center text-xs"
            >
              {isLoading ? "Loading..." : "Load more"}
            </Button>
          )}
        </>
      )}
    </div>
  );
}
