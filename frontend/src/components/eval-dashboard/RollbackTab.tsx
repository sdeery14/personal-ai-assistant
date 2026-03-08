"use client";

import { useState } from "react";
import { Button, Card, Input, Dialog } from "@/components/ui";
import { Skeleton } from "@/components/ui/Skeleton";
import { usePrompts, useRollback } from "@/hooks/useEvalDashboard";
import type { AuditRecord } from "@/types/eval-dashboard";

export function RollbackTab() {
  const { prompts, isLoading: promptsLoading } = usePrompts();
  const {
    rollbackInfo,
    isLoading,
    error,
    getRollbackInfo,
    executeRollback,
  } = useRollback();

  const [selectedPrompt, setSelectedPrompt] = useState("");
  const [reason, setReason] = useState("");
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [auditResult, setAuditResult] = useState<AuditRecord | null>(null);

  const handleSelectPrompt = async (promptName: string) => {
    setSelectedPrompt(promptName);
    setAuditResult(null);
    setReason("");
    if (promptName) {
      await getRollbackInfo(promptName);
    }
  };

  const handleRollback = async () => {
    if (!rollbackInfo || rollbackInfo.previous_version === null || !reason.trim())
      return;
    const result = await executeRollback(
      rollbackInfo.prompt_name,
      rollbackInfo.alias,
      rollbackInfo.previous_version,
      reason.trim()
    );
    if (result) {
      setAuditResult(result);
      setShowConfirmDialog(false);
      setReason("");
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
        <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
          Select Prompt
        </label>
        <select
          value={selectedPrompt}
          onChange={(e) => handleSelectPrompt(e.target.value)}
          className="block w-64 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
        >
          <option value="">Choose a prompt...</option>
          {prompts.map((p) => (
            <option key={p.name} value={p.name}>
              {p.name} (v{p.current_version})
            </option>
          ))}
        </select>
      </Card>

      {error && (
        <Card>
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </Card>
      )}

      {/* Rollback info */}
      {rollbackInfo && (
        <Card>
          <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">
            Rollback: {rollbackInfo.prompt_name}
          </h3>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
            <dt className="text-gray-500 dark:text-gray-400">Alias</dt>
            <dd className="text-gray-900 dark:text-gray-100">
              {rollbackInfo.alias}
            </dd>
            <dt className="text-gray-500 dark:text-gray-400">Current Version</dt>
            <dd className="text-gray-900 dark:text-gray-100">
              v{rollbackInfo.current_version}
            </dd>
            <dt className="text-gray-500 dark:text-gray-400">Target Version</dt>
            <dd className="text-gray-900 dark:text-gray-100">
              {rollbackInfo.previous_version !== null
                ? `v${rollbackInfo.previous_version}`
                : "—"}
            </dd>
          </dl>

          {rollbackInfo.previous_version === null ? (
            <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">
              No previous version available
            </p>
          ) : (
            <div className="mt-4 space-y-3">
              <Input
                label="Reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Why are you rolling back?"
              />
              <Button
                variant="danger"
                size="sm"
                onClick={() => setShowConfirmDialog(true)}
                disabled={!reason.trim()}
                isLoading={isLoading}
              >
                Rollback
              </Button>
            </div>
          )}
        </Card>
      )}

      {/* Audit result */}
      {auditResult && (
        <Card>
          <h3 className="mb-2 text-sm font-semibold text-green-700 dark:text-green-400">
            Rollback Successful
          </h3>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
            <dt className="text-gray-500 dark:text-gray-400">Prompt</dt>
            <dd className="text-gray-900 dark:text-gray-100">
              {auditResult.prompt_name}
            </dd>
            <dt className="text-gray-500 dark:text-gray-400">Version</dt>
            <dd className="text-gray-900 dark:text-gray-100">
              v{auditResult.from_version} → v{auditResult.to_version}
            </dd>
            <dt className="text-gray-500 dark:text-gray-400">Alias</dt>
            <dd className="text-gray-900 dark:text-gray-100">
              {auditResult.alias}
            </dd>
            <dt className="text-gray-500 dark:text-gray-400">Actor</dt>
            <dd className="text-gray-900 dark:text-gray-100">
              {auditResult.actor}
            </dd>
            <dt className="text-gray-500 dark:text-gray-400">Time</dt>
            <dd className="text-gray-900 dark:text-gray-100">
              {new Date(auditResult.timestamp).toLocaleString()}
            </dd>
            <dt className="text-gray-500 dark:text-gray-400">Reason</dt>
            <dd className="text-gray-900 dark:text-gray-100">
              {auditResult.reason}
            </dd>
          </dl>
        </Card>
      )}

      {/* Confirm dialog */}
      <Dialog
        open={showConfirmDialog}
        onClose={() => setShowConfirmDialog(false)}
        onConfirm={handleRollback}
        title="Confirm Rollback"
        description={`Roll back ${rollbackInfo?.promptName} from v${rollbackInfo?.currentVersion} to v${rollbackInfo?.previousVersion}? This action will be audited.`}
        confirmLabel="Rollback"
        confirmVariant="danger"
        isLoading={isLoading}
      />
    </div>
  );
}
