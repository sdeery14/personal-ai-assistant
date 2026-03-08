"use client";

import { useParams, useSearchParams } from "next/navigation";
import { useRunTraces } from "@/hooks/useEvalExplorer";
import { TraceViewer } from "@/components/eval-explorer/TraceViewer";
import { SessionViewer } from "@/components/eval-explorer/SessionViewer";
import { Breadcrumb } from "@/components/eval-nav/Breadcrumb";

export default function RunDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();

  const runId = params.runId as string;
  const experimentId = searchParams.get("experiment_id") || "";
  const experimentName = searchParams.get("experiment_name") || "";
  const evalType = searchParams.get("eval_type") || "";

  const { traces, sessions, isLoading, error } = useRunTraces(runId, evalType);

  const breadcrumbItems = [
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

      {sessions.length > 0 && (
        <div className="mb-6">
          <SessionViewer sessions={sessions} />
        </div>
      )}

      <TraceViewer traces={traces} isLoading={isLoading} error={error} />
    </div>
  );
}
