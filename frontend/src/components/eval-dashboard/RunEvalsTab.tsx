"use client";

import { useState } from "react";
import { Button, Card } from "@/components/ui";
import { Skeleton } from "@/components/ui/Skeleton";
import { useEvalRun } from "@/hooks/useEvalDashboard";
import type { RegressionReport } from "@/types/eval-dashboard";

const verdictStyles: Record<string, string> = {
  REGRESSION: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  WARNING: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  IMPROVED: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  PASS: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
};

export function RunEvalsTab() {
  const { status, isLoading, error, startRun, refreshStatus } = useEvalRun();
  const [suite, setSuite] = useState("core");

  const handleRun = async () => {
    await startRun(suite);
  };

  const isRunning = status?.status === "running";

  return (
    <div className="space-y-4">
      {/* Controls */}
      <Card>
        <div className="flex items-end gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Suite
            </label>
            <div className="flex gap-2">
              {["core", "full"].map((s) => (
                <button
                  key={s}
                  onClick={() => setSuite(s)}
                  className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
                    suite === s
                      ? "bg-blue-600 text-white dark:bg-blue-500"
                      : "bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
          <Button
            onClick={handleRun}
            disabled={isRunning}
            isLoading={isLoading && !status}
          >
            {isRunning ? "Run in progress" : "Run Suite"}
          </Button>
          {status && (
            <Button
              variant="secondary"
              size="sm"
              onClick={refreshStatus}
              isLoading={isLoading}
            >
              Refresh
            </Button>
          )}
        </div>
      </Card>

      {error && (
        <Card>
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </Card>
      )}

      {/* Run status */}
      {status && (
        <Card>
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              Run: {status.run_id.slice(0, 8)}
              <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                ({status.suite})
              </span>
            </h3>
            <StatusBadge status={status.status} />
          </div>

          {/* Progress */}
          {isRunning && (
            <div className="mb-4">
              <div className="mb-1 flex justify-between text-xs text-gray-600 dark:text-gray-400">
                <span>Progress</span>
                <span>
                  {status.completed}/{status.total}
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
                <div
                  className="h-full rounded-full bg-blue-600 transition-all dark:bg-blue-500"
                  style={{
                    width: `${status.total > 0 ? (status.completed / status.total) * 100 : 0}%`,
                  }}
                />
              </div>
            </div>
          )}

          {/* Per-eval results */}
          {status.results.length > 0 && (
            <div className="mb-4">
              <h4 className="mb-2 text-xs font-medium text-gray-600 dark:text-gray-400">
                Results
              </h4>
              <div className="space-y-1">
                {status.results.map((r, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between rounded px-2 py-1 text-xs"
                  >
                    <span className="text-gray-700 dark:text-gray-300">
                      {r.dataset_path.split("/").pop()}
                    </span>
                    <span
                      className={`rounded px-1.5 py-0.5 font-medium ${
                        r.passed
                          ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                          : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                      }`}
                    >
                      {r.passed ? "PASS" : "FAIL"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Regression results after completion */}
          {status.status === "completed" && status.regression_reports && (
            <div>
              <h4 className="mb-2 text-xs font-medium text-gray-600 dark:text-gray-400">
                Regression Check
              </h4>
              {status.regression_reports.length === 0 ? (
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  No regression data available
                </p>
              ) : (
                <div className="space-y-1">
                  {status.regression_reports.map((r: RegressionReport) => (
                    <div
                      key={r.eval_type}
                      className="flex items-center justify-between rounded px-2 py-1 text-xs"
                    >
                      <span className="text-gray-700 dark:text-gray-300">
                        {r.eval_type}
                      </span>
                      <span
                        className={`rounded px-1.5 py-0.5 font-semibold ${verdictStyles[r.verdict] || verdictStyles.PASS}`}
                      >
                        {r.verdict}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Timestamps */}
          <div className="mt-3 text-xs text-gray-500 dark:text-gray-400">
            Started: {new Date(status.started_at).toLocaleString()}
            {status.finished_at && (
              <span className="ml-3">
                Finished: {new Date(status.finished_at).toLocaleString()}
              </span>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    running: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    completed:
      "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    failed: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  };
  return (
    <span
      className={`inline-block rounded px-2 py-0.5 text-xs font-semibold ${styles[status] || styles.running}`}
    >
      {status}
    </span>
  );
}
