import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { ALL_INDIA_YEARS, allIndiaOverviewSchema, allIndiaResultSchema } from "./all-india-raw";

const PHASE14 = path.resolve(__dirname, "../../../../backend/app/evidence_data/phase14");
const read = (name: string) => JSON.parse(readFileSync(path.join(PHASE14, name), "utf8"));

const result = (year: number) => {
  const payload = read(`all_india_raw_${year}.json`);
  return { year, evidence_role: payload.evidence_role, evidence_label: payload.label, evidence_sha256: "a".repeat(64), protocol_sha256: payload.protocol_sha256, payload, caveats: ["x"] };
};

describe("all-India Raw verification client schemas against the real tracked evidence", () => {
  it.each([...ALL_INDIA_YEARS])("accepts the frozen result for %i and keeps the Raw-only label", (year) => {
    const parsed = allIndiaResultSchema.parse(result(year));
    expect(parsed.payload.forecast_nature).toContain("no model was applied");
    expect(parsed.payload.metrics.ALL_INDIA.cell_count).toBe(
      parsed.payload.metrics.INSIDE_MODEL_DOMAIN.cell_count + parsed.payload.metrics.NORTH_OF_DOMAIN.cell_count + parsed.payload.metrics.EAST_AND_NORTH_EAST.cell_count + parsed.payload.metrics.EAST_COAST_PENINSULA.cell_count + parsed.payload.metrics.SOUTH_OF_DOMAIN.cell_count,
    );
  });

  it("represents an unsupported region as a status and never as a number", () => {
    const parsed = allIndiaResultSchema.parse(result(2025));
    const south = parsed.payload.metrics.SOUTH_OF_DOMAIN.categorical.very_heavy;
    expect("status" in south && south.status === "insufficient_support").toBe(true);
  });

  it("rejects a result missing a region and a heavy block that lacks both a status and counts", () => {
    const missing = result(2024);
    delete (missing.payload.metrics as Record<string, unknown>).NORTH_OF_DOMAIN;
    expect(() => allIndiaResultSchema.parse(missing)).toThrow();
    const bad = result(2024);
    bad.payload.metrics.ALL_INDIA.categorical.heavy = { foo: 1 };
    expect(() => allIndiaResultSchema.parse(bad)).toThrow();
  });

  it("accepts the overview built from the frozen protocol", () => {
    const protocol = read("all_india_raw_protocol_v1.json");
    const parsed = allIndiaOverviewSchema.parse({
      protocol_sha256: "a".repeat(64), manifest_sha256: "b".repeat(64), ledger_sha256: "c".repeat(64), status: protocol.status, purpose: protocol.purpose, definition: protocol.definition,
      evaluation: protocol.evaluation, decision_rule: protocol.decision_rule, not_established: protocol.not_established_whatever_the_result,
      available: ALL_INDIA_YEARS.map((year) => ({ year, evidence_role: "r", evidence_label: "l", cases_scored: 1, development: year === 2024 })), caveats: ["x"],
    });
    expect(parsed.decision_rule.startsWith("none")).toBe(true);
    expect(parsed.definition.regions.cell_counts.INSIDE_MODEL_DOMAIN).toBe(2401);
  });
});
