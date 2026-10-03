import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { R03_TASKS, R05_MODELS, confirmationResultSchema, r03ResultSchema, r05ResultSchema, reforecastOverviewSchema } from "./reforecast";

const PHASE15 = path.resolve(__dirname, "../../../../backend/app/evidence_data/phase15");
const read = (name: string) => JSON.parse(readFileSync(path.join(PHASE15, name), "utf8"));
const wrap = (payload: Record<string, unknown>) => ({ evidence_role: payload.evidence_role, evidence_label: payload.label, evidence_sha256: "a".repeat(64), protocol_sha256: payload.protocol_sha256, payload, caveats: ["x"] });

describe("reforecast study client schemas against the real tracked evidence", () => {
  it("accepts the frozen R05 result and keeps the honest findings", () => {
    const parsed = r05ResultSchema.parse(wrap(read("reforecast_r05_test.json")));
    for (const m of ["M0", "B0", "B1", "R_hard", "R_soft"]) expect(parsed.payload.pooled[m]).toBeDefined();
    expect(R05_MODELS).toContain("R_soft");
    expect(parsed.payload.bundle_decisions.B0.decision.BIAS_OK).toBe(false);
    expect(parsed.payload.bundle_decisions.B0.decision.tier).toBe("NONE");
    expect(parsed.payload.regime_decisions.R_soft.adds_value.adds_value).toBe(false);
    expect(parsed.payload.support.supported.very_heavy).toBe(true);
  });

  it("accepts the confirmatory result and keeps the corrected-bias and tier findings", () => {
    const parsed = confirmationResultSchema.parse(wrap(read("reforecast_r05_confirmation.json")));
    expect(parsed.payload.bundle_decision.decision.tier).toBe("FULL");
    expect(parsed.payload.pooled.B1_uncorrected.bias_mm).toBeGreaterThan(1.5);
    expect(Math.abs(parsed.payload.pooled.B1_shifted.bias_mm)).toBeLessThan(1.5);
    const bad = read("reforecast_r05_confirmation.json");
    delete bad.bundle_decision;
    expect(() => confirmationResultSchema.parse(wrap(bad))).toThrow();
  });

  it("accepts the frozen R03 result: every task has a tier and none is shown without cases", () => {
    const parsed = r03ResultSchema.parse(wrap(read("reforecast_r03_test.json")));
    for (const t of R03_TASKS) expect(parsed.payload.tasks[t].cases).toBeGreaterThan(0);
    expect(parsed.payload.tasks.WESTERN_DISTURBANCE.tier).toBe("USEFUL");
  });

  it("rejects a result without its bundle decisions and a task with an unknown shape", () => {
    const bad = read("reforecast_r05_test.json");
    delete bad.bundle_decisions;
    expect(() => r05ResultSchema.parse(wrap(bad))).toThrow();
    const r03 = read("reforecast_r03_test.json");
    r03.tasks.ACTIVE.validated = "yes";
    expect(() => r03ResultSchema.parse(wrap(r03))).toThrow();
  });

  it("accepts the overview built from the frozen files", () => {
    const protocol = read("reforecast_study_protocol_v1.json");
    const selection = read("reforecast_selection_freeze.json");
    const tasks = read("regime_tasks_selection_freeze.json");
    const unseal = read("reforecast_unseal_record.json");
    const { grid, ...r05 } = protocol.r05;
    const parsed = reforecastOverviewSchema.parse({
      protocol_sha256: "a".repeat(64), manifest_sha256: "b".repeat(64), purpose: protocol.purpose, populations: protocol.populations, data: {}, r05: { ...r05, grid_size: grid.size }, r03: protocol.r03,
      selection: { selection: selection.selection }, regime_tasks_selection: { tasks: tasks.tasks }, unseal_record: unseal, evidence_label: "x", caveats: ["x"],
    });
    expect(parsed.populations.sealed_test_years).toEqual([2014, 2015, 2016]);
    expect(parsed.r05.grid_size).toBe(24);
  });
});
