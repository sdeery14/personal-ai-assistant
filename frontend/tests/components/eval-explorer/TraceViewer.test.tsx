import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { TraceViewer } from "@/components/eval-explorer/TraceViewer";
import type { TraceDetail } from "@/types/eval-explorer";

function makeTrace(overrides: Partial<TraceDetail> = {}): TraceDetail {
  return {
    trace_id: "trace-1",
    case_id: "case-1",
    user_prompt: "What is the weather today?",
    assistant_response: "The weather today is sunny.",
    duration_ms: 150,
    error: null,
    session_id: null,
    assessments: [
      {
        name: "quality",
        raw_value: "excellent",
        normalized_score: 5.0,
        passed: true,
        rationale: "Response is accurate and helpful",
        source_type: "LLM_JUDGE",
      },
    ],
    ...overrides,
  };
}

describe("TraceViewer", () => {
  it("shows loading skeleton", () => {
    render(<TraceViewer traces={[]} isLoading={true} error={null} />);
    expect(document.querySelector(".animate-pulse")).toBeInTheDocument();
  });

  it("shows empty state", () => {
    render(<TraceViewer traces={[]} isLoading={false} error={null} />);
    expect(screen.getByText(/no traces found/i)).toBeInTheDocument();
  });

  it("shows error message", () => {
    render(<TraceViewer traces={[]} isLoading={false} error="Failed to load" />);
    expect(screen.getByText("Failed to load")).toBeInTheDocument();
  });

  it("renders trace rows with assessments", () => {
    const traces = [makeTrace()];
    render(<TraceViewer traces={traces} isLoading={false} error={null} />);
    expect(screen.getByText(/what is the weather/i)).toBeInTheDocument();
    expect(screen.getByText("quality: 5.0")).toBeInTheDocument();
  });

  it("expands trace to show full details", () => {
    const traces = [makeTrace()];
    render(<TraceViewer traces={traces} isLoading={false} error={null} />);
    // Click to expand
    fireEvent.click(screen.getByText(/what is the weather/i));
    expect(screen.getByText("The weather today is sunny.")).toBeInTheDocument();
    expect(screen.getByText("Response is accurate and helpful")).toBeInTheDocument();
  });

  it("renders multi-scorer assessments", () => {
    const traces = [
      makeTrace({
        assessments: [
          {
            name: "quality",
            raw_value: 4.5,
            normalized_score: 4.5,
            passed: true,
            rationale: null,
            source_type: "LLM_JUDGE",
          },
          {
            name: "behavior",
            raw_value: true,
            normalized_score: 1.0,
            passed: true,
            rationale: "Correct tool usage",
            source_type: "CODE",
          },
        ],
      }),
    ];
    render(<TraceViewer traces={traces} isLoading={false} error={null} />);
    expect(screen.getByText("quality: 4.5")).toBeInTheDocument();
    expect(screen.getByText("behavior: 1.0")).toBeInTheDocument();
  });
});
