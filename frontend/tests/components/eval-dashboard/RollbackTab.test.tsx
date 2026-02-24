import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { RollbackTab } from "@/components/eval-dashboard/RollbackTab";
import type { PromptListItem, RollbackInfo } from "@/types/eval-dashboard";

const mockGetRollbackInfo = vi.fn();
const mockExecuteRollback = vi.fn();

const defaultPromptsHook = {
  prompts: [] as PromptListItem[],
  isLoading: false,
  error: null as string | null,
  refresh: vi.fn(),
};

const defaultRollbackHook = {
  rollbackInfo: null as RollbackInfo | null,
  isLoading: false,
  error: null as string | null,
  getRollbackInfo: mockGetRollbackInfo,
  executeRollback: mockExecuteRollback,
};

vi.mock("@/hooks/useEvalDashboard", () => ({
  usePrompts: () => defaultPromptsHook,
  useRollback: () => defaultRollbackHook,
}));

vi.mock("next-auth/react", () => ({
  useSession: () => ({
    data: { accessToken: "test-token", user: { name: "Admin", isAdmin: true } },
  }),
  getSession: () =>
    Promise.resolve({ accessToken: "test-token" }),
}));

describe("RollbackTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    defaultPromptsHook.prompts = [
      { name: "system", currentVersion: 3 },
      { name: "judge", currentVersion: 1 },
    ];
    defaultPromptsHook.isLoading = false;
    defaultRollbackHook.rollbackInfo = null;
    defaultRollbackHook.isLoading = false;
    defaultRollbackHook.error = null;
  });

  it("renders prompt selector", () => {
    render(<RollbackTab />);
    expect(screen.getByText("Select Prompt")).toBeInTheDocument();
    expect(screen.getByText("Choose a prompt...")).toBeInTheDocument();
  });

  it("calls getRollbackInfo on prompt selection", () => {
    render(<RollbackTab />);
    const select = screen.getByRole("combobox");
    fireEvent.change(select, { target: { value: "system" } });
    expect(mockGetRollbackInfo).toHaveBeenCalledWith("system");
  });

  it("shows rollback info with versions", () => {
    defaultRollbackHook.rollbackInfo = {
      promptName: "system",
      currentVersion: 3,
      previousVersion: 2,
      alias: "production",
    };
    render(<RollbackTab />);
    expect(screen.getByText("v3")).toBeInTheDocument();
    expect(screen.getByText("v2")).toBeInTheDocument();
  });

  it("disables rollback when no previous version", () => {
    defaultRollbackHook.rollbackInfo = {
      promptName: "judge",
      currentVersion: 1,
      previousVersion: null,
      alias: "production",
    };
    render(<RollbackTab />);
    expect(
      screen.getByText("No previous version available")
    ).toBeInTheDocument();
  });

  it("requires reason before executing rollback", () => {
    defaultRollbackHook.rollbackInfo = {
      promptName: "system",
      currentVersion: 3,
      previousVersion: 2,
      alias: "production",
    };
    render(<RollbackTab />);

    // The card's Rollback button (size="sm") should be disabled without reason
    const rollbackButtons = screen.getAllByText("Rollback");
    const cardButton = rollbackButtons[0];
    expect(cardButton).toBeDisabled();

    // Enter a reason
    const input = screen.getByPlaceholderText("Why are you rolling back?");
    fireEvent.change(input, { target: { value: "regression fix" } });

    // Now button should be enabled
    expect(cardButton).not.toBeDisabled();
  });

  it("shows loading skeleton for prompts", () => {
    defaultPromptsHook.isLoading = true;
    defaultPromptsHook.prompts = [];
    const { container } = render(<RollbackTab />);
    expect(container.querySelectorAll(".animate-pulse").length).toBeGreaterThan(
      0
    );
  });
});
