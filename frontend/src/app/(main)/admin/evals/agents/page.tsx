"use client";

import { useRouter } from "next/navigation";
import { useAgentVersions } from "@/hooks/useEvalExplorer";
import { Skeleton } from "@/components/ui/Skeleton";
import { Card } from "@/components/ui";
import type { AgentVersionSummary } from "@/types/eval-explorer";

export default function AgentsPage() {
  const router = useRouter();
  const { agents, isLoading, error } = useAgentVersions();

  if (isLoading) {
    return (
      <div className="space-y-3">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Agents</h1>
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <Card className="p-4">
        <p className="text-red-600 dark:text-red-400">Error: {error}</p>
      </Card>
    );
  }

  if (agents.length === 0) {
    return (
      <div>
        <h1 className="mb-4 text-2xl font-bold text-gray-900 dark:text-white">Agents</h1>
        <Card className="p-6 text-center text-gray-500 dark:text-gray-400">
          <p className="text-lg font-medium">No agent versions yet</p>
          <p className="mt-1 text-sm">
            Run an eval suite to automatically create agent versions from your git commits.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <h1 className="mb-4 text-2xl font-bold text-gray-900 dark:text-white">Agents</h1>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead>
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Commit</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Branch</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Date</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Quality</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Dirty</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {agents.map((agent: AgentVersionSummary) => (
              <tr
                key={agent.model_id}
                onClick={() => router.push(`/admin/evals/agents/${agent.model_id}`)}
                className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                <td className="px-4 py-2 text-sm font-mono text-blue-600 dark:text-blue-400">
                  {agent.git_commit_short}
                </td>
                <td className="px-4 py-2 text-sm text-gray-900 dark:text-gray-100">
                  {agent.git_branch}
                </td>
                <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400">
                  {agent.creation_timestamp
                    ? new Date(agent.creation_timestamp).toLocaleDateString()
                    : "—"}
                </td>
                <td className="px-4 py-2 text-sm text-gray-900 dark:text-gray-100">
                  {agent.aggregate_quality != null
                    ? agent.aggregate_quality.toFixed(1)
                    : "—"}
                </td>
                <td className="px-4 py-2 text-sm">
                  {agent.git_dirty && (
                    <span className="rounded bg-yellow-100 px-1.5 py-0.5 text-xs text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400">
                      dirty
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
