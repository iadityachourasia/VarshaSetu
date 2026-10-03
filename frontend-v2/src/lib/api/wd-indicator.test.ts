import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { WD_YEARS, wdCasesSchema, wdOverviewSchema, wdResultSchema } from "./wd-indicator";

const PHASE13 = path.resolve(__dirname, "../../../../backend/app/evidence_data/phase13");
const read = (name: string) => JSON.parse(readFileSync(path.join(PHASE13, name), "utf8"));

const result = (year: number) => {
  const payload = read(`wd_indicator_${year}.json`);
  return { year, evidence_role: payload.evidence_role, evidence_label: payload.label, evidence_sha256: "a".repeat(64), protocol_sha256: payload.protocol_sha256, payload, caveats: ["x"] };
};

describe("western-disturbance indicator client schemas against the real tracked evidence", () => {
  it.each([...WD_YEARS])("accepts the frozen result for %i and keeps the heuristic label", (year) => {
    const parsed = wdResultSchema.parse(result(year));
    expect(parsed.payload.indicator_nature).toContain("not a validated detection");
    expect(parsed.payload.groups.flagged.cases + parsed.payload.groups.not_flagged.cases).toBe(parsed.payload.cases_scored);
  });

  it("accepts the case table with flags and indices", () => {
    const cases = read("wd_indicator_cases_v1.json");
    const parsed = wdCasesSchema.parse({ year: 2025, evidence_label: "l", cases_file_sha256: "a".repeat(64), threshold: cases.threshold, cases: cases.populations["2025"], caveats: ["x"] });
    expect(parsed.cases).toHaveLength(375);
    expect(parsed.cases.filter((c) => c.flag).length).toBe(81);
  });

  it("rejects a flag that is not a boolean and a result without its groups", () => {
    const cases = read("wd_indicator_cases_v1.json");
    const bad = structuredClone(cases.populations["2025"]);
    bad[0].flag = "yes";
    expect(() => wdCasesSchema.parse({ year: 2025, evidence_label: "l", cases_file_sha256: "a".repeat(64), threshold: cases.threshold, cases: bad, caveats: [] })).toThrow();
    const noGroups = result(2024);
    delete (noGroups.payload as Record<string, unknown>).groups;
    expect(() => wdResultSchema.parse(noGroups)).toThrow();
  });

  it("accepts the overview built from the frozen protocol and manifest and carries the negative decision", () => {
    const protocol = read("wd_indicator_protocol_v1.json");
    const manifest = read("wd_indicator_manifest.json");
    const parsed = wdOverviewSchema.parse({
      protocol_sha256: "a".repeat(64), manifest_sha256: "b".repeat(64), cases_file_sha256: "c".repeat(64), status: protocol.status, purpose: protocol.purpose, definition: protocol.definition,
      evaluation: protocol.evaluation, decision: manifest.decision, not_established: protocol.not_established_whatever_the_result,
      available: WD_YEARS.map((year) => ({ year, evidence_role: "r", evidence_label: "l", cases_scored: 1, development: year === 2021 || year === 2024 })), caveats: ["x"],
    });
    expect(parsed.decision.associated).toBe(false);
    expect(parsed.definition.training_year).toBe(2023);
  });
});
