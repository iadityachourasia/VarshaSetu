import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import operational2025 from "./operational-2025.json";

const project = process.cwd();
const source = (path: string) => readFileSync(resolve(project, path), "utf8");

describe("Phase 4L scientific communication", () => {
  it("pins every displayed 2025 number to the frozen final-result artifact", () => {
    const bytes = readFileSync(resolve(project, "../experiments/recent_historical/phase4j_operational_final_test_v1/FINAL_TEST_RESULT.json"));
    const result = JSON.parse(bytes.toString("utf8"));
    expect(createHash("sha256").update(bytes).digest("hex")).toBe(operational2025.source_sha256);
    expect(result.status).toBe(operational2025.status);
    expect(result.case_count).toBe(operational2025.case_count);
    expect(result.cell_count).toBe(operational2025.paired_cell_count);
    expect(result.primary.raw_rmse_mm).toBe(operational2025.raw_rmse_mm);
    expect(result.primary.selected_m1_rmse_mm).toBe(operational2025.selected_rmse_mm);
    expect(result.deterministic.M2.continuous.rmse_mm).toBe(operational2025.secondary_m2_rmse_mm);
    expect(result.probability.heavy.metrics.bss).toBe(operational2025.heavy_bss);
    expect(result.probability.very_heavy.metrics.bss).toBe(operational2025.very_heavy_bss);
    expect(result.probability.heavy.metrics.categorical.metrics.FAR).toBe(operational2025.heavy_far);
    expect(result.probability.very_heavy.metrics.categorical.metrics.FAR).toBe(operational2025.very_heavy_far);
    for (const threshold of ["heavy", "very_heavy"] as const) {
      for (const scale of ["1", "3", "5", "9"] as const) {
        expect(result.fss[threshold][scale].matched_raw.fss).toBeGreaterThan(result.fss[threshold][scale].matched_selected.fss);
      }
    }
    expect(operational2025.extreme_spatial_classification).toBe("RAW_BETTER");
    expect((100 * (operational2025.raw_rmse_mm - operational2025.selected_rmse_mm) / operational2025.raw_rmse_mm).toFixed(2)).toBe("3.66");
  });

  it("scopes the 2019 API and the separate 2025 summary", () => {
    const overview = source("src/app/page.tsx");
    const verification = source("src/app/verification/page.tsx");
    const methodology = source("src/app/methodology/page.tsx");
    expect(overview).toContain("2019 GEFSv12 REFORECAST");
    expect(overview).toContain("getScience(\"/model-comparison\"");
    expect(overview).toContain("2025 · HISTORICAL OPERATIONAL GEFS");
    expect(overview).toContain("The 2019 and 2025 results are not pooled");
    expect(overview).toContain("Raw GEFS retained better Heavy and Very Heavy spatial FSS");
    expect(verification).toContain("2019 retrospective benchmark");
    expect(verification).toContain("2025 operational-era historical benchmark");
    expect(verification).toContain("different GEFS lineages and populations are not pooled");
    expect(verification).toContain("Raw GEFS retained stronger heavy and very-heavy spatial FSS");
    expect(methodology).toContain("forecast-only pseudo-regime");
    expect(methodology).toContain("FINAL TEST COMPLETED");
  });

  it("keeps interactive maps historical and avoids stale holdout/live claims", () => {
    for (const path of [
      "src/components/forecast/forecast-workspace.tsx",
      "src/components/extremes/extremes-workspace.tsx",
      "src/components/districts/district-workspace.tsx",
    ]) {
      const text = source(path);
      expect(text).toMatch(/2019 historical|2019 Historical/);
      expect(text).toMatch(/not (a |an )?live|not live warnings|not an advisory/i);
    }
    for (const path of ["src/app/page.tsx", "src/app/verification/page.tsx", "src/app/methodology/page.tsx"]) {
      expect(source(path)).not.toMatch(/untouched|still sealed|operationally ready/i);
    }
  });
});
