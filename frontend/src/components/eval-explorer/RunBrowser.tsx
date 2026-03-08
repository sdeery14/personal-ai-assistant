"use client";

import { useState, useMemo } from "react";
import { Card } from "@/components/ui";
import { Skeleton } from "@/components/ui/Skeleton";
import type { RunSummary } from "@/types/eval-explorer";

interface RunBrowserProps {
  runs: RunSummary[];
  isLoading: boolean;
  error: string | null;
  onSelect: (run: RunSummary) => void;
  selectedRunIds?: string[];
  onToggleSelect?: (runId: string) => void;
  onCompare?: () => void;
}

type SortKey = "timestamp" | "pass_rate" | "universal_quality" | "trace_count";
type SortDir = "asc" | "desc";

const PAGE_SIZE = 25;

function formatDate(ts: string): string {
  return new Date(ts).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatPercent(val: number | undefined): string {
  if (val === undefined || val === null) return "-";
  return `${(val * 100).toFixed(1)}%`;
}

function formatScore(val: number | null): string {
  if (val === null || val === undefined) return "-";
  return val.toFixed(2);
}

export function RunBrowser({
  runs,
  isLoading,
  error,
  onSelect,
  selectedRunIds = [],
  onToggleSelect,
  onCompare,
}: RunBrowserProps) {
  const [sortKey, setSortKey] = useState<SortKey>("timestamp");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [page, setPage] = useState(0);

  const sorted = useMemo(() => {
    const copy = [...runs];
    copy.sort((a, b) => {
      let av: number;
      let bv: number;
      switch (sortKey) {
        case "timestamp":
          av = new Date(a.timestamp).getTime();
          bv = new Date(b.timestamp).getTime();
          break;
        case "pass_rate":
          av = a.metrics.pass_rate ?? -1;
          bv = b.metrics.pass_rate ?? -1;
          break;
        case "universal_quality":
          av = a.universal_quality ?? -1;
          bv = b.universal_quality ?? -1;
          break;
        case "trace_count":
          av = a.trace_count;
          bv = b.trace_count;
          break;
      }
      return sortDir === "asc" ? av - bv : bv - av;
    });
    return copy;
  }, [runs, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const pageRuns = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
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

  if (runs.length === 0) {
    return (
      <Card className="p-4">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No runs found for this experiment.
        </p>
      </Card>
    );
  }

  return (
    <div>
      {onToggleSelect && selectedRunIds.length === 2 && onCompare && (
        <div className="mb-2 flex justify-end">
          <button
            onClick={onCompare}
            className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700"
          >
            Compare Selected ({selectedRunIds.length})
          </button>
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700">
              {onToggleSelect && <th className="px-2 py-2 w-8"></th>}
              <th
                className="cursor-pointer px-3 py-2 font-medium text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200"
                onClick={() => handleSort("timestamp")}
              >
                Timestamp{sortIndicator("timestamp")}
              </th>
              <th className="px-3 py-2 font-medium text-gray-600 dark:text-gray-400">
                Model
              </th>
              <th
                className="cursor-pointer px-3 py-2 font-medium text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200"
                onClick={() => handleSort("pass_rate")}
              >
                Pass Rate{sortIndicator("pass_rate")}
              </th>
              <th
                className="cursor-pointer px-3 py-2 font-medium text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200"
                onClick={() => handleSort("universal_quality")}
              >
                Quality{sortIndicator("universal_quality")}
              </th>
              <th
                className="cursor-pointer px-3 py-2 font-medium text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200"
                onClick={() => handleSort("trace_count")}
              >
                Cases{sortIndicator("trace_count")}
              </th>
              <th className="px-3 py-2 font-medium text-gray-600 dark:text-gray-400">
                Git SHA
              </th>
            </tr>
          </thead>
          <tbody>
            {pageRuns.map((run) => (
              <tr
                key={run.run_id}
                className="cursor-pointer border-b border-gray-100 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800/50"
                onClick={() => onSelect(run)}
              >
                {onToggleSelect && (
                  <td className="px-2 py-2">
                    <input
                      type="checkbox"
                      checked={selectedRunIds.includes(run.run_id)}
                      onChange={(e) => {
                        e.stopPropagation();
                        onToggleSelect(run.run_id);
                      }}
                      onClick={(e) => e.stopPropagation()}
                      disabled={
                        !selectedRunIds.includes(run.run_id) &&
                        selectedRunIds.length >= 2
                      }
                      className="rounded"
                    />
                  </td>
                )}
                <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                  {formatDate(run.timestamp)}
                </td>
                <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                  {run.params.model || run.params.openai_model || "-"}
                </td>
                <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                  {formatPercent(run.metrics.pass_rate)}
                </td>
                <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                  {formatScore(run.universal_quality)}
                </td>
                <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                  {run.trace_count}
                </td>
                <td className="px-3 py-2 font-mono text-xs text-gray-500 dark:text-gray-500">
                  {(run.params.git_sha || "-").substring(0, 7)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {totalPages > 1 && (
        <div className="mt-2 flex items-center justify-between px-3 text-xs text-gray-500 dark:text-gray-400">
          <span>
            Page {page + 1} of {totalPages} ({sorted.length} runs)
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="rounded px-2 py-1 hover:bg-gray-100 disabled:opacity-50 dark:hover:bg-gray-800"
            >
              Prev
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="rounded px-2 py-1 hover:bg-gray-100 disabled:opacity-50 dark:hover:bg-gray-800"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
