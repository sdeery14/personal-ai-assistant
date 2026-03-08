import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AgentDetail } from "@/components/eval-explorer/AgentDetail";
import type { AgentVersionDetail } from "@/types/eval-explorer";

const mockAgent: AgentVersionDetail = {
  model_id: "model-1",
  name: "assistant",
  git_branch: "main",
  git_commit: "abc1234def5678",
  git_commit_short: "abc1234",
  creation_timestamp: "2026-03-01T12:00:00Z",
  aggregate_quality: 4.2,
  experiment_count: 2,
  total_traces: 10,
  git_repo_url: "https://github.com/user/repo",
  experiment_results: [
    {
      experiment_name: "eval-quality",
      experiment_id: "exp-1",
      eval_type: "quality",
      run_count: 3,
      pass_rate: 0.85,
      average_quality: 4.2,
      latest_run_id: "run-1",
    },
  ],
};

describe("AgentDetail", () => {
  it("renders git metadata", () => {
    render(
      <AgentDetail agent={mockAgent} isLoading={false} error={null} />
    );
    expect(screen.getByText("abc1234def5678")).toBeDefined();
    expect(screen.getByText("main")).toBeDefined();
  });

  it("renders experiment results table", () => {
    render(
      <AgentDetail agent={mockAgent} isLoading={false} error={null} />
    );
    expect(screen.getByText("eval-quality")).toBeDefined();
    expect(screen.getByText("quality")).toBeDefined();
    expect(screen.getByText("85.0%")).toBeDefined();
    expect(screen.getAllByText("4.20").length).toBeGreaterThanOrEqual(1);
  });

  it("shows loading skeleton", () => {
    const { container } = render(
      <AgentDetail agent={null} isLoading={true} error={null} />
    );
    expect(container.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
  });

  it("shows error message", () => {
    render(
      <AgentDetail agent={null} isLoading={false} error="Something went wrong" />
    );
    expect(screen.getByText("Error: Something went wrong")).toBeDefined();
  });

  it("shows not found for null agent", () => {
    render(
      <AgentDetail agent={null} isLoading={false} error={null} />
    );
    expect(screen.getByText("Agent version not found.")).toBeDefined();
  });

  it("calls onExperimentClick when clicking experiment row", () => {
    const onExperimentClick = vi.fn();
    render(
      <AgentDetail
        agent={mockAgent}
        isLoading={false}
        error={null}
        onExperimentClick={onExperimentClick}
      />
    );
    fireEvent.click(screen.getByText("eval-quality"));
    expect(onExperimentClick).toHaveBeenCalledWith("exp-1", "quality", "eval-quality");
  });

});
