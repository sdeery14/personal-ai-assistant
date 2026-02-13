"use client";

import { useMemories } from "@/hooks/useMemories";
import { MemoryCard } from "./MemoryCard";
import { Input, Button } from "@/components/ui";
import { MemoryType } from "@/types/memory";

const memoryTypes: MemoryType[] = ["fact", "preference", "decision", "note", "episode"];

export function MemoryList() {
  const {
    memories,
    total,
    isLoading,
    query,
    setQuery,
    typeFilter,
    setTypeFilter,
    fetchMemories,
    deleteMemory,
  } = useMemories();

  const hasMore = memories.length < total;

  return (
    <div className="flex flex-col h-full">
      {/* Search and filter controls */}
      <div className="flex gap-3 border-b border-gray-200 p-4">
        <div className="flex-1">
          <Input
            placeholder="Search memories..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value as MemoryType | "")}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm"
        >
          <option value="">All types</option>
          {memoryTypes.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      {/* Memory list */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="mx-auto max-w-3xl space-y-3">
          {memories.map((memory) => (
            <MemoryCard
              key={memory.id}
              memory={memory}
              onDelete={deleteMemory}
            />
          ))}

          {memories.length === 0 && !isLoading && (
            <p className="py-8 text-center text-sm text-gray-400">
              {query || typeFilter ? "No memories match your search." : "No memories stored yet."}
            </p>
          )}

          {isLoading && (
            <p className="py-4 text-center text-sm text-gray-400">Loading...</p>
          )}

          {hasMore && !isLoading && (
            <div className="py-2 text-center">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => fetchMemories(memories.length)}
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
