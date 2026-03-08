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
import type { QualityTrendPoint } from "@/types/eval-explorer";

interface UniversalQualityChartProps {
  points: QualityTrendPoint[];
  isLoading: boolean;
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

function formatDate(ts: string): string {
  return new Date(ts).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

interface ChartDataPoint {
  timestamp: string;
  label: string;
  [evalType: string]: string | number;
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

export function UniversalQualityChart({
  points,
  isLoading,
}: UniversalQualityChartProps) {
  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-gray-500 dark:text-gray-400">
        Loading quality trend...
      </div>
    );
  }

  if (points.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-gray-500 dark:text-gray-400">
        No universal quality data available. Run evals with a universal quality scorer to populate this chart.
      </div>
    );
  }

  // Group points by timestamp, create one data point per unique timestamp
  const evalTypes = [...new Set(points.map((p) => p.eval_type))].sort();

  // Build chart data: one row per unique timestamp across all eval types
  const timeMap = new Map<string, ChartDataPoint>();
  for (const p of points) {
    const key = p.timestamp;
    if (!timeMap.has(key)) {
      timeMap.set(key, {
        timestamp: key,
        label: formatDate(key),
      });
    }
    timeMap.get(key)![p.eval_type] = p.universal_quality;
  }

  const data = [...timeMap.values()].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart
        data={data}
        margin={{ top: 10, right: 20, left: 10, bottom: 5 }}
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
        <Legend
          wrapperStyle={{ fontSize: 11 }}
        />
        {evalTypes.map((et) => (
          <Line
            key={et}
            type="monotone"
            dataKey={et}
            name={et}
            stroke={getColor(et)}
            strokeWidth={2}
            dot={{ r: 2, fill: getColor(et) }}
            activeDot={{ r: 4 }}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
