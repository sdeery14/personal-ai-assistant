import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AgentDetail } from "@/components/eval-explorer/AgentDetail";
import type { AgentVersionDetail } from "@/types/eval-explorer";

const mockAgent: AgentVersionDetail = {
  model_id: "model-1",
  name: "assistant",
  git_branch: "main",
  git_commit: "abc1234def5678",
  git_commit_short: "abc1234",
  creation_timestamp: "2026-03-01T12:00:00Z",
  aggregate_quality: 4.2,
  experiment_count: 2,
  total_traces: 10,
  git_repo_url: "https://github.com/user/repo",
  experiment_results: [
    {
      experiment_name: "eval-quality",
      experiment_id: "exp-1",
      eval_type: "quality",
      run_count: 3,
      pass_rate: 0.85,
      average_quality: 4.2,
      latest_run_id: "run-1",
    },
  ],
  config: {
    model: "gpt-4.1",
    name: "Assistant",
    framework: "openai-agents-sdk",
    max_tokens: 2000,
    timeout_seconds: 30,
    system_prompt: "You are a helpful assistant.",
    guardrails: [
      { name: "validate_input", type: "input" },
      { name: "validate_output", type: "output" },
    ],
    specialists: [
      {
        name: "ask_memory_agent",
        type: "agent",
        model: "gpt-4.1",
        tools: ["query_memory", "save_memory", "delete_memory"],
        description: "Delegate to the memory specialist.",
      },
      {
        name: "ask_weather_agent",
        type: "agent",
        model: "gpt-4.1",
        tools: ["get_weather"],
        description: "Delegate to the weather specialist.",
      },
    ],
    graph: {
      nodes: [
        { id: "orchestrator", label: "Assistant", type: "orchestrator" },
        { id: "specialist-0", label: "ask_memory_agent", type: "agent", tools: ["query_memory", "save_memory"] },
        { id: "specialist-1", label: "ask_weather_agent", type: "agent", tools: ["get_weather"] },
      ],
      edges: [
        { source: "orchestrator", target: "specialist-0", label: "delegates" },
        { source: "orchestrator", target: "specialist-1", label: "delegates" },
      ],
    },
  },
};

describe("AgentDetail", () => {
  it("renders overview with model config", () => {
    render(
      <AgentDetail agent={mockAgent} isLoading={false} error={null} />
    );
    expect(screen.getByText("abc1234")).toBeDefined();
    expect(screen.getByText("main")).toBeDefined();
    expect(screen.getAllByText("gpt-4.1").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("openai-agents-sdk")).toBeDefined();
    expect(screen.getByText("2000")).toBeDefined();
    expect(screen.getByText("30s")).toBeDefined();
  });

  it("renders agent architecture graph", () => {
    render(
      <AgentDetail agent={mockAgent} isLoading={false} error={null} />
    );
    expect(screen.getByText("Agent Architecture")).toBeDefined();
    // Names appear in both graph and specialists list
    expect(screen.getAllByText("ask_memory_agent").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("ask_weather_agent").length).toBeGreaterThanOrEqual(1);
  });

  it("renders guardrails", () => {
    render(
      <AgentDetail agent={mockAgent} isLoading={false} error={null} />
    );
    expect(screen.getByText("Guardrails")).toBeDefined();
    expect(screen.getByText("validate_input")).toBeDefined();
    expect(screen.getByText("validate_output")).toBeDefined();
  });

  it("renders system prompt with expand toggle", () => {
    const longPrompt = "A".repeat(300);
    const agentWithLongPrompt = {
      ...mockAgent,
      config: { ...mockAgent.config, system_prompt: longPrompt },
    };
    render(
      <AgentDetail agent={agentWithLongPrompt} isLoading={false} error={null} />
    );
    expect(screen.getByText("System Prompt")).toBeDefined();
    expect(screen.getByText("Show full prompt")).toBeDefined();
  });

  it("renders specialist details with tools", () => {
    render(
      <AgentDetail agent={mockAgent} isLoading={false} error={null} />
    );
    expect(screen.getByText("Specialists (2)")).toBeDefined();
    // Tool names appear in both graph and specialists sections
    expect(screen.getAllByText("query_memory").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("get_weather").length).toBeGreaterThanOrEqual(1);
  });

  it("renders experiment results table", () => {
    render(
      <AgentDetail agent={mockAgent} isLoading={false} error={null} />
    );
    expect(screen.getByText("eval-quality")).toBeDefined();
    expect(screen.getByText("85.0%")).toBeDefined();
  });

  it("shows loading skeleton", () => {
    const { container } = render(
      <AgentDetail agent={null} isLoading={true} error={null} />
    );
    expect(container.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
  });

  it("shows error message", () => {
    render(
      <AgentDetail agent={null} isLoading={false} error="Something went wrong" />
    );
    expect(screen.getByText("Error: Something went wrong")).toBeDefined();
  });

  it("shows not found for null agent", () => {
    render(
      <AgentDetail agent={null} isLoading={false} error={null} />
    );
    expect(screen.getByText("Agent version not found.")).toBeDefined();
  });

  it("calls onExperimentClick when clicking experiment row", () => {
    const onExperimentClick = vi.fn();
    render(
      <AgentDetail
        agent={mockAgent}
        isLoading={false}
        error={null}
        onExperimentClick={onExperimentClick}
      />
    );
    fireEvent.click(screen.getByText("eval-quality"));
    expect(onExperimentClick).toHaveBeenCalledWith("exp-1", "quality", "eval-quality");
  });
});
