import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { PromoteTab } from "@/components/eval-dashboard/PromoteTab";
import type { PromptListItem, PromotionGateResult } from "@/types/eval-dashboard";

const mockCheckGate = vi.fn();
const mockExecutePromotion = vi.fn();

const defaultPromptsHook = {
  prompts: [] as PromptListItem[],
  isLoading: false,
  error: null as string | null,
  refresh: vi.fn(),
};

const defaultPromoteHook = {
  checkGate: mockCheckGate,
  executePromotion: mockExecutePromotion,
  isLoading: false,
  error: null as string | null,
};

vi.mock("@/hooks/useEvalDashboard", () => ({
  usePrompts: () => defaultPromptsHook,
  usePromote: () => defaultPromoteHook,
}));

vi.mock("next-auth/react", () => ({
  useSession: () => ({
    data: { accessToken: "test-token", user: { name: "Admin", isAdmin: true } },
  }),
  getSession: () =>
    Promise.resolve({ accessToken: "test-token" }),
}));

describe("PromoteTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    defaultPromptsHook.prompts = [
      { name: "system", currentVersion: 2 },
      { name: "judge", currentVersion: 1 },
    ];
    defaultPromptsHook.isLoading = false;
    defaultPromoteHook.isLoading = false;
    defaultPromoteHook.error = null;
  });

  it("renders prompt selector", () => {
    render(<PromoteTab />);
    expect(screen.getByText("Select Prompt")).toBeInTheDocument();
    expect(screen.getByText("Choose a prompt...")).toBeInTheDocument();
  });

  it("shows prompt options in dropdown", () => {
    render(<PromoteTab />);
    expect(screen.getByText("system (v2)")).toBeInTheDocument();
    expect(screen.getByText("judge (v1)")).toBeInTheDocument();
  });

  it("check gate button is disabled when no prompt selected", () => {
    render(<PromoteTab />);
    const button = screen.getByText("Check Gate");
    expect(button).toBeDisabled();
  });

  it("shows gate check results when allowed", async () => {
    const gateResult: PromotionGateResult = {
      allowed: true,
      promptName: "system",
      fromAlias: "experiment",
      toAlias: "production",
      version: 2,
      evalResults: [
        {
          evalType: "quality",
          passRate: 0.9,
          threshold: 0.8,
          passed: true,
          runId: "run-1",
        },
      ],
      blockingEvals: [],
      justifyingRunIds: ["run-1"],
    };
    mockCheckGate.mockResolvedValue(gateResult);

    render(<PromoteTab />);

    // Select prompt
    const select = screen.getByRole("combobox");
    fireEvent.change(select, { target: { value: "system" } });

    // Click check gate
    fireEvent.click(screen.getByText("Check Gate"));

    // Wait for results
    await vi.waitFor(() => {
      expect(mockCheckGate).toHaveBeenCalledWith("system");
    });
  });

  it("shows loading skeleton for prompts", () => {
    defaultPromptsHook.isLoading = true;
    defaultPromptsHook.prompts = [];
    const { container } = render(<PromoteTab />);
    expect(container.querySelectorAll(".animate-pulse").length).toBeGreaterThan(
      0
    );
  });
});
