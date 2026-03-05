import { render, screen } from "@testing-library/react";
import { LandscapeHint } from "../landscape-hint";

describe("LandscapeHint", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders children", () => {
    render(
      <LandscapeHint>
        <div data-testid="child">Chart content</div>
      </LandscapeHint>
    );
    expect(screen.getByTestId("child")).toHaveTextContent("Chart content");
  });

  it("uses custom storageKey when provided", () => {
    render(
      <LandscapeHint storageKey="custom-key">
        <span>Content</span>
      </LandscapeHint>
    );
    expect(screen.getByText("Content")).toBeInTheDocument();
  });
});
