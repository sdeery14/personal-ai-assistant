import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { TrendsTab } from "@/components/eval-dashboard/TrendsTab";
import type { TrendSummary, RegressionReport } from "@/types/eval-dashboard";

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

const mockTrendsRefresh = vi.fn();
const mockRegressionsRefresh = vi.fn();

const defaultTrendsReturn = {
  summaries: [] as TrendSummary[],
  isLoading: false,
  error: null as string | null,
  refresh: mockTrendsRefresh,
};

const defaultRegressionsReturn = {
  reports: [] as RegressionReport[],
  hasRegressions: false,
  isLoading: false,
  error: null as string | null,
  refresh: mockRegressionsRefresh,
};

vi.mock("@/hooks/useEvalDashboard", () => ({
  useTrends: () => defaultTrendsReturn,
  useRegressions: () => defaultRegressionsReturn,
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

function makeReport(overrides: Partial<RegressionReport> = {}): RegressionReport {
  return {
    eval_type: "quality",
    baseline_run_id: "run-0",
    current_run_id: "run-1",
    baseline_pass_rate: 0.85,
    current_pass_rate: 0.9,
    delta_pp: 5.0,
    threshold: 0.8,
    verdict: "PASS",
    changed_prompts: [],
    baseline_timestamp: "2026-02-23T12:00:00Z",
    current_timestamp: "2026-02-24T12:00:00Z",
    ...overrides,
  };
}

describe("TrendsTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    defaultTrendsReturn.summaries = [];
    defaultTrendsReturn.isLoading = false;
    defaultTrendsReturn.error = null;
    defaultRegressionsReturn.reports = [];
    defaultRegressionsReturn.hasRegressions = false;
    defaultRegressionsReturn.isLoading = false;
    defaultRegressionsReturn.error = null;
  });

  it("shows empty state when no summaries", () => {
    render(<TrendsTab />);
    expect(screen.getByText("No eval data available yet")).toBeInTheDocument();
  });

  it("renders summary table with eval types", () => {
    defaultTrendsReturn.summaries = [
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
    defaultTrendsReturn.isLoading = true;
    const { container } = render(<TrendsTab />);
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("shows error with retry button", () => {
    defaultTrendsReturn.error = "Failed to load trends";
    render(<TrendsTab />);
    expect(screen.getByText("Failed to load trends")).toBeInTheDocument();
    expect(screen.getByText("Retry")).toBeInTheDocument();
  });

  it("clicking a row expands detail view", () => {
    defaultTrendsReturn.summaries = [makeSummary()];
    render(<TrendsTab />);

    fireEvent.click(screen.getByText("quality"));
    // Detail view should show the chart container
    expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
  });

  it("shows delta column from regression data", () => {
    defaultTrendsReturn.summaries = [
      makeSummary({ eval_type: "quality" }),
      makeSummary({ eval_type: "security" }),
    ];
    defaultRegressionsReturn.reports = [
      makeReport({ eval_type: "quality", verdict: "PASS", delta_pp: 5.0 }),
      makeReport({ eval_type: "security", verdict: "REGRESSION", delta_pp: -15.0 }),
    ];
    defaultRegressionsReturn.hasRegressions = true;
    render(<TrendsTab />);

    expect(screen.getByText("+5.0pp")).toBeInTheDocument();
    expect(screen.getByText("-15.0pp")).toBeInTheDocument();
  });

  it("shows regressions detected banner", () => {
    defaultTrendsReturn.summaries = [makeSummary()];
    defaultRegressionsReturn.reports = [makeReport({ verdict: "REGRESSION" })];
    defaultRegressionsReturn.hasRegressions = true;
    render(<TrendsTab />);

    expect(screen.getByText("Regressions detected")).toBeInTheDocument();
  });

  it("shows no regressions banner when all pass", () => {
    defaultTrendsReturn.summaries = [makeSummary()];
    defaultRegressionsReturn.reports = [makeReport({ verdict: "PASS" })];
    defaultRegressionsReturn.hasRegressions = false;
    render(<TrendsTab />);

    expect(screen.getByText("No regressions detected")).toBeInTheDocument();
  });

  it("shows changed prompts in detail view", () => {
    defaultTrendsReturn.summaries = [makeSummary({ eval_type: "quality" })];
    defaultRegressionsReturn.reports = [
      makeReport({
        eval_type: "quality",
        changed_prompts: [
          {
            timestamp: "2026-02-24T12:00:00Z",
            run_id: "run-1",
            prompt_name: "system",
            from_version: "1",
            to_version: "2",
          },
        ],
      }),
    ];
    render(<TrendsTab />);

    fireEvent.click(screen.getByText("quality"));
    expect(screen.getByText(/Changed: system v1/)).toBeInTheDocument();
  });

  it("shows runs dropdown in detail view", () => {
    defaultTrendsReturn.summaries = [makeSummary()];
    render(<TrendsTab />);

    fireEvent.click(screen.getByText("quality"));
    const select = screen.getByDisplayValue("10");
    expect(select).toBeInTheDocument();
  });

  it("shows dash for delta when no regression data for eval type", () => {
    defaultTrendsReturn.summaries = [makeSummary({ eval_type: "quality" })];
    // No regression reports
    render(<TrendsTab />);

    expect(screen.getByText("\u2014")).toBeInTheDocument();
  });
});
