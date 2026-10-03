import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ForestPlot, tickDigits } from "./forest-plot";

describe("forest plot", () => {
  const rows = [
    { label: "M3 – Raw", point: -0.11, low: -0.13, high: -0.09 },
    { label: "M3 – M4", point: 0.001, low: -0.002, high: 0.004 },
    { label: "M2 – Raw", point: null, low: null, high: null },
  ];
  const html = renderToStaticMarkup(createElement(ForestPlot, { title: "Δ CSI", rows }));
  it("states in its accessible name how many intervals exclude zero", () => {
    expect(html).toContain("1 of 2 intervals exclude zero");
  });
  it("marks only the interval that excludes zero, and says so for a row without one", () => {
    expect(html.match(/forest-excludes/g)).toHaveLength(1);
    expect(html).toContain("not reported");
    expect(html.match(/forest-point/g)).toHaveLength(2);
  });
  it("prints each point estimate with its sign", () => {
    expect(html).toContain("-0.110");
    expect(html).toContain("+0.001");
  });
  it("chooses axis precision from the span", () => {
    expect(tickDigits(2)).toBe(1);
    expect(tickDigits(0.3)).toBe(2);
    expect(tickDigits(0.02)).toBe(3);
  });
});
