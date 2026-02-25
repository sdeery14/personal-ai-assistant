"use client";

import { useState } from "react";
import { Button, Card, Input } from "@/components/ui";
import { Skeleton } from "@/components/ui/Skeleton";
import { usePrompts, usePromote } from "@/hooks/useEvalDashboard";
import type { PromotionGateResult, AuditRecord } from "@/types/eval-dashboard";

export function PromoteTab() {
  const { prompts, isLoading: promptsLoading } = usePrompts();
  const { checkGate, executePromotion, isLoading, error } = usePromote();

  const [selectedPrompt, setSelectedPrompt] = useState("");
  const [gateResult, setGateResult] = useState<PromotionGateResult | null>(null);
  const [auditResult, setAuditResult] = useState<AuditRecord | null>(null);
  const [forceReason, setForceReason] = useState("");
  const [showForceDialog, setShowForceDialog] = useState(false);

  const handleCheckGate = async () => {
    if (!selectedPrompt) return;
    setAuditResult(null);
    const result = await checkGate(selectedPrompt);
    setGateResult(result);
  };

  const handlePromote = async () => {
    if (!gateResult) return;
    const result = await executePromotion(
      gateResult.prompt_name,
      gateResult.to_alias,
      gateResult.version,
      false,
      ""
    );
    if (result) {
      setAuditResult(result);
      setGateResult(null);
    }
  };

  const handleForcePromote = async () => {
    if (!gateResult || !forceReason.trim()) return;
    const result = await executePromotion(
      gateResult.prompt_name,
      gateResult.to_alias,
      gateResult.version,
      true,
      forceReason.trim()
    );
    if (result) {
      setAuditResult(result);
      setGateResult(null);
      setShowForceDialog(false);
      setForceReason("");
    }
  };

  if (promptsLoading) {
    return (
      <Card>
        <div className="space-y-3">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-10 w-64" />
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Prompt selector */}
      <Card>
        <div className="flex items-end gap-3">
          <div className="w-64">
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Select Prompt
            </label>
            <select
              value={selectedPrompt}
              onChange={(e) => {
                setSelectedPrompt(e.target.value);
                setGateResult(null);
                setAuditResult(null);
              }}
              className="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
            >
              <option value="">Choose a prompt...</option>
              {prompts.map((p) => (
                <option key={p.name} value={p.name}>
                  {p.name} (v{p.current_version})
                </option>
              ))}
            </select>
          </div>
          <Button
            onClick={handleCheckGate}
            disabled={!selectedPrompt}
            isLoading={isLoading}
            size="sm"
          >
            Check Gate
          </Button>
        </div>
      </Card>

      {error && (
        <Card>
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </Card>
      )}

      {/* Gate check results */}
      {gateResult && (
        <Card>
          <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">
            Promotion Gate: {gateResult.prompt_name} v{gateResult.version}
            <span className="ml-2">
              ({gateResult.from_alias} → {gateResult.to_alias})
            </span>
          </h3>

          <table className="mb-4 w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="px-3 py-2 text-left font-medium text-gray-700 dark:text-gray-300">
                  Eval Type
                </th>
                <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-300">
                  Pass Rate
                </th>
                <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-300">
                  Threshold
                </th>
                <th className="px-3 py-2 text-center font-medium text-gray-700 dark:text-gray-300">
                  Result
                </th>
              </tr>
            </thead>
            <tbody>
              {gateResult.eval_results.map((e) => (
                <tr
                  key={e.eval_type}
                  className="border-b border-gray-100 dark:border-gray-800"
                >
                  <td className="px-3 py-2 text-gray-900 dark:text-gray-100">
                    {e.eval_type}
                  </td>
                  <td className="px-3 py-2 text-right text-gray-700 dark:text-gray-300">
                    {(e.pass_rate * 100).toFixed(1)}%
                  </td>
                  <td className="px-3 py-2 text-right text-gray-700 dark:text-gray-300">
                    {(e.threshold * 100).toFixed(1)}%
                  </td>
                  <td className="px-3 py-2 text-center">
                    <span
                      className={`inline-block rounded px-2 py-0.5 text-xs font-semibold ${
                        e.passed
                          ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                          : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                      }`}
                    >
                      {e.passed ? "PASS" : "FAIL"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {gateResult.allowed ? (
            <Button onClick={handlePromote} isLoading={isLoading}>
              Promote
            </Button>
          ) : (
            <div className="space-y-2">
              <p className="text-sm text-red-600 dark:text-red-400">
                Blocked by: {gateResult.blocking_evals.join(", ")}
              </p>
              <Button
                variant="danger"
                size="sm"
                onClick={() => setShowForceDialog(true)}
              >
                Force Promote
              </Button>
            </div>
          )}
        </Card>
      )}

      {/* Audit result */}
      {auditResult && <AuditDisplay record={auditResult} />}

      {/* Force promote dialog */}
      {showForceDialog && (
        <>
          <div
            className="fixed inset-0 z-50 bg-black/50"
            onClick={() => {
              setShowForceDialog(false);
              setForceReason("");
            }}
          />
          <div className="fixed inset-0 z-[60] flex items-center justify-center">
            <div className="mx-4 w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Force Promote
              </h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                This promotion was blocked by eval gates. Provide a reason to
                override.
              </p>
              <div className="mt-3">
                <Input
                  label="Reason"
                  value={forceReason}
                  onChange={(e) => setForceReason(e.target.value)}
                  placeholder="Why are you overriding the gate?"
                />
              </div>
              <div className="mt-4 flex justify-end gap-3">
                <Button
                  variant="secondary"
                  onClick={() => {
                    setShowForceDialog(false);
                    setForceReason("");
                  }}
                >
                  Cancel
                </Button>
                <Button
                  variant="danger"
                  onClick={handleForcePromote}
                  disabled={!forceReason.trim()}
                  isLoading={isLoading}
                >
                  Force Promote
                </Button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function AuditDisplay({ record }: { record: AuditRecord }) {
  return (
    <Card>
      <h3 className="mb-2 text-sm font-semibold text-green-700 dark:text-green-400">
        Promotion Successful
      </h3>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
        <dt className="text-gray-500 dark:text-gray-400">Prompt</dt>
        <dd className="text-gray-900 dark:text-gray-100">{record.prompt_name}</dd>
        <dt className="text-gray-500 dark:text-gray-400">Version</dt>
        <dd className="text-gray-900 dark:text-gray-100">
          v{record.from_version} → v{record.to_version}
        </dd>
        <dt className="text-gray-500 dark:text-gray-400">Alias</dt>
        <dd className="text-gray-900 dark:text-gray-100">{record.alias}</dd>
        <dt className="text-gray-500 dark:text-gray-400">Actor</dt>
        <dd className="text-gray-900 dark:text-gray-100">{record.actor}</dd>
        <dt className="text-gray-500 dark:text-gray-400">Time</dt>
        <dd className="text-gray-900 dark:text-gray-100">
          {new Date(record.timestamp).toLocaleString()}
        </dd>
        {record.reason && (
          <>
            <dt className="text-gray-500 dark:text-gray-400">Reason</dt>
            <dd className="text-gray-900 dark:text-gray-100">{record.reason}</dd>
          </>
        )}
      </dl>
    </Card>
  );
}
