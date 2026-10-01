import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { geoawareEvaluationSchema, geoawareOverviewSchema } from "./geoaware";

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
