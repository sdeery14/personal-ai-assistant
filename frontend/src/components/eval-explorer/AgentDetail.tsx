"use client";

import { useState } from "react";
import { Card } from "@/components/ui";
import { Skeleton } from "@/components/ui/Skeleton";
import type { AgentVersionDetail, ExperimentResult } from "@/types/eval-explorer";

interface AgentDetailProps {
  agent: AgentVersionDetail | null;
  isLoading: boolean;
  error: string | null;
  onExperimentClick?: (experimentId: string, evalType: string, name: string) => void;
}

function formatPercent(val: number | null): string {
  if (val === null) return "-";
  return `${(val * 100).toFixed(1)}%`;
}

function formatScore(val: number | null): string {
  if (val === null) return "-";
  return val.toFixed(2);
}

export function AgentDetail({
  agent,
  isLoading,
  error,
  onExperimentClick,
}: AgentDetailProps) {
  const [showDiff, setShowDiff] = useState(false);

  if (error) {
    return (
      <Card className="p-4">
        <p className="text-red-600 dark:text-red-400">Error: {error}</p>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-6 w-64" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (!agent) {
    return (
      <Card className="p-4">
        <p className="text-gray-500 dark:text-gray-400">Agent version not found.</p>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Git metadata */}
      <Card className="p-4">
        <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">
          Git Info
        </h2>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
          <dt className="text-gray-500 dark:text-gray-400">Commit</dt>
          <dd className="font-mono text-gray-900 dark:text-gray-100">{agent.git_commit}</dd>

          <dt className="text-gray-500 dark:text-gray-400">Branch</dt>
          <dd className="text-gray-900 dark:text-gray-100">{agent.git_branch}</dd>

          <dt className="text-gray-500 dark:text-gray-400">Date</dt>
          <dd className="text-gray-900 dark:text-gray-100">
            {agent.creation_timestamp
              ? new Date(agent.creation_timestamp).toLocaleString()
              : "-"}
          </dd>

          <dt className="text-gray-500 dark:text-gray-400">Aggregate Quality</dt>
          <dd className="text-gray-900 dark:text-gray-100">
            {agent.aggregate_quality != null ? agent.aggregate_quality.toFixed(2) : "-"}
          </dd>

          <dt className="text-gray-500 dark:text-gray-400">Total Traces</dt>
          <dd className="text-gray-900 dark:text-gray-100">{agent.total_traces}</dd>

          <dt className="text-gray-500 dark:text-gray-400">Status</dt>
          <dd>
            {agent.git_dirty ? (
              <span className="rounded bg-yellow-100 px-1.5 py-0.5 text-xs text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400">
                dirty
              </span>
            ) : (
              <span className="rounded bg-green-100 px-1.5 py-0.5 text-xs text-green-800 dark:bg-green-900/30 dark:text-green-400">
                clean
              </span>
            )}
          </dd>
        </dl>

        {agent.git_dirty && agent.git_diff && (
          <div className="mt-3">
            <button
              onClick={() => setShowDiff(!showDiff)}
              className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
            >
              {showDiff ? "Hide diff" : "Show diff"}
            </button>
            {showDiff && (
              <pre className="mt-2 max-h-64 overflow-auto rounded bg-gray-900 p-3 text-xs text-gray-200">
                {agent.git_diff}
              </pre>
            )}
          </div>
        )}
      </Card>

      {/* Experiment results */}
      <Card className="p-4">
        <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">
          Experiment Results ({agent.experiment_results.length})
        </h2>
        {agent.experiment_results.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            No experiment results linked to this agent version.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="px-3 py-2 font-medium text-gray-600 dark:text-gray-400">Experiment</th>
                  <th className="px-3 py-2 font-medium text-gray-600 dark:text-gray-400">Eval Type</th>
                  <th className="px-3 py-2 font-medium text-gray-600 dark:text-gray-400">Runs</th>
                  <th className="px-3 py-2 font-medium text-gray-600 dark:text-gray-400">Pass Rate</th>
                  <th className="px-3 py-2 font-medium text-gray-600 dark:text-gray-400">Avg Quality</th>
                </tr>
              </thead>
              <tbody>
                {agent.experiment_results.map((er: ExperimentResult) => (
                  <tr
                    key={er.experiment_id}
                    className={`border-b border-gray-100 dark:border-gray-800 ${
                      onExperimentClick
                        ? "cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50"
                        : ""
                    }`}
                    onClick={() =>
                      onExperimentClick?.(er.experiment_id, er.eval_type, er.experiment_name)
                    }
                  >
                    <td className="px-3 py-2 font-medium text-blue-600 dark:text-blue-400">
                      {er.experiment_name}
                    </td>
                    <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                      {er.eval_type}
                    </td>
                    <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                      {er.run_count}
                    </td>
                    <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                      {formatPercent(er.pass_rate)}
                    </td>
                    <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                      {formatScore(er.average_quality)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
