"use client";

import { Card } from "@/components/ui";
import { Skeleton } from "@/components/ui/Skeleton";
import type { AgentVersionSummary } from "@/types/eval-explorer";

interface VersionTrendChartProps {
  agents: AgentVersionSummary[];
  isLoading: boolean;
  onVersionClick?: (modelId: string) => void;
}

export function VersionTrendChart({
  agents,
  isLoading,
  onVersionClick,
}: VersionTrendChartProps) {
  if (isLoading) {
    return <Skeleton className="h-48 w-full" />;
  }

  // Filter to agents with quality scores, sorted oldest first
  const withQuality = agents
    .filter((a) => a.aggregate_quality != null)
    .sort(
      (a, b) =>
        new Date(a.creation_timestamp).getTime() -
        new Date(b.creation_timestamp).getTime()
    );

  if (withQuality.length === 0) {
    return (
      <Card className="p-6 text-center text-gray-500 dark:text-gray-400">
        <p className="text-lg font-medium">No quality data yet</p>
        <p className="mt-1 text-sm">
          Run evals with git versioning enabled to see quality trends across agent versions.
        </p>
      </Card>
    );
  }

  // Simple bar chart using CSS (no Recharts dependency needed for MVP)
  const maxQuality = 5.0;

  return (
    <Card className="p-4">
      <h3 className="mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">
        Agent Quality Over Versions
      </h3>
      <div className="flex items-end gap-1" style={{ height: 160 }}>
        {withQuality.map((agent) => {
          const quality = agent.aggregate_quality!;
          const heightPct = (quality / maxQuality) * 100;
          const barColor =
            quality >= 4.0
              ? "bg-green-500 dark:bg-green-400"
              : quality >= 3.0
                ? "bg-yellow-500 dark:bg-yellow-400"
                : "bg-red-500 dark:bg-red-400";

          return (
            <div
              key={agent.model_id}
              className="group relative flex flex-1 flex-col items-center justify-end"
              style={{ height: "100%" }}
            >
              {/* Tooltip */}
              <div className="pointer-events-none absolute bottom-full mb-1 hidden rounded bg-gray-900 px-2 py-1 text-xs text-white shadow group-hover:block dark:bg-gray-700">
                <div>{agent.git_commit}</div>
                <div>{agent.git_branch}</div>
                <div>Quality: {quality.toFixed(2)}</div>
                <div>{new Date(agent.creation_timestamp).toLocaleDateString()}</div>
              </div>
              {/* Bar */}
              <div
                className={`w-full min-w-[8px] max-w-[40px] rounded-t ${barColor} ${
                  onVersionClick ? "cursor-pointer hover:opacity-80" : ""
                }`}
                style={{ height: `${heightPct}%` }}
                onClick={() => onVersionClick?.(agent.model_id)}
              />
              {/* Label */}
              <span className="mt-1 text-[10px] text-gray-500 dark:text-gray-400 truncate max-w-[40px]">
                {agent.git_commit_short}
              </span>
            </div>
          );
        })}
      </div>
      {/* Y-axis labels */}
      <div className="mt-1 flex justify-between text-[10px] text-gray-400">
        <span>0</span>
        <span>5.0</span>
      </div>
    </Card>
  );
}
