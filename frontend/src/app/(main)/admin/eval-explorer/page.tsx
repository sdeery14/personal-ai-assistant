"use client";

import { useEffect, useState, useCallback } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui";
import { Tabs } from "@/components/ui/Tabs";
import { UniversalQualityChart } from "@/components/eval-explorer/UniversalQualityChart";
import { ExperimentBrowser } from "@/components/eval-explorer/ExperimentBrowser";
import { RunBrowser } from "@/components/eval-explorer/RunBrowser";
import { RunComparison } from "@/components/eval-explorer/RunComparison";
import { TraceViewer } from "@/components/eval-explorer/TraceViewer";
import { SessionViewer } from "@/components/eval-explorer/SessionViewer";
import { DatasetViewer } from "@/components/eval-explorer/DatasetViewer";
import {
  useExperiments,
  useExperimentRuns,
  useRunTraces,
  useUniversalQualityTrend,
  useDatasets,
  useDatasetDetail,
} from "@/hooks/useEvalExplorer";
import type { ExperimentSummary, RunSummary } from "@/types/eval-explorer";

const TABS = [
  { id: "browse", label: "Browse" },
  { id: "datasets", label: "Datasets" },
];

export default function EvalExplorerPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const isAdmin = (session?.user as { isAdmin?: boolean })?.isAdmin;
  const [activeTab, setActiveTab] = useState("browse");

  // Drill-down state
  const [selectedExperiment, setSelectedExperiment] =
    useState<ExperimentSummary | null>(null);
  const [selectedRun, setSelectedRun] = useState<RunSummary | null>(null);

  // Comparison state
  const [compareRunIds, setCompareRunIds] = useState<string[]>([]);
  const [compareRuns, setCompareRuns] = useState<[RunSummary, RunSummary] | null>(null);

  // Dataset state
  const [selectedDatasetName, setSelectedDatasetName] = useState<string>("");

  // Data hooks
  const { points, isLoading: trendLoading } = useUniversalQualityTrend();
  const { experiments, isLoading: expLoading, error: expError } = useExperiments();
  const {
    runs,
    isLoading: runsLoading,
    error: runsError,
  } = useExperimentRuns(
    selectedExperiment?.experiment_id ?? null,
    selectedExperiment?.eval_type ?? null
  );
  const {
    traces,
    sessions,
    isLoading: tracesLoading,
    error: tracesError,
  } = useRunTraces(
    selectedRun?.run_id ?? null,
    selectedExperiment?.eval_type ?? null
  );
  const { datasets, isLoading: datasetsLoading, error: datasetsError } =
    useDatasets();
  const {
    dataset: selectedDatasetDetail,
    isLoading: datasetDetailLoading,
  } = useDatasetDetail(selectedDatasetName || null);

  useEffect(() => {
    if (session && !isAdmin) {
      router.replace("/chat");
    }
  }, [session, isAdmin, router]);

  const handleSelectExperiment = useCallback((exp: ExperimentSummary) => {
    setSelectedExperiment(exp);
    setSelectedRun(null);
    setCompareRunIds([]);
    setCompareRuns(null);
  }, []);

  const handleSelectRun = useCallback((run: RunSummary) => {
    setSelectedRun(run);
  }, []);

  const handleToggleCompareRun = useCallback((runId: string) => {
    setCompareRunIds((prev) => {
      if (prev.includes(runId)) {
        return prev.filter((id) => id !== runId);
      }
      if (prev.length >= 2) return prev;
      return [...prev, runId];
    });
  }, []);

  const handleCompare = useCallback(() => {
    if (compareRunIds.length !== 2) return;
    const runA = runs.find((r) => r.run_id === compareRunIds[0]);
    const runB = runs.find((r) => r.run_id === compareRunIds[1]);
    if (runA && runB) {
      setCompareRuns([runA, runB]);
    }
  }, [compareRunIds, runs]);

  const handleBackToExperiments = useCallback(() => {
    setSelectedExperiment(null);
    setSelectedRun(null);
    setCompareRunIds([]);
    setCompareRuns(null);
  }, []);

  const handleBackToRuns = useCallback(() => {
    setSelectedRun(null);
  }, []);

  const handleSelectDataset = useCallback((name: string) => {
    setSelectedDatasetName(name);
  }, []);

  if (!isAdmin) return null;

  // Breadcrumb
  const breadcrumbs: { label: string; onClick?: () => void }[] = [
    { label: "Experiments", onClick: selectedExperiment ? handleBackToExperiments : undefined },
  ];
  if (selectedExperiment) {
    breadcrumbs.push({
      label: selectedExperiment.name,
      onClick: selectedRun ? handleBackToRuns : undefined,
    });
  }
  if (selectedRun) {
    breadcrumbs.push({ label: `Run ${selectedRun.run_id.substring(0, 8)}` });
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Eval Explorer
        </h1>
      </div>

      {/* Universal Quality Trend — always visible */}
      <Card className="mb-6 p-4">
        <h2 className="mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">
          Universal Quality Trend
        </h2>
        <UniversalQualityChart points={points} isLoading={trendLoading} />
      </Card>

      <Tabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />

      <div className="mt-4">
        {activeTab === "browse" && (
          <>
            {/* Breadcrumb navigation */}
            {selectedExperiment && (
              <nav className="mb-3 flex items-center gap-1 text-sm">
                {breadcrumbs.map((bc, i) => (
                  <span key={i} className="flex items-center gap-1">
                    {i > 0 && (
                      <span className="text-gray-400">/</span>
                    )}
                    {bc.onClick ? (
                      <button
                        onClick={bc.onClick}
                        className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                      >
                        {bc.label}
                      </button>
                    ) : (
                      <span className="text-gray-700 dark:text-gray-300">
                        {bc.label}
                      </span>
                    )}
                  </span>
                ))}
              </nav>
            )}

            {/* Comparison view */}
            {compareRuns && (
              <div className="mb-4">
                <RunComparison
                  runA={compareRuns[0]}
                  runB={compareRuns[1]}
                  onClose={() => {
                    setCompareRuns(null);
                    setCompareRunIds([]);
                  }}
                />
              </div>
            )}

            {/* Drill-down views */}
            {!selectedExperiment && (
              <ExperimentBrowser
                experiments={experiments}
                isLoading={expLoading}
                error={expError}
                onSelect={handleSelectExperiment}
              />
            )}

            {selectedExperiment && !selectedRun && (
              <RunBrowser
                runs={runs}
                isLoading={runsLoading}
                error={runsError}
                onSelect={handleSelectRun}
                selectedRunIds={compareRunIds}
                onToggleSelect={handleToggleCompareRun}
                onCompare={handleCompare}
              />
            )}

            {selectedRun && (
              <>
                {sessions.length > 0 && (
                  <div className="mb-4">
                    <SessionViewer sessions={sessions} />
                  </div>
                )}
                <TraceViewer
                  traces={traces}
                  isLoading={tracesLoading}
                  error={tracesError}
                />
              </>
            )}
          </>
        )}

        {activeTab === "datasets" && (
          <DatasetViewer
            datasets={datasets}
            isLoading={datasetsLoading}
            error={datasetsError}
            onSelectDataset={handleSelectDataset}
            selectedDataset={selectedDatasetDetail}
            selectedDatasetLoading={datasetDetailLoading}
          />
        )}
      </div>
    </div>
  );
}
