"use client";

import { useEntities } from "@/hooks/useEntities";
import { EntityDetail } from "./EntityDetail";
import { Input, Button } from "@/components/ui";
import { EntityType } from "@/types/knowledge";

const entityTypes: EntityType[] = ["person", "project", "tool", "concept", "organization"];

export function EntityList() {
  const {
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
  } = useEntities();

  const hasMore = entities.length < total;

  return (
    <div className="flex flex-col h-full">
      {/* Search and filter controls */}
      <div className="flex gap-3 border-b border-gray-200 p-4 dark:border-gray-700">
        <div className="flex-1">
          <Input
            placeholder="Search entities..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value as EntityType | "")}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
        >
          <option value="">All types</option>
          {entityTypes.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      {/* Entity list */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="mx-auto max-w-3xl space-y-3">
          {entities.map((entity) => (
            <EntityDetail
              key={entity.id}
              entity={entity}
              relationships={relationships[entity.id]}
              isLoadingRelationships={loadingRelationships === entity.id}
              onExpand={fetchRelationships}
            />
          ))}

          {entities.length === 0 && !isLoading && (
            <p className="py-8 text-center text-sm text-gray-400 dark:text-gray-500">
              {query || typeFilter
                ? "No entities match your search."
                : "No knowledge graph entities yet."}
            </p>
          )}

          {isLoading && (
            <p className="py-4 text-center text-sm text-gray-400 dark:text-gray-500">Loading...</p>
          )}

          {hasMore && !isLoading && (
            <div className="py-2 text-center">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => fetchEntities(entities.length)}
              >
                Load more
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
