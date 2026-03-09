import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { QualityTrendChart } from "@/components/eval-explorer/QualityTrendChart";
import type { AgentVersionSummary, QualityTrendPoint } from "@/types/eval-explorer";

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: ({ name }: { name: string }) => <div data-testid={`line-${name}`} />,
  XAxis: () => <div />,
  YAxis: () => <div />,
  CartesianGrid: () => <div />,
  Tooltip: () => <div />,
  Legend: () => <div />,
}));

const mockAgents: AgentVersionSummary[] = [
  {
    model_id: "model-1",
    name: "assistant",
    git_branch: "main",
    git_commit: "abc1234def5678",
    git_commit_short: "abc1234",
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
    creation_timestamp: "2026-03-02T12:00:00Z",
    aggregate_quality: 3.5,
    experiment_count: 2,
    total_traces: 8,
  },
];

const mockPoints: QualityTrendPoint[] = [
  {
    eval_type: "quality",
    timestamp: "2026-03-01T12:30:00Z",
    universal_quality: 4.5,
    run_id: "run-1",
    git_sha: "abc1234",
  },
  {
    eval_type: "onboarding",
    timestamp: "2026-03-01T12:45:00Z",
    universal_quality: 3.9,
    run_id: "run-2",
    git_sha: "abc1234",
  },
];

describe("QualityTrendChart", () => {
  it("shows loading skeleton", () => {
    const { container } = render(
      <QualityTrendChart agents={[]} points={[]} isLoading={true} />
    );
    expect(container.querySelector(".animate-pulse")).toBeInTheDocument();
  });

  it("shows empty state when no quality data", () => {
    render(
      <QualityTrendChart agents={[]} points={[]} isLoading={false} />
    );
    expect(screen.getByText("No quality data yet")).toBeInTheDocument();
  });

  it("shows empty state when agents have no quality scores", () => {
    const noQuality = mockAgents.map((a) => ({ ...a, aggregate_quality: null }));
    render(
      <QualityTrendChart agents={noQuality} points={[]} isLoading={false} />
    );
    expect(screen.getByText("No quality data yet")).toBeInTheDocument();
  });

  it("renders overall line and per-eval-type lines", () => {
    render(
      <QualityTrendChart
        agents={mockAgents}
        points={mockPoints}
        isLoading={false}
      />
    );
    expect(screen.getByTestId("line-chart")).toBeInTheDocument();
    expect(screen.getByTestId("line-Overall")).toBeInTheDocument();
    expect(screen.getByTestId("line-quality")).toBeInTheDocument();
    expect(screen.getByTestId("line-onboarding")).toBeInTheDocument();
  });

  it("renders chart with agents only (no trend points)", () => {
    render(
      <QualityTrendChart
        agents={mockAgents}
        points={[]}
        isLoading={false}
      />
    );
    expect(screen.getByTestId("line-chart")).toBeInTheDocument();
    expect(screen.getByTestId("line-Overall")).toBeInTheDocument();
  });
});
