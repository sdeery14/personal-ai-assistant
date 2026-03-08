"use client";

import { useParams, useRouter } from "next/navigation";
import { useAgentVersionDetail } from "@/hooks/useEvalExplorer";
import { AgentDetail } from "@/components/eval-explorer/AgentDetail";
import { Breadcrumb } from "@/components/eval-nav/Breadcrumb";

export default function AgentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const modelId = params.modelId as string;
  const { agent, isLoading, error } = useAgentVersionDetail(modelId);

  const breadcrumbItems = [
    { label: "Agents", href: "/admin/evals/agents" },
    {
      label: agent?.git_commit_short || modelId.substring(0, 8),
      href: `/admin/evals/agents/${modelId}`,
    },
  ];

  return (
    <div>
      <Breadcrumb items={breadcrumbItems} />
      <AgentDetail
        agent={agent}
        isLoading={isLoading}
        error={error}
        onExperimentClick={(experimentId, evalType, name) =>
          router.push(
            `/admin/evals/experiments/${experimentId}?name=${encodeURIComponent(name)}&eval_type=${encodeURIComponent(evalType)}`
          )
        }
      />
    </div>
  );
}
