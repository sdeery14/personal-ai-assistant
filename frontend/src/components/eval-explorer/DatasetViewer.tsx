"use client";

import { useState } from "react";
import { Card } from "@/components/ui";
import { Skeleton } from "@/components/ui/Skeleton";
import type { DatasetDetail, DatasetCase } from "@/types/eval-explorer";

interface DatasetViewerProps {
  datasets: DatasetDetail[];
  isLoading: boolean;
  error: string | null;
  onSelectDataset: (name: string) => void;
  selectedDataset: DatasetDetail | null;
  selectedDatasetLoading: boolean;
}

function CaseRow({ c }: { c: DatasetCase }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border-b border-gray-100 dark:border-gray-800">
      <div
        className="flex cursor-pointer items-center gap-3 px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-800/50"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="text-xs text-gray-400">
          {expanded ? "\u25BC" : "\u25B6"}
        </span>
        <span className="font-mono text-xs text-gray-500">{c.id}</span>
        <span className="flex-1 truncate text-sm text-gray-700 dark:text-gray-300">
          {c.user_prompt.substring(0, 120)}
          {c.user_prompt.length > 120 ? "..." : ""}
        </span>
        {c.tags.length > 0 && (
          <div className="flex gap-1">
            {c.tags.map((tag) => (
              <span
                key={tag}
                className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-400"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
      {expanded && (
        <div className="bg-gray-50 px-6 py-3 dark:bg-gray-900/50">
          <div className="mb-2">
            <h4 className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">
              Prompt
            </h4>
            <p className="whitespace-pre-wrap text-sm text-gray-800 dark:text-gray-200">
              {c.user_prompt}
            </p>
          </div>
          {c.rubric && (
            <div className="mb-2">
              <h4 className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">
                Rubric
              </h4>
              <p className="whitespace-pre-wrap text-sm text-gray-800 dark:text-gray-200">
                {c.rubric}
              </p>
            </div>
          )}
          {Object.keys(c.extra).length > 0 && (
            <div>
              <h4 className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">
                Extra Fields
              </h4>
              <div className="space-y-1">
                {Object.entries(c.extra).map(([key, val]) => (
                  <div key={key} className="text-xs">
                    <span className="font-mono text-gray-500">{key}:</span>{" "}
                    <span className="text-gray-700 dark:text-gray-300">
                      {typeof val === "object" ? JSON.stringify(val) : String(val)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function DatasetViewer({
  datasets,
  isLoading,
  error,
  onSelectDataset,
  selectedDataset,
  selectedDatasetLoading,
}: DatasetViewerProps) {
  if (error) {
    return (
      <Card className="p-4">
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card className="p-4">
        <Skeleton className="mb-2 h-6 w-48" />
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="mb-1 h-10 w-full" />
        ))}
      </Card>
    );
  }

  if (datasets.length === 0) {
    return (
      <Card className="p-4">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No datasets found.
        </p>
      </Card>
    );
  }

  // If a dataset is selected, show its cases
  if (selectedDataset) {
    return (
      <div>
        <button
          onClick={() => onSelectDataset("")}
          className="mb-3 text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
        >
          &larr; Back to datasets
        </button>
        <Card className="p-4">
          <h3 className="mb-1 text-sm font-medium text-gray-900 dark:text-white">
            {selectedDataset.name}
          </h3>
          <p className="mb-1 text-xs text-gray-500 dark:text-gray-400">
            {selectedDataset.description}
          </p>
          <p className="mb-3 text-xs text-gray-400">
            {selectedDataset.case_count} cases
            {selectedDataset.version && ` \u00B7 v${selectedDataset.version}`}
            {` \u00B7 ${selectedDataset.file_path}`}
          </p>
          {selectedDatasetLoading ? (
            <Skeleton className="h-40 w-full" />
          ) : (
            selectedDataset.cases.map((c) => <CaseRow key={c.id} c={c} />)
          )}
        </Card>
      </div>
    );
  }

  // Dataset list
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-gray-200 dark:border-gray-700">
            <th className="px-3 py-2 font-medium text-gray-600 dark:text-gray-400">
              Dataset
            </th>
            <th className="px-3 py-2 font-medium text-gray-600 dark:text-gray-400">
              Description
            </th>
            <th className="px-3 py-2 font-medium text-gray-600 dark:text-gray-400">
              Cases
            </th>
            <th className="px-3 py-2 font-medium text-gray-600 dark:text-gray-400">
              Version
            </th>
          </tr>
        </thead>
        <tbody>
          {datasets.map((ds) => (
            <tr
              key={ds.name}
              className="cursor-pointer border-b border-gray-100 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800/50"
              onClick={() => onSelectDataset(ds.name)}
            >
              <td className="px-3 py-2 font-medium text-blue-600 dark:text-blue-400">
                {ds.name}
              </td>
              <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                {ds.description || "-"}
              </td>
              <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                {ds.case_count}
              </td>
              <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                {ds.version || "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
