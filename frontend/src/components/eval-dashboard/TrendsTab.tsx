"use client";

import { useState } from "react";
import { Card, Button } from "@/components/ui";
import { Skeleton } from "@/components/ui/Skeleton";
import { TrendChart } from "./TrendChart";
import { useTrends } from "@/hooks/useEvalDashboard";
import type { TrendSummary } from "@/types/eval-dashboard";

const LIMIT_OPTIONS = [5, 10, 20, 50];

const trendColors: Record<string, string> = {
  improving: "text-green-600 dark:text-green-400",
  stable: "text-gray-500 dark:text-gray-400",
  degrading: "text-red-600 dark:text-red-400",
};

const trendArrows: Record<string, string> = {
  improving: "\u2191",
  stable: "\u2192",
  degrading: "\u2193",
};

export function TrendsTab() {
  const [limit, setLimit] = useState(10);
  const { summaries, isLoading, error, refresh } = useTrends(undefined, limit);
  const [expandedType, setExpandedType] = useState<string | null>(null);

  if (isLoading && summaries.length === 0) {
    return (
      <Card>
        <div className="space-y-3">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        <Button variant="secondary" size="sm" onClick={refresh} className="mt-2">
          Retry
        </Button>
      </Card>
    );
  }

  if (summaries.length === 0) {
    return (
      <Card>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No eval data available yet
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600 dark:text-gray-400">
            Runs:
          </label>
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="rounded border border-gray-300 bg-white px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
          >
            {LIMIT_OPTIONS.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>
        <Button variant="secondary" size="sm" onClick={refresh} isLoading={isLoading}>
          Refresh
        </Button>
      </div>

      <Card padding="sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700">
              <th className="px-3 py-2 text-left font-medium text-gray-700 dark:text-gray-300">
                Eval Type
              </th>
              <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-300">
                Latest Pass Rate
              </th>
              <th className="px-3 py-2 text-center font-medium text-gray-700 dark:text-gray-300">
                Trend
              </th>
              <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-300">
                Runs
              </th>
            </tr>
          </thead>
          <tbody>
            {summaries.map((s: TrendSummary) => (
              <tr
                key={s.evalType}
                className="cursor-pointer border-b border-gray-100 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-700/50"
                onClick={() =>
                  setExpandedType(expandedType === s.evalType ? null : s.evalType)
                }
              >
                <td className="px-3 py-2 font-medium text-gray-900 dark:text-gray-100">
                  {s.evalType}
                </td>
                <td className="px-3 py-2 text-right text-gray-700 dark:text-gray-300">
                  {(s.latestPassRate * 100).toFixed(1)}%
                </td>
                <td
                  className={`px-3 py-2 text-center font-medium ${trendColors[s.trendDirection] || trendColors.stable}`}
                >
                  {trendArrows[s.trendDirection] || trendArrows.stable}{" "}
                  {s.trendDirection}
                </td>
                <td className="px-3 py-2 text-right text-gray-700 dark:text-gray-300">
                  {s.runCount}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {/* Detail view for expanded eval type */}
      {expandedType && (
        <DetailView
          summary={summaries.find((s) => s.evalType === expandedType)!}
        />
      )}
    </div>
  );
}

function DetailView({ summary }: { summary: TrendSummary }) {
  return (
    <Card>
      <h3 className="mb-3 text-lg font-semibold text-gray-900 dark:text-gray-100">
        {summary.evalType}
      </h3>
      <TrendChart
        points={summary.points}
        promptChanges={summary.promptChanges}
      />
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700">
              <th className="px-2 py-1.5 text-left font-medium text-gray-600 dark:text-gray-400">
                Run ID
              </th>
              <th className="px-2 py-1.5 text-left font-medium text-gray-600 dark:text-gray-400">
                Date
              </th>
              <th className="px-2 py-1.5 text-right font-medium text-gray-600 dark:text-gray-400">
                Pass Rate
              </th>
              <th className="px-2 py-1.5 text-right font-medium text-gray-600 dark:text-gray-400">
                Avg Score
              </th>
              <th className="px-2 py-1.5 text-left font-medium text-gray-600 dark:text-gray-400">
                Status
              </th>
            </tr>
          </thead>
          <tbody>
            {summary.points.map((p) => (
              <tr
                key={p.runId}
                className="border-b border-gray-100 dark:border-gray-800"
              >
                <td className="px-2 py-1.5 font-mono text-gray-700 dark:text-gray-300">
                  {p.runId.slice(0, 8)}
                </td>
                <td className="px-2 py-1.5 text-gray-600 dark:text-gray-400">
                  {new Date(p.timestamp).toLocaleString()}
                </td>
                <td className="px-2 py-1.5 text-right text-gray-700 dark:text-gray-300">
                  {(p.passRate * 100).toFixed(1)}%
                </td>
                <td className="px-2 py-1.5 text-right text-gray-700 dark:text-gray-300">
                  {p.averageScore.toFixed(2)}
                </td>
                <td className="px-2 py-1.5">
                  <span
                    className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${
                      p.evalStatus === "passed"
                        ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                        : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                    }`}
                  >
                    {p.evalStatus}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
