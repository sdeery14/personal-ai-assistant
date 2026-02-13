"use client";

import { useState } from "react";
import { Entity, Relationship } from "@/types/knowledge";

interface EntityDetailProps {
  entity: Entity;
  relationships: Relationship[] | undefined;
  isLoadingRelationships: boolean;
  onExpand: (entityId: string) => void;
}

const typeBadgeColors: Record<string, string> = {
  person: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200",
  project: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200",
  tool: "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-200",
  concept: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-200",
  organization: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200",
};

export function EntityDetail({
  entity,
  relationships,
  isLoadingRelationships,
  onExpand,
}: EntityDetailProps) {
  const [expanded, setExpanded] = useState(false);

  const badgeColor = typeBadgeColors[entity.type] || "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200";

  const toggleExpand = () => {
    if (!expanded) {
      onExpand(entity.id);
    }
    setExpanded(!expanded);
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
      <button
        onClick={toggleExpand}
        className="w-full p-4 text-left hover:bg-gray-50 transition-colors dark:hover:bg-gray-700/50"
      >
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-medium text-gray-900 dark:text-gray-100">{entity.name}</h3>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${badgeColor}`}>
                {entity.type}
              </span>
            </div>
            {entity.description && (
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{entity.description}</p>
            )}
            {entity.aliases.length > 0 && (
              <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
                Also known as: {entity.aliases.join(", ")}
              </p>
            )}
          </div>
          <span className="text-xs text-gray-400 dark:text-gray-500">
            {entity.mention_count} mention{entity.mention_count !== 1 ? "s" : ""}
          </span>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-gray-100 px-4 py-3 dark:border-gray-700">
          {isLoadingRelationships && (
            <p className="text-sm text-gray-400 dark:text-gray-500">Loading relationships...</p>
          )}
          {relationships && relationships.length === 0 && (
            <p className="text-sm text-gray-400 dark:text-gray-500">No relationships found.</p>
          )}
          {relationships && relationships.length > 0 && (
            <ul className="space-y-2">
              {relationships.map((rel) => (
                <li key={rel.id} className="flex items-center gap-2 text-sm">
                  <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs font-mono text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                    {rel.relationship_type}
                  </span>
                  <span className="text-gray-700 dark:text-gray-300">
                    {rel.target_entity
                      ? rel.target_entity.name
                      : rel.source_entity?.name || "Unknown"}
                  </span>
                  {rel.context && (
                    <span className="text-xs text-gray-400 truncate dark:text-gray-500">
                      — {rel.context}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
