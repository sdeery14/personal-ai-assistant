import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { RunEvalsTab } from "@/components/eval-dashboard/RunEvalsTab";
import type { EvalRunStatus } from "@/types/eval-dashboard";

const mockStartRun = vi.fn();
const mockRefreshStatus = vi.fn();

const defaultHookReturn = {
  status: null as EvalRunStatus | null,
  isLoading: false,
  error: null as string | null,
  startRun: mockStartRun,
  refreshStatus: mockRefreshStatus,
};

vi.mock("@/hooks/useEvalDashboard", () => ({
  useEvalRun: () => defaultHookReturn,
}));

vi.mock("next-auth/react", () => ({
  useSession: () => ({
    data: { accessToken: "test-token", user: { name: "Admin", isAdmin: true } },
  }),
  getSession: () =>
    Promise.resolve({ accessToken: "test-token" }),
}));

describe("RunEvalsTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    defaultHookReturn.status = null;
    defaultHookReturn.isLoading = false;
    defaultHookReturn.error = null;
  });

  it("renders suite selector and run button", () => {
    render(<RunEvalsTab />);
    expect(screen.getByText("core")).toBeInTheDocument();
    expect(screen.getByText("full")).toBeInTheDocument();
    expect(screen.getByText("Run Suite")).toBeInTheDocument();
  });

  it("calls startRun on button click", () => {
    render(<RunEvalsTab />);
    fireEvent.click(screen.getByText("Run Suite"));
    expect(mockStartRun).toHaveBeenCalledWith("core");
  });

  it("allows selecting full suite", () => {
    render(<RunEvalsTab />);
    fireEvent.click(screen.getByText("full"));
    fireEvent.click(screen.getByText("Run Suite"));
    expect(mockStartRun).toHaveBeenCalledWith("full");
  });

  it("shows progress during run", () => {
    defaultHookReturn.status = {
      runId: "test-123",
      suite: "core",
      status: "running",
      total: 5,
      completed: 2,
      results: [
        { datasetPath: "eval/golden_dataset.json", exitCode: 0, passed: true },
        { datasetPath: "eval/security_golden_dataset.json", exitCode: 0, passed: true },
      ],
      regressionReports: null,
      startedAt: "2026-02-24T12:00:00Z",
      finishedAt: null,
    };
    render(<RunEvalsTab />);

    expect(screen.getByText("2/5")).toBeInTheDocument();
    expect(screen.getByText("Run in progress")).toBeInTheDocument();
  });

  it("shows completion with results", () => {
    defaultHookReturn.status = {
      runId: "test-123",
      suite: "core",
      status: "completed",
      total: 2,
      completed: 2,
      results: [
        { datasetPath: "eval/golden_dataset.json", exitCode: 0, passed: true },
        { datasetPath: "eval/security_golden_dataset.json", exitCode: 1, passed: false },
      ],
      regressionReports: [],
      startedAt: "2026-02-24T12:00:00Z",
      finishedAt: "2026-02-24T12:05:00Z",
    };
    render(<RunEvalsTab />);

    expect(screen.getByText("completed")).toBeInTheDocument();
    expect(screen.getByText("golden_dataset.json")).toBeInTheDocument();
  });

  it("shows error message", () => {
    defaultHookReturn.error = "Failed to start eval run";
    render(<RunEvalsTab />);
    expect(screen.getByText("Failed to start eval run")).toBeInTheDocument();
  });
});
