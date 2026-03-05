import { renderHook, act } from "@testing-library/react";
import { useOrientation } from "../use-orientation";

describe("useOrientation", () => {
  it("returns orientation state", () => {
    const { result } = renderHook(() => useOrientation());
    expect(result.current).toHaveProperty("isLandscape");
    expect(result.current).toHaveProperty("isPortrait");
    expect(result.current).toHaveProperty("angle");
    expect(typeof result.current.isLandscape).toBe("boolean");
    expect(typeof result.current.isPortrait).toBe("boolean");
    expect(result.current.isLandscape).toBe(!result.current.isPortrait);
  });
});
