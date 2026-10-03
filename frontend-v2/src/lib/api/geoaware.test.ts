import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { geoawareEvaluationSchema, geoawareFollowupSchema, geoawareOverviewSchema } from "./geoaware";

const PHASE9 = path.resolve(__dirname, "../../../../backend/app/evidence_data/phase9");
const read = (name: string) => JSON.parse(readFileSync(path.join(PHASE9, name), "utf8"));

describe("geography-aware evidence client schemas", () => {
  it.each([2024, 2025])("accepts the frozen evaluation for %i", (year) => {
    const payload = read(`geoaware_evaluation_B_${year}.json`);
    const parsed = geoawareEvaluationSchema.parse({ year, evidence_role: payload.evidence_role, evidence_label: payload.evidence_role, evidence_sha256: "a".repeat(64), payload, caveats: ["x"] });
    expect(parsed.payload.support.COASTAL_AND_OROGRAPHIC.heavy.supported).toBe(true);
    expect(parsed.payload.guardrails_on_evaluation_population.A3).toHaveProperty("G2");
  });

  it("accepts the overview built from the frozen files and keeps the negative verdict", () => {
    const freeze = read("geoaware_selection_freeze.json");
    const protocol = read("geoaware_protocol_v1.json");
    const parsed = geoawareOverviewSchema.parse({
      protocol_sha256: "a".repeat(64), selection_freeze_sha256: "b".repeat(64), manifest_sha256: "c".repeat(64), status: protocol.status, approval: protocol.approval,
      decision: read("geoaware_decision.json"), selection: freeze.selection, training: freeze.training, configurations: freeze.all_configurations,
      arms: protocol.feature_registry_v2.arms, available: [], caveats: ["x"],
    });
    expect(parsed.decision.adds_value).toBe(false);
    expect(parsed.decision.geography_attribution).toBeNull();
    expect(parsed.selection.A0.selected).toBeNull();
  });

  it("rejects an overview that claims attribution to geography", () => {
    const freeze = read("geoaware_selection_freeze.json");
    const protocol = read("geoaware_protocol_v1.json");
    const decision = { ...read("geoaware_decision.json"), geography_attribution: "geography" };
    expect(() => geoawareOverviewSchema.parse({
      protocol_sha256: "a".repeat(64), selection_freeze_sha256: "b".repeat(64), manifest_sha256: "c".repeat(64), status: protocol.status, approval: protocol.approval,
      decision, selection: freeze.selection, training: freeze.training, configurations: freeze.all_configurations, arms: protocol.feature_registry_v2.arms, available: [], caveats: [],
    })).toThrow();
  });
});


