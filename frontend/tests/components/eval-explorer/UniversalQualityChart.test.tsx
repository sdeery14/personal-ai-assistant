import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { UniversalQualityChart } from "@/components/eval-explorer/UniversalQualityChart";
import type { QualityTrendPoint } from "@/types/eval-explorer";

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

function makePoint(overrides: Partial<QualityTrendPoint> = {}): QualityTrendPoint {
  return {
    eval_type: "quality",
    timestamp: "2026-03-01T12:00:00Z",
    universal_quality: 4.2,
    run_id: "run-1",
    ...overrides,
  };
}

describe("UniversalQualityChart", () => {
  it("shows loading state", () => {
    render(<UniversalQualityChart points={[]} isLoading={true} />);
    expect(screen.getByText(/loading quality trend/i)).toBeInTheDocument();
  });

  it("shows empty state when no data", () => {
    render(<UniversalQualityChart points={[]} isLoading={false} />);
    expect(screen.getByText(/no universal quality data/i)).toBeInTheDocument();
  });

  it("renders chart with multiple eval type lines", () => {
    const points = [
      makePoint({ eval_type: "quality", universal_quality: 4.2 }),
      makePoint({ eval_type: "security", universal_quality: 3.8, run_id: "run-2" }),
      makePoint({ eval_type: "memory", universal_quality: 4.5, run_id: "run-3" }),
    ];
    render(<UniversalQualityChart points={points} isLoading={false} />);
    expect(screen.getByTestId("line-chart")).toBeInTheDocument();
    expect(screen.getByTestId("line-quality")).toBeInTheDocument();
    expect(screen.getByTestId("line-security")).toBeInTheDocument();
    expect(screen.getByTestId("line-memory")).toBeInTheDocument();
  });
});
