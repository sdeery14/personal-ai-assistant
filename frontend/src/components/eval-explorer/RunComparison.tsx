"use client";

import { useMemo } from "react";
import { Card } from "@/components/ui";
import type { RunSummary } from "@/types/eval-explorer";

interface RunComparisonProps {
  runA: RunSummary;
  runB: RunSummary;
  onClose: () => void;
}

function DeltaCell({ a, b, format = "number" }: { a?: number; b?: number; format?: "number" | "percent" }) {
  if (a === undefined && b === undefined) return <td className="px-3 py-1">-</td>;

  const av = a ?? 0;
  const bv = b ?? 0;
  const delta = bv - av;

  const fmt = (v: number) =>
    format === "percent" ? `${(v * 100).toFixed(1)}%` : v.toFixed(2);

  const deltaColor =
    delta > 0
      ? "text-green-600 dark:text-green-400"
      : delta < 0
        ? "text-red-600 dark:text-red-400"
        : "text-gray-500";

  return (
    <td className="px-3 py-1 text-sm">
      <span className="text-gray-700 dark:text-gray-300">{fmt(av)}</span>
      {" \u2192 "}
      <span className="text-gray-700 dark:text-gray-300">{fmt(bv)}</span>
      {delta !== 0 && (
        <span className={`ml-1 text-xs ${deltaColor}`}>
          ({delta > 0 ? "+" : ""}
          {fmt(delta)})
        </span>
      )}
    </td>
  );
}

export function RunComparison({ runA, runB, onClose }: RunComparisonProps) {
  // Collect all metric keys from both runs
  const allMetricKeys = useMemo(() => {
    const keys = new Set([
      ...Object.keys(runA.metrics),
      ...Object.keys(runB.metrics),
    ]);
    return [...keys].sort();
  }, [runA.metrics, runB.metrics]);

  // Collect all param keys
  const allParamKeys = useMemo(() => {
    const keys = new Set([
      ...Object.keys(runA.params),
      ...Object.keys(runB.params),
    ]);
    return [...keys].sort();
  }, [runA.params, runB.params]);

  return (
    <Card className="p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-900 dark:text-white">
          Run Comparison
        </h3>
        <button
          onClick={onClose}
          className="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
        >
          Close
        </button>
      </div>

      {/* Params diff */}
      <div className="mb-4">
        <h4 className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">
          Parameters
        </h4>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700">
              <th className="px-3 py-1 text-left text-xs font-medium text-gray-500">
                Param
              </th>
              <th className="px-3 py-1 text-left text-xs font-medium text-gray-500">
                Run A
              </th>
              <th className="px-3 py-1 text-left text-xs font-medium text-gray-500">
                Run B
              </th>
            </tr>
          </thead>
          <tbody>
            {allParamKeys.map((key) => {
              const aVal = runA.params[key] || "-";
              const bVal = runB.params[key] || "-";
              const changed = aVal !== bVal;
              return (
                <tr
                  key={key}
                  className={`border-b border-gray-100 dark:border-gray-800 ${
                    changed ? "bg-yellow-50 dark:bg-yellow-900/10" : ""
                  }`}
                >
                  <td className="px-3 py-1 font-mono text-xs text-gray-600 dark:text-gray-400">
                    {key}
                  </td>
                  <td className="px-3 py-1 text-sm text-gray-700 dark:text-gray-300">
                    {aVal}
                  </td>
                  <td className="px-3 py-1 text-sm text-gray-700 dark:text-gray-300">
                    {bVal}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Metrics diff */}
      <div>
        <h4 className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">
          Metrics
        </h4>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700">
              <th className="px-3 py-1 text-left text-xs font-medium text-gray-500">
                Metric
              </th>
              <th className="px-3 py-1 text-left text-xs font-medium text-gray-500">
                Run A \u2192 Run B (Delta)
              </th>
            </tr>
          </thead>
          <tbody>
            {allMetricKeys.map((key) => {
              const isPercent = key.includes("rate");
              return (
                <tr
                  key={key}
                  className="border-b border-gray-100 dark:border-gray-800"
                >
                  <td className="px-3 py-1 font-mono text-xs text-gray-600 dark:text-gray-400">
                    {key}
                  </td>
                  <DeltaCell
                    a={runA.metrics[key]}
                    b={runB.metrics[key]}
                    format={isPercent ? "percent" : "number"}
                  />
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
