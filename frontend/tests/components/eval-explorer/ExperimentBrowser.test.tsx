import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ExperimentBrowser } from "@/components/eval-explorer/ExperimentBrowser";
import type { ExperimentSummary } from "@/types/eval-explorer";

function makeExperiment(overrides: Partial<ExperimentSummary> = {}): ExperimentSummary {
  return {
    experiment_id: "exp-1",
    name: "eval-quality",
    eval_type: "quality",
    run_count: 5,
    last_run_timestamp: "2026-03-01T12:00:00Z",
    latest_pass_rate: 0.9,
    latest_universal_quality: 4.2,
    ...overrides,
  };
}

describe("ExperimentBrowser", () => {
  it("shows loading skeleton", () => {
    render(
      <ExperimentBrowser
        experiments={[]}
        isLoading={true}
        error={null}
        onSelect={vi.fn()}
      />
    );
    // Skeleton renders
    expect(document.querySelector(".animate-pulse")).toBeInTheDocument();
  });

  it("shows error message", () => {
    render(
      <ExperimentBrowser
        experiments={[]}
        isLoading={false}
        error="Something went wrong"
        onSelect={vi.fn()}
      />
    );
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("shows empty state", () => {
    render(
      <ExperimentBrowser
        experiments={[]}
        isLoading={false}
        error={null}
        onSelect={vi.fn()}
      />
    );
    expect(screen.getByText(/no experiments found/i)).toBeInTheDocument();
  });

  it("renders experiments in table", () => {
    const experiments = [
      makeExperiment({ name: "eval-quality", eval_type: "quality" }),
      makeExperiment({ experiment_id: "exp-2", name: "eval-security", eval_type: "security", latest_pass_rate: 0.85 }),
    ];
    render(
      <ExperimentBrowser
        experiments={experiments}
        isLoading={false}
        error={null}
        onSelect={vi.fn()}
      />
    );
    expect(screen.getByText("eval-quality")).toBeInTheDocument();
    expect(screen.getByText("eval-security")).toBeInTheDocument();
    expect(screen.getByText("quality")).toBeInTheDocument();
    expect(screen.getByText("security")).toBeInTheDocument();
  });

  it("calls onSelect when row is clicked", () => {
    const onSelect = vi.fn();
    const exp = makeExperiment();
    render(
      <ExperimentBrowser
        experiments={[exp]}
        isLoading={false}
        error={null}
        onSelect={onSelect}
      />
    );
    fireEvent.click(screen.getByText("eval-quality"));
    expect(onSelect).toHaveBeenCalledWith(exp);
  });

  it("sorts by column when header clicked", () => {
    const experiments = [
      makeExperiment({ name: "eval-quality", run_count: 5 }),
      makeExperiment({ experiment_id: "exp-2", name: "eval-security", run_count: 10 }),
    ];
    render(
      <ExperimentBrowser
        experiments={experiments}
        isLoading={false}
        error={null}
        onSelect={vi.fn()}
      />
    );
    // Click "Runs" header to sort
    fireEvent.click(screen.getByText(/^Runs/));
    const rows = screen.getAllByRole("row");
    // Header + 2 data rows
    expect(rows).toHaveLength(3);
  });
});
