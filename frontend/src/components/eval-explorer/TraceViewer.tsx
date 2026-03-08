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

// ---------------------------------------------------------------------------
// Rating helpers
// ---------------------------------------------------------------------------

const RATING_LABELS: Record<number, string> = {
  5: "excellent",
  4: "good",
  3: "adequate",
  2: "poor",
  1: "unacceptable",
};

const RATING_STYLES: Record<string, string> = {
  excellent: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  good: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  adequate: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  poor: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  unacceptable: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
};

function getRatingLabel(score: number): string {
  return RATING_LABELS[Math.floor(score)] || `${score.toFixed(1)}`;
}

function RatingBadge({ label }: { label: string }) {
  const style = RATING_STYLES[label] ?? "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400";
  return (
    <span className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium capitalize ${style}`}>
      {label}
    </span>
  );
}

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

// ---------------------------------------------------------------------------
// Assessment categorization
// ---------------------------------------------------------------------------

function categorizeAssessments(assessments: AssessmentDetail[]) {
  const rubric = assessments.find(
    (a) => a.name === "rubric" || (a.source_type === "HUMAN" && typeof a.raw_value === "string" && String(a.raw_value).length > 30)
  );
  const judges = assessments.filter(
    (a) => a !== rubric && (a.source_type === "LLM_JUDGE" || a.normalized_score !== null)
  );
  const other = assessments.filter((a) => a !== rubric && !judges.includes(a));
  return { rubric, judges, other };
}

// ---------------------------------------------------------------------------
// Trace row
// ---------------------------------------------------------------------------

function TraceRow({ trace }: { trace: TraceDetail }) {
  const [expanded, setExpanded] = useState(false);
  const { rubric, judges, other } = categorizeAssessments(trace.assessments);

  // Primary score for the condensed row rating badge
  const primaryJudge = judges[0];
  const ratingLabel = primaryJudge?.normalized_score != null
    ? getRatingLabel(primaryJudge.normalized_score)
    : null;

  return (
    <div className="border-b border-gray-100 dark:border-gray-800">
      {/* Condensed row */}
      <div
        className="flex cursor-pointer items-center gap-3 px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-800/50"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="text-xs text-gray-400">{expanded ? "\u25BC" : "\u25B6"}</span>
        <span className="min-w-[60px] font-mono text-xs text-gray-500 dark:text-gray-500">
          {trace.case_id || trace.trace_id.substring(0, 8)}
        </span>
        {ratingLabel && <RatingBadge label={ratingLabel} />}
        <span className="flex-1 truncate text-sm text-gray-700 dark:text-gray-300">
          {trace.user_prompt.substring(0, 120)}
          {trace.user_prompt.length > 120 ? "..." : ""}
        </span>
        {trace.duration_ms != null && trace.duration_ms > 0 && (
          <span className="text-xs text-gray-400">{trace.duration_ms}ms</span>
        )}
        {trace.error && (
          <span className="rounded bg-red-100 px-1.5 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-400">
            error
          </span>
        )}
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="space-y-3 bg-gray-50 px-6 py-3 dark:bg-gray-900/50">
          {/* Conversation */}
          <div className="space-y-2">
            <div className="rounded border-l-2 border-blue-400 bg-blue-50/50 px-3 py-2 text-sm dark:border-blue-500 dark:bg-blue-900/20">
              <span className="text-xs font-semibold text-blue-600 dark:text-blue-400">User</span>
              <p className="mt-1 whitespace-pre-wrap text-gray-800 dark:text-gray-200">
                {trace.user_prompt}
              </p>
            </div>
            <div className="rounded border-l-2 border-green-400 bg-green-50/50 px-3 py-2 text-sm dark:border-green-500 dark:bg-green-900/20">
              <span className="text-xs font-semibold text-green-600 dark:text-green-400">Assistant</span>
              <p className="mt-1 whitespace-pre-wrap text-gray-800 dark:text-gray-200">
                {trace.assistant_response}
              </p>
            </div>
          </div>

          {/* Error */}
          {trace.error && (
            <div className="rounded border border-red-200 bg-red-50/50 p-3 dark:border-red-800 dark:bg-red-900/20">
              <p className="text-xs font-semibold text-red-600 dark:text-red-400">Error</p>
              <p className="mt-1 text-sm text-red-700 dark:text-red-300">{trace.error}</p>
            </div>
          )}

          {/* Rubric (shown before judge feedback for context) */}
          {rubric && (
            <div className="rounded border border-gray-200 bg-white p-3 dark:border-gray-600 dark:bg-gray-800">
              <p className="mb-1 text-xs font-semibold text-gray-500 dark:text-gray-400">Rubric</p>
              <p className="whitespace-pre-wrap text-xs text-gray-700 dark:text-gray-300">
                {String(rubric.raw_value)}
              </p>
            </div>
          )}

          {/* Judge assessments */}
          {judges.length > 0 && (
            <div className="rounded border border-amber-200 bg-amber-50/50 p-3 dark:border-amber-800 dark:bg-amber-900/20">
              <p className="mb-2 text-xs font-semibold text-amber-700 dark:text-amber-400">
                Judge Feedback
              </p>
              {judges.map((a, i) => (
                <div key={i} className={i > 0 ? "mt-2 border-t border-amber-200 pt-2 dark:border-amber-800" : ""}>
                  <div className="mb-1 flex items-center gap-2">
                    <ScoreBadge assessment={a} />
                    {a.source_type && (
                      <span className="text-xs text-gray-400">({a.source_type})</span>
                    )}
                  </div>
                  {a.rationale && (
                    <p className="whitespace-pre-wrap text-xs text-gray-800 dark:text-gray-200">
                      {a.rationale}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Other assessments (behavioral scorers, etc.) */}
          {other.length > 0 && (
            <div>
              <p className="mb-2 text-xs font-medium text-gray-500 dark:text-gray-400">
                Other Assessments
              </p>
              <div className="space-y-2">
                {other.map((a, i) => (
                  <div
                    key={i}
                    className="rounded border border-gray-200 bg-white p-2 dark:border-gray-700 dark:bg-gray-800"
                  >
                    <div className="flex items-center gap-2">
                      <ScoreBadge assessment={a} />
                      {a.source_type && (
                        <span className="text-xs text-gray-400">({a.source_type})</span>
                      )}
                    </div>
                    {a.rationale && (
                      <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">{a.rationale}</p>
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
