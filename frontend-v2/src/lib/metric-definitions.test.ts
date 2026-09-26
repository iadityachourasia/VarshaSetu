import { describe, expect, it } from "vitest";
import { METRIC_DEFINITION } from "./metric-definitions";

describe("METRIC_DEFINITION", () => {
  it("covers every metric abbreviation this app displays", () => {
    for (const term of ["RMSE", "MAE", "Bias", "POD", "FAR", "CSI", "ETS", "FSS", "Brier", "BSS", "PR-AUC", "ROC-AUC"]) {
      expect(METRIC_DEFINITION[term], `missing definition for ${term}`).toBeTypeOf("string");
      expect(METRIC_DEFINITION[term].length).toBeGreaterThan(10);
    }
  });

  it("never claims this project's own result is good inside a definition", () => {
    for (const [term, definition] of Object.entries(METRIC_DEFINITION)) {
      expect(definition.toLowerCase(), term).not.toMatch(/our |varshasetu|this project/);
    }
  });
});
