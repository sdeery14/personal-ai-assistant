"use client";

import { useSchedules } from "@/hooks/useSchedules";
import { ScheduleList } from "@/components/schedule/ScheduleList";

export default function SchedulesPage() {
  const {
    schedules,
    total,
    isLoading,
    statusFilter,
    setStatusFilter,
    fetchSchedules,
  } = useSchedules();

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <h1 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
        Scheduled Tasks
      </h1>
      <p className="mb-6 text-sm text-gray-500 dark:text-gray-400">
        Tasks created through conversation. Ask the assistant to schedule, pause, or cancel tasks.
      </p>
      <ScheduleList
        schedules={schedules}
        total={total}
        isLoading={isLoading}
        statusFilter={statusFilter}
        onFilterChange={setStatusFilter}
        onLoadMore={() => fetchSchedules(schedules.length)}
      />
    </div>
  );
}
