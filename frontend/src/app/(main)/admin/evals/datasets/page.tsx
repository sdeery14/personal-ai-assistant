"use client";

import { useRouter } from "next/navigation";
import { useDatasets } from "@/hooks/useEvalExplorer";
import { DatasetViewer } from "@/components/eval-explorer/DatasetViewer";

export default function DatasetsPage() {
  const router = useRouter();
  const { datasets, isLoading, error } = useDatasets();

  return (
    <div>
      <h1 className="mb-4 text-2xl font-bold text-gray-900 dark:text-white">
        Datasets
      </h1>
      <DatasetViewer
        datasets={datasets}
        isLoading={isLoading}
        error={error}
        selectedDataset={null}
        selectedDatasetLoading={false}
        onSelectDataset={(name) => router.push(`/admin/evals/datasets/${name}`)}
      />
    </div>
  );
}
