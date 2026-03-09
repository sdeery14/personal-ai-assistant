import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { EvalSubNav } from "@/components/eval-nav/EvalSubNav";

let mockPathname = "/admin/evals";
vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname,
}));

describe("EvalSubNav", () => {
  it("renders all sub-navigation links", () => {
    render(<EvalSubNav />);
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Agents")).toBeInTheDocument();
    expect(screen.getByText("Experiments")).toBeInTheDocument();
    expect(screen.getByText("Datasets")).toBeInTheDocument();
    expect(screen.getByText("Trends")).toBeInTheDocument();
  });

  it("highlights Dashboard when on exact /admin/evals path", () => {
    mockPathname = "/admin/evals";
    render(<EvalSubNav />);
    const dashboardLink = screen.getByText("Dashboard");
    expect(dashboardLink.className).toContain("bg-blue-100");
  });

  it("highlights Experiments when path starts with /admin/evals/experiments", () => {
    mockPathname = "/admin/evals/experiments/123";
    render(<EvalSubNav />);
    const expLink = screen.getByText("Experiments");
    expect(expLink.className).toContain("bg-blue-100");
    const dashLink = screen.getByText("Dashboard");
    expect(dashLink.className).not.toContain("bg-blue-100");
  });

  it("links point to correct hrefs", () => {
    mockPathname = "/admin/evals";
    render(<EvalSubNav />);
    expect(screen.getByText("Agents").closest("a")).toHaveAttribute(
      "href",
      "/admin/evals/agents"
    );
    expect(screen.getByText("Trends").closest("a")).toHaveAttribute(
      "href",
      "/admin/evals/trends"
    );
  });
});
