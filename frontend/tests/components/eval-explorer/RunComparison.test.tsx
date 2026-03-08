import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { RunComparison } from "@/components/eval-explorer/RunComparison";
import type { RunSummary } from "@/types/eval-explorer";

function makeRun(overrides: Partial<RunSummary> = {}): RunSummary {
  return {
    run_id: "run-1",
    timestamp: "2026-03-01T12:00:00Z",
    params: { model: "gpt-4o", git_sha: "abc1234" },
    metrics: { pass_rate: 0.9, average_score: 4.2 },
    universal_quality: 4.2,
    trace_count: 10,
    ...overrides,
  };
}

describe("RunComparison", () => {
  it("renders comparison with param and metric diffs", () => {
    const runA = makeRun({ run_id: "run-a", params: { model: "gpt-4o" }, metrics: { pass_rate: 0.8 } });
    const runB = makeRun({ run_id: "run-b", params: { model: "gpt-4o-mini" }, metrics: { pass_rate: 0.9 } });
    render(<RunComparison runA={runA} runB={runB} onClose={vi.fn()} />);
    expect(screen.getByText("Run Comparison")).toBeInTheDocument();
    expect(screen.getByText("gpt-4o")).toBeInTheDocument();
    expect(screen.getByText("gpt-4o-mini")).toBeInTheDocument();
  });

  it("highlights changed params", () => {
    const runA = makeRun({ params: { model: "gpt-4o" } });
    const runB = makeRun({ params: { model: "gpt-4o-mini" } });
    const { container } = render(
      <RunComparison runA={runA} runB={runB} onClose={vi.fn()} />
    );
    // Changed param rows should have yellow background
    const yellowRows = container.querySelectorAll(".bg-yellow-50");
    expect(yellowRows.length).toBeGreaterThan(0);
  });

  it("calls onClose when close button clicked", () => {
    const onClose = vi.fn();
    render(
      <RunComparison runA={makeRun()} runB={makeRun()} onClose={onClose} />
    );
    fireEvent.click(screen.getByText("Close"));
    expect(onClose).toHaveBeenCalled();
  });
});
