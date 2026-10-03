import { describe, expect, it } from "vitest";
import { countUpText, decimalsOf, easeOut } from "./motion";

describe("count-up never misstates a value", () => {
  it("lands on the exact formatted target at the end", () => {
    expect(countUpText(9.73, 2, 1)).toBe("9.73");
    expect(countUpText(17.8487, 4, 1)).toBe("17.8487");
    expect(countUpText(3.66, 2, 5)).toBe("3.66");
    expect(countUpText(0, 2, 1)).toBe("0.00");
  });
  it("never exceeds the target on the way, for any progress", () => {
    for (const target of [0.5, 9.73, 19.7735, 331755]) {
      let previous = -1;
      for (let step = 0; step <= 100; step++) {
        const shown = Number(countUpText(target, 4, step / 100));
        expect(shown).toBeLessThanOrEqual(target + 1e-9);
        expect(shown).toBeGreaterThanOrEqual(previous);
        previous = shown;
      }
    }
  });
  it("clamps the easing outside zero to one and starts at zero", () => {
    expect(easeOut(-1)).toBe(0);
    expect(easeOut(2)).toBe(1);
    expect(countUpText(10, 1, 0)).toBe("0.0");
  });
  it("reads the number of decimals from the written value", () => {
    expect(decimalsOf("9.73")).toBe(2);
    expect(decimalsOf("12")).toBe(0);
    expect(decimalsOf("0.0948")).toBe(4);
  });
});
