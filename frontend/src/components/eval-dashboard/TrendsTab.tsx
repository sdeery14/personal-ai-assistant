"use client";

import { useState, useMemo } from "react";
import { Card, Button } from "@/components/ui";
import { Skeleton } from "@/components/ui/Skeleton";
import { TrendChart } from "./TrendChart";
import { useTrends, useRegressions, useRunDetail } from "@/hooks/useEvalDashboard";
import { RunDetailPanel } from "./RunDetailPanel";
import type { TrendSummary, RegressionReport } from "@/types/eval-dashboard";

const DETAIL_LIMIT_OPTIONS = [5, 10, 20, 50, 100];

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

const verdictStyles: Record<string, string> = {
  REGRESSION: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  WARNING: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  IMPROVED: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  PASS: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
};

function VerdictBadge({ verdict }: { verdict: string }) {
  return (
    <span
      className={`inline-block rounded px-2 py-0.5 text-xs font-semibold ${verdictStyles[verdict] || verdictStyles.PASS}`}
    >
      {verdict}
    </span>
  );
}

function formatDelta(delta: number): string {
  const sign = delta > 0 ? "+" : "";
  return `${sign}${delta.toFixed(1)}pp`;
}

export function TrendsTab() {
  const { summaries, isLoading, error, refresh } = useTrends(undefined, 100);
  const {
    reports,
    hasRegressions,
    isLoading: regressionsLoading,
    error: regressionsError,
  } = useRegressions();
  const [expandedType, setExpandedType] = useState<string | null>(null);

  // Build a lookup from eval_type to regression report
  const regressionByType = new Map<string, RegressionReport>();
  reports.forEach((r) => regressionByType.set(r.eval_type, r));

  const loading = isLoading || regressionsLoading;

  if (loading && summaries.length === 0) {
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
        <div className="flex items-center gap-4">
          {/* Regression banner */}
          {reports.length > 0 && (
            hasRegressions ? (
              <span className="text-sm font-medium text-red-600 dark:text-red-400">
                Regressions detected
              </span>
            ) : (
              <span className="text-sm font-medium text-green-600 dark:text-green-400">
                No regressions detected
              </span>
            )
          )}
          {regressionsError && (
            <span className="text-xs text-yellow-600 dark:text-yellow-400">
              Regression data unavailable
            </span>
          )}
        </div>
        <Button variant="secondary" size="sm" onClick={refresh} isLoading={loading}>
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
              <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-300">
                Delta
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
            {summaries.map((s: TrendSummary, idx: number) => {
              const reg = regressionByType.get(s.eval_type);
              return (
                <tr
                  key={`trend-${s.eval_type}-${idx}`}
                  className="cursor-pointer border-b border-gray-100 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-700/50"
                  onClick={() =>
                    setExpandedType(expandedType === s.eval_type ? null : s.eval_type)
                  }
                >
                  <td className="px-3 py-2 font-medium text-gray-900 dark:text-gray-100">
                    {s.eval_type}
                  </td>
                  <td className="px-3 py-2 text-right text-gray-700 dark:text-gray-300">
                    {(s.latest_pass_rate * 100).toFixed(1)}%
                  </td>
                  <td
                    className={`px-3 py-2 text-right font-medium ${
                      reg
                        ? reg.delta_pp > 0
                          ? "text-green-600 dark:text-green-400"
                          : reg.delta_pp < 0
                            ? "text-red-600 dark:text-red-400"
                            : "text-gray-500"
                        : "text-gray-400"
                    }`}
                  >
                    {reg ? formatDelta(reg.delta_pp) : "\u2014"}
                  </td>
                  <td
                    className={`px-3 py-2 text-center font-medium ${trendColors[s.trend_direction] || trendColors.stable}`}
                  >
                    {trendArrows[s.trend_direction] || trendArrows.stable}{" "}
                    {s.trend_direction}
                  </td>
                  <td className="px-3 py-2 text-right text-gray-700 dark:text-gray-300">
                    {s.run_count}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>

      {/* Detail view for expanded eval type */}
      {expandedType && (
        <DetailView
          summary={summaries.find((s) => s.eval_type === expandedType)!}
          regression={regressionByType.get(expandedType)}
        />
      )}
    </div>
  );
}

type SortKey = "timestamp" | "pass_rate" | "average_score" | "total_cases" | "error_cases" | "eval_status";
type SortDir = "asc" | "desc";

function SortArrow({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return null;
  return <span className="ml-1">{dir === "asc" ? "\u25B2" : "\u25BC"}</span>;
}

function DetailView({
  summary,
  regression,
}: {
  summary: TrendSummary;
  regression?: RegressionReport;
}) {
  const [detailLimit, setDetailLimit] = useState(10);
  const [sortKey, setSortKey] = useState<SortKey>("timestamp");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const { detail, isLoading: detailLoading, error: detailError, fetchDetail, clear: clearDetail } = useRunDetail();

  // Slice points to the most recent N (points are sorted oldest → newest)
  const visiblePoints = summary.points.slice(-detailLimit);

  const sortedPoints = useMemo(() => {
    const sorted = [...visiblePoints].sort((a, b) => {
      let cmp = 0;
      if (sortKey === "timestamp") {
        cmp = new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
      } else if (sortKey === "pass_rate") {
        cmp = a.pass_rate - b.pass_rate;
      } else if (sortKey === "average_score") {
        cmp = a.average_score - b.average_score;
      } else if (sortKey === "total_cases") {
        cmp = a.total_cases - b.total_cases;
      } else if (sortKey === "error_cases") {
        cmp = a.error_cases - b.error_cases;
      } else if (sortKey === "eval_status") {
        cmp = a.eval_status.localeCompare(b.eval_status);
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
    return sorted;
  }, [visiblePoints, sortKey, sortDir]);

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  return (
    <Card>
      <h3 className="mb-3 text-lg font-semibold text-gray-900 dark:text-gray-100">
        {summary.eval_type}
      </h3>

      {/* Regression detail */}
      {regression && (
        <div className="mb-4 flex flex-wrap items-center gap-3 text-sm">
          <VerdictBadge verdict={regression.verdict} />
          <span className="text-gray-600 dark:text-gray-400">
            Baseline: {(regression.baseline_pass_rate * 100).toFixed(1)}%
          </span>
          <span className="text-gray-600 dark:text-gray-400">
            Current: {(regression.current_pass_rate * 100).toFixed(1)}%
          </span>
          <span
            className={`font-medium ${
              regression.delta_pp > 0
                ? "text-green-600 dark:text-green-400"
                : regression.delta_pp < 0
                  ? "text-red-600 dark:text-red-400"
                  : "text-gray-500"
            }`}
          >
            {formatDelta(regression.delta_pp)}
          </span>
          <span className="text-gray-500 dark:text-gray-400">
            (threshold: {(regression.threshold * 100).toFixed(1)}%)
          </span>
        </div>
      )}

      {/* Changed prompts */}
      {regression && regression.changed_prompts.length > 0 && (
        <div className="mb-4 text-xs text-gray-500 dark:text-gray-400">
          {regression.changed_prompts.map((c, i) => (
            <span key={i}>
              Changed: {c.prompt_name} v{c.from_version} &rarr; v{c.to_version}
              {i < regression.changed_prompts.length - 1 && ", "}
            </span>
          ))}
        </div>
      )}

      {/* Runs dropdown */}
      <div className="mb-3 flex items-center gap-2">
        <label className="text-sm text-gray-600 dark:text-gray-400">
          Runs:
        </label>
        <select
          value={detailLimit}
          onChange={(e) => setDetailLimit(Number(e.target.value))}
          className="rounded border border-gray-300 bg-white px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
        >
          {DETAIL_LIMIT_OPTIONS.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
      </div>

      <TrendChart
        points={visiblePoints}
        promptChanges={summary.prompt_changes}
      />
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700">
              <th className="px-2 py-1.5 text-left font-medium text-gray-600 dark:text-gray-400">
                Run ID
              </th>
              <th
                className="cursor-pointer select-none px-2 py-1.5 text-left font-medium text-gray-600 dark:text-gray-400"
                onClick={() => handleSort("timestamp")}
              >
                Date
                <SortArrow active={sortKey === "timestamp"} dir={sortDir} />
              </th>
              <th
                className="cursor-pointer select-none px-2 py-1.5 text-right font-medium text-gray-600 dark:text-gray-400"
                onClick={() => handleSort("pass_rate")}
              >
                Pass Rate
                <SortArrow active={sortKey === "pass_rate"} dir={sortDir} />
              </th>
              <th
                className="cursor-pointer select-none px-2 py-1.5 text-right font-medium text-gray-600 dark:text-gray-400"
                onClick={() => handleSort("average_score")}
              >
                Avg Score
                <SortArrow active={sortKey === "average_score"} dir={sortDir} />
              </th>
              <th
                className="cursor-pointer select-none px-2 py-1.5 text-right font-medium text-gray-600 dark:text-gray-400"
                onClick={() => handleSort("total_cases")}
              >
                Cases
                <SortArrow active={sortKey === "total_cases"} dir={sortDir} />
              </th>
              <th
                className="cursor-pointer select-none px-2 py-1.5 text-right font-medium text-gray-600 dark:text-gray-400"
                onClick={() => handleSort("error_cases")}
              >
                Errors
                <SortArrow active={sortKey === "error_cases"} dir={sortDir} />
              </th>
              <th
                className="cursor-pointer select-none px-2 py-1.5 text-left font-medium text-gray-600 dark:text-gray-400"
                onClick={() => handleSort("eval_status")}
              >
                Status
                <SortArrow active={sortKey === "eval_status"} dir={sortDir} />
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedPoints.map((p) => (
              <tr
                key={p.run_id}
                className={`cursor-pointer border-b border-gray-100 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-700/50 ${
                  selectedRunId === p.run_id ? "bg-blue-50/50 dark:bg-blue-900/10" : ""
                }`}
                onClick={() => {
                  if (selectedRunId === p.run_id) {
                    setSelectedRunId(null);
                    clearDetail();
                  } else {
                    setSelectedRunId(p.run_id);
                    fetchDetail(p.run_id, summary.eval_type);
                  }
                }}
              >
                <td className="px-2 py-1.5 font-mono text-gray-700 dark:text-gray-300">
                  {p.run_id.slice(0, 8)}
                </td>
                <td className="px-2 py-1.5 text-gray-600 dark:text-gray-400">
                  {new Date(p.timestamp).toLocaleString()}
                </td>
                <td className="px-2 py-1.5 text-right text-gray-700 dark:text-gray-300">
                  {(p.pass_rate * 100).toFixed(1)}%
                </td>
                <td className="px-2 py-1.5 text-right text-gray-700 dark:text-gray-300">
                  {p.average_score > 0 ? p.average_score.toFixed(2) : "-"}
                </td>
                <td className="px-2 py-1.5 text-right text-gray-700 dark:text-gray-300">
                  {p.total_cases}
                </td>
                <td className="px-2 py-1.5 text-right text-gray-700 dark:text-gray-300">
                  {p.error_cases > 0 ? (
                    <span className="text-red-600 dark:text-red-400">{p.error_cases}</span>
                  ) : (
                    0
                  )}
                </td>
                <td className="px-2 py-1.5">
                  <span
                    className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${
                      p.eval_status === "error"
                        ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                        : p.eval_status === "partial"
                          ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                          : "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                    }`}
                  >
                    {p.eval_status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Run detail panel */}
      {selectedRunId && detailLoading && (
        <div className="mt-4 text-sm text-gray-500 dark:text-gray-400">
          Loading run detail...
        </div>
      )}
      {selectedRunId && detailError && (
        <div className="mt-4 text-sm text-red-600 dark:text-red-400">
          {detailError}
        </div>
      )}
      {selectedRunId && detail && detail.run_id === selectedRunId && (
        <div className="mt-4">
          <RunDetailPanel
            detail={detail}
            onClose={() => {
              setSelectedRunId(null);
              clearDetail();
            }}
          />
        </div>
      )}
    </Card>
  );
}
