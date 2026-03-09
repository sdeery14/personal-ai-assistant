import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { DatasetViewer } from "@/components/eval-explorer/DatasetViewer";
import type { DatasetDetail } from "@/types/eval-explorer";

function makeDataset(overrides: Partial<DatasetDetail> = {}): DatasetDetail {
  return {
    dataset_id: "d-123",
    name: "quality-v1.0.0",
    dataset_type: "quality",
    version: "1.0.0",
    source_file: "golden_dataset.json",
    case_count: 10,
    experiment_ids: ["1"],
    created_time: "2026-03-01T12:00:00Z",
    cases: [],
    ...overrides,
  };
}

function makeDatasetWithCases(): DatasetDetail {
  return {
    dataset_id: "d-123",
    name: "quality-v1.0.0",
    dataset_type: "quality",
    version: "1.0.0",
    source_file: "golden_dataset.json",
    case_count: 2,
    experiment_ids: ["1"],
    created_time: "2026-03-01T12:00:00Z",
    cases: [
      {
        record_id: "dr-1",
        inputs: { question: "What is AI?" },
        expectations: { rubric: "Should explain artificial intelligence" },
        extra: {},
      },
      {
        record_id: "dr-2",
        inputs: { question: "How does memory work?" },
        expectations: {},
        extra: { custom_field: "value" },
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
      makeDataset({ dataset_id: "d-456", name: "security-v1.0.0", dataset_type: "security", case_count: 20 }),
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
    expect(screen.getByText("quality-v1.0.0")).toBeInTheDocument();
    expect(screen.getByText("security-v1.0.0")).toBeInTheDocument();
  });

  it("calls onSelectDataset with dataset_id when row clicked", () => {
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
    fireEvent.click(screen.getByText("quality-v1.0.0"));
    expect(onSelect).toHaveBeenCalledWith("d-123");
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

  it("expands case to show expectations", () => {
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
