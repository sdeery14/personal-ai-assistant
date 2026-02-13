"use client";

import { useState, useCallback, useEffect } from "react";
import { useSession } from "next-auth/react";
import { MemoryItem, MemoryType } from "@/types/memory";
import { PaginatedResponse } from "@/types/chat";
import { apiClient } from "@/lib/api-client";

export function useMemories() {
  const { data: session } = useSession();
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<MemoryType | "">("");

  const fetchMemories = useCallback(
    async (offset = 0) => {
      if (!session?.accessToken) return;
      setIsLoading(true);
      try {
        const params: Record<string, string | number> = { limit: 50, offset };
        if (query) params.q = query;
        if (typeFilter) params.type = typeFilter;

        const data = await apiClient.get<PaginatedResponse<MemoryItem>>(
          "/memories",
          params,
        );

        if (offset === 0) {
          setMemories(data.items);
        } else {
          setMemories((prev) => [...prev, ...data.items]);
        }
        setTotal(data.total);
      } catch {
        // silently fail
      } finally {
        setIsLoading(false);
      }
    },
    [session?.accessToken, query, typeFilter],
  );

  const deleteMemory = useCallback(
    async (id: string) => {
      if (!session?.accessToken) return;
      // Optimistic update
      setMemories((prev) => prev.filter((m) => m.id !== id));
      setTotal((prev) => prev - 1);
      try {
        await apiClient.del(`/memories/${id}`);
      } catch {
        // Revert on failure
        fetchMemories();
      }
    },
    [session?.accessToken, fetchMemories],
  );

  useEffect(() => {
    fetchMemories();
  }, [fetchMemories]);

  return {
    memories,
    total,
    isLoading,
    query,
    setQuery,
    typeFilter,
    setTypeFilter,
    fetchMemories,
    deleteMemory,
  };
}
