import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { RunBrowser } from "@/components/eval-explorer/RunBrowser";
import type { RunSummary } from "@/types/eval-explorer";

function makeRun(overrides: Partial<RunSummary> = {}): RunSummary {
  return {
    run_id: "run-1",
    timestamp: "2026-03-01T12:00:00Z",
    params: { model: "gpt-4o", git_sha: "abc1234def5678" },
    metrics: { pass_rate: 0.9, average_score: 4.2, total_cases: 10 },
    universal_quality: 4.2,
    trace_count: 10,
    ...overrides,
  };
}

describe("RunBrowser", () => {
  it("shows loading skeleton", () => {
    render(
      <RunBrowser runs={[]} isLoading={true} error={null} onSelect={vi.fn()} />
    );
    expect(document.querySelector(".animate-pulse")).toBeInTheDocument();
  });

  it("shows empty state", () => {
    render(
      <RunBrowser runs={[]} isLoading={false} error={null} onSelect={vi.fn()} />
    );
    expect(screen.getByText(/no runs found/i)).toBeInTheDocument();
  });

  it("renders runs with metadata", () => {
    const runs = [makeRun()];
    render(
      <RunBrowser runs={runs} isLoading={false} error={null} onSelect={vi.fn()} />
    );
    expect(screen.getByText("gpt-4o")).toBeInTheDocument();
    expect(screen.getByText("90.0%")).toBeInTheDocument();
    expect(screen.getByText("4.20")).toBeInTheDocument();
    expect(screen.getByText("abc1234")).toBeInTheDocument();
  });

  it("calls onSelect when row clicked", () => {
    const onSelect = vi.fn();
    const run = makeRun();
    render(
      <RunBrowser runs={[run]} isLoading={false} error={null} onSelect={onSelect} />
    );
    fireEvent.click(screen.getByText("gpt-4o"));
    expect(onSelect).toHaveBeenCalledWith(run);
  });

  it("shows compare button when 2 runs selected", () => {
    const runs = [
      makeRun({ run_id: "run-1" }),
      makeRun({ run_id: "run-2" }),
    ];
    const onCompare = vi.fn();
    render(
      <RunBrowser
        runs={runs}
        isLoading={false}
        error={null}
        onSelect={vi.fn()}
        selectedRunIds={["run-1", "run-2"]}
        onToggleSelect={vi.fn()}
        onCompare={onCompare}
      />
    );
    const compareBtn = screen.getByText(/compare selected/i);
    expect(compareBtn).toBeInTheDocument();
    fireEvent.click(compareBtn);
    expect(onCompare).toHaveBeenCalled();
  });
});
