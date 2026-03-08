import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { DatasetViewer } from "@/components/eval-explorer/DatasetViewer";
import type { DatasetDetail } from "@/types/eval-explorer";

function makeDataset(overrides: Partial<DatasetDetail> = {}): DatasetDetail {
  return {
    name: "golden_dataset",
    file_path: "eval/golden_dataset.json",
    version: "1.0",
    description: "Quality evaluation golden dataset",
    case_count: 10,
    cases: [],
    ...overrides,
  };
}

function makeDatasetWithCases(): DatasetDetail {
  return {
    name: "golden_dataset",
    file_path: "eval/golden_dataset.json",
    version: "1.0",
    description: "Quality evaluation golden dataset",
    case_count: 2,
    cases: [
      {
        id: "case-1",
        user_prompt: "What is AI?",
        rubric: "Should explain artificial intelligence",
        tags: ["basic", "intro"],
        extra: {},
      },
      {
        id: "case-2",
        user_prompt: "How does memory work?",
        rubric: null,
        tags: [],
        extra: { expected_behavior: "allow" },
      },
    ],
  };
}

describe("DatasetViewer", () => {
  it("shows loading skeleton", () => {
    render(
      <DatasetViewer
        datasets={[]}
        isLoading={true}
        error={null}
        onSelectDataset={vi.fn()}
        selectedDataset={null}
        selectedDatasetLoading={false}
      />
    );
    expect(document.querySelector(".animate-pulse")).toBeInTheDocument();
  });

  it("shows empty state", () => {
    render(
      <DatasetViewer
        datasets={[]}
        isLoading={false}
        error={null}
        onSelectDataset={vi.fn()}
        selectedDataset={null}
        selectedDatasetLoading={false}
      />
    );
    expect(screen.getByText(/no datasets found/i)).toBeInTheDocument();
  });

  it("renders dataset list", () => {
    const datasets = [
      makeDataset(),
      makeDataset({ name: "security_golden_dataset", description: "Security tests", case_count: 20 }),
    ];
    render(
      <DatasetViewer
        datasets={datasets}
        isLoading={false}
        error={null}
        onSelectDataset={vi.fn()}
        selectedDataset={null}
        selectedDatasetLoading={false}
      />
    );
    expect(screen.getByText("golden_dataset")).toBeInTheDocument();
    expect(screen.getByText("security_golden_dataset")).toBeInTheDocument();
  });

  it("calls onSelectDataset when row clicked", () => {
    const onSelect = vi.fn();
    render(
      <DatasetViewer
        datasets={[makeDataset()]}
        isLoading={false}
        error={null}
        onSelectDataset={onSelect}
        selectedDataset={null}
        selectedDatasetLoading={false}
      />
    );
    fireEvent.click(screen.getByText("golden_dataset"));
    expect(onSelect).toHaveBeenCalledWith("golden_dataset");
  });

  it("shows dataset detail with cases when selected", () => {
    const selected = makeDatasetWithCases();
    render(
      <DatasetViewer
        datasets={[makeDataset()]}
        isLoading={false}
        error={null}
        onSelectDataset={vi.fn()}
        selectedDataset={selected}
        selectedDatasetLoading={false}
      />
    );
    expect(screen.getByText(/2\s+cases/)).toBeInTheDocument();
    expect(screen.getByText(/what is ai/i)).toBeInTheDocument();
  });

  it("expands case to show rubric and extra fields", () => {
    const selected = makeDatasetWithCases();
    render(
      <DatasetViewer
        datasets={[makeDataset()]}
        isLoading={false}
        error={null}
        onSelectDataset={vi.fn()}
        selectedDataset={selected}
        selectedDatasetLoading={false}
      />
    );
    // Click first case to expand
    fireEvent.click(screen.getByText(/what is ai/i));
    expect(screen.getByText("Should explain artificial intelligence")).toBeInTheDocument();
  });
});
