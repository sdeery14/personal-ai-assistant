import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { RegressionsTab } from "@/components/eval-dashboard/RegressionsTab";
import type { RegressionReport } from "@/types/eval-dashboard";

const mockRefresh = vi.fn();

const defaultHookReturn = {
  reports: [] as RegressionReport[],
  hasRegressions: false,
  isLoading: false,
  error: null as string | null,
  refresh: mockRefresh,
};

vi.mock("@/hooks/useEvalDashboard", () => ({
  useRegressions: () => defaultHookReturn,
}));

vi.mock("next-auth/react", () => ({
  useSession: () => ({
    data: { accessToken: "test-token", user: { name: "Admin", isAdmin: true } },
  }),
  getSession: () =>
    Promise.resolve({ accessToken: "test-token" }),
}));

function makeReport(overrides: Partial<RegressionReport> = {}): RegressionReport {
  return {
    eval_type: "quality",
    baseline_run_id: "run-0",
    current_run_id: "run-1",
    baseline_pass_rate: 0.85,
    current_pass_rate: 0.9,
    delta_pp: 0.05,
    threshold: 0.8,
    verdict: "PASS",
    changed_prompts: [],
    baseline_timestamp: "2026-02-23T12:00:00Z",
    current_timestamp: "2026-02-24T12:00:00Z",
    ...overrides,
  };
}

describe("RegressionsTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    defaultHookReturn.reports = [];
    defaultHookReturn.hasRegressions = false;
    defaultHookReturn.isLoading = false;
    defaultHookReturn.error = null;
  });

  it("shows empty state when no reports", () => {
    render(<RegressionsTab />);
    expect(
      screen.getByText("No eval types with sufficient data for comparison.")
    ).toBeInTheDocument();
  });

  it("renders comparison table with verdicts", () => {
    defaultHookReturn.reports = [
      makeReport({ eval_type: "quality", verdict: "PASS" }),
      makeReport({
        eval_type: "security",
        verdict: "REGRESSION",
        delta_pp: -0.15,
      }),
    ];
    defaultHookReturn.hasRegressions = true;
    render(<RegressionsTab />);

    expect(screen.getByText("quality")).toBeInTheDocument();
    expect(screen.getByText("security")).toBeInTheDocument();
    expect(screen.getByText("PASS")).toBeInTheDocument();
    expect(screen.getByText("REGRESSION")).toBeInTheDocument();
  });

  it("shows regressions detected message when has regressions", () => {
    defaultHookReturn.reports = [
      makeReport({ verdict: "REGRESSION" }),
    ];
    defaultHookReturn.hasRegressions = true;
    render(<RegressionsTab />);
    expect(screen.getByText("Regressions detected")).toBeInTheDocument();
  });

  it("shows no regressions message when all pass", () => {
    defaultHookReturn.reports = [makeReport({ verdict: "PASS" })];
    defaultHookReturn.hasRegressions = false;
    render(<RegressionsTab />);
    expect(screen.getByText("No regressions detected")).toBeInTheDocument();
  });

  it("displays changed prompts", () => {
    defaultHookReturn.reports = [
      makeReport({
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
    render(<RegressionsTab />);
    expect(screen.getByText(/Changed: system v1 → v2/)).toBeInTheDocument();
  });

  it("shows loading skeleton", () => {
    defaultHookReturn.isLoading = true;
    const { container } = render(<RegressionsTab />);
    expect(container.querySelectorAll(".animate-pulse").length).toBeGreaterThan(
      0
    );
  });

  it("shows summary counts", () => {
    defaultHookReturn.reports = [
      makeReport({ verdict: "PASS" }),
      makeReport({ eval_type: "security", verdict: "REGRESSION" }),
    ];
    defaultHookReturn.hasRegressions = true;
    render(<RegressionsTab />);
    expect(screen.getByText("1 PASS")).toBeInTheDocument();
    expect(screen.getByText("1 REGRESSION")).toBeInTheDocument();
  });
});
