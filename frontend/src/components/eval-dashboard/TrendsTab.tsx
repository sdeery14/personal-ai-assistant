"use client";

import { useState } from "react";
import { Card, Button } from "@/components/ui";
import { Skeleton } from "@/components/ui/Skeleton";
import { TrendChart } from "./TrendChart";
import { useTrends, useRegressions } from "@/hooks/useEvalDashboard";
import type { TrendSummary, RegressionReport } from "@/types/eval-dashboard";

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
  const [limit, setLimit] = useState(10);
  const { summaries, isLoading, error, refresh } = useTrends(undefined, limit);
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

function DetailView({
  summary,
  regression,
}: {
  summary: TrendSummary;
  regression?: RegressionReport;
}) {
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

      <TrendChart
        points={summary.points}
        promptChanges={summary.prompt_changes}
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
                key={p.run_id}
                className="border-b border-gray-100 dark:border-gray-800"
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
                  {p.average_score.toFixed(2)}
                </td>
                <td className="px-2 py-1.5">
                  <span
                    className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${
                      p.eval_status === "passed"
                        ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                        : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
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
    </Card>
  );
}
