import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { COASTAL_YEARS, coastalCasesSchema, coastalOverviewSchema, coastalResultSchema } from "./coastal-regime";

const PHASE12 = path.resolve(__dirname, "../../../../backend/app/evidence_data/phase12");
const read = (name: string) => JSON.parse(readFileSync(path.join(PHASE12, name), "utf8"));
const TRACK: Record<number, string> = { 2018: "A", 2019: "A", 2024: "B", 2025: "B" };

const result = (year: number) => {
  const payload = read(`coastal_regime_${TRACK[year]}_${year}.json`);
  return { track: TRACK[year], year, evidence_role: payload.evidence_role, evidence_label: payload.label, evidence_sha256: "a".repeat(64), protocol_sha256: payload.protocol_sha256, payload, caveats: ["x"] };
};

describe("coastal regime client schemas against the real tracked evidence", () => {
  it.each([...COASTAL_YEARS])("accepts the frozen result for %i and keeps the heuristic label", (year) => {
    const parsed = coastalResultSchema.parse(result(year));
    expect(parsed.payload.regime_nature).toContain("not a probability");
    expect(parsed.payload.groups.STRONG.cases + parsed.payload.groups.WEAK.cases + parsed.payload.groups.MODERATE.cases).toBe(parsed.payload.cases);
  });

  it("accepts the case table with classes and percentiles", () => {
    const cases = read("coastal_regime_cases_v1.json");
    const parsed = coastalCasesSchema.parse({ track: "B", year: 2025, evidence_label: "l", cases_file_sha256: "a".repeat(64), cut_points: cases.cut_points.B, cases: cases.populations.B2025, caveats: ["x"] });
    expect(parsed.cases).toHaveLength(232);
    expect(parsed.cases.every((c) => c.class !== null)).toBe(true);
  });

  it("rejects a class outside the three declared and a result without its groups", () => {
    const cases = read("coastal_regime_cases_v1.json");
    const bad = structuredClone(cases.populations.B2025);
    bad[0].class = "EXTREME";
    expect(() => coastalCasesSchema.parse({ track: "B", year: 2025, evidence_label: "l", cases_file_sha256: "a".repeat(64), cut_points: cases.cut_points.B, cases: bad, caveats: [] })).toThrow();
    const noGroups = result(2024);
    delete (noGroups.payload as Record<string, unknown>).groups;
    expect(() => coastalResultSchema.parse(noGroups)).toThrow();
  });

  it("accepts the overview built from the frozen protocol and manifest", () => {
    const protocol = read("coastal_regime_protocol_v1.json");
    const manifest = read("coastal_regime_manifest.json");
    const parsed = coastalOverviewSchema.parse({
      protocol_sha256: "a".repeat(64), manifest_sha256: "b".repeat(64), cases_file_sha256: "c".repeat(64), status: protocol.status, purpose: protocol.purpose, definition: protocol.definition,
      decision: manifest.decision, available: COASTAL_YEARS.map((year) => ({ track: TRACK[year], year, evidence_role: "r", evidence_label: "l", cases: 1, development: year === 2018 || year === 2024 })), caveats: ["x"],
    });
    expect(parsed.decision.discriminates).toBe(true);
    expect(parsed.definition.cut_points.A.training_year).toBe(2017);
  });
});
