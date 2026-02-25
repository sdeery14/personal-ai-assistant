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
    eval_type: "quality",
    latest_pass_rate: 0.9,
    trend_direction: "stable",
    run_count: 5,
    points: [
      {
        run_id: "run-1",
        timestamp: "2026-02-24T12:00:00Z",
        eval_type: "quality",
        pass_rate: 0.9,
        average_score: 4.2,
        total_cases: 10,
        error_cases: 0,
        prompt_versions: { system: "1" },
        eval_status: "passed",
      },
    ],
    prompt_changes: [],
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
      makeSummary({ eval_type: "quality", latest_pass_rate: 0.9, run_count: 5 }),
      makeSummary({ eval_type: "security", latest_pass_rate: 0.85, run_count: 3 }),
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
