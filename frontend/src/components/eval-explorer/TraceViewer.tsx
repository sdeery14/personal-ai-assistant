"use client";

import { useState } from "react";
import { Card } from "@/components/ui";
import { Skeleton } from "@/components/ui/Skeleton";
import type { TraceDetail, AssessmentDetail } from "@/types/eval-explorer";

interface TraceViewerProps {
  traces: TraceDetail[];
  isLoading: boolean;
  error: string | null;
}

const PAGE_SIZE = 25;

function ScoreBadge({ assessment }: { assessment: AssessmentDetail }) {
  const passed = assessment.passed;
  const bgColor =
    passed === true
      ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
      : passed === false
        ? "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
        : "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300";

  const display =
    assessment.normalized_score !== null
      ? assessment.normalized_score.toFixed(1)
      : String(assessment.raw_value);

  return (
    <span
      className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${bgColor}`}
      title={assessment.rationale || undefined}
    >
      {assessment.name}: {display}
    </span>
  );
}

function TraceRow({ trace }: { trace: TraceDetail }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border-b border-gray-100 dark:border-gray-800">
      <div
        className="flex cursor-pointer items-center gap-3 px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-800/50"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="text-xs text-gray-400">{expanded ? "\u25BC" : "\u25B6"}</span>
        <span className="min-w-[80px] font-mono text-xs text-gray-500 dark:text-gray-500">
          {trace.case_id || trace.trace_id.substring(0, 8)}
        </span>
        <span className="flex-1 truncate text-sm text-gray-700 dark:text-gray-300">
          {trace.user_prompt.substring(0, 100)}
          {trace.user_prompt.length > 100 ? "..." : ""}
        </span>
        {trace.duration_ms !== null && (
          <span className="text-xs text-gray-400">{trace.duration_ms}ms</span>
        )}
        <div className="flex gap-1">
          {trace.assessments.map((a, i) => (
            <ScoreBadge key={i} assessment={a} />
          ))}
        </div>
      </div>
      {expanded && (
        <div className="bg-gray-50 px-6 py-3 dark:bg-gray-900/50">
          <div className="mb-3">
            <h4 className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">
              User Prompt
            </h4>
            <p className="whitespace-pre-wrap text-sm text-gray-800 dark:text-gray-200">
              {trace.user_prompt}
            </p>
          </div>
          <div className="mb-3">
            <h4 className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">
              Assistant Response
            </h4>
            <p className="whitespace-pre-wrap text-sm text-gray-800 dark:text-gray-200">
              {trace.assistant_response}
            </p>
          </div>
          {trace.error && (
            <div className="mb-3">
              <h4 className="mb-1 text-xs font-medium text-red-500">Error</h4>
              <p className="text-sm text-red-600 dark:text-red-400">
                {trace.error}
              </p>
            </div>
          )}
          {trace.assessments.length > 0 && (
            <div>
              <h4 className="mb-2 text-xs font-medium text-gray-500 dark:text-gray-400">
                Assessments
              </h4>
              <div className="space-y-2">
                {trace.assessments.map((a, i) => (
                  <div
                    key={i}
                    className="rounded border border-gray-200 bg-white p-2 dark:border-gray-700 dark:bg-gray-800"
                  >
                    <div className="flex items-center gap-2">
                      <ScoreBadge assessment={a} />
                      {a.source_type && (
                        <span className="text-xs text-gray-400">
                          ({a.source_type})
                        </span>
                      )}
                    </div>
                    {a.rationale && (
                      <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                        {a.rationale}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function TraceViewer({ traces, isLoading, error }: TraceViewerProps) {
  const [page, setPage] = useState(0);

  if (error) {
    return (
      <Card className="p-4">
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card className="p-4">
        <Skeleton className="mb-2 h-6 w-48" />
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="mb-1 h-10 w-full" />
        ))}
      </Card>
    );
  }

  if (traces.length === 0) {
    return (
      <Card className="p-4">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No traces found for this run.
        </p>
      </Card>
    );
  }

  const totalPages = Math.max(1, Math.ceil(traces.length / PAGE_SIZE));
  const pageTraces = traces.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  return (
    <div>
      <div className="mb-2 text-xs text-gray-500 dark:text-gray-400">
        {traces.length} traces
      </div>
      {pageTraces.map((trace) => (
        <TraceRow key={trace.trace_id} trace={trace} />
      ))}
      {totalPages > 1 && (
        <div className="mt-2 flex items-center justify-between px-3 text-xs text-gray-500 dark:text-gray-400">
          <span>
            Page {page + 1} of {totalPages}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="rounded px-2 py-1 hover:bg-gray-100 disabled:opacity-50 dark:hover:bg-gray-800"
            >
              Prev
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="rounded px-2 py-1 hover:bg-gray-100 disabled:opacity-50 dark:hover:bg-gray-800"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
