"use client";

import { useParams } from "next/navigation";
import { useDatasetDetail } from "@/hooks/useEvalExplorer";
import { DatasetViewer } from "@/components/eval-explorer/DatasetViewer";
import { Breadcrumb } from "@/components/eval-nav/Breadcrumb";

export default function DatasetDetailPage() {
  const params = useParams();
  const datasetName = params.datasetName as string;
  const { dataset, isLoading, error } = useDatasetDetail(datasetName);

  const breadcrumbItems = [
    { label: "Datasets", href: "/admin/evals/datasets" },
    { label: datasetName, href: `/admin/evals/datasets/${datasetName}` },
  ];

  return (
    <div>
      <Breadcrumb items={breadcrumbItems} />
      <h1 className="mb-4 text-2xl font-bold text-gray-900 dark:text-white">
        {datasetName}
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
