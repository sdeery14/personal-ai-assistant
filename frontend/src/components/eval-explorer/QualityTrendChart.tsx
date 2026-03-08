"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { Card } from "@/components/ui";
import { Skeleton } from "@/components/ui/Skeleton";
import type { AgentVersionSummary, QualityTrendPoint } from "@/types/eval-explorer";

interface QualityTrendChartProps {
  agents: AgentVersionSummary[];
  points: QualityTrendPoint[];
  isLoading: boolean;
  onVersionClick?: (modelId: string) => void;
}

const EVAL_TYPE_COLORS: Record<string, string> = {
  quality: "#3b82f6",
  security: "#ef4444",
  memory: "#10b981",
  "memory-write": "#14b8a6",
  weather: "#f59e0b",
  "graph-extraction": "#8b5cf6",
  onboarding: "#ec4899",
  contradiction: "#f97316",
  "memory-informed": "#06b6d4",
  "multi-cap": "#6366f1",
  "long-conversation": "#84cc16",
  politeness: "#a855f7",
  empathy: "#d946ef",
  conciseness: "#0ea5e9",
  helpfulness: "#22c55e",
  accuracy: "#eab308",
  safety: "#dc2626",
  relevance: "#2563eb",
};

function getColor(evalType: string): string {
  return EVAL_TYPE_COLORS[evalType] || "#6b7280";
}

interface ChartDataPoint {
  label: string;
  timestamp: string;
  model_id: string;
  overall: number | null;
  [evalType: string]: string | number | null;
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded border border-gray-200 bg-white px-3 py-2 text-xs shadow dark:border-gray-700 dark:bg-gray-800">
      <p className="mb-1 font-medium text-gray-900 dark:text-gray-100">
        {label}
      </p>
      {payload.map((entry) => (
        <p key={entry.name} style={{ color: entry.color }}>
          {entry.name}: {entry.value.toFixed(2)}
        </p>
      ))}
    </div>
  );
}

export function QualityTrendChart({
  agents,
  points,
  isLoading,
  onVersionClick,
}: QualityTrendChartProps) {
  if (isLoading) {
    return <Skeleton className="h-80 w-full" />;
  }

  // Filter agents with quality, sorted oldest-first
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
          Run evals to see quality trends across agent versions.
        </p>
      </Card>
    );
  }

  // Build a map: git_commit_short -> per-eval-type scores from quality trend points
  const commitScores = new Map<string, Record<string, number>>();
  for (const p of points) {
    // Match point to an agent version by finding the closest timestamp
    const matchedAgent = withQuality.find((a) => {
      // Points from the same run share approximately the same timestamp
      const agentTime = new Date(a.creation_timestamp).getTime();
      const pointTime = new Date(p.timestamp).getTime();
      // Within 2 hours — same eval session
      return Math.abs(agentTime - pointTime) < 2 * 60 * 60 * 1000;
    });
    if (matchedAgent) {
      const key = matchedAgent.git_commit_short;
      if (!commitScores.has(key)) commitScores.set(key, {});
      commitScores.get(key)![p.eval_type] = p.universal_quality;
    }
  }

  // Collect all eval types from the points
  const evalTypes = [...new Set(points.map((p) => p.eval_type))].sort();

  // Build chart data: one row per agent version
  const data: ChartDataPoint[] = withQuality.map((agent) => {
    const row: ChartDataPoint = {
      label: agent.git_commit_short,
      timestamp: agent.creation_timestamp,
      model_id: agent.model_id,
      overall: agent.aggregate_quality,
    };
    const scores = commitScores.get(agent.git_commit_short);
    if (scores) {
      for (const et of evalTypes) {
        row[et] = scores[et] ?? null;
      }
    }
    return row;
  });

  return (
    <Card className="p-4">
      <ResponsiveContainer width="100%" height={320}>
        <LineChart
          data={data}
          margin={{ top: 10, right: 20, left: 10, bottom: 5 }}
          onClick={(e) => {
            if (onVersionClick && e?.activePayload?.[0]?.payload?.model_id) {
              onVersionClick(e.activePayload[0].payload.model_id);
            }
          }}
        >
          <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11 }}
            className="text-gray-500 dark:text-gray-400"
          />
          <YAxis
            domain={[1, 5]}
            ticks={[1, 2, 3, 4, 5]}
            tick={{ fontSize: 11 }}
            className="text-gray-500 dark:text-gray-400"
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: 11 }} />

          {/* Overall quality line — bold */}
          <Line
            type="monotone"
            dataKey="overall"
            name="Overall"
            stroke="#111827"
            strokeWidth={3}
            dot={{ r: 4, fill: "#111827", stroke: "#fff", strokeWidth: 2 }}
            activeDot={{ r: 6 }}
            connectNulls
          />

          {/* Per-eval-type lines — thinner */}
          {evalTypes.map((et) => (
            <Line
              key={et}
              type="monotone"
              dataKey={et}
              name={et}
              stroke={getColor(et)}
              strokeWidth={1.5}
              strokeDasharray="4 2"
              dot={{ r: 2, fill: getColor(et) }}
              activeDot={{ r: 4 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}
