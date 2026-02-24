"use client";

import { Card, Button } from "@/components/ui";
import { Skeleton } from "@/components/ui/Skeleton";
import { useRegressions } from "@/hooks/useEvalDashboard";
import type { RegressionReport } from "@/types/eval-dashboard";

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
  return `${sign}${(delta * 100).toFixed(1)}pp`;
}

export function RegressionsTab() {
  const { reports, hasRegressions, isLoading, error, refresh } =
    useRegressions();

  if (isLoading && reports.length === 0) {
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

  if (reports.length === 0) {
    return (
      <Card>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No eval types with sufficient data for comparison.
        </p>
      </Card>
    );
  }

  // Summary counts
  const counts: Record<string, number> = {};
  reports.forEach((r) => {
    counts[r.verdict] = (counts[r.verdict] || 0) + 1;
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {hasRegressions ? (
            <span className="text-sm font-medium text-red-600 dark:text-red-400">
              Regressions detected
            </span>
          ) : (
            <span className="text-sm font-medium text-green-600 dark:text-green-400">
              No regressions detected
            </span>
          )}
          <div className="flex gap-2 text-xs text-gray-500 dark:text-gray-400">
            {Object.entries(counts).map(([verdict, count]) => (
              <span key={verdict}>
                {count} {verdict}
              </span>
            ))}
          </div>
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
                Baseline
              </th>
              <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-300">
                Current
              </th>
              <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-300">
                Delta
              </th>
              <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-300">
                Threshold
              </th>
              <th className="px-3 py-2 text-center font-medium text-gray-700 dark:text-gray-300">
                Verdict
              </th>
            </tr>
          </thead>
          <tbody>
            {reports.map((r: RegressionReport) => (
              <tr
                key={r.evalType}
                className="border-b border-gray-100 dark:border-gray-800"
              >
                <td className="px-3 py-2 font-medium text-gray-900 dark:text-gray-100">
                  {r.evalType}
                  {r.changedPrompts.length > 0 && (
                    <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      {r.changedPrompts.map((c, i) => (
                        <span key={i}>
                          Changed: {c.promptName} v{c.fromVersion} → v
                          {c.toVersion}
                          {i < r.changedPrompts.length - 1 && ", "}
                        </span>
                      ))}
                    </div>
                  )}
                </td>
                <td className="px-3 py-2 text-right text-gray-700 dark:text-gray-300">
                  {(r.baselinePassRate * 100).toFixed(1)}%
                </td>
                <td className="px-3 py-2 text-right text-gray-700 dark:text-gray-300">
                  {(r.currentPassRate * 100).toFixed(1)}%
                </td>
                <td
                  className={`px-3 py-2 text-right font-medium ${
                    r.deltaPp > 0
                      ? "text-green-600 dark:text-green-400"
                      : r.deltaPp < 0
                        ? "text-red-600 dark:text-red-400"
                        : "text-gray-500"
                  }`}
                >
                  {formatDelta(r.deltaPp)}
                </td>
                <td className="px-3 py-2 text-right text-gray-700 dark:text-gray-300">
                  {(r.threshold * 100).toFixed(1)}%
                </td>
                <td className="px-3 py-2 text-center">
                  <VerdictBadge verdict={r.verdict} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
