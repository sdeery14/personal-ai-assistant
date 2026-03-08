"use client";

import { useRouter } from "next/navigation";
import { useExperiments } from "@/hooks/useEvalExplorer";
import { ExperimentBrowser } from "@/components/eval-explorer/ExperimentBrowser";

export default function ExperimentsPage() {
  const router = useRouter();
  const { experiments, isLoading, error } = useExperiments();

  return (
    <div>
      <h1 className="mb-4 text-2xl font-bold text-gray-900 dark:text-white">
        Experiments
      </h1>
      <ExperimentBrowser
        experiments={experiments}
        isLoading={isLoading}
        error={error}
        onSelect={(exp) =>
          router.push(
            `/admin/evals/experiments/${exp.experiment_id}?name=${encodeURIComponent(exp.name)}&eval_type=${encodeURIComponent(exp.eval_type)}`
          )
        }
      />
    </div>
  );
}