describe("geography-aware follow-up client schema", () => {
  const PHASE11 = path.resolve(__dirname, "../../../../backend/app/evidence_data/phase11");
  const read11 = (name: string) => JSON.parse(readFileSync(path.join(PHASE11, name), "utf8"));
  type Json = Record<string, unknown>;
  type RawMetrics = { rmse_mm: number; bias_mm: number; heavy: { csi: number | null }; zone: { heavy_csi: number | null; heavy_frequency_bias: number | null }; very_heavy: { frequency_bias: number | null } };
  type RawSelected = { grid_index: number; config: Record<string, unknown>; pooled_out_of_fold: { rmse_mm: number }; features: number; g3_passes_in_every_year: boolean; by_year: Record<string, RawMetrics> };
  type ServedMetrics = { rmse_mm?: number; bias_mm: number; heavy_csi: number | null; zone_heavy_csi: number | null; zone_heavy_frequency_bias: number | null; very_heavy_frequency_bias: number | null };
  type ServedSelected = { grid_index: number; config: Record<string, unknown>; pooled_rmse_mm: number; features: number; g3_passes_in_every_year: boolean; by_year: Record<string, ServedMetrics> };
  type Body = { v2_selection: Record<string, ServedSelected | null>; test_2022: { decisions: Record<string, Json> } & Json } & Record<string, unknown>;
  const served = (freeze: { selection: Record<string, { selected: RawSelected | null }> }) => {
    const out: Record<string, ServedSelected | null> = {};
    for (const [arm, block] of Object.entries(freeze.selection)) {
      const c = block.selected;
      out[arm] = c && {
        grid_index: c.grid_index, config: c.config, pooled_rmse_mm: c.pooled_out_of_fold.rmse_mm, features: c.features, g3_passes_in_every_year: c.g3_passes_in_every_year,
        by_year: Object.fromEntries(Object.entries(c.by_year).map(([y, m]) => [y, { rmse_mm: m.rmse_mm, bias_mm: m.bias_mm, heavy_csi: m.heavy.csi, zone_heavy_csi: m.zone.heavy_csi, zone_heavy_frequency_bias: m.zone.heavy_frequency_bias, very_heavy_frequency_bias: m.very_heavy.frequency_bias }])),
      };
    }
    return out;
  };
  const compose = (mutate?: (body: Body) => void): Body => {
    const f2 = read11("geoaware_followup_selection_freeze_v2.json");
    const f3 = read11("geoaware_followup_selection_freeze_v3.json");
    const p3 = read11("geoaware_followup_protocol_v3.json");
    const summary = read11("geoaware_followup_development_summary.json");
    const record = read11("geoaware_followup_unseal_record.json");
    const result = read11("geoaware_followup_test_2022.json");
    const zone = "COASTAL_AND_OROGRAPHIC";
    const labels = [...new Set(Object.values<{ candidate: string; comparator: string }>(result.decisions).flatMap((d) => [d.candidate, d.comparator]).concat("M0"))].sort();
    const pooled = Object.fromEntries(labels.map((l) => [l, {
      rmse_mm: result.pooled[l].ALL.rmse_mm, bias_mm: result.pooled[l].ALL.bias_mm, heavy_csi: result.pooled[l].ALL.categorical.heavy.CSI, very_heavy_frequency_bias: result.pooled[l].ALL.categorical.very_heavy.frequency_bias,
      zone_heavy_csi: result.pooled[l][zone].categorical.heavy.CSI, zone_heavy_frequency_bias: result.pooled[l][zone].categorical.heavy.frequency_bias, zone_bias_mm: result.pooled[l][zone].bias_mm,
    }]));
    const body: Body = {
      protocol_v1_sha256: "a".repeat(64), protocol_v2_sha256: "b".repeat(64), protocol_v3_sha256: "c".repeat(64), freeze_v1_sha256: "d".repeat(64), freeze_v2_sha256: "e".repeat(64),
      freeze_v3_sha256: "f".repeat(64), summary_sha256: "1".repeat(64), unseal_record_sha256: "2".repeat(64), test_result_sha256: "3".repeat(64),
      sealed_test: { year: 2022, opened: true, status: "OPENED_ONCE_UNDER_THE_UNSEAL_RECORD", sealed_at_selection_freezes: true },
      unseal_record: { written_at_utc: record.written_at_utc, owner_message: record.owner_message, what_is_not_authorised: record.what_is_not_authorised, disclosed_before_opening: record.disclosed_before_opening, hashes_listed: Object.keys(record.hashes).length },
      approval: p3.approval, contamination_disclosure: p3.contamination_disclosure, changes: p3.changes, post_hoc_disclosure: p3.post_hoc_disclosure, decision_rule: p3.decision_rule,
      development_years: f2.development.years, v1_outcome: { all_arms_without_candidate: true, arms: {} }, v2_selection: served(f2), v3_selection: served(f3),
      eligible_v2_by_arm: { B0: 3, B1: 4, B0Z: 3, B1Z: 2 }, raw_heavy_csi_by_year: f2.development.raw_heavy_csi_by_year,
      matched_configuration_comparison: { configurations: 16, zone_heavy_csi_higher_in_every_held_out_year: summary.b1_versus_b0_counts.zone_heavy_csi_higher_in_every_held_out_year, pooled_rmse_lower: summary.b1_versus_b0_counts.pooled_rmse_lower },
      test_2022: {
        label: result.label, claim: result.claim, claim_wording: result.claim_wording, cases: result.cases, run_at_utc: result.run_at_utc, multiplicity: result.multiplicity,
        support_zone: result.support[zone], candidate_sets: result.candidate_sets, models: Object.fromEntries(Object.entries<Json>(result.models).filter(([l]) => l in pooled)), pooled_summary: pooled,
        decisions: Object.fromEntries(Object.entries<Json>(result.decisions).map(([k, d]) => [k, Object.fromEntries(["candidate", "comparator", "status", "adds_value", "P1_zone_heavy_csi_beats_comparator_975", "P2_overall_rmse_within_tolerance", "P3_gating_guardrails_G1_G2_G4", "guardrails", "g3_reported_only", "zone_heavy_csi_difference", "overall_rmse_difference", "level"].map((f) => [f, d[f]]))])),
        sensitivity: [], by_lead: Object.fromEntries(Object.entries<{ cases: number; models: Record<string, Record<string, { categorical: { heavy: { CSI: number | null } }; rmse_mm: number }>> }>(result.by_lead).map(([lead, b]) => [lead, { cases: b.cases, models: Object.fromEntries(Object.entries(b.models).map(([l, m]) => [l, { rmse_mm: m.ALL.rmse_mm, zone_heavy_csi: m[zone].categorical.heavy.CSI }])) }])),
        limits: result.limits,
      },
      caveats: ["x"],
    };
    mutate?.(body);
    return body;
  };

  it("accepts the frozen evidence, including the unseal record and the 2022 test result", () => {
    const parsed = geoawareFollowupSchema.parse(compose());
    expect(parsed.sealed_test).toMatchObject({ year: 2022, opened: true, sealed_at_selection_freezes: true });
    expect(parsed.unseal_record.owner_message.verbatim).toBe("do all of three perfectly");
    expect(Object.keys(parsed.v3_selection).sort()).toEqual(["B0", "B0Z", "B1", "B1Z"]);
    expect(parsed.test_2022.label).toBe("INDEPENDENT TEST: first use of this year");
    expect(parsed.test_2022.decisions.v3_primary.adds_value).toBe(true);
    expect(parsed.test_2022.decisions.v2_secondary.adds_value).toBe(false);
  });

  it("keeps an unevaluable test as null, never as a pass or a fail", () => {
    const parsed = geoawareFollowupSchema.parse(compose((b) => { Object.assign(b.test_2022.decisions.v3_primary, { adds_value: null, status: "UNEVALUABLE" }); }));
    expect(parsed.test_2022.decisions.v3_primary.adds_value).toBeNull();
  });

  it("accepts an arm without a candidate as null, never as a number", () => {
    const parsed = geoawareFollowupSchema.parse(compose((b) => { b.v2_selection.B1Z = null; }));
    expect(parsed.v2_selection.B1Z).toBeNull();
  });

  it("rejects a payload that is missing the test result or an interval level", () => {
    expect(() => geoawareFollowupSchema.parse(compose((b) => { delete (b as Record<string, unknown>).test_2022; }))).toThrow();
    expect(() => geoawareFollowupSchema.parse(compose((b) => { delete b.v2_selection.B0!.by_year["2021"].rmse_mm; }))).toThrow();
  });
});
