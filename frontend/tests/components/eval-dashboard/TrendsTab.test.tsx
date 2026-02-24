import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { TrendsTab } from "@/components/eval-dashboard/TrendsTab";
import type { TrendSummary } from "@/types/eval-dashboard";

// Mock recharts to avoid rendering issues in tests
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: () => <div />,
  XAxis: () => <div />,
  YAxis: () => <div />,
  CartesianGrid: () => <div />,
  Tooltip: () => <div />,
  ReferenceDot: () => <div />,
}));

const mockRefresh = vi.fn();

const defaultHookReturn = {
  summaries: [] as TrendSummary[],
  isLoading: false,
  error: null as string | null,
  refresh: mockRefresh,
};

vi.mock("@/hooks/useEvalDashboard", () => ({
  useTrends: () => defaultHookReturn,
}));

vi.mock("next-auth/react", () => ({
  useSession: () => ({
    data: { accessToken: "test-token", user: { name: "Admin", isAdmin: true } },
  }),
  getSession: () =>
    Promise.resolve({ accessToken: "test-token" }),
}));

function makeSummary(overrides: Partial<TrendSummary> = {}): TrendSummary {
  return {
    evalType: "quality",
    latestPassRate: 0.9,
    trendDirection: "stable",
    runCount: 5,
    points: [
      {
        runId: "run-1",
        timestamp: "2026-02-24T12:00:00Z",
        evalType: "quality",
        passRate: 0.9,
        averageScore: 4.2,
        totalCases: 10,
        errorCases: 0,
        promptVersions: { system: "1" },
        evalStatus: "passed",
      },
    ],
    promptChanges: [],
    ...overrides,
  };
}

describe("TrendsTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    defaultHookReturn.summaries = [];
    defaultHookReturn.isLoading = false;
    defaultHookReturn.error = null;
  });

  it("shows empty state when no summaries", () => {
    render(<TrendsTab />);
    expect(screen.getByText("No eval data available yet")).toBeInTheDocument();
  });

  it("renders summary table with eval types", () => {
    defaultHookReturn.summaries = [
      makeSummary({ evalType: "quality", latestPassRate: 0.9, runCount: 5 }),
      makeSummary({ evalType: "security", latestPassRate: 0.85, runCount: 3 }),
    ];
    render(<TrendsTab />);

    expect(screen.getByText("quality")).toBeInTheDocument();
    expect(screen.getByText("security")).toBeInTheDocument();
    expect(screen.getByText("90.0%")).toBeInTheDocument();
    expect(screen.getByText("85.0%")).toBeInTheDocument();
  });

  it("shows loading skeleton", () => {
    defaultHookReturn.isLoading = true;
    const { container } = render(<TrendsTab />);
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("shows error with retry button", () => {
    defaultHookReturn.error = "Failed to load trends";
    render(<TrendsTab />);
    expect(screen.getByText("Failed to load trends")).toBeInTheDocument();
    expect(screen.getByText("Retry")).toBeInTheDocument();
  });

  it("clicking a row expands detail view", () => {
    defaultHookReturn.summaries = [makeSummary()];
    render(<TrendsTab />);

    fireEvent.click(screen.getByText("quality"));
    // Detail view should show the chart container
    expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
  });
});
