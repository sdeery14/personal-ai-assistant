"use client";

import { useState, useCallback, useEffect } from "react";
import { useSession } from "next-auth/react";
import type { ScheduledTask } from "@/types/schedule";
import { apiClient } from "@/lib/api-client";

export function useSchedules() {
  const { data: session } = useSession();
  const [schedules, setSchedules] = useState<ScheduledTask[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);

  const fetchSchedules = useCallback(
    async (offset = 0) => {
      if (!session?.accessToken) return;
      setIsLoading(true);
      try {
        const params: Record<string, string | number> = { limit: 20, offset };
        if (statusFilter) {
          params.status = statusFilter;
        }
        const data = await apiClient.getSchedules(params);
        if (offset === 0) {
          setSchedules(data.items);
        } else {
          setSchedules((prev) => [...prev, ...data.items]);
        }
        setTotal(data.total);
      } catch {
        // silently fail
      } finally {
        setIsLoading(false);
      }
    },
    [session?.accessToken, statusFilter],
  );

  // Fetch on mount and when filter changes
  useEffect(() => {
    fetchSchedules();
  }, [fetchSchedules]);

  return {
    schedules,
    total,
    isLoading,
    statusFilter,
    setStatusFilter,
    fetchSchedules,
  };
}
