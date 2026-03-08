"use client";

import { useRouter } from "next/navigation";
import { TrendsTab } from "@/components/eval-dashboard/TrendsTab";
import { QualityTrendChart } from "@/components/eval-explorer/QualityTrendChart";
import { useUniversalQualityTrend, useAgentVersions } from "@/hooks/useEvalExplorer";

export default function TrendsPage() {
  const router = useRouter();
  const { points, isLoading: trendsLoading } = useUniversalQualityTrend();
  const { agents, isLoading: agentsLoading } = useAgentVersions();

  return (
    <div>
      <h1 className="mb-4 text-2xl font-bold text-gray-900 dark:text-white">
        Trends
      </h1>

      <div className="mb-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-800 dark:text-gray-200">
          Quality by Agent Version
        </h2>
        <QualityTrendChart
          agents={agents}
          points={points}
          isLoading={agentsLoading || trendsLoading}
          onVersionClick={(modelId) => router.push(`/admin/evals/agents/${modelId}`)}
        />
      </div>

      <div>
        <h2 className="mb-2 text-lg font-semibold text-gray-800 dark:text-gray-200">
          Per-Eval Type
        </h2>
        <TrendsTab />
      </div>
    </div>
  );
}
