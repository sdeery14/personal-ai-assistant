"use client";

import { useState } from "react";
import { Card } from "@/components/ui";
import { Skeleton } from "@/components/ui/Skeleton";
import type { SessionGroup, AssessmentDetail } from "@/types/eval-explorer";

interface SessionViewerProps {
  sessions: SessionGroup[];
  isLoading: boolean;
  error: string | null;
}

// ---------------------------------------------------------------------------
// Rating helpers (shared with TraceViewer)
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
// Session row (matches TraceViewer condensed/expanded pattern)
// ---------------------------------------------------------------------------

function SessionRow({ session }: { session: SessionGroup }) {
  const [expanded, setExpanded] = useState(false);

  // Get rating from session-level assessment
  const assessment = session.session_assessment;
  const ratingLabel = assessment?.normalized_score != null
    ? getRatingLabel(assessment.normalized_score)
    : null;

  // Total duration across all turns
  const totalDuration = session.traces.reduce(
    (sum, t) => sum + (t.duration_ms ?? 0),
    0
  );

  return (
    <div className="border-b border-gray-100 dark:border-gray-800">
      {/* Condensed row */}
      <div
        className="flex cursor-pointer items-center gap-3 px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-800/50"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="text-xs text-gray-400">{expanded ? "\u25BC" : "\u25B6"}</span>
        <span className="min-w-[60px] font-mono text-xs text-gray-500 dark:text-gray-500">
          {session.session_id}
        </span>
        {ratingLabel && <RatingBadge label={ratingLabel} />}
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {session.traces.length} turns
        </span>
        <span className="flex-1 truncate text-sm text-gray-700 dark:text-gray-300">
          {session.traces[0]?.user_prompt.substring(0, 100)}
          {(session.traces[0]?.user_prompt.length ?? 0) > 100 ? "..." : ""}
        </span>
        {totalDuration > 0 && (
          <span className="text-xs text-gray-400">{totalDuration}ms</span>
        )}
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="space-y-3 bg-gray-50 px-6 py-3 dark:bg-gray-900/50">
          {/* Conversation turns */}
          <div className="space-y-2">
            {session.traces.map((trace, idx) => (
              <div key={trace.trace_id}>
                <div className="mb-1 text-xs text-gray-400">
                  Turn {idx + 1}
                  {trace.duration_ms != null && trace.duration_ms > 0 && ` · ${trace.duration_ms}ms`}
                </div>
                <div className="rounded border-l-2 border-blue-400 bg-blue-50/50 px-3 py-2 text-sm dark:border-blue-500 dark:bg-blue-900/20">
                  <span className="text-xs font-semibold text-blue-600 dark:text-blue-400">User</span>
                  <p className="mt-1 whitespace-pre-wrap text-gray-800 dark:text-gray-200">
                    {trace.user_prompt}
                  </p>
                </div>
                <div className="mt-1 rounded border-l-2 border-green-400 bg-green-50/50 px-3 py-2 text-sm dark:border-green-500 dark:bg-green-900/20">
                  <span className="text-xs font-semibold text-green-600 dark:text-green-400">Assistant</span>
                  <p className="mt-1 whitespace-pre-wrap text-gray-800 dark:text-gray-200">
                    {trace.assistant_response}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* Session-level assessment */}
          {assessment && (
            <div className="rounded border border-amber-200 bg-amber-50/50 p-3 dark:border-amber-800 dark:bg-amber-900/20">
              <p className="mb-2 text-xs font-semibold text-amber-700 dark:text-amber-400">
                Session Assessment
              </p>
              <div className="mb-1 flex items-center gap-2">
                <ScoreBadge assessment={assessment} />
                {assessment.source_type && (
                  <span className="text-xs text-gray-400">({assessment.source_type})</span>
                )}
              </div>
              {assessment.rationale && (
                <p className="whitespace-pre-wrap text-xs text-gray-800 dark:text-gray-200">
                  {assessment.rationale}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function SessionViewer({ sessions, isLoading, error }: SessionViewerProps) {
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

  if (sessions.length === 0) {
    return (
      <Card className="p-4">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No sessions found for this run.
        </p>
      </Card>
    );
  }

  return (
    <div>
      <div className="mb-2 text-xs text-gray-500 dark:text-gray-400">
        {sessions.length} sessions
      </div>
      {sessions.map((session) => (
        <SessionRow key={session.session_id} session={session} />
      ))}
    </div>
  );
}
