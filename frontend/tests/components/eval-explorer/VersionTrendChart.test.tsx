import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { VersionTrendChart } from "@/components/eval-explorer/VersionTrendChart";
import type { AgentVersionSummary } from "@/types/eval-explorer";

const mockAgents: AgentVersionSummary[] = [
  {
    model_id: "model-1",
    name: "assistant",
    git_branch: "main",
    git_commit: "abc1234def5678",
    git_commit_short: "abc1234",
    git_dirty: false,
    creation_timestamp: "2026-03-01T12:00:00Z",
    aggregate_quality: 4.2,
    experiment_count: 2,
    total_traces: 10,
  },
  {
    model_id: "model-2",
    name: "assistant",
    git_branch: "main",
    git_commit: "def5678abc1234",
    git_commit_short: "def5678",
    git_dirty: false,
    creation_timestamp: "2026-03-02T12:00:00Z",
    aggregate_quality: 3.5,
    experiment_count: 2,
    total_traces: 8,
  },
];

describe("VersionTrendChart", () => {
  it("renders bars for agents with quality", () => {
    render(
      <VersionTrendChart agents={mockAgents} isLoading={false} />
    );
    expect(screen.getByText("abc1234")).toBeDefined();
    expect(screen.getByText("def5678")).toBeDefined();
  });

  it("shows empty state when no quality data", () => {
    const noQuality = mockAgents.map((a) => ({ ...a, aggregate_quality: null }));
    render(
      <VersionTrendChart agents={noQuality} isLoading={false} />
    );
    expect(screen.getByText("No quality data yet")).toBeDefined();
  });

  it("shows loading skeleton", () => {
    const { container } = render(
      <VersionTrendChart agents={[]} isLoading={true} />
    );
    expect(container.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
  });

  it("calls onVersionClick when bar is clicked", () => {
    const onVersionClick = vi.fn();
    const { container } = render(
      <VersionTrendChart
        agents={mockAgents}
        isLoading={false}
        onVersionClick={onVersionClick}
      />
    );
    // Find bars with cursor-pointer class (clickable bars)
    const bars = container.querySelectorAll(".cursor-pointer");
    expect(bars.length).toBeGreaterThan(0);
    fireEvent.click(bars[0]);
    expect(onVersionClick).toHaveBeenCalled();
  });
});
