"use client";

import { useParams } from "next/navigation";
import { useDatasetDetail } from "@/hooks/useEvalExplorer";
import { DatasetViewer } from "@/components/eval-explorer/DatasetViewer";
import { Breadcrumb } from "@/components/eval-nav/Breadcrumb";

export default function DatasetDetailPage() {
  const params = useParams();
  const datasetId = params.datasetId as string;
  const { dataset, isLoading, error } = useDatasetDetail(datasetId);

  const breadcrumbItems = [
    { label: "Datasets", href: "/admin/evals/datasets" },
    { label: dataset?.name || datasetId, href: `/admin/evals/datasets/${datasetId}` },
  ];

  return (
    <div>
      <Breadcrumb items={breadcrumbItems} />
      <h1 className="mb-4 text-2xl font-bold text-gray-900 dark:text-white">
        {dataset?.name || datasetId}
      </h1>
      <DatasetViewer
        datasets={dataset ? [dataset] : []}
        isLoading={isLoading}
        error={error}
        selectedDataset={dataset}
        selectedDatasetLoading={false}
        onSelectDataset={() => {}}
      />
    </div>
  );
}
