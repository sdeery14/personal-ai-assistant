"use client";

import { useState } from "react";
import { Card } from "@/components/ui";
import { Skeleton } from "@/components/ui/Skeleton";
import type {
  AgentVersionDetail,
  ExperimentResult,
  AgentConfig,
  AgentGraphNode,
} from "@/types/eval-explorer";

interface AgentDetailProps {
  agent: AgentVersionDetail | null;
  isLoading: boolean;
  error: string | null;
  onExperimentClick?: (experimentId: string, evalType: string, name: string) => void;
}

function formatPercent(val: number | null): string {
  if (val === null) return "-";
  return `${(val * 100).toFixed(1)}%`;
}

function formatScore(val: number | null): string {
  if (val === null) return "-";
  return val.toFixed(2);
}

// ---------------------------------------------------------------------------
// Agent Graph Visualization (pure CSS, no library)
// ---------------------------------------------------------------------------

function AgentGraphView({ config }: { config: AgentConfig }) {
  const { graph } = config;
  if (!graph.nodes.length) return null;

  const orchestrator = graph.nodes.find((n) => n.type === "orchestrator");
  const specialists = graph.nodes.filter((n) => n.type !== "orchestrator");

  if (!orchestrator) return null;

  return (
    <div className="flex flex-col items-center gap-4">
      {/* Orchestrator node */}
      <div className="rounded-lg border-2 border-blue-500 bg-blue-50 px-4 py-2 text-center dark:border-blue-400 dark:bg-blue-900/20">
        <p className="text-sm font-semibold text-blue-700 dark:text-blue-300">
          {orchestrator.label}
        </p>
        <p className="text-xs text-blue-500 dark:text-blue-400">orchestrator</p>
      </div>

      {/* Connection lines */}
      {specialists.length > 0 && (
        <>
          <div className="h-4 w-px bg-gray-300 dark:bg-gray-600" />
          <div className="text-xs text-gray-400">delegates to</div>
          <div className="h-2 w-px bg-gray-300 dark:bg-gray-600" />
        </>
      )}

      {/* Specialist nodes */}
      <div className="flex flex-wrap justify-center gap-3">
        {specialists.map((node: AgentGraphNode) => (
          <div
            key={node.id}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-center shadow-sm dark:border-gray-600 dark:bg-gray-800"
          >
            <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
              {node.label}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {node.type}
            </p>
            {node.tools && node.tools.length > 0 && (
              <div className="mt-1 flex flex-wrap justify-center gap-1">
                {node.tools.map((tool) => (
                  <span
                    key={tool}
                    className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600 dark:bg-gray-700 dark:text-gray-400"
                  >
                    {tool}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// System Prompt Section (collapsible)
// ---------------------------------------------------------------------------

function SystemPromptSection({ prompt }: { prompt: string }) {
  const [expanded, setExpanded] = useState(false);

  if (!prompt) return null;

  const preview = prompt.slice(0, 200);
  const needsTruncation = prompt.length > 200;

  return (
    <div>
      <pre className="whitespace-pre-wrap rounded bg-gray-50 p-3 text-xs leading-relaxed text-gray-800 dark:bg-gray-900 dark:text-gray-200">
        {expanded || !needsTruncation ? prompt : preview + "..."}
      </pre>
      {needsTruncation && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-1 text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
        >
          {expanded ? "Show less" : "Show full prompt"}
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function AgentDetail({
  agent,
  isLoading,
  error,
  onExperimentClick,
}: AgentDetailProps) {
  if (error) {
    return (
      <Card className="p-4">
        <p className="text-red-600 dark:text-red-400">Error: {error}</p>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-6 w-64" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (!agent) {
    return (
      <Card className="p-4">
        <p className="text-gray-500 dark:text-gray-400">Agent version not found.</p>
      </Card>
    );
  }

  const { config } = agent;
  const hasConfig = config && config.model;

  return (
    <div className="space-y-4">
      {/* Git & Model metadata */}
      <Card className="p-4">
        <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">
          Overview
        </h2>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-4">
          <dt className="text-gray-500 dark:text-gray-400">Commit</dt>
          <dd className="font-mono text-gray-900 dark:text-gray-100">{agent.git_commit_short}</dd>

          <dt className="text-gray-500 dark:text-gray-400">Branch</dt>
          <dd className="text-gray-900 dark:text-gray-100">{agent.git_branch}</dd>

          <dt className="text-gray-500 dark:text-gray-400">Date</dt>
          <dd className="text-gray-900 dark:text-gray-100">
            {agent.creation_timestamp
              ? new Date(agent.creation_timestamp).toLocaleString()
              : "-"}
          </dd>

          <dt className="text-gray-500 dark:text-gray-400">Quality</dt>
          <dd className="text-gray-900 dark:text-gray-100">
            {agent.aggregate_quality != null ? agent.aggregate_quality.toFixed(2) : "-"}
          </dd>

          {hasConfig && (
            <>
              <dt className="text-gray-500 dark:text-gray-400">Model</dt>
              <dd className="font-mono text-gray-900 dark:text-gray-100">{config.model}</dd>

              <dt className="text-gray-500 dark:text-gray-400">Framework</dt>
              <dd className="text-gray-900 dark:text-gray-100">{config.framework}</dd>

              <dt className="text-gray-500 dark:text-gray-400">Max Tokens</dt>
              <dd className="text-gray-900 dark:text-gray-100">{config.max_tokens ?? "-"}</dd>

              <dt className="text-gray-500 dark:text-gray-400">Timeout</dt>
              <dd className="text-gray-900 dark:text-gray-100">
                {config.timeout_seconds ? `${config.timeout_seconds}s` : "-"}
              </dd>
            </>
          )}

          <dt className="text-gray-500 dark:text-gray-400">Total Traces</dt>
          <dd className="text-gray-900 dark:text-gray-100">{agent.total_traces}</dd>
        </dl>
      </Card>

      {/* Agent Architecture Graph */}
      {hasConfig && config.graph.nodes.length > 0 && (
        <Card className="p-4">
          <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">
            Agent Architecture
          </h2>
          <AgentGraphView config={config} />
        </Card>
      )}

      {/* Guardrails */}
      {hasConfig && config.guardrails.length > 0 && (
        <Card className="p-4">
          <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">
            Guardrails
          </h2>
          <div className="flex flex-wrap gap-2">
            {config.guardrails.map((g, i) => (
              <span
                key={i}
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
                  g.type === "input"
                    ? "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400"
                    : "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400"
                }`}
              >
                <span className="font-semibold uppercase">{g.type}</span>
                {g.name}
              </span>
            ))}
          </div>
        </Card>
      )}

      {/* System Prompt */}
      {hasConfig && config.system_prompt && (
        <Card className="p-4">
          <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">
            System Prompt
          </h2>
          <SystemPromptSection prompt={config.system_prompt} />
        </Card>
      )}

      {/* Specialist Agents */}
      {hasConfig && config.specialists.length > 0 && (
        <Card className="p-4">
          <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">
            Specialists ({config.specialists.length})
          </h2>
          <div className="space-y-3">
            {config.specialists.map((spec, i) => (
              <div
                key={i}
                className="rounded-lg border border-gray-200 p-3 dark:border-gray-700"
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {spec.name}
                  </span>
                  <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium uppercase text-gray-500 dark:bg-gray-700 dark:text-gray-400">
                    {spec.type}
                  </span>
                  {spec.model && (
                    <span className="font-mono text-xs text-gray-500 dark:text-gray-400">
                      {spec.model}
                    </span>
                  )}
                </div>
                {spec.description && (
                  <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                    {spec.description}
                  </p>
                )}
                {spec.tools.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {spec.tools.map((tool) => (
                      <span
                        key={tool}
                        className="rounded bg-blue-50 px-2 py-0.5 text-[11px] font-mono text-blue-700 dark:bg-blue-900/20 dark:text-blue-400"
                      >
                        {tool}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Experiment results */}
      <Card className="p-4">
        <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">
          Experiment Results ({agent.experiment_results.length})
        </h2>
        {agent.experiment_results.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            No experiment results linked to this agent version.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="px-3 py-2 font-medium text-gray-600 dark:text-gray-400">Experiment</th>
                  <th className="px-3 py-2 font-medium text-gray-600 dark:text-gray-400">Eval Type</th>
                  <th className="px-3 py-2 font-medium text-gray-600 dark:text-gray-400">Runs</th>
                  <th className="px-3 py-2 font-medium text-gray-600 dark:text-gray-400">Pass Rate</th>
                  <th className="px-3 py-2 font-medium text-gray-600 dark:text-gray-400">Avg Quality</th>
                </tr>
              </thead>
              <tbody>
                {agent.experiment_results.map((er: ExperimentResult) => (
                  <tr
                    key={er.experiment_id}
                    className={`border-b border-gray-100 dark:border-gray-800 ${
                      onExperimentClick
                        ? "cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50"
                        : ""
                    }`}
                    onClick={() =>
                      onExperimentClick?.(er.experiment_id, er.eval_type, er.experiment_name)
                    }
                  >
                    <td className="px-3 py-2 font-medium text-blue-600 dark:text-blue-400">
                      {er.experiment_name}
                    </td>
                    <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                      {er.eval_type}
                    </td>
                    <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                      {er.run_count}
                    </td>
                    <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                      {formatPercent(er.pass_rate)}
                    </td>
                    <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                      {formatScore(er.average_quality)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
