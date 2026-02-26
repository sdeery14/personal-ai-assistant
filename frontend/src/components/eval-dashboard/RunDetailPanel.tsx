"use client";

import { Fragment, useState, useMemo } from "react";
import { Card, Button } from "@/components/ui";
import type { RunDetail, RunCaseResult } from "@/types/eval-dashboard";

type CaseSortKey = "case_id" | "score" | "passed" | "duration_ms" | "error";
type SortDir = "asc" | "desc";

function SortArrow({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return null;
  return <span className="ml-1">{dir === "asc" ? "\u25B2" : "\u25BC"}</span>;
}

function PassedBadge({ passed }: { passed: boolean | null }) {
  if (passed === null) {
    return (
      <span className="inline-block rounded px-1.5 py-0.5 text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400">
        N/A
      </span>
    );
  }
  return (
    <span
      className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${
        passed
          ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
          : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
      }`}
    >
      {passed ? "Pass" : "Fail"}
    </span>
  );
}

/** Parse a conversation transcript string into user/assistant turn pairs. */
function parseTranscript(
  text: string
): { role: "user" | "assistant"; content: string }[] {
  const turns: { role: "user" | "assistant"; content: string }[] = [];
  // Match patterns like "[turn-1] User:" or "[turn-1] Assistant:"
  const regex = /\[turn-\d+]\s*(User|Assistant):\s*/gi;
  let lastIndex = 0;
  let lastRole: "user" | "assistant" | null = null;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (lastRole !== null) {
      turns.push({ role: lastRole, content: text.slice(lastIndex, match.index).trim() });
    }
    lastRole = match[1].toLowerCase() as "user" | "assistant";
    lastIndex = regex.lastIndex;
  }
  if (lastRole !== null) {
    turns.push({ role: lastRole, content: text.slice(lastIndex).trim() });
  }
  // If no turn markers found, return the whole thing as a single assistant entry
  if (turns.length === 0 && text) {
    turns.push({ role: "assistant", content: text });
  }
  return turns;
}

function ConversationView({ transcript }: { transcript: string }) {
  const turns = parseTranscript(transcript);
  return (
    <div className="space-y-2">
      {turns.map((t, i) => (
        <div
          key={i}
          className={`rounded px-3 py-2 text-xs ${
            t.role === "user"
              ? "border-l-2 border-blue-400 bg-blue-50/50 dark:border-blue-500 dark:bg-blue-900/20"
              : "border-l-2 border-green-400 bg-green-50/50 dark:border-green-500 dark:bg-green-900/20"
          }`}
        >
          <span
            className={`font-semibold ${
              t.role === "user"
                ? "text-blue-600 dark:text-blue-400"
                : "text-green-600 dark:text-green-400"
            }`}
          >
            {t.role === "user" ? "User" : "Assistant"}
          </span>
          <p className="mt-1 whitespace-pre-wrap text-gray-800 dark:text-gray-200">
            {t.content}
          </p>
        </div>
      ))}
    </div>
  );
}

function CaseExpandedRow({ c }: { c: RunCaseResult }) {
  const transcript =
    typeof c.extra.conversation_transcript === "string"
      ? c.extra.conversation_transcript
      : null;

  // Separate conversation_transcript and persona from other extra fields
  const extraEntries = Object.entries(c.extra).filter(
    ([k, v]) =>
      v !== null &&
      v !== undefined &&
      v !== "" &&
      k !== "conversation_transcript" &&
      k !== "persona"
  );

  const persona =
    typeof c.extra.persona === "string" ? c.extra.persona : null;

  const hasPromptResponse = !!(c.user_prompt || c.assistant_response);

  return (
    <tr>
      <td colSpan={6} className="px-2 py-3">
        <div className="space-y-3 rounded border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/50">
          {/* Persona label */}
          {persona && (
            <div>
              <span className="rounded bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
                {persona}
              </span>
            </div>
          )}

          {/* Multi-turn conversation view */}
          {transcript && (
            <div>
              <p className="mb-1 text-xs font-semibold text-gray-500 dark:text-gray-400">
                Conversation
              </p>
              <ConversationView transcript={transcript} />
            </div>
          )}

          {/* Single-turn prompt/response view (same styling as multi-turn) */}
          {hasPromptResponse && (
            <div>
              <p className="mb-1 text-xs font-semibold text-gray-500 dark:text-gray-400">
                Conversation
              </p>
              <div className="space-y-2">
                {c.user_prompt && (
                  <div className="rounded px-3 py-2 text-xs border-l-2 border-blue-400 bg-blue-50/50 dark:border-blue-500 dark:bg-blue-900/20">
                    <span className="font-semibold text-blue-600 dark:text-blue-400">
                      User
                    </span>
                    <p className="mt-1 whitespace-pre-wrap text-gray-800 dark:text-gray-200">
                      {c.user_prompt}
                    </p>
                  </div>
                )}
                {c.assistant_response && (
                  <div className="rounded px-3 py-2 text-xs border-l-2 border-green-400 bg-green-50/50 dark:border-green-500 dark:bg-green-900/20">
                    <span className="font-semibold text-green-600 dark:text-green-400">
                      Assistant
                    </span>
                    <p className="mt-1 whitespace-pre-wrap text-gray-800 dark:text-gray-200">
                      {c.assistant_response}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Nothing to show */}
          {!transcript && !hasPromptResponse && (
            <p className="text-xs text-gray-400 dark:text-gray-500">
              No conversation data available.
            </p>
          )}

          {c.justification && (
            <div>
              <p className="mb-1 text-xs font-semibold text-gray-500 dark:text-gray-400">
                Justification
              </p>
              <p className="whitespace-pre-wrap text-xs text-gray-800 dark:text-gray-200">
                {c.justification}
              </p>
            </div>
          )}
          {c.error && (
            <div>
              <p className="mb-1 text-xs font-semibold text-yellow-600 dark:text-yellow-400">
                Error
              </p>
              <p className="whitespace-pre-wrap text-xs text-yellow-700 dark:text-yellow-300">
                {c.error}
              </p>
            </div>
          )}
          {extraEntries.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-semibold text-gray-500 dark:text-gray-400">
                Extra Fields
              </p>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                {extraEntries.map(([k, v]) => (
                  <div key={k}>
                    <span className="font-medium text-gray-600 dark:text-gray-400">
                      {k}:
                    </span>{" "}
                    <span className="text-gray-800 dark:text-gray-200">
                      {typeof v === "object" ? JSON.stringify(v) : String(v)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </td>
    </tr>
  );
}

export function RunDetailPanel({
  detail,
  onClose,
}: {
  detail: RunDetail;
  onClose: () => void;
}) {
  const [expandedCaseId, setExpandedCaseId] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<CaseSortKey>("case_id");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  // Extract key params
  const model = detail.params["model"] || detail.params["openai_model"] || "-";
  const judgeModel = detail.params["judge_model"] || "-";
  const datasetVersion = detail.params["dataset_version"] || detail.params["dataset"] || "-";

  // Extract key metrics
  const passRate = detail.metrics["pass_rate"];
  const avgScore = detail.metrics["average_score"];
  const totalCases = detail.metrics["total_cases"];
  const errorCases = detail.metrics["error_cases"];

  // Prompt versions from params matching prompt.*
  const promptVersions = Object.entries(detail.params)
    .filter(([k]) => k.startsWith("prompt."))
    .map(([k, v]) => [k.replace("prompt.", ""), v] as const);

  // Computed case counts
  const passedCount = detail.cases.filter((c) => c.passed === true).length;
  const failedCount = detail.cases.filter((c) => c.passed === false).length;
  const errorCount = detail.cases.filter((c) => c.error != null).length;

  const sortedCases = useMemo(() => {
    return [...detail.cases].sort((a, b) => {
      let cmp = 0;
      if (sortKey === "case_id") {
        cmp = a.case_id.localeCompare(b.case_id);
      } else if (sortKey === "score") {
        cmp = (a.score ?? -1) - (b.score ?? -1);
      } else if (sortKey === "passed") {
        const av = a.passed === null ? -1 : a.passed ? 1 : 0;
        const bv = b.passed === null ? -1 : b.passed ? 1 : 0;
        cmp = av - bv;
      } else if (sortKey === "duration_ms") {
        cmp = (a.duration_ms ?? 0) - (b.duration_ms ?? 0);
      } else if (sortKey === "error") {
        const ae = a.error ? 1 : 0;
        const be = b.error ? 1 : 0;
        cmp = ae - be;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [detail.cases, sortKey, sortDir]);

  function handleSort(key: CaseSortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "case_id" ? "asc" : "desc");
    }
  }

  return (
    <Card>
      {/* Header */}
      <div className="mb-4 flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Run Detail
          </h3>
          <p className="mt-1 font-mono text-xs text-gray-500 dark:text-gray-400">
            {detail.run_id}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {detail.eval_type} &middot;{" "}
            {new Date(detail.timestamp).toLocaleString()}
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={onClose}>
          Close
        </Button>
      </div>

      {/* Metadata grid */}
      <div className="mb-4 grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-4">
        <div>
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
            Model
          </span>
          <p className="text-gray-800 dark:text-gray-200">{model}</p>
        </div>
        <div>
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
            Judge Model
          </span>
          <p className="text-gray-800 dark:text-gray-200">{judgeModel}</p>
        </div>
        <div>
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
            Dataset
          </span>
          <p className="text-gray-800 dark:text-gray-200">{datasetVersion}</p>
        </div>
        <div>
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
            Pass Rate
          </span>
          <p className="text-gray-800 dark:text-gray-200">
            {passRate != null ? `${(passRate * 100).toFixed(1)}%` : "-"}
          </p>
        </div>
        <div>
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
            Avg Score
          </span>
          <p className="text-gray-800 dark:text-gray-200">
            {avgScore != null ? avgScore.toFixed(2) : "-"}
          </p>
        </div>
        <div>
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
            Total Cases
          </span>
          <p className="text-gray-800 dark:text-gray-200">
            {totalCases != null ? totalCases : detail.cases.length}
          </p>
        </div>
        <div>
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
            Passed / Failed / Errors
          </span>
          <p className="text-gray-800 dark:text-gray-200">
            <span className="text-green-600 dark:text-green-400">
              {passedCount}
            </span>{" "}
            /{" "}
            <span className="text-red-600 dark:text-red-400">
              {failedCount}
            </span>{" "}
            /{" "}
            <span className="text-yellow-600 dark:text-yellow-400">
              {errorCount}
            </span>
          </p>
        </div>
        <div>
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
            Error Cases (metric)
          </span>
          <p className="text-gray-800 dark:text-gray-200">
            {errorCases != null ? errorCases : "-"}
          </p>
        </div>
      </div>

      {/* Prompt versions */}
      {promptVersions.length > 0 && (
        <div className="mb-4">
          <p className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">
            Prompt Versions
          </p>
          <div className="flex flex-wrap gap-2">
            {promptVersions.map(([name, ver]) => (
              <span
                key={name}
                className="rounded bg-blue-50 px-2 py-0.5 text-xs text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
              >
                {name}: v{ver}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Cases table */}
      {detail.cases.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th
                  className="cursor-pointer select-none px-2 py-1.5 text-left font-medium text-gray-600 dark:text-gray-400"
                  onClick={() => handleSort("case_id")}
                >
                  Case ID
                  <SortArrow active={sortKey === "case_id"} dir={sortDir} />
                </th>
                <th
                  className="cursor-pointer select-none px-2 py-1.5 text-right font-medium text-gray-600 dark:text-gray-400"
                  onClick={() => handleSort("score")}
                >
                  Score
                  <SortArrow active={sortKey === "score"} dir={sortDir} />
                </th>
                <th
                  className="cursor-pointer select-none px-2 py-1.5 text-center font-medium text-gray-600 dark:text-gray-400"
                  onClick={() => handleSort("passed")}
                >
                  Result
                  <SortArrow active={sortKey === "passed"} dir={sortDir} />
                </th>
                <th
                  className="cursor-pointer select-none px-2 py-1.5 text-right font-medium text-gray-600 dark:text-gray-400"
                  onClick={() => handleSort("duration_ms")}
                >
                  Duration
                  <SortArrow active={sortKey === "duration_ms"} dir={sortDir} />
                </th>
                <th
                  className="cursor-pointer select-none px-2 py-1.5 text-center font-medium text-gray-600 dark:text-gray-400"
                  onClick={() => handleSort("error")}
                >
                  Error
                  <SortArrow active={sortKey === "error"} dir={sortDir} />
                </th>
                <th className="px-2 py-1.5 text-left font-medium text-gray-600 dark:text-gray-400">
                  Prompt (preview)
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedCases.map((c) => (
                <Fragment key={c.case_id}>
                  <tr
                    className={`cursor-pointer border-b border-gray-100 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-700/50 ${
                      expandedCaseId === c.case_id
                        ? "bg-blue-50/50 dark:bg-blue-900/10"
                        : ""
                    }`}
                    onClick={() =>
                      setExpandedCaseId(
                        expandedCaseId === c.case_id ? null : c.case_id
                      )
                    }
                  >
                    <td className="px-2 py-1.5 font-mono text-gray-700 dark:text-gray-300">
                      {c.case_id}
                    </td>
                    <td className="px-2 py-1.5 text-right text-gray-700 dark:text-gray-300">
                      {c.score != null ? c.score.toFixed(2) : "-"}
                    </td>
                    <td className="px-2 py-1.5 text-center">
                      <PassedBadge passed={c.passed} />
                    </td>
                    <td className="px-2 py-1.5 text-right text-gray-700 dark:text-gray-300">
                      {c.duration_ms != null ? `${c.duration_ms}ms` : "-"}
                    </td>
                    <td className="px-2 py-1.5 text-center">
                      {c.error ? (
                        <span className="inline-block rounded px-1.5 py-0.5 text-xs font-medium bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400">
                          Yes
                        </span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="max-w-xs truncate px-2 py-1.5 text-gray-600 dark:text-gray-400">
                      {c.user_prompt.slice(0, 80)}
                      {c.user_prompt.length > 80 ? "..." : ""}
                    </td>
                  </tr>
                  {expandedCaseId === c.case_id && (
                    <CaseExpandedRow c={c} />
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {detail.cases.length === 0 && (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No per-case results available for this run.
        </p>
      )}
    </Card>
  );
}
