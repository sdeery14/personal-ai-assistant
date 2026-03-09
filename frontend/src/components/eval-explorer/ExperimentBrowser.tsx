"use client";

import { useState, useMemo } from "react";
import { Card } from "@/components/ui";
import { Skeleton } from "@/components/ui/Skeleton";
import type { ExperimentSummary } from "@/types/eval-explorer";

interface ExperimentBrowserProps {
  experiments: ExperimentSummary[];
  isLoading: boolean;
  error: string | null;
  onSelect: (experiment: ExperimentSummary) => void;
}

type SortKey = "name" | "eval_type" | "run_count" | "last_run_timestamp" | "latest_pass_rate" | "latest_universal_quality";
type SortDir = "asc" | "desc";

function formatDate(ts: string | null): string {
  if (!ts) return "-";
  return new Date(ts).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatPercent(val: number | null): string {
  if (val === null) return "-";
  return `${(val * 100).toFixed(1)}%`;
}

function formatScore(val: number | null): string {
  if (val === null) return "-";
  return val.toFixed(2);
}

export function ExperimentBrowser({
  experiments,
  isLoading,
  error,
  onSelect,
}: ExperimentBrowserProps) {
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const sorted = useMemo(() => {
    const copy = [...experiments];
    copy.sort((a, b) => {
      let av: string | number | null = a[sortKey] as string | number | null;
      let bv: string | number | null = b[sortKey] as string | number | null;
      if (av === null) av = sortDir === "asc" ? Infinity : -Infinity;
      if (bv === null) bv = sortDir === "asc" ? Infinity : -Infinity;
      if (typeof av === "string" && typeof bv === "string") {
        return sortDir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      return sortDir === "asc"
        ? (av as number) - (bv as number)
        : (bv as number) - (av as number);
    });
    return copy;
  }, [experiments, sortKey, sortDir]);

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  function sortIndicator(key: SortKey) {
    if (sortKey !== key) return "";
    return sortDir === "asc" ? " \u25B2" : " \u25BC";
  }

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

  if (experiments.length === 0) {
    return (
      <Card className="p-4">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No experiments found. Run some evals first.
        </p>
      </Card>
    );
  }

  const headers: { key: SortKey; label: string }[] = [
    { key: "name", label: "Experiment" },
    { key: "eval_type", label: "Eval Type" },
    { key: "run_count", label: "Runs" },
    { key: "last_run_timestamp", label: "Last Run" },
    { key: "latest_pass_rate", label: "Pass Rate" },
    { key: "latest_universal_quality", label: "Quality" },
  ];

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-gray-200 dark:border-gray-700">
            {headers.map((h) => (
              <th
                key={h.key}
                className="cursor-pointer px-3 py-2 font-medium text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200"
                onClick={() => handleSort(h.key)}
              >
                {h.label}
                {sortIndicator(h.key)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((exp) => (
            <tr
              key={exp.experiment_id}
              className="cursor-pointer border-b border-gray-100 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800/50"
              onClick={() => onSelect(exp)}
            >
              <td className="px-3 py-2 font-medium text-blue-600 dark:text-blue-400">
                {exp.name}
              </td>
              <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                {exp.eval_type}
              </td>
              <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                {exp.run_count}
              </td>
              <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                {formatDate(exp.last_run_timestamp)}
              </td>
              <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                {formatPercent(exp.latest_pass_rate)}
              </td>
              <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                {formatScore(exp.latest_universal_quality)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
