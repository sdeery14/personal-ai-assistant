"use client";

import { useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useExperimentRuns } from "@/hooks/useEvalExplorer";
import { RunBrowser } from "@/components/eval-explorer/RunBrowser";
import { RunComparison } from "@/components/eval-explorer/RunComparison";
import { Breadcrumb } from "@/components/eval-nav/Breadcrumb";

export default function ExperimentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();

  const experimentId = params.experimentId as string;
  const experimentName = searchParams.get("name") || experimentId;
  const evalType = searchParams.get("eval_type") || "";

  const { runs, isLoading, error } = useExperimentRuns(experimentId, evalType);

  const [selectedRunIds, setSelectedRunIds] = useState<string[]>([]);
  const [showComparison, setShowComparison] = useState(false);

  function handleToggleSelect(runId: string) {
    setSelectedRunIds((prev) =>
      prev.includes(runId) ? prev.filter((id) => id !== runId) : [...prev, runId]
    );
    setShowComparison(false);
  }

  const breadcrumbItems = [
    { label: "Experiments", href: "/admin/evals/experiments" },
    {
      label: experimentName,
      href: `/admin/evals/experiments/${experimentId}?name=${encodeURIComponent(experimentName)}&eval_type=${encodeURIComponent(evalType)}`,
    },
  ];

  const runA = runs.find((r) => r.run_id === selectedRunIds[0]);
  const runB = runs.find((r) => r.run_id === selectedRunIds[1]);

  return (
    <div>
      <Breadcrumb items={breadcrumbItems} />
      <h1 className="mb-4 text-2xl font-bold text-gray-900 dark:text-white">
        {experimentName}
      </h1>
      {evalType && (
        <p className="mb-4 text-sm text-gray-500 dark:text-gray-400">
          Eval type: {evalType}
        </p>
      )}

      <RunBrowser
        runs={runs}
        isLoading={isLoading}
        error={error}
        onSelect={(run) =>
          router.push(
            `/admin/evals/runs/${run.run_id}?experiment_id=${experimentId}&experiment_name=${encodeURIComponent(experimentName)}&eval_type=${encodeURIComponent(evalType)}`
          )
        }
        selectedRunIds={selectedRunIds}
        onToggleSelect={handleToggleSelect}
        onCompare={() => setShowComparison(true)}
      />

      {showComparison && runA && runB && (
        <div className="mt-4">
          <RunComparison
            runA={runA}
            runB={runB}
            onClose={() => {
              setShowComparison(false);
              setSelectedRunIds([]);
            }}
          />
        </div>
      )}
    </div>
  );
}
