import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { SessionViewer } from "@/components/eval-explorer/SessionViewer";
import type { SessionGroup } from "@/types/eval-explorer";

function makeSession(overrides: Partial<SessionGroup> = {}): SessionGroup {
  return {
    session_id: "onboard-student",
    eval_type: "onboarding",
    traces: [
      {
        trace_id: "trace-1",
        case_id: "case-1",
        user_prompt: "Hello, I need help",
        assistant_response: "Welcome! How can I assist you?",
        duration_ms: 100,
        error: null,
        session_id: "onboard-student",
        assessments: [],
      },
      {
        trace_id: "trace-2",
        case_id: "case-1",
        user_prompt: "Tell me about the weather",
        assistant_response: "It is sunny today.",
        duration_ms: 150,
        error: null,
        session_id: "onboard-student",
        assessments: [],
      },
    ],
    session_assessment: {
      name: "onboarding_quality",
      raw_value: "good",
      normalized_score: 4.0,
      passed: true,
      rationale: "Good conversation flow",
      source_type: "LLM_JUDGE",
    },
    ...overrides,
  };
}

describe("SessionViewer", () => {
  it("shows empty state when no sessions", () => {
    render(<SessionViewer sessions={[]} isLoading={false} error={null} />);
    expect(screen.getByText(/no sessions found/i)).toBeInTheDocument();
  });

  it("shows loading skeleton", () => {
    render(<SessionViewer sessions={[]} isLoading={true} error={null} />);
    expect(document.querySelector(".animate-pulse")).toBeInTheDocument();
  });

  it("shows error message", () => {
    render(<SessionViewer sessions={[]} isLoading={false} error="Failed to load" />);
    expect(screen.getByText("Failed to load")).toBeInTheDocument();
  });

  it("renders session rows with turn count and rating badge", () => {
    const sessions = [makeSession()];
    render(<SessionViewer sessions={sessions} isLoading={false} error={null} />);
    expect(screen.getByText("1 sessions")).toBeInTheDocument();
    expect(screen.getByText("2 turns")).toBeInTheDocument();
    expect(screen.getByText("onboard-student")).toBeInTheDocument();
    // Rating badge from normalized_score 4.0
    expect(screen.getByText("good")).toBeInTheDocument();
  });

  it("expands to show conversation turns and assessment", () => {
    const sessions = [makeSession()];
    render(<SessionViewer sessions={sessions} isLoading={false} error={null} />);
    // Click to expand
    fireEvent.click(screen.getByText("2 turns"));
    // User prompts appear in both condensed preview and expanded view
    expect(screen.getAllByText("Hello, I need help").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Welcome! How can I assist/)).toBeInTheDocument();
    expect(screen.getByText("Tell me about the weather")).toBeInTheDocument();
    expect(screen.getByText("Good conversation flow")).toBeInTheDocument();
    expect(screen.getByText("Session Assessment")).toBeInTheDocument();
  });
});
