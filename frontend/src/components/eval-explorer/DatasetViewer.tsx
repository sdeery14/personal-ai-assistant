"use client";

import { useState } from "react";
import { Card } from "@/components/ui";
import { Skeleton } from "@/components/ui/Skeleton";
import type { DatasetDetail, DatasetCase } from "@/types/eval-explorer";

interface DatasetViewerProps {
  datasets: DatasetDetail[];
  isLoading: boolean;
  error: string | null;
  onSelectDataset: (datasetId: string) => void;
  selectedDataset: DatasetDetail | null;
  selectedDatasetLoading: boolean;
}

function CaseRow({ c }: { c: DatasetCase }) {
  const [expanded, setExpanded] = useState(false);

  // Extract a display prompt from inputs
  const prompt =
    (c.inputs.question as string) ||
    (c.inputs.user_prompt as string) ||
    (c.inputs.message as string) ||
    (c.inputs.input as string) ||
    JSON.stringify(c.inputs);

  // Extract rubric from expectations
  const rubric =
    (c.expectations.rubric as string) ||
    (c.expectations.expected_behavior as string) ||
    null;

  return (
    <div className="border-b border-gray-100 dark:border-gray-800">
      <div
        className="flex cursor-pointer items-center gap-3 px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-800/50"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="text-xs text-gray-400">
          {expanded ? "\u25BC" : "\u25B6"}
        </span>
        <span className="font-mono text-xs text-gray-500">
          {c.record_id.substring(0, 12)}
        </span>
        <span className="flex-1 truncate text-sm text-gray-700 dark:text-gray-300">
          {prompt.substring(0, 120)}
          {prompt.length > 120 ? "..." : ""}
        </span>
      </div>
      {expanded && (
        <div className="bg-gray-50 px-6 py-3 dark:bg-gray-900/50">
          <div className="mb-2">
            <h4 className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">
              Inputs
            </h4>
            {Object.entries(c.inputs).map(([key, val]) => (
              <div key={key} className="mb-1 text-sm">
                <span className="font-mono text-xs text-gray-500">{key}:</span>{" "}
                <span className="whitespace-pre-wrap text-gray-800 dark:text-gray-200">
                  {typeof val === "object" ? JSON.stringify(val, null, 2) : String(val)}
                </span>
              </div>
            ))}
          </div>
          {Object.keys(c.expectations).length > 0 && (
            <div className="mb-2">
              <h4 className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">
                Expectations
              </h4>
              {rubric ? (
                <p className="whitespace-pre-wrap text-sm text-gray-800 dark:text-gray-200">
                  {rubric}
                </p>
              ) : (
                Object.entries(c.expectations).map(([key, val]) => (
                  <div key={key} className="mb-1 text-sm">
                    <span className="font-mono text-xs text-gray-500">{key}:</span>{" "}
                    <span className="whitespace-pre-wrap text-gray-800 dark:text-gray-200">
                      {typeof val === "object" ? JSON.stringify(val, null, 2) : String(val)}
                    </span>
                  </div>
                ))
              )}
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
          No datasets found. Run an evaluation to register datasets in MLflow.
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
          <p className="mb-3 text-xs text-gray-400">
            {selectedDataset.case_count} cases
            {selectedDataset.version && ` \u00B7 v${selectedDataset.version}`}
            {selectedDataset.dataset_type && ` \u00B7 ${selectedDataset.dataset_type}`}
            {selectedDataset.source_file && ` \u00B7 ${selectedDataset.source_file}`}
          </p>
          {selectedDatasetLoading ? (
            <Skeleton className="h-40 w-full" />
          ) : (
            selectedDataset.cases.map((c) => (
              <CaseRow key={c.record_id} c={c} />
            ))
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
              Type
            </th>
            <th className="px-3 py-2 font-medium text-gray-600 dark:text-gray-400">
              Cases
            </th>
            <th className="px-3 py-2 font-medium text-gray-600 dark:text-gray-400">
              Version
            </th>
            <th className="px-3 py-2 font-medium text-gray-600 dark:text-gray-400">
              Source
            </th>
          </tr>
        </thead>
        <tbody>
          {datasets.map((ds) => (
            <tr
              key={ds.dataset_id}
              className="cursor-pointer border-b border-gray-100 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800/50"
              onClick={() => onSelectDataset(ds.dataset_id)}
            >
              <td className="px-3 py-2 font-medium text-blue-600 dark:text-blue-400">
                {ds.name}
              </td>
              <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                {ds.dataset_type || "-"}
              </td>
              <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                {ds.case_count}
              </td>
              <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                {ds.version || "-"}
              </td>
              <td className="px-3 py-2 font-mono text-xs text-gray-500">
                {ds.source_file || "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
