"use client";

import { useParams, useSearchParams } from "next/navigation";
import { Card } from "@/components/ui";
import { Skeleton } from "@/components/ui/Skeleton";
import { useRunTraces } from "@/hooks/useEvalExplorer";
import { useRunDetail } from "@/hooks/useEvalDashboard";
import { TraceViewer } from "@/components/eval-explorer/TraceViewer";
import { SessionViewer } from "@/components/eval-explorer/SessionViewer";
import { Breadcrumb } from "@/components/eval-nav/Breadcrumb";

function RunMetadataHeader({ runId, evalType }: { runId: string; evalType: string }) {
  const { detail, isLoading, error } = useRunDetail(runId, evalType);

  if (isLoading) {
    return (
      <Card className="mb-4 p-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      </Card>
    );
  }

  if (error || !detail) return null;

  const model = detail.params["assistant_model"] || "-";
  const judgeModel = detail.params["judge_model"] || "-";
  const datasetVersion = detail.params["dataset_version"] || "-";
  const gitSha = detail.params["git_sha"] ?? null;
  const passRate = detail.metrics["pass_rate"];
  const avgScore = detail.metrics["average_score"];
  const totalCases = detail.metrics["total_cases"];
  const errorCases = detail.metrics["error_cases"];

  const promptVersions = Object.entries(detail.params)
    .filter(([k]) => k.startsWith("prompt."))
    .map(([k, v]) => [k.replace("prompt.", ""), v] as const);

  return (
    <Card className="mb-4 p-4">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
          Run Summary
        </h2>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {new Date(detail.timestamp).toLocaleString()}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-4">
        <div>
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Model</span>
          <p className="font-mono text-gray-800 dark:text-gray-200">{model}</p>
        </div>
        <div>
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Judge</span>
          <p className="font-mono text-gray-800 dark:text-gray-200">{judgeModel}</p>
        </div>
        <div>
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Dataset</span>
          <p className="text-gray-800 dark:text-gray-200">{datasetVersion}</p>
        </div>
        {gitSha && (
          <div>
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Git SHA</span>
            <p className="font-mono text-gray-800 dark:text-gray-200">{gitSha}</p>
          </div>
        )}
        <div>
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Pass Rate</span>
          <p className="text-gray-800 dark:text-gray-200">
            {passRate != null ? `${(passRate * 100).toFixed(1)}%` : "-"}
          </p>
        </div>
        <div>
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Avg Score</span>
          <p className="text-gray-800 dark:text-gray-200">
            {avgScore != null ? avgScore.toFixed(2) : "-"}
          </p>
        </div>
        <div>
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Cases</span>
          <p className="text-gray-800 dark:text-gray-200">
            {totalCases != null ? totalCases : "-"}
          </p>
        </div>
        <div>
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Errors</span>
          <p className={
            (errorCases ?? 0) === 0
              ? "text-green-600 dark:text-green-400"
              : "text-yellow-600 dark:text-yellow-400"
          }>
            {errorCases != null ? errorCases : "-"}
          </p>
        </div>
      </div>

      {promptVersions.length > 0 && (
        <div className="mt-3">
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
            Prompt Versions
          </span>
          <div className="mt-1 flex flex-wrap gap-2">
            {promptVersions.map(([name, ver]) => (
              <span
                key={name}
                className="rounded bg-blue-50 px-2 py-0.5 text-xs text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
              >
                {name}: v{ver}
              </span>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

export default function RunDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();

  const runId = params.runId as string;
  const experimentId = searchParams.get("experiment_id") || "";
  const experimentName = searchParams.get("experiment_name") || "";
  const evalType = searchParams.get("eval_type") || "";
  const from = searchParams.get("from") || "";

  const { traces, sessions, isLoading, error } = useRunTraces(runId, evalType);

  const breadcrumbItems = from === "dashboard"
    ? [
        { label: "Dashboard", href: "/admin/evals" },
        { label: `Run ${runId.substring(0, 8)}`, href: `/admin/evals/runs/${runId}` },
      ]
    : [
        { label: "Experiments", href: "/admin/evals/experiments" },
        ...(experimentId
          ? [
              {
                label: experimentName || experimentId,
                href: `/admin/evals/experiments/${experimentId}?name=${encodeURIComponent(experimentName)}&eval_type=${encodeURIComponent(evalType)}`,
              },
            ]
          : []),
        { label: `Run ${runId.substring(0, 8)}`, href: `/admin/evals/runs/${runId}` },
      ];

  return (
    <div>
      <Breadcrumb items={breadcrumbItems} />
      <h1 className="mb-4 text-2xl font-bold text-gray-900 dark:text-white">
        Run {runId.substring(0, 8)}
      </h1>
      {evalType && (
        <p className="mb-4 text-sm text-gray-500 dark:text-gray-400">
          Eval type: {evalType}
        </p>
      )}

      {evalType && <RunMetadataHeader runId={runId} evalType={evalType} />}

      {sessions.length > 0 ? (
        <SessionViewer sessions={sessions} isLoading={isLoading} error={error} />
      ) : (
        <TraceViewer traces={traces} isLoading={isLoading} error={error} />
      )}
    </div>
  );
}
