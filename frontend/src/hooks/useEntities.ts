"use client";

import { useState, useCallback, useEffect } from "react";
import { useSession } from "next-auth/react";
import { Entity, EntityType, Relationship } from "@/types/knowledge";
import { PaginatedResponse } from "@/types/chat";
import { apiClient } from "@/lib/api-client";

export function useEntities() {
  const { data: session } = useSession();
  const [entities, setEntities] = useState<Entity[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<EntityType | "">("");
  const [relationships, setRelationships] = useState<Record<string, Relationship[]>>({});
  const [loadingRelationships, setLoadingRelationships] = useState<string | null>(null);

  const fetchEntities = useCallback(
    async (offset = 0) => {
      if (!session?.accessToken) return;
      setIsLoading(true);
      try {
        const params: Record<string, string | number> = { limit: 50, offset };
        if (query) params.q = query;
        if (typeFilter) params.type = typeFilter;

        const data = await apiClient.get<PaginatedResponse<Entity>>(
          "/entities",
          params,
        );

        if (offset === 0) {
          setEntities(data.items);
        } else {
          setEntities((prev) => [...prev, ...data.items]);
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

  const fetchRelationships = useCallback(
    async (entityId: string) => {
      if (!session?.accessToken) return;
      if (relationships[entityId]) return; // Already loaded

      setLoadingRelationships(entityId);
      try {
        const data = await apiClient.get<Relationship[]>(
          `/entities/${entityId}/relationships`,
        );
        setRelationships((prev) => ({ ...prev, [entityId]: data }));
      } catch {
        setRelationships((prev) => ({ ...prev, [entityId]: [] }));
      } finally {
        setLoadingRelationships(null);
      }
    },
    [session?.accessToken, relationships],
  );

  useEffect(() => {
    fetchEntities();
  }, [fetchEntities]);

  return {
    entities,
    total,
    isLoading,
    query,
    setQuery,
    typeFilter,
    setTypeFilter,
    relationships,
    loadingRelationships,
    fetchEntities,
    fetchRelationships,
  };
}
