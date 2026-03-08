import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { SessionViewer } from "@/components/eval-explorer/SessionViewer";
import type { SessionGroup } from "@/types/eval-explorer";

function makeSession(overrides: Partial<SessionGroup> = {}): SessionGroup {
  return {
    session_id: "session-abc123def456",
    eval_type: "onboarding",
    traces: [
      {
        trace_id: "trace-1",
        case_id: "case-1",
        user_prompt: "Hello, I need help",
        assistant_response: "Welcome! How can I assist you?",
        duration_ms: 100,
        error: null,
        session_id: "session-abc123def456",
        assessments: [],
      },
      {
        trace_id: "trace-2",
        case_id: "case-1",
        user_prompt: "Tell me about the weather",
        assistant_response: "It is sunny today.",
        duration_ms: 150,
        error: null,
        session_id: "session-abc123def456",
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
  it("returns null when no sessions", () => {
    const { container } = render(<SessionViewer sessions={[]} />);
    expect(container.innerHTML).toBe("");
  });

  it("renders session cards with turn count", () => {
    const sessions = [makeSession()];
    render(<SessionViewer sessions={sessions} />);
    expect(screen.getByText("Sessions (1)")).toBeInTheDocument();
    expect(screen.getByText("2 turns")).toBeInTheDocument();
  });

  it("shows session assessment badge", () => {
    const sessions = [makeSession()];
    render(<SessionViewer sessions={sessions} />);
    expect(screen.getByText("onboarding_quality: 4.0")).toBeInTheDocument();
  });

  it("expands to show conversation timeline", () => {
    const sessions = [makeSession()];
    render(<SessionViewer sessions={sessions} />);
    // Click to expand
    fireEvent.click(screen.getByText("2 turns"));
    expect(screen.getByText("Hello, I need help")).toBeInTheDocument();
    expect(screen.getByText(/Welcome! How can I assist/)).toBeInTheDocument();
    expect(screen.getByText("Tell me about the weather")).toBeInTheDocument();
    expect(screen.getByText("Good conversation flow")).toBeInTheDocument();
  });
});
