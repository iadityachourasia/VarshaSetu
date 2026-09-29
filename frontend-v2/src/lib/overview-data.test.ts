import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { overview2019, overview2019Snapshot, overview2025, resolve2019Overview } from "./overview-data";
import operational2025 from "./benchmarks/operational-2025.json";
import reforecast2019 from "./benchmarks/reforecast-2019-overview.json";

type Status = NonNullable<Parameters<typeof overview2019>[0]>;
type Comparison = NonNullable<Parameters<typeof overview2019>[1]>;
type Cases2019 = NonNullable<Parameters<typeof overview2019>[2]>;
type Cases2025 = NonNullable<Parameters<typeof overview2025>[0]>;

const provenance = { artifact_manifest_sha256: "frozen-manifest" };
const status = { case_count: 2, provenance } as Status;
const comparison = {
  test_year: 2019,
  provenance,
  results: {
    M0_RAW_GEFS: { same_case_count: 2, overall: { continuous: { rmse_mm: 20 } } },
    M2_GLOBAL_XGBOOST: { same_case_count: 2, overall: { continuous: { rmse_mm: 18 } } },
  },
} as unknown as Comparison;
const cases2019 = {
  provenance,
  cases: [
    { case_id: "case-a", initialization_utc: "2019-06-01T00:00:00Z", raw_rmse_mm: 21, corrected_rmse_mm: 19 },
    { case_id: "case-b", initialization_utc: "2019-06-02T00:00:00Z", raw_rmse_mm: 19, corrected_rmse_mm: 17 },
  ],
} as Cases2019;

describe("overview scientific sourcing", () => {
  it("uses the 2019 API comparison and refuses mismatched lineage", () => {
    expect(overview2019(status, comparison, cases2019)).toMatchObject({
      raw: 20, corrected: 18, reductionPercent: "10.00", caseCount: 2,
    });
    expect(overview2019(status, comparison, { ...cases2019, provenance: { ...cases2019.provenance, artifact_manifest_sha256: "other" } })?.series).toBeNull();
    expect(overview2019({ ...status, case_count: 3 }, comparison, cases2019)).toBeNull();
  });

  it("keeps the independent pinned 2025 result when 2019 is unavailable", () => {
    expect(overview2019(null, null, null)).toBeNull();
    expect(overview2025(null)).toMatchObject({
      year: 2025, caseCount: 232, reductionPercent: "3.66", series: null,
    });
    expect(overview2025(null)?.raw).toBeCloseTo(16.165724938462002);
    expect(overview2025(null)?.corrected).toBeCloseTo(15.573561739774954);
  });

  it("reconstructs the 2019 fallback from hash-pinned frozen results and real cases", () => {
    const root = resolve(process.cwd(), "..");
    const hash = (path: string) => createHash("sha256").update(readFileSync(resolve(root, path))).digest("hex");
    expect(hash("data/manifests/phase2c/artifact_manifest.json")).toBe(reforecast2019.artifact_manifest_sha256);
    expect(hash("data/manifests/phase2b/2019_final_results.json")).toBe(reforecast2019.phase2b_results_sha256);
    expect(hash("data/manifests/phase2c/2019_final_results.json")).toBe(reforecast2019.phase2c_results_sha256);
    const phase2b = JSON.parse(readFileSync(resolve(root, "data/manifests/phase2b/2019_final_results.json"), "utf8"));
    const phase2c = JSON.parse(readFileSync(resolve(root, "data/manifests/phase2c/2019_final_results.json"), "utf8"));
    expect(reforecast2019.cases).toEqual(phase2c.case_metadata.map((item: Record<string, unknown>) => ({
      case_id: item.case_id, initialization_utc: item.initialization_utc,
      raw_rmse_mm: item.raw_rmse_mm, corrected_rmse_mm: item.corrected_rmse_mm,
    })));
    expect(overview2019Snapshot()).toMatchObject({
      caseCount: 255,
      raw: phase2b.test_results.M0_RAW_GEFS.overall.continuous.rmse_mm,
      corrected: phase2b.test_results.M2_GLOBAL_XGBOOST.overall.continuous.rmse_mm,
      reductionPercent: "9.73",
    });
    expect(overview2019Snapshot()?.series).toHaveLength(255);
  });

  it("uses the snapshot only for transport failures, never HTTP, contract, or lineage failures", () => {
    const network = { status: "rejected", reason: new TypeError("fetch failed") } as const;
    const serverFailure = { status: "rejected", reason: new Error("Scientific artifacts are unavailable") } as const;
    const liveStatus = { status: "fulfilled", value: status } as const;
    const liveComparison = { status: "fulfilled", value: comparison } as const;
    const liveCases = { status: "fulfilled", value: cases2019 } as const;
    expect(resolve2019Overview(liveStatus, liveComparison, liveCases).source).toBe("verified_api");
    expect(resolve2019Overview(network, network, network)).toMatchObject({ source: "verified_snapshot", benchmark: { caseCount: 255 } });
    expect(resolve2019Overview(serverFailure, network, network)).toMatchObject({ source: "unavailable", benchmark: null });
    expect(resolve2019Overview(network, network, serverFailure)).toMatchObject({ source: "unavailable", benchmark: null });
    expect(resolve2019Overview(liveStatus, network, network)).toMatchObject({ source: "unavailable", benchmark: null });
    const pinnedStatus = { status: "fulfilled", value: { ...status, provenance: { ...status.provenance, artifact_manifest_sha256: reforecast2019.artifact_manifest_sha256 } } } as const;
    expect(resolve2019Overview(pinnedStatus, network, network).source).toBe("verified_snapshot");
    expect(resolve2019Overview(liveStatus, { status: "fulfilled", value: { ...comparison, test_year: 2020 } as unknown as Comparison }, liveCases).source).toBe("unavailable");
  });

  it("plots 2025 cases only for a complete eligible final-test population", () => {
    const valid = {
      year: 2025,
      total: 375,
      page: 1,
      page_size: 400,
      cases: Array.from({ length: 375 }, (_, index) => ({
        case_id: "case-" + index,
        year: 2025,
        year_role: "FINAL_TEST_COMPLETED",
        source_complete: true,
        deterministic_source_eligible: index < 232,
        initialization_utc: "2025-06-01T00:00:00Z",
        raw_rmse_mm: index < 232 ? operational2025.raw_rmse_mm : null,
        m1_rmse_mm: index < 232 ? operational2025.selected_rmse_mm : null,
      })),
    } as unknown as Cases2025;
    expect(overview2025(valid)?.series).toHaveLength(232);
    expect(overview2025({ ...valid, cases: valid.cases.slice(1) })?.series).toBeNull();
    expect(overview2025({ ...valid, cases: [{ ...valid.cases[0], case_id: valid.cases[1].case_id }, ...valid.cases.slice(1)] })?.series).toBeNull();
    expect(overview2025({ ...valid, cases: [{ ...valid.cases[0], raw_rmse_mm: 99 }, ...valid.cases.slice(1)] })?.series).toBeNull();
  });

  it("pins the 2025 displayed values to the frozen final-test artifact hash", () => {
    const bytes = readFileSync(resolve(process.cwd(), "../experiments/recent_historical/phase4j_operational_final_test_v1/FINAL_TEST_RESULT.json"));
    expect(createHash("sha256").update(bytes).digest("hex")).toBe(operational2025.source_sha256);
    expect(operational2025.case_count).toBe(232);
    expect(operational2025.raw_rmse_mm).toBeCloseTo(16.165724938462002);
    expect(operational2025.selected_rmse_mm).toBeCloseTo(15.573561739774954);
  });
});
