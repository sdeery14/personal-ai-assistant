import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Breadcrumb } from "@/components/eval-nav/Breadcrumb";

describe("Breadcrumb", () => {
  it("renders nothing when items is empty", () => {
    const { container } = render(<Breadcrumb items={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders a single item as non-linked text", () => {
    render(<Breadcrumb items={[{ label: "Experiments", href: "/admin/evals/experiments" }]} />);
    const item = screen.getByText("Experiments");
    expect(item.tagName).not.toBe("A");
    expect(item.className).toContain("font-medium");
  });

  it("renders multiple items with links except the last", () => {
    render(
      <Breadcrumb
        items={[
          { label: "Experiments", href: "/admin/evals/experiments" },
          { label: "quality", href: "/admin/evals/experiments/1" },
          { label: "Run abc123", href: "/admin/evals/runs/abc123" },
        ]}
      />
    );
    const expLink = screen.getByText("Experiments");
    expect(expLink.closest("a")).toHaveAttribute("href", "/admin/evals/experiments");

    const qualityLink = screen.getByText("quality");
    expect(qualityLink.closest("a")).toHaveAttribute("href", "/admin/evals/experiments/1");

    const runText = screen.getByText("Run abc123");
    expect(runText.tagName).not.toBe("A");
  });

  it("renders separators between items", () => {
    render(
      <Breadcrumb
        items={[
          { label: "Experiments", href: "/admin/evals/experiments" },
          { label: "quality", href: "/admin/evals/experiments/1" },
        ]}
      />
    );
    expect(screen.getByText("/")).toBeInTheDocument();
  });
});
