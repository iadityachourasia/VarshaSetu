import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { zoneForcingSchema, zoneGeographySchema, zoneOverviewSchema, zoneVerificationSchema } from "./zones";

const PHASE7 = path.resolve(__dirname, "../../../../backend/app/evidence_data/phase7");
const read = (name: string) => JSON.parse(readFileSync(path.join(PHASE7, name), "utf8"));
const wrap = (stage: string, track: string, year: number, payload: Record<string, unknown>) => ({
  track, year, evidence_role: payload.evidence_role, evidence_label: String(payload.evidence_role), evidence_sha256: "a".repeat(64), stage, payload, caveats: ["x"],
});

describe("zone evidence client schemas", () => {
  it.each([["A", 2018], ["A", 2019], ["B", 2024], ["B", 2025]] as const)("accepts the frozen Stage 1 and Stage 2 evidence for %s %i", (track, year) => {
    const stage1 = zoneVerificationSchema.parse(wrap("stage1", track, year, read(`zone_verification_${track}_${year}.json`)));
    const stage2 = zoneForcingSchema.parse(wrap("stage2", track, year, read(`zone_stage2_${track}_${year}.json`)));
    expect(stage1.payload.zones.ALL.cells).toBe(1301);
    expect(Object.keys(stage2.payload.forcing_cut_points.cut_points)).toHaveLength(4);
  });

  it("keeps an unsupported stratum as a status, never a number", () => {
    const payload = read("zone_stage2_B_2025.json");
    const thin = Object.entries(payload.support as Record<string, { heavy_supported: boolean }>).find(([, gate]) => !gate.heavy_supported);
    expect(thin).toBeDefined();
    const parsed = zoneForcingSchema.parse(wrap("stage2", "B", 2025, payload));
    const heavy = parsed.payload.pooled[thin![0]].M0.categorical?.heavy;
    expect(heavy?.status).toBe("insufficient_support");
    expect(heavy?.CSI).toBeUndefined();
  });

  it("rejects a payload whose stage does not match the endpoint", () => {
    expect(() => zoneVerificationSchema.parse(wrap("stage2", "B", 2025, read("zone_verification_B_2025.json")))).toThrow();
  });

  it("accepts the geography and overview responses with the Stage 3 gate closed", () => {
    const geography = read("static_geography_v1.json");
    const g = zoneGeographySchema.parse({
      source: geography.source, grid: geography.grid, qa: geography.qa, zone_cell_counts: geography.zone_cell_counts, zone_notes: { COASTAL: "x" },
      sensitivity_only_counts: geography.sensitivity_only_counts, fields: geography.fields, geography_sha256: "b".repeat(64), caveats: [],
    });
    expect(Object.values(g.zone_cell_counts).reduce((a, b) => a + b, 0)).toBe(1301);
    const overview = zoneOverviewSchema.parse({
      protocol_sha256: "c".repeat(64), spec_sha256: "d".repeat(64), geography_sha256: "e".repeat(64), stage1_manifest_sha256: "f".repeat(64), stage2_manifest_sha256: "0".repeat(64),
      status: "APPROVED_FOR_STAGES_0_TO_2", stage_3_authorised: false, stage_3_recommended_by_pre_registered_rule: true, available: [],
      decision_stage1: read("zone_decision_summary.json"), decision_stage2: read("zone_stage2_summary.json"), caveats: [],
    });
    expect(overview.stage_3_authorised).toBe(false);
    expect(overview.decision_stage1.tracks.B.tests).toBeGreaterThan(0);
  });
});
