import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { VALIDATION_YEARS, regimeValidationOverviewSchema, regimeValidationResultSchema } from "./regime-validation";

const PHASE6 = path.resolve(__dirname, "../../../../backend/app/evidence_data/phase6");
const read = (name: string) => JSON.parse(readFileSync(path.join(PHASE6, name), "utf8"));
const TRACK: Record<number, string> = { 2018: "A", 2019: "A", 2024: "B", 2025: "B" };

const result = (year: number) => {
  const payload = read(`regime_validation_${TRACK[year]}_${year}.json`);
  return { track: TRACK[year], year, evidence_role: payload.evidence_role, evidence_label: payload.label, evidence_sha256: "a".repeat(64), protocol_sha256: payload.protocol_sha256, payload, caveats: ["x"] };
};

describe("independent regime validation client schemas", () => {
  it.each([...VALIDATION_YEARS])("accepts the frozen result for %i", (year) => {
    const parsed = regimeValidationResultSchema.parse(result(year));
    expect(parsed.payload.depression).toContain("NOT VALIDATED");
    expect(parsed.payload.pseudo_label_agreement_is_separate).toBe(true);
  });

  it("keeps an unsupported task as a status with no score, and a scored task with its interval", () => {
    const unsupported = regimeValidationResultSchema.parse(result(2025));
    expect(unsupported.payload.tasks.active_vs_not_active.status).toBe("insufficient_support");
    expect("balanced_accuracy" in unsupported.payload.tasks.active_vs_not_active).toBe(false);
    const scored = regimeValidationResultSchema.parse(result(2019));
    const task = scored.payload.tasks.active_vs_not_active;
    expect(task.status).toBe("scored");
    if (task.status === "scored") expect(task.balanced_accuracy_bootstrap?.interval95).toHaveLength(2);
  });

  it("rejects a task that claims a score without the fields a scored task carries", () => {
    const bad = result(2019);
    delete (bad.payload.tasks.active_vs_not_active as Record<string, unknown>).hits;
    expect(() => regimeValidationResultSchema.parse(bad)).toThrow();
    const worse = result(2025);
    (worse.payload.tasks.active_vs_not_active as Record<string, unknown>).status = "maybe";
    expect(() => regimeValidationResultSchema.parse(worse)).toThrow();
  });

  it("accepts the overview built from the frozen protocol", () => {
    const protocol = read("regime_validation_protocol_v1.json");
    const clim = protocol.criteria.climatology;
    const parsed = regimeValidationOverviewSchema.parse({
      protocol_sha256: "a".repeat(64), manifest_sha256: "b".repeat(64), status: protocol.status, purpose: protocol.purpose,
      criteria: { ...protocol.criteria, climatology: { years: clim.years, files: Object.keys(clim.file_sha256).length, sigma_mm_per_day: clim.sigma_mm_per_day } },
      tasks: protocol.tasks, support_gate: protocol.support_gate, observation_only_counts: protocol.observation_only_counts, approval: protocol.approval,
      available: VALIDATION_YEARS.map((year) => ({ track: TRACK[year], year, evidence_role: "r", evidence_label: "l", cases_labelled: 1 })), caveats: ["x"],
    });
    expect(parsed.criteria.not_the_published_classification).toBe(true);
    expect(parsed.criteria.climatology.files).toBe(36);
  });
});
