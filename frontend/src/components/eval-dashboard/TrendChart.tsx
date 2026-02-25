"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceDot,
} from "recharts";
import type { TrendPoint, PromptChange } from "@/types/eval-dashboard";

interface TrendChartProps {
  points: TrendPoint[];
  promptChanges: PromptChange[];
}

function formatDate(ts: string): string {
  return new Date(ts).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: TrendPoint }>;
}) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded border border-gray-200 bg-white px-3 py-2 text-xs shadow dark:border-gray-700 dark:bg-gray-800">
      <p className="font-medium text-gray-900 dark:text-gray-100">
        {new Date(p.timestamp).toLocaleString()}
      </p>
      <p className="text-gray-600 dark:text-gray-400">
        Pass Rate: {(p.pass_rate * 100).toFixed(1)}%
      </p>
      <p className="text-gray-600 dark:text-gray-400">
        Avg Score: {p.average_score.toFixed(2)}
      </p>
      <p className="text-gray-600 dark:text-gray-400">
        Cases: {p.total_cases} ({p.error_cases} errors)
      </p>
    </div>
  );
}

export function TrendChart({ points, promptChanges }: TrendChartProps) {
  if (points.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-gray-500 dark:text-gray-400">
        No data points available
      </div>
    );
  }

  const data = points.map((p) => ({
    ...p,
    passRatePct: p.pass_rate * 100,
    label: formatDate(p.timestamp),
  }));

  // Map prompt changes to their nearest data point index
  const changeIndices = new Set(
    promptChanges.map((c) => {
      const idx = data.findIndex((d) => d.run_id === c.run_id);
      return idx >= 0 ? idx : null;
    }).filter((i): i is number => i !== null)
  );

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11 }}
          className="text-gray-500 dark:text-gray-400"
        />
        <YAxis
          domain={[0, 100]}
          tick={{ fontSize: 11 }}
          tickFormatter={(v: number) => `${v}%`}
          className="text-gray-500 dark:text-gray-400"
        />
        <Tooltip content={<CustomTooltip />} />
        <Line
          type="monotone"
          dataKey="passRatePct"
          stroke="#3b82f6"
          strokeWidth={2}
          dot={{ r: 3, fill: "#3b82f6" }}
          activeDot={{ r: 5 }}
        />
        {/* Prompt change markers */}
        {data.map(
          (d, i) =>
            changeIndices.has(i) && (
              <ReferenceDot
                key={`change-${i}`}
                x={d.label}
                y={d.passRatePct}
                r={6}
                fill="#f59e0b"
                stroke="#fff"
                strokeWidth={2}
              />
            )
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}
