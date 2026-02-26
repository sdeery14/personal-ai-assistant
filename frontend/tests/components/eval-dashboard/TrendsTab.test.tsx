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

const mockFetchDetail = vi.fn();
const mockClearDetail = vi.fn();

const defaultRunDetailReturn = {
  detail: null,
  isLoading: false,
  error: null as string | null,
  fetchDetail: mockFetchDetail,
  clear: mockClearDetail,
};

vi.mock("@/hooks/useEvalDashboard", () => ({
  useTrends: () => defaultTrendsReturn,
  useRegressions: () => defaultRegressionsReturn,
  useRunDetail: () => defaultRunDetailReturn,
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
    defaultRunDetailReturn.detail = null;
    defaultRunDetailReturn.isLoading = false;
    defaultRunDetailReturn.error = null;
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

  it("detail table defaults to latest-first", () => {
    defaultTrendsReturn.summaries = [
      makeSummary({
        eval_type: "quality",
        points: [
          {
            run_id: "run-old",
            timestamp: "2026-02-20T12:00:00Z",
            eval_type: "quality",
            pass_rate: 0.7,
            average_score: 3.5,
            total_cases: 10,
            error_cases: 0,
            prompt_versions: { system: "1" },
            eval_status: "passed",
          },
          {
            run_id: "run-mid",
            timestamp: "2026-02-22T12:00:00Z",
            eval_type: "quality",
            pass_rate: 0.8,
            average_score: 4.0,
            total_cases: 10,
            error_cases: 0,
            prompt_versions: { system: "1" },
            eval_status: "passed",
          },
          {
            run_id: "run-new",
            timestamp: "2026-02-24T12:00:00Z",
            eval_type: "quality",
            pass_rate: 0.9,
            average_score: 4.5,
            total_cases: 10,
            error_cases: 0,
            prompt_versions: { system: "1" },
            eval_status: "passed",
          },
        ],
      }),
    ];
    render(<TrendsTab />);
    fireEvent.click(screen.getByText("quality"));

    const rows = screen.getAllByRole("row").filter((row) =>
      row.querySelector("td.font-mono")
    );
    // First data row should be the newest run
    expect(rows[0]).toHaveTextContent("run-new");
    expect(rows[2]).toHaveTextContent("run-old");
  });

  it("clicking a column header toggles sort order", () => {
    defaultTrendsReturn.summaries = [
      makeSummary({
        eval_type: "quality",
        points: [
          {
            run_id: "run-low",
            timestamp: "2026-02-20T12:00:00Z",
            eval_type: "quality",
            pass_rate: 0.5,
            average_score: 2.0,
            total_cases: 10,
            error_cases: 0,
            prompt_versions: { system: "1" },
            eval_status: "passed",
          },
          {
            run_id: "run-high",
            timestamp: "2026-02-24T12:00:00Z",
            eval_type: "quality",
            pass_rate: 0.9,
            average_score: 4.5,
            total_cases: 10,
            error_cases: 0,
            prompt_versions: { system: "1" },
            eval_status: "passed",
          },
        ],
      }),
    ];
    render(<TrendsTab />);
    fireEvent.click(screen.getByText("quality"));

    // Default: Date desc — run-high (newest) first
    let rows = screen.getAllByRole("row").filter((row) =>
      row.querySelector("td.font-mono")
    );
    expect(rows[0]).toHaveTextContent("run-high");

    // Click Date header to toggle to asc
    fireEvent.click(screen.getByText(/^Date/));
    rows = screen.getAllByRole("row").filter((row) =>
      row.querySelector("td.font-mono")
    );
    expect(rows[0]).toHaveTextContent("run-low");

    // Click Pass Rate to sort desc by pass_rate
    fireEvent.click(screen.getByText(/^Pass Rate/));
    rows = screen.getAllByRole("row").filter((row) =>
      row.querySelector("td.font-mono")
    );
    expect(rows[0]).toHaveTextContent("run-high");
  });
});
