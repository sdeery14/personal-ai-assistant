"use client";

import { useState } from "react";
import { Card } from "@/components/ui";
import type { SessionGroup, AssessmentDetail } from "@/types/eval-explorer";

interface SessionViewerProps {
  sessions: SessionGroup[];
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

function SessionCard({ session }: { session: SessionGroup }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Card className="mb-3">
      <div
        className="flex cursor-pointer items-center justify-between px-4 py-3"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-400">
            {expanded ? "\u25BC" : "\u25B6"}
          </span>
          <span className="font-mono text-xs text-gray-600 dark:text-gray-400">
            {session.session_id.substring(0, 12)}...
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {session.traces.length} turns
          </span>
        </div>
        {session.session_assessment && (
          <ScoreBadge assessment={session.session_assessment} />
        )}
      </div>
      {expanded && (
        <div className="border-t border-gray-200 px-4 py-3 dark:border-gray-700">
          <div className="space-y-3">
            {session.traces.map((trace, idx) => (
              <div key={trace.trace_id} className="relative pl-4">
                <div className="absolute left-0 top-0 bottom-0 w-px bg-gray-200 dark:bg-gray-700" />
                <div className="mb-1 text-xs text-gray-400">
                  Turn {idx + 1}
                  {trace.duration_ms !== null && ` \u00B7 ${trace.duration_ms}ms`}
                </div>
                <div className="mb-1 rounded bg-blue-50 px-2 py-1 text-sm dark:bg-blue-900/20">
                  <span className="text-xs font-medium text-blue-600 dark:text-blue-400">
                    User:
                  </span>{" "}
                  <span className="text-gray-800 dark:text-gray-200">
                    {trace.user_prompt}
                  </span>
                </div>
                <div className="rounded bg-gray-50 px-2 py-1 text-sm dark:bg-gray-800/50">
                  <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                    Assistant:
                  </span>{" "}
                  <span className="text-gray-800 dark:text-gray-200">
                    {trace.assistant_response}
                  </span>
                </div>
                {trace.assessments.length > 0 && (
                  <div className="mt-1 flex gap-1">
                    {trace.assessments.map((a, i) => (
                      <ScoreBadge key={i} assessment={a} />
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
          {session.session_assessment?.rationale && (
            <div className="mt-3 border-t border-gray-200 pt-2 dark:border-gray-700">
              <p className="text-xs text-gray-500 dark:text-gray-400">
                <span className="font-medium">Session Assessment:</span>{" "}
                {session.session_assessment.rationale}
              </p>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

export function SessionViewer({ sessions }: SessionViewerProps) {
  if (sessions.length === 0) return null;

  return (
    <div>
      <h3 className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
        Sessions ({sessions.length})
      </h3>
      {sessions.map((session) => (
        <SessionCard key={session.session_id} session={session} />
      ))}
    </div>
  );
}
