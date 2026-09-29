import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { BenchmarkChart, pairedCaseSeries } from "./benchmark-chart";

describe("overview benchmark case series", () => {
  const cases = [
    { case_id: "july", initialization_utc: "2019-07-02T00:00:00Z", raw_rmse_mm: 18, corrected_rmse_mm: 16 },
    { case_id: "june", initialization_utc: "2019-06-01T00:00:00Z", raw_rmse_mm: 21, corrected_rmse_mm: 19 },
  ];

  it("plots only a complete paired population in date order", () => {
    const points = pairedCaseSeries(cases, 2, 2019);
    expect(points?.map((point) => point.raw)).toEqual([21, 18]);
    expect(pairedCaseSeries(cases, 3, 2019)).toBeNull();
    expect(pairedCaseSeries([...cases, { ...cases[0], case_id: "missing", corrected_rmse_mm: null }], 3, 2019)).toBeNull();
    expect(pairedCaseSeries([{ ...cases[0], raw_rmse_mm: -1 }, cases[1]], 2, 2019)).toBeNull();
    expect(pairedCaseSeries([{ ...cases[0], case_id: cases[1].case_id }, cases[1]], 2, 2019)).toBeNull();
    expect(pairedCaseSeries([{ ...cases[0], eligible: false }, cases[1]], 2, 2019)).toBeNull();
    expect(pairedCaseSeries(cases, 2, 2025)).toBeNull();
  });

  it("labels the real per-case series separately from aggregate RMSE", () => {
    const markup = renderToStaticMarkup(createElement(BenchmarkChart, {
      points: pairedCaseSeries(cases, 2, 2019), year: 2019, raw: 19.77, corrected: 17.85, correctedLabel: "Global XGBoost",
    }));
    expect(markup).toContain("per-case RMSE (mm) · 2 paired cases");
    expect(markup).toContain("forecast initialization date");
    expect(markup).toContain("overview-chart-raw");
    expect(markup).toContain("overview-chart-corrected");
  });

  it("shows sourced aggregate values when the case series is unavailable", () => {
    const markup = renderToStaticMarkup(createElement(BenchmarkChart, {
      points: null, year: 2025, raw: 16.165724938462002, corrected: 15.573561739774954, correctedLabel: "M1 Ridge",
    }));
    expect(markup).toContain("case series unavailable");
    expect(markup).toContain("16.17 mm");
    expect(markup).toContain("15.57 mm");
    expect(markup).not.toContain("overview-chart-raw");
  });
});
