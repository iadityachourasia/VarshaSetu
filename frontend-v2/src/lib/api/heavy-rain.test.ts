import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { heavyRainCaseSchema, heavyRainDistrictsSchema, heavyRainOverviewSchema } from "./heavy-rain";

const REPO = path.resolve(__dirname, "../../../..");
const PHASE15 = path.join(REPO, "backend/app/evidence_data/phase15");
const PHASE17 = path.join(REPO, "backend/app/evidence_data/phase17");
const manifest = JSON.parse(readFileSync(path.join(PHASE17, "heavy_rain_b1_manifest.json"), "utf8"));
const confirmation = JSON.parse(readFileSync(path.join(PHASE15, "reforecast_r05_confirmation.json"), "utf8"));

describe("heavy-rain layer contracts", () => {
  const overview = {
    year: manifest.year, cases: manifest.cases, evidence_label: "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST", bundle_label: "x", shift_mm: manifest.shift_mm,
    bias_guardrail_mm: 1.5, slice_bias_within_limit: false, thresholds_mm: { heavy: 64.5, very_heavy: 115.6 }, decision_thresholds: manifest.thresholds, protocol_sha256: manifest.protocol_sha256, manifest_sha256: "a".repeat(64), arrays_sha256: manifest.arrays_sha256,
    summary: manifest.summary_2019,
    confirmation: { label: confirmation.label, years: confirmation.years, cases: confirmation.cases, tier: confirmation.bundle_decision.decision.tier, bias_within_limit: confirmation.bundle_decision.decision.BIAS_OK,
      delta_source: confirmation.delta_source, pooled: { M0: confirmation.pooled.M0, B1_shifted: confirmation.pooled.B1_shifted }, exceedance: { "B1:heavy": confirmation.exceedance["B1:heavy"].test, "B1:very_heavy": confirmation.exceedance["B1:very_heavy"].test } },
    caveats: ["one"],
  };
  it("accepts the frozen manifest and confirmation as the overview payload", () => {
    const parsed = heavyRainOverviewSchema.parse(overview);
    expect(parsed.summary.classifier.heavy.tau).toBe(manifest.thresholds.heavy);
    expect(parsed.confirmation.tier).toBe(confirmation.bundle_decision.decision.tier);
  });
  it("refuses an overview without the evidence label or with a malformed hash", () => {
    expect(() => heavyRainOverviewSchema.parse({ ...overview, evidence_label: undefined })).toThrow();
    expect(() => heavyRainOverviewSchema.parse({ ...overview, protocol_sha256: "short" })).toThrow();
  });
  it("accepts undefined cells as null and refuses a non-numeric cell", () => {
    const row = Array(49).fill(null);
    const grid = Array(49).fill(row);
    const base = { case_id: "x", year: 2019, b1_rainfall_mm: grid, heavy_score: grid, very_heavy_score: grid, heavy_decision: grid, very_heavy_decision: grid, decision_thresholds: manifest.thresholds, b1_rmse_mm: 1, evidence_label: "l", caveats: [] };
    expect(heavyRainCaseSchema.parse(base).heavy_score[0][0]).toBeNull();
    expect(() => heavyRainCaseSchema.parse({ ...base, heavy_score: [["a"]] })).toThrow();
  });
  it("requires every district field the table and map read", () => {
    const row = { district_id: "d", district_name: "n", valid_grid_cells: 3, raw_mean_mm: 1, corrected_mean_mm: 2, corrected_max_mm: 3, heavy_probability: 0.5, very_heavy_probability: 0.2, heavy_flag_area_fraction: 1, very_heavy_flag_area_fraction: 0, heavy_area_fraction: 0, very_heavy_area_fraction: 0 };
    const body = { case_id: "c", year: 2019, districts: [row], aggregation: "a", decision_thresholds: manifest.thresholds, evidence_label: "l", caveats: [] };
    expect(heavyRainDistrictsSchema.parse(body).districts).toHaveLength(1);
    const broken: Record<string, unknown> = { ...row };
    delete broken.heavy_flag_area_fraction;
    expect(() => heavyRainDistrictsSchema.parse({ ...body, districts: [broken] })).toThrow();
  });
});
